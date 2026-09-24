"""
D0PA1 control -- BLINK DETECTOR RUNNER over real clips (§19 row 15).

The one committed command that runs the blink detector on a real video
clip, so the result a report cites can be re-produced by someone else from
the repository (D4), not from a scratchpad driver. For each clip:

  1. analyze_video.analyze_video(clip)        -- the same function the CLI calls
  2. analyze_video.aperture_stream_as_tuples() -- the committed converter
  3. controls.blink_positive.run_detector_on_aperture_stream()
  4. write the detector output, with provenance, OUTSIDE the repository

G1 -- THIS FILE COMPUTES AND STORES. NOTHING ELSE. It never reads a manual
count file, never matches events, never computes any agreement metric, and
never emits a verdict. That is a separate, later reporting step, and the
frozen criterion is applied by a human. tests/test_run_blink_detector.py
enforces this by AST, not by convention.

BLIND-COUNT PROTECTION: the detector's output is written to disk only. This
script never prints the detected timestamps or how many there are -- manual
counts may still be in progress when it runs, and a counter who has seen
the detector's answer cannot produce an independent one.

Deliberately calls analyze_video.analyze_video(), NOT the CLI's
_analyze_and_report(): the latter appends a stub agent exchange to
logs/agent_log.jsonl, which is noise in this control's execution record.

G5: analyze_video.py, controls/blink_positive.py and every features/ module
are imported and called, never modified.

G4: this script handles paths and numbers only. Output location comes from
D0PA1_VIDEO_RAW_STORAGE_LOCATION (privacy/video_storage_config.py -- raises
if unset, no fallback) and is REFUSED if it resolves inside the repository.

Timestamp semantics, stated so a later reader cannot miss them: the
detected timestamps are BlinkDetector's REOPEN-confirmation moments, not
closure onsets (see run_detector_on_aperture_stream's own docstring and
docs/CONTROLS.md). Recorded in every output file as `timestamp_semantics`.

USAGE:
    python controls/run_blink_detector.py <clip.mp4 | folder> \
        [--subject-id P01] [--context-id ...] [--device-id ...]
"""

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import analyze_video
from controls.blink_positive import BlinkPositiveConfig, run_detector_on_aperture_stream
from privacy.video_storage_config import VIDEO_STORAGE_LOCATION_ENV_VAR, resolve_video_storage_config
from simulation.provenance import capture_run_provenance

OUTPUT_SCHEMA_VERSION = "1.0"
RECORD_TYPE = "blink_detector_output"
OUTPUT_SUBDIR = "detector_output"

# <subject>_clip<nn>, e.g. P01_clip01 -> P01. The CLIP_LOG.txt naming
# convention. Anything else is "not unambiguous" and needs --subject-id.
CLIP_FILENAME_PATTERN = re.compile(r"^(P\d+)_clip\d+$")

TIMESTAMP_SEMANTICS = (
    "reopen_confirmation -- BlinkDetector.update() returned True at this "
    "timestamp; NOT the closure onset (see "
    "controls.blink_positive.run_detector_on_aperture_stream docstring)"
)

# Source files whose exact content determines this output, hashed per run.
CODE_PATH_FILES = (
    "controls/run_blink_detector.py",
    "controls/blink_positive.py",
    "analyze_video.py",
    "features/attention.py",
    "privacy/video_storage_config.py",
)


class SubjectIdError(ValueError):
    """Raised when a clip's subject_id cannot be established unambiguously."""


class OutputLocationError(RuntimeError):
    """Raised when the output location would fall inside the repository."""


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_inside(path, root):
    path = os.path.normcase(os.path.realpath(path))
    root = os.path.normcase(os.path.realpath(root))
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:  # different drives on Windows
        return False


def resolve_output_root():
    """<D0PA1_VIDEO_RAW_STORAGE_LOCATION>/detector_output. Raises (via
    resolve_video_storage_config) if the variable is unset, and raises
    OutputLocationError if the result is inside the repository -- enforced
    here, not merely defaulted."""
    storage = resolve_video_storage_config()
    out_root = os.path.join(storage.storage_location, OUTPUT_SUBDIR)
    if _is_inside(out_root, REPO_ROOT):
        raise OutputLocationError(
            f"Refusing to write detector output inside the repository: {out_root} "
            f"resolves under {REPO_ROOT}. Point {VIDEO_STORAGE_LOCATION_ENV_VAR} at a "
            "folder OUTSIDE the repository (D0PA1_Client_SignOff_001.md §5.2)."
        )
    return out_root, storage


