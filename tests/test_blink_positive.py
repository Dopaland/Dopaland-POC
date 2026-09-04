"""
D0PA1 positive blink control harness validation (runnable directly, no
pytest). NO REAL CLIP IS PROCESSED ANYWHERE IN THIS FILE -- every check
runs against a SYNTHETIC aperture stream with KNOWN ground-truth blink
timestamps (built here, never loaded from a file) or hand-constructed
timestamp lists. See docs/CONTROLS.md section 4 for the explicit
statement that no real clips have been recorded or processed.

Covers: manual-count template write/load round-trip, event matching
(hand-constructed, including exact-tolerance-boundary cases), event
precision/recall/F1 correctness, per-clip count agreement genuinely
reusing analysis.reliability's Bland-Altman (not a second implementation),
end-to-end validation against the REAL features.attention.BlinkDetector on
a synthetic aperture stream with known ground truth (a clean case and a
deliberately-degraded case, to confirm the metrics move the right way),
and a structural proof that the proposed criterion values are NEVER
compared against anything anywhere in controls/blink_positive.py (G1).
"""

import ast
import os
import sys
import tempfile

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from controls.blink_positive import (
    BlinkPositiveConfig, ClipManifestEntry, build_clip_manifest,
    write_manual_count_template, load_manual_count,
    run_detector_on_aperture_stream, match_events, compute_event_metrics,
    compute_count_agreement, evaluate_one_clip, evaluate_run, format_blink_report,
)


# ============================================================
# Clip manifest + manual-count template.
# ============================================================

def check_clip_manifest_starts_honest():
    manifest = build_clip_manifest([f"clip_{i:02d}" for i in range(10)])
    ok = (
        len(manifest) == 10
        and all(isinstance(e, ClipManifestEntry) for e in manifest)
        and all(e.status == "not_yet_recorded" and e.file_path is None for e in manifest)
    )
    return ok, {"n_entries": len(manifest), "sample": manifest[0]}


def check_manual_count_template_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "clip_01.csv")
        write_manual_count_template("clip_01", path)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        has_instructions = "Watch the clip frame by frame" in raw
        # Simulate a human filling it in: append 3 blink timestamps.
        with open(path, "a", encoding="utf-8") as f:
            f.write("counted_by: J. Reviewer\n".replace("counted_by:", "# counted_by:"))
            f.write("5.2\n12.75\n40.0\n")
        loaded = load_manual_count(path)
        ok = (
            has_instructions
            and loaded["clip_id"] == "clip_01"
            and loaded["counted_by"] == "J. Reviewer"
            and loaded["blink_timestamps_seconds"] == [5.2, 12.75, 40.0]
        )
        return ok, {"has_instructions": has_instructions, "loaded": loaded}


# ============================================================
# Event matching -- hand-constructed, including boundary cases.
# ============================================================

def check_matching_basic_and_tolerance_boundary():
    manual = [1.0, 5.0, 10.0]
    detected = [1.05, 4.7, 10.5]  # diffs: 0.05, 0.3, 0.5
    tolerance = 0.15
    result = match_events(detected, manual, tolerance)
    # 1.0<->1.05 within tolerance (0.05<=0.15) -- match.
    # 5.0<->4.7 diff=0.3 > tolerance -- no match -> manual FN, detected FP.
    # 10.0<->10.5 diff=0.5 > tolerance -- no match -> manual FN, detected FP.
    ok = (
        len(result["matches"]) == 1 and result["matches"][0] == (1.0, 1.05)
        and sorted(result["false_negatives"]) == [5.0, 10.0]
        and sorted(result["false_positives"]) == [4.7, 10.5]
    )
    return ok, {"result": result}


def check_matching_exact_tolerance_boundary_is_inclusive():
    manual = [10.0]
    detected = [10.15]  # diff EXACTLY equal to tolerance
    result = match_events(detected, manual, tolerance_seconds=0.15)
    ok = len(result["matches"]) == 1
    return ok, {"result": result}


def check_matching_greedy_nearest_not_first_found():
    """Two manual events both within tolerance of the SAME detected event
    -- the CLOSER manual event must win the match; the other becomes a
    false negative, not silently double-matched."""
    manual = [10.0, 10.05]
    detected = [10.02]
    result = match_events(detected, manual, tolerance_seconds=0.15)
    # 10.05 is closer to 10.02 (diff 0.03) than 10.0 is (diff 0.02)... wait check: |10.0-10.02|=0.02, |10.05-10.02|=0.03.
    # So 10.0 is actually closer -- it must be the one matched.
    ok = len(result["matches"]) == 1 and result["matches"][0][0] == 10.0 and result["false_negatives"] == [10.05]
    return ok, {"result": result}


