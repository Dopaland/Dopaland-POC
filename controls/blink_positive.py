"""
D0PA1 control -- POSITIVE BLINK CONTROL HARNESS.

Compares features.attention.BlinkDetector's output against a manual,
frame-by-frame blink count over N one-minute clips. G1: this harness
computes and reports numbers (event precision/recall/F1, per-clip count
Bland-Altman). It NEVER compares a computed value to a criterion and
NEVER returns a pass/fail -- see BlinkPositiveConfig's own docstring for
where the client-accepted criterion values (D0PA1_Client_SignOff_001.md
§3) live and why they are never read back by any function in this file.

3.4 -- SCOPE LIMIT, stated here and repeated in docs/CONTROLS.md: this
validates blink-count DETECTION only. It establishes no psychological
interpretation of blinking (fatigue, attention, affect, anything else). A
detector that reliably counts blinks the way a human would is a
DETECTION-validation result; it is not, and is never presented as,
construct validation of what blinking MEANS.

3.3 -- THE CLIPS DO NOT EXIST YET. Every function below is exercised in
tests/test_blink_positive.py against SYNTHETIC aperture streams with
KNOWN ground-truth blink timestamps -- never a real clip. No placeholder
"result" for a real clip is generated anywhere in this file or committed
to this repository. See docs/CONTROLS.md section 4 for the explicit
statement that no real clips have been processed.

REUSES, not reimplemented:
  - features.attention.BlinkDetector -- the actual detector under test,
    imported and run unmodified (G5: this harness observes it, never
    patches its thresholds).
  - analysis.reliability.compute_bland_altman_pair /
    plot_bland_altman_svg -- per-clip count agreement (3.1's "Bland-Altman
    on the paired counts") is built by treating "detected count" and
    "manual count" as two columns of a (n_clips, 2) matrix and calling the
    SAME Bland-Altman function analysis/reliability.py already has and
    tests, rather than a third implementation of limits-of-agreement math.
"""

import csv
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import numpy as np

from features.attention import BlinkDetector
from analysis.reliability import compute_bland_altman_pair, plot_bland_altman_svg


# ============================================================
# 3.2 -- matching tolerance and pass criterion, PARAMETERS, not literals.
#
# G1, restated precisely for this file: `matching_tolerance_ms` IS used by
# match_events() below -- it is a genuine ALGORITHM PARAMETER (how close
# in time two events must be to count as the same blink), not a verdict.
# `criterion_event_f1` / `criterion_count_tolerance_fraction` /
# `criterion_count_min_clips_fraction` are DIFFERENT: they are the
# pass criterion values, stored here ONLY so they travel with
# every report as pre-registered, hashed numbers a human can read
# alongside the computed metrics. NO function in this file reads them
# back to make a comparison -- grep this file: there is no
# `config.criterion_event_f1` reference anywhere outside this dataclass's
# own definition and its config_hash(). Wiring them in as defaults is
# this task's explicit instruction; comparing them to anything is not.
#
# ACCEPTED by the client, `D0PA1_Client_SignOff_001.md` §3 (2026-09-18) --
# no value below changed at signature; the values proposed here were
# accepted exactly as stored. Frozen from that date: not revisable in
# light of results (§7 of that record).
# ============================================================

@dataclass(frozen=True)
class BlinkPositiveConfig:
    matching_tolerance_ms: float = 150.0

    # ACCEPTED criterion values (D0PA1_Client_SignOff_001.md §3) -- stored,
    # hashed, NEVER compared against anything by any function in this
    # module (G1: a human applies these after collection).
    criterion_event_f1: float = 0.80
    criterion_count_tolerance_fraction: float = 0.20
    criterion_count_min_clips_fraction: float = 0.80  # "at least 8 of 10 clips"

    def matching_tolerance_seconds(self):
        return self.matching_tolerance_ms / 1000.0

    def config_hash(self):
        import hashlib
        import json
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


# ============================================================
# 3.1a -- clip manifest structure.
# ============================================================

@dataclass
class ClipManifestEntry:
    """One one-minute clip. `file_path` and `status` reflect reality --
    see the module docstring: no real clip exists yet, so every entry a
    caller constructs today has status="not_yet_recorded" and
    file_path=None."""

    clip_id: str
    status: str = "not_yet_recorded"  # "not_yet_recorded" | "recorded" | "manually_counted" | "detector_run"
    file_path: str = None
    expected_duration_seconds: float = 60.0
    notes: str = ""


VALID_CLIP_STATUSES = ("not_yet_recorded", "recorded", "manually_counted", "detector_run")


def build_clip_manifest(clip_ids):
    """clip_ids: iterable of strings. Returns a list[ClipManifestEntry],
    every one status="not_yet_recorded" -- the honest starting state."""
    return [ClipManifestEntry(clip_id=cid) for cid in clip_ids]


# ============================================================
# 3.1b -- manual-count entry format, a human can fill in without touching
# code: one plain CSV per clip, one blink timestamp (seconds from clip
# start) per row. write_manual_count_template() produces a ready-to-fill
# file with instructions as a comment header; load_manual_count() reads
# it back.
# ============================================================