def clip_id_from_path(clip_path):
    return os.path.splitext(os.path.basename(clip_path))[0]


def resolve_subject_id(clip_path, subject_id_arg=None):
    """Returns (subject_id, source). Filename is parsed first; an explicit
    argument must agree with it when both exist. Never defaults."""
    clip_id = clip_id_from_path(clip_path)
    m = CLIP_FILENAME_PATTERN.match(clip_id)
    from_name = m.group(1) if m else None
    arg = subject_id_arg.strip() if subject_id_arg is not None else None
    if arg == "":
        raise SubjectIdError("--subject-id was given but is blank.")

    if from_name and arg:
        if from_name != arg:
            raise SubjectIdError(
                f"subject_id conflict for {clip_id!r}: filename says {from_name!r}, "
                f"--subject-id says {arg!r}. Resolve which is correct before running."
            )
        return arg, "filename_and_argument"
    if from_name:
        return from_name, "filename"
    if arg:
        return arg, "argument"
    raise SubjectIdError(
        f"No subject_id for {clip_id!r}: the filename does not match "
        f"{CLIP_FILENAME_PATTERN.pattern!r} and no --subject-id was given. "
        "Refusing to guess (hard constraint 7)."
    )


def collect_clips(target):
    """A single clip path -> [path]; a folder -> its video files in sorted
    filename order (analyze_video's own scanner, deterministic)."""
    if os.path.isdir(target):
        clips = analyze_video._scan_video_folder(target)
        if not clips:
            raise FileNotFoundError(f"No video files found in folder {target}")
        return clips
    if os.path.isfile(target):
        return [target]
    raise FileNotFoundError(f"Clip or folder not found: {target}")


def _code_versions():
    import cv2
    import mediapipe
    import numpy
    files = {}
    for rel in CODE_PATH_FILES:
        try:
            files[rel] = _sha256_file(os.path.join(REPO_ROOT, *rel.split("/")))
        except OSError as e:
            files[rel] = f"UNREADABLE: {e}"
    return {
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "analyze_video_schema_version": analyze_video.SCHEMA_VERSION,
        "code_sha256": files,
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "opencv": cv2.__version__,
        "mediapipe": mediapipe.__version__,
    }


def _optional_id(value, name):
    """context_id / device_id: always present in the record. Missing is a
    value with a reason, never an absent key (hard constraints 7 and 8)."""
    if value is not None and value.strip():
        return {name: value.strip(), f"{name}_missingness_reason": None}
    return {name: None, f"{name}_missingness_reason": "not_provided_to_runner"}


def run_clip(clip_path, subject_id, subject_id_source, run_context, _analyze_fn=None):
    """Runs one clip and returns its output record (not yet written).
    _analyze_fn exists only so tests can substitute analyze_video without
    loading MediaPipe; production always uses analyze_video.analyze_video."""
    analyze_fn = _analyze_fn or analyze_video.analyze_video
    started = datetime.now(timezone.utc)
    result = analyze_fn(clip_path)
    finished_analysis = datetime.now(timezone.utc)

    if result is None:
        analysis = {"status": "could_not_open", "mode": None, "failure_code": "could_not_open",
                    "video_fps_used": None, "video_duration_sec": None}
        stream = []
    else:
        analysis = {k: result.get(k) for k in ("status", "mode", "failure_code", "video_fps_used", "video_duration_sec")}
        stream = result.get("aperture_stream") or []

    n_frames = len(stream)
    n_present = sum(1 for s in stream if s.get("aperture") is not None)
    missingness = {
        "frames_total": n_frames,
        "frames_aperture_present": n_present,
        "frames_aperture_none": n_frames - n_present,
        "aperture_present_fraction": (n_present / n_frames) if n_frames else None,
        "aperture_present_fraction_missingness_reason": None if n_frames else "zero_frames_in_stream",
    }

    if n_frames:
        detected = run_detector_on_aperture_stream(analyze_video.aperture_stream_as_tuples(stream))
        detector = {"ran": True, "detected_blink_timestamps_seconds": list(detected),
                    "missingness_reason": None}
    else:
        detector = {"ran": False, "detected_blink_timestamps_seconds": None,
                    "missingness_reason": "empty_aperture_stream"}
    detector["timestamp_semantics"] = TIMESTAMP_SEMANTICS

    record = {
        "record_type": RECORD_TYPE,
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "experiment_id": run_context["provenance"]["experiment_id"],
        "clip_filename": os.path.basename(clip_path),
        "clip_id": clip_id_from_path(clip_path),
        "clip_sha256": _sha256_file(clip_path),
        "clip_size_bytes": os.path.getsize(clip_path),
        "subject_id": subject_id,
        "subject_id_source": subject_id_source,
        **_optional_id(run_context["context_id"], "context_id"),
        **_optional_id(run_context["device_id"], "device_id"),
        "started_at_utc": started.isoformat(),
        "analysis_finished_at_utc": finished_analysis.isoformat(),
        "analysis": analysis,
        "missingness": missingness,
        "detector": detector,
        "aperture_stream": stream,
        "provenance": run_context["provenance"],
        "config_hashes": run_context["config_hashes"],
        "code_versions": run_context["code_versions"],
    }
    return record