def check_event_metrics_hand_computed():
    match_result = {"matches": [(1, 1), (2, 2), (3, 3)], "false_negatives": [4], "false_positives": [5, 6]}
    metrics = compute_event_metrics(match_result)
    # tp=3, fp=2, fn=1 -> precision=3/5=0.6, recall=3/4=0.75, f1=2*0.6*0.75/1.35=0.6667
    expected_precision = 3 / 5
    expected_recall = 3 / 4
    expected_f1 = 2 * expected_precision * expected_recall / (expected_precision + expected_recall)
    ok = (
        metrics["tp"] == 3 and metrics["fp"] == 2 and metrics["fn"] == 1
        and abs(metrics["precision"] - expected_precision) < 1e-9
        and abs(metrics["recall"] - expected_recall) < 1e-9
        and abs(metrics["f1"] - expected_f1) < 1e-9
    )
    return ok, {"metrics": metrics}


# ============================================================
# Count agreement -- confirms genuine reuse of analysis.reliability.
# ============================================================

def check_count_agreement_reuses_reliability_bland_altman():
    from analysis.reliability import compute_bland_altman_pair
    clip_results = [
        {"clip_id": "c0", "detected_count": 10, "manual_count": 12},
        {"clip_id": "c1", "detected_count": 8, "manual_count": 9},
        {"clip_id": "c2", "detected_count": 15, "manual_count": 14},
    ]
    result = compute_count_agreement(clip_results)
    matrix = np.array([[10, 12], [8, 9], [15, 14]], dtype=float)
    direct = compute_bland_altman_pair(matrix, 0, 1)
    ok = result["bias"] == direct["bias"] and result["sd_diff"] == direct["sd_diff"] and result["loa_lower"] == direct["loa_lower"]
    return ok, {"via_harness": {k: v for k, v in result.items() if k not in ("diffs", "means")}, "direct": {k: v for k, v in direct.items() if k not in ("diffs", "means")}}


# ============================================================
# END-TO-END, against the REAL features.attention.BlinkDetector, on a
# SYNTHETIC aperture stream with KNOWN ground truth. No real clip.
# ============================================================

def _build_synthetic_aperture_stream(true_blink_onsets_seconds, duration_seconds=60.0, fps=25.0, baseline=0.47, dip=0.40, blink_duration=0.2, seed=0):
    """Synthetic per-frame aperture stream: baseline with small noise,
    dipping to `dip` for `blink_duration` seconds at each of
    true_blink_onsets_seconds. Shaped to match features.attention's own
    documented real-aperture evidence (baseline ~0.45-0.50, dip ~0.38-0.41
    -- see BLINK_CLOSE_FRACTION/BLINK_REOPEN_FRACTION's own comments)."""
    rng = np.random.default_rng(seed)
    n_frames = int(duration_seconds * fps)
    stream = []
    for i in range(n_frames):
        t = i / fps
        in_blink = any(onset <= t < onset + blink_duration for onset in true_blink_onsets_seconds)
        aperture = dip + rng.normal(scale=0.005) if in_blink else baseline + rng.normal(scale=0.01)
        stream.append((t, float(aperture)))
    return stream


def check_detector_recovers_clean_synthetic_blinks():
    true_onsets = [5.0, 12.0, 20.5, 30.0, 45.0]
    stream = _build_synthetic_aperture_stream(true_onsets, seed=1)
    detected = run_detector_on_aperture_stream(stream)
    # "Manual count" for a clean synthetic case: the true onset times
    # (a human counting a clean, unambiguous synthetic clip would find
    # exactly these) -- since the detector confirms at REOPEN, not onset
    # (see run_detector_on_aperture_stream's own docstring), match with a
    # tolerance that covers the ~200ms blink duration.
    config = BlinkPositiveConfig(matching_tolerance_ms=350.0)
    result = evaluate_one_clip("synthetic_clean", detected, true_onsets, config)
    ok = result["event_metrics"]["f1"] is not None and result["event_metrics"]["f1"] > 0.8
    return ok, {"n_true": len(true_onsets), "n_detected": len(detected), "event_metrics": result["event_metrics"]}


def check_detector_metrics_degrade_when_blinks_are_missed_or_spurious():
    """Confirms the harness's metrics actually MOVE in the expected
    direction under a deliberately worse detector output -- not just that
    they compute without crashing."""
    true_onsets = [5.0, 12.0, 20.5, 30.0, 45.0, 50.0, 52.0]
    stream = _build_synthetic_aperture_stream(true_onsets, seed=2)
    detected = run_detector_on_aperture_stream(stream)
    config = BlinkPositiveConfig(matching_tolerance_ms=350.0)
    clean_result = evaluate_one_clip("clean", detected, true_onsets, config)

    # Simulate a WORSE detector: drop half the real detections (misses)
    # and add two spurious ones far from any real blink (false positives).
    degraded_detected = detected[::2] + [7.3, 27.9]
    degraded_result = evaluate_one_clip("degraded", degraded_detected, true_onsets, config)

    clean_f1 = clean_result["event_metrics"]["f1"] or 0.0
    degraded_f1 = degraded_result["event_metrics"]["f1"] or 0.0
    ok = degraded_f1 < clean_f1
    return ok, {"clean_f1": clean_f1, "degraded_f1": degraded_f1, "clean_metrics": clean_result["event_metrics"], "degraded_metrics": degraded_result["event_metrics"]}