MANUAL_COUNT_TEMPLATE_HEADER = (
    "# Manual blink count for clip: {clip_id}\n"
    "# Watch the clip frame by frame. For EVERY blink you see, add one line\n"
    "# below with the approximate time (in seconds, decimals allowed) from\n"
    "# the start of the clip that the eye closes. One blink per line.\n"
    "# Do not edit the header lines (starting with #). Save and close when done.\n"
    "# counted_by: <your name or initials>\n"
    "blink_timestamp_seconds\n"
)


def write_manual_count_template(clip_id, path):
    """Writes a ready-to-fill CSV template. A human opens this in any text
    editor or spreadsheet program, adds one row per blink they observe,
    and saves it -- no code editing required."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(MANUAL_COUNT_TEMPLATE_HEADER.format(clip_id=clip_id))
    return path


def load_manual_count(path):
    """Reads a filled-in template back. Returns {"clip_id", "counted_by",
    "blink_timestamps_seconds": sorted list of float}. Lines starting with
    '#' (including a filled-in 'counted_by:' line) are metadata, not data
    -- parsed out, not fed to the matcher as a timestamp."""
    clip_id = None
    counted_by = None
    timestamps = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if line.startswith("# Manual blink count for clip:"):
                    clip_id = line.split(":", 1)[1].strip()
                elif line.startswith("# counted_by:"):
                    val = line.split(":", 1)[1].strip()
                    counted_by = val if val and not val.startswith("<") else None
                continue
            if line == "blink_timestamp_seconds":
                continue  # header row
            timestamps.append(float(line))
    return {"clip_id": clip_id, "counted_by": counted_by, "blink_timestamps_seconds": sorted(timestamps)}


# ============================================================
# Running the REAL detector (features.attention.BlinkDetector, reused
# unmodified) over an aperture stream -> a list of confirmed-blink
# timestamps.
# ============================================================

def run_detector_on_aperture_stream(aperture_stream):
    """aperture_stream: list of (timestamp_seconds, aperture_or_None)
    pairs, in chronological order (aperture_or_None mirrors a real
    per-frame reading -- None on a frame with no face/occluded eye,
    exactly what BlinkDetector.update() already expects). Returns a
    sorted list of confirmed-blink timestamps (the `now` value passed to
    update() at the exact call where it returned True -- i.e. the
    REOPEN-confirmation moment, not the closure onset; stated explicitly
    since it is a real methodological choice that affects how a ~150ms
    tolerance should be read)."""
    detector = BlinkDetector()
    confirmed = []
    for ts, aperture in aperture_stream:
        if detector.update(aperture, ts):
            confirmed.append(ts)
    return confirmed


# ============================================================
# 3.1c -- event-matching routine, CONFIGURABLE tolerance.
# ============================================================

def match_events(detected_timestamps, manual_timestamps, tolerance_seconds):
    """Greedy nearest-neighbor matching, globally sorted by absolute time
    difference (not index order) -- a manual event and a detected event
    within `tolerance_seconds` of each other, and not already matched to
    something closer, are paired. Returns
    {"matches": [(manual_ts, detected_ts), ...], "false_negatives":
    [unmatched manual timestamps], "false_positives": [unmatched detected
    timestamps]}.

    Manual counts are ground truth (this is a POSITIVE control against a
    human count, not a comparison between two peers): an unmatched manual
    event is a false negative (detector missed a real blink); an
    unmatched detected event is a false positive (detector saw a blink
    that wasn't there)."""
    # A tiny epsilon absorbs binary floating-point representation error
    # (e.g. abs(10.15 - 10.0) == 0.15000000000000036, not exactly 0.15) --
    # this is NOT a second, hidden tolerance value: it exists only so a
    # timestamp difference a human would call "exactly at the tolerance"
    # is not excluded purely because of how 0.15 happens to round in
    # binary. tolerance_seconds itself is still the one real parameter.
    boundary_epsilon = 1e-9
    candidates = []
    for mi, mt in enumerate(manual_timestamps):
        for di, dt in enumerate(detected_timestamps):
            diff = abs(mt - dt)
            if diff <= tolerance_seconds + boundary_epsilon:
                candidates.append((diff, mi, di))
    candidates.sort(key=lambda c: c[0])

    matched_manual = set()
    matched_detected = set()
    matches = []
    for diff, mi, di in candidates:
        if mi in matched_manual or di in matched_detected:
            continue
        matched_manual.add(mi)
        matched_detected.add(di)
        matches.append((manual_timestamps[mi], detected_timestamps[di]))

    false_negatives = [manual_timestamps[mi] for mi in range(len(manual_timestamps)) if mi not in matched_manual]
    false_positives = [detected_timestamps[di] for di in range(len(detected_timestamps)) if di not in matched_detected]
    return {"matches": matches, "false_negatives": false_negatives, "false_positives": false_positives}


def compute_event_metrics(match_result):
    """event precision/recall/F1 from a match_events() result. Returns
    numbers; sets nothing, decides nothing."""
    tp = len(match_result["matches"])
    fp = len(match_result["false_positives"])
    fn = len(match_result["false_negatives"])
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    f1 = (2 * precision * recall / (precision + recall)) if (precision is not None and recall is not None and (precision + recall) > 0) else None
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


# ============================================================
# 3.1d -- per-clip count agreement, Bland-Altman -- REUSES
# analysis.reliability directly.
# ============================================================

def compute_count_agreement(clip_results):
    """clip_results: list of {"clip_id", "detected_count", "manual_count"}.
    Builds a (n_clips, 2) matrix ["detected", "manual"] and reuses
    analysis.reliability.compute_bland_altman_pair -- the SAME function
    analysis/reliability.py's own tests already validate, not a second
    implementation of bias/limits-of-agreement math."""
    matrix = np.array([[r["detected_count"], r["manual_count"]] for r in clip_results], dtype=float)
    return compute_bland_altman_pair(matrix, 0, 1)


# ============================================================
# One-clip and full-run report assembly.
# ============================================================

def evaluate_one_clip(clip_id, detected_timestamps, manual_timestamps, config: BlinkPositiveConfig):
    match_result = match_events(detected_timestamps, manual_timestamps, config.matching_tolerance_seconds())
    event_metrics = compute_event_metrics(match_result)
    return {
        "clip_id": clip_id,
        "detected_count": len(detected_timestamps),
        "manual_count": len(manual_timestamps),
        "event_metrics": event_metrics,
        "match_result": match_result,
    }


def evaluate_run(per_clip_inputs, config=None):
    """per_clip_inputs: list of (clip_id, detected_timestamps, manual_timestamps).
    Returns per-clip results, pooled event precision/recall/F1 (TP/FP/FN
    summed across all clips, then one set of ratios -- never a mean-of-
    ratios, which would weight a 1-blink clip the same as a 30-blink one),
    and the count-agreement Bland-Altman result. NO field in the return
    value is a boolean or a label -- config_hash travels with the report
    so the tolerance that produced it is always inspectable."""
    if config is None:
        config = BlinkPositiveConfig()

    per_clip = [evaluate_one_clip(cid, det, man, config) for cid, det, man in per_clip_inputs]

    pooled_tp = sum(c["event_metrics"]["tp"] for c in per_clip)
    pooled_fp = sum(c["event_metrics"]["fp"] for c in per_clip)
    pooled_fn = sum(c["event_metrics"]["fn"] for c in per_clip)
    pooled_precision = pooled_tp / (pooled_tp + pooled_fp) if (pooled_tp + pooled_fp) > 0 else None
    pooled_recall = pooled_tp / (pooled_tp + pooled_fn) if (pooled_tp + pooled_fn) > 0 else None
    pooled_f1 = (
        (2 * pooled_precision * pooled_recall / (pooled_precision + pooled_recall))
        if (pooled_precision is not None and pooled_recall is not None and (pooled_precision + pooled_recall) > 0)
        else None
    )

    count_agreement = compute_count_agreement([{"clip_id": c["clip_id"], "detected_count": c["detected_count"], "manual_count": c["manual_count"]} for c in per_clip])

    return {
        "per_clip": per_clip,
        "pooled_event_metrics": {"tp": pooled_tp, "fp": pooled_fp, "fn": pooled_fn, "precision": pooled_precision, "recall": pooled_recall, "f1": pooled_f1},
        "count_agreement": count_agreement,
        "config_hash": config.config_hash(),
        "n_clips": len(per_clip),
    }


def format_blink_report(result):
    """No verdict, no highlighting -- a human reads the numbers next to
    the config_hash-pinned criterion values, which this function does NOT
    print as a comparison, only the raw computed numbers."""
    lines = []
    header = f"{'clip_id':16s} {'detected':>9s} {'manual':>7s} {'tp':>4s} {'fp':>4s} {'fn':>4s} {'precision':>10s} {'recall':>8s} {'f1':>7s}"
    lines.append(header)
    lines.append("-" * len(header))
    for c in result["per_clip"]:
        m = c["event_metrics"]
        p = f"{m['precision']:.3f}" if m["precision"] is not None else "n/a"
        r = f"{m['recall']:.3f}" if m["recall"] is not None else "n/a"
        f1 = f"{m['f1']:.3f}" if m["f1"] is not None else "n/a"
        lines.append(f"{c['clip_id']:16s} {c['detected_count']:>9d} {c['manual_count']:>7d} {m['tp']:>4d} {m['fp']:>4d} {m['fn']:>4d} {p:>10s} {r:>8s} {f1:>7s}")
    lines.append("")
    pm = result["pooled_event_metrics"]
    lines.append(f"POOLED (across {result['n_clips']} clips): tp={pm['tp']} fp={pm['fp']} fn={pm['fn']} precision={pm['precision']} recall={pm['recall']} f1={pm['f1']}")
    ba = result["count_agreement"]
    lines.append(f"COUNT AGREEMENT (Bland-Altman, detected - manual): bias={ba['bias']} sd_diff={ba['sd_diff']} loa=[{ba['loa_lower']}, {ba['loa_upper']}]")
    lines.append(f"config_hash={result['config_hash']}")
    return "\n".join(lines)