def run(target, subject_id_arg=None, context_id=None, device_id=None, _analyze_fn=None):
    """Validates everything up front (output location, every clip's
    subject_id) before processing ANY clip, so a bad id never leaves a
    half-finished run. Returns the path of the run manifest."""
    out_root, storage = resolve_output_root()
    clips = collect_clips(target)
    if subject_id_arg is not None and len(clips) > 1:
        raise SubjectIdError(
            "--subject-id applies to a single clip only; a folder holds clips of "
            "different people, so one id for all of them would be a guess. Name "
            "folder clips <subject>_clip<nn> instead."
        )
    subject_ids = [resolve_subject_id(c, subject_id_arg) for c in clips]

    provenance = capture_run_provenance(label="blink_detector")
    run_context = {
        "provenance": {**asdict(provenance), "provenance_hash": provenance.provenance_hash()},
        "config_hashes": {
            "blink_positive_config": BlinkPositiveConfig().config_hash(),
            "video_storage_config": storage.config_hash(),
        },
        "code_versions": _code_versions(),
        "context_id": context_id,
        "device_id": device_id,
    }

    run_dir = os.path.join(out_root, provenance.experiment_id)
    os.makedirs(run_dir, exist_ok=False)

    covered = []
    for clip_path, (subject_id, source) in zip(clips, subject_ids):
        record = run_clip(clip_path, subject_id, source, run_context, _analyze_fn=_analyze_fn)
        out_path = os.path.join(run_dir, f"{record['clip_id']}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        covered.append({"clip_filename": record["clip_filename"], "subject_id": subject_id,
                        "analysis_status": record["analysis"]["status"], "output_file": os.path.basename(out_path)})
        frac = record["missingness"]["aperture_present_fraction"]
        frac_display = f"{frac:.2%}" if frac is not None else "n/a"
        print(f"[run_blink_detector] {record['clip_filename']}: analysis={record['analysis']['status']}, "
              f"aperture present {frac_display} -> written {out_path}")

    manifest = {
        "record_type": "blink_detector_run_manifest",
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "experiment_id": provenance.experiment_id,
        "target": os.path.abspath(target),
        "clips_covered": covered,
        "n_clips": len(covered),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": run_context["provenance"],
        "config_hashes": run_context["config_hashes"],
        "code_versions": run_context["code_versions"],
    }
    manifest_path = os.path.join(run_dir, "run_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[run_blink_detector] run manifest -> {manifest_path}")
    return manifest_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="D0PA1 blink detector runner (computes and stores only)")
    parser.add_argument("target", help="a clip file, or a folder of clips (processed in sorted filename order)")
    parser.add_argument("--subject-id", default=None, help="required only when a single clip's filename is not <subject>_clip<nn>")
    parser.add_argument("--context-id", default=None)
    parser.add_argument("--device-id", default=None)
    args = parser.parse_args(argv)
    try:
        run(args.target, args.subject_id, args.context_id, args.device_id)
    except (SubjectIdError, OutputLocationError, FileNotFoundError, RuntimeError) as e:
        print(f">>> ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