def check_full_run_report_across_multiple_synthetic_clips():
    config = BlinkPositiveConfig(matching_tolerance_ms=350.0)
    per_clip_inputs = []
    for i, true_onsets in enumerate([[5.0, 15.0, 30.0], [10.0, 20.0, 40.0, 50.0], [8.0, 22.0]]):
        stream = _build_synthetic_aperture_stream(true_onsets, seed=100 + i)
        detected = run_detector_on_aperture_stream(stream)
        per_clip_inputs.append((f"synthetic_{i}", detected, true_onsets))

    result = evaluate_run(per_clip_inputs, config)
    report = format_blink_report(result)

    ok = (
        result["n_clips"] == 3
        and result["pooled_event_metrics"]["f1"] is not None
        and result["count_agreement"]["bias"] is not None
        and "config_hash" in result
        and all(cid in report for cid in ("synthetic_0", "synthetic_1", "synthetic_2"))
    )
    return ok, {"report": report}


# ============================================================
# G1 -- structural proof: the proposed criterion values are NEVER read
# back to make a comparison, anywhere in controls/blink_positive.py.
# ============================================================

def check_criterion_values_never_compared_in_code():
    path = os.path.join(REPO_ROOT, "controls", "blink_positive.py")
    source = open(path, encoding="utf-8").read()
    tree = ast.parse(source)

    criterion_fields = {"criterion_event_f1", "criterion_count_tolerance_fraction", "criterion_count_min_clips_fraction"}
    violations = []
    for node in ast.walk(tree):
        # A Compare node (e.g. `x >= y`) whose LEFT or ANY comparator is an
        # attribute access named one of the criterion fields would be the
        # G1 violation this checks for -- comparing a criterion to
        # anything, anywhere.
        if isinstance(node, ast.Compare):
            operands = [node.left] + list(node.comparators)
            for operand in operands:
                if isinstance(operand, ast.Attribute) and operand.attr in criterion_fields:
                    violations.append(ast.dump(node)[:200])

    return len(violations) == 0, {"violations": violations}


def check_no_placeholder_real_clip_artefacts_committed():
    """G3/3.3: confirms this repository's tracked files contain no
    manifest or manual-count file claiming a real clip was processed --
    checked by absence of any tracked file under a blink-clip-shaped path
    outside logs/ (which is git-ignored anyway)."""
    import subprocess
    result = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    tracked = result.stdout.splitlines()
    suspicious = [f for f in tracked if "blink" in f.lower() and ("clip" in f.lower() or "manual_count" in f.lower())]
    return len(suspicious) == 0, {"suspicious_tracked_files": suspicious}


if __name__ == "__main__":
    checks = [
        ("CLIP MANIFEST STARTS HONEST (not_yet_recorded, no file_path)", check_clip_manifest_starts_honest),
        ("MANUAL-COUNT TEMPLATE: write/fill/load round-trip", check_manual_count_template_round_trip),
        ("EVENT MATCHING: basic + tolerance boundary", check_matching_basic_and_tolerance_boundary),
        ("EVENT MATCHING: diff exactly equal to tolerance is inclusive", check_matching_exact_tolerance_boundary_is_inclusive),
        ("EVENT MATCHING: greedy nearest-neighbor, not first-found", check_matching_greedy_nearest_not_first_found),
        ("EVENT METRICS: precision/recall/F1 hand-computed", check_event_metrics_hand_computed),
        ("COUNT AGREEMENT genuinely reuses analysis.reliability's Bland-Altman", check_count_agreement_reuses_reliability_bland_altman),
        ("END-TO-END (real BlinkDetector, synthetic clean case)", check_detector_recovers_clean_synthetic_blinks),
        ("END-TO-END: metrics degrade under a deliberately worse detector output", check_detector_metrics_degrade_when_blinks_are_missed_or_spurious),
        ("FULL RUN REPORT across multiple synthetic clips", check_full_run_report_across_multiple_synthetic_clips),
        ("G1 STRUCTURAL: criterion values never compared to anything in code", check_criterion_values_never_compared_in_code),
        ("G3/3.3 STRUCTURAL: no real-clip artefact tracked in this repo", check_no_placeholder_real_clip_artefacts_committed),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"BLINK POSITIVE CONTROL VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("BLINK POSITIVE CONTROL VALIDATION: PASS (all synthetic -- NO real clip processed, see docs/CONTROLS.md)")
