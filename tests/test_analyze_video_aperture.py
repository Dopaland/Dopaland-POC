"""
D0PA1 analyze_video.py aperture-export validation (runnable directly, no
pytest, no camera, no real video file, no MediaPipe model load). Covers
the RETENTION change (Change 1 of CLAUDE_CODE_PROMPT_aperture_export.md):
that the per-frame aperture stream round-trips into
controls.blink_positive.run_detector_on_aperture_stream without
reshaping, that None survives a JSON write/read cycle exactly (the
schema this module's own aperture_stream entries are written into), and
that the result-dict builders (_ok_result / _mode_b_result /
_failed_result) all carry the aperture_stream through unchanged with the
correct "validated" flag per mode.

Does NOT exercise the live per-frame collection loop inside
_run_mode_a/_run_mode_b themselves -- those need a real video file and
loaded MediaPipe FaceLandmarker/PoseLandmarker models, same reason
av_sync_flash.py's VideoLuminanceCapture/AudioEnergyCapture are not
unit-tested directly. See this task's own report for the real,
end-to-end demonstration against an actual (synthetic) video file, run
manually rather than as part of this suite.
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from analyze_video import aperture_stream_as_tuples, _ok_result, _mode_b_result, _failed_result
from controls.blink_positive import run_detector_on_aperture_stream


def check_aperture_stream_round_trips_without_reshaping():
    """The exact point of Change 1's consumability requirement: build a
    stream in this module's own {"t":..., "aperture":...} schema, convert
    with aperture_stream_as_tuples, and feed the result STRAIGHT into
    run_detector_on_aperture_stream with no further reshaping by this
    test."""
    stream = [
        {"t": 0.0, "aperture": 0.30},
        {"t": 0.033, "aperture": 0.29},
        {"t": 0.067, "aperture": None},  # a no-detect frame
        {"t": 0.1, "aperture": 0.05},    # a real closure, if k/baseline allow
        {"t": 0.133, "aperture": 0.31},
    ]
    tuples = aperture_stream_as_tuples(stream)
    ok = tuples == [(0.0, 0.30), (0.033, 0.29), (0.067, None), (0.1, 0.05), (0.133, 0.31)]
    # Must run without raising -- the actual "does the path exist and
    # work" proof. Correctness of the onset count is not the point (too
    # short a stream to warm up a baseline; an empty result is fine).
    onsets = run_detector_on_aperture_stream(tuples)
    ok = ok and isinstance(onsets, list)
    return ok, {"tuples": tuples, "onsets": onsets}


def check_none_survives_json_write_and_read_exactly():
    """aperture_stream entries are written to disk as part of the ordinary
    JSON result file (json.dump/json.load) -- confirm None on a no-detect
    frame comes back as None, not dropped, not coerced to 0.0 or NaN, and
    not interpolated from neighbouring frames."""
    stream = [
        {"t": 0.0, "aperture": 0.412},
        {"t": 0.033, "aperture": None},
        {"t": 0.067, "aperture": None},
        {"t": 0.1, "aperture": 0.398},
    ]
    raw = json.dumps({"aperture_stream": stream})
    loaded = json.loads(raw)["aperture_stream"]
    ok = loaded == stream
    ok = ok and loaded[1]["aperture"] is None and loaded[2]["aperture"] is None
    ok = ok and len(loaded) == 4  # no row dropped
    return ok, loaded


def check_ok_result_carries_aperture_stream_and_validated_true():
    """Mode A's result builder: aperture_stream passed through unchanged,
    validated=True (Mode A is the calibrated path)."""
    stream = [{"t": 0.0, "aperture": 0.4}, {"t": 0.033, "aperture": None}]
    reference = {"calibration_seconds": 25.0, "quality": {"possibly_not_neutral": False}}
    result = _ok_result(
        "fake_video.mp4", 30.0, 60.0, reference,
        calibration_frames_total=750, calibration_frames_detected=750, timeline=[],
        aperture_stream=stream,
    )
    ok = result["aperture_stream"] == stream
    ok = ok and result["validated"] is True
    return ok, {"aperture_stream": result["aperture_stream"], "validated": result["validated"]}


def check_mode_b_result_carries_aperture_stream_and_validated_false():
    """Mode B's result builder: same aperture_stream contract, but
    validated=False -- Mode B stays uncalibrated/approximate throughout,
    unaffected by this change."""
    stream = [{"t": 0.0, "aperture": 0.4}, {"t": 0.033, "aperture": None}]
    face_instability = {"likely_multiple_or_changing_faces": False}
    result = _mode_b_result(
        "fake_video.mp4", 30.0, 60.0, n_frames_total=1800, n_frames_face_detected=1200,
        timeline=[], face_instability=face_instability, fallback_reasons=[],
        aperture_stream=stream,
    )
    ok = result["aperture_stream"] == stream
    ok = ok and result["validated"] is False
    return ok, {"aperture_stream": result["aperture_stream"], "validated": result["validated"]}


def check_failed_result_defaults_aperture_stream_to_empty_list():
    """A hard-fail (e.g. zero readable frames) must still carry a real,
    empty aperture_stream field -- never omitted, never None -- so a
    consumer never has to special-case a missing key."""
    result = _failed_result(
        "fake_video.mp4", 30.0, None, "A_calibrated", "no_frames_readable",
        ["no frames were read from the video"],
    )
    ok = result["aperture_stream"] == []
    return ok, result["aperture_stream"]


if __name__ == "__main__":
    checks = [
        ("aperture stream round-trips into run_detector_on_aperture_stream, no reshaping", check_aperture_stream_round_trips_without_reshaping),
        ("None survives a JSON write/read cycle exactly", check_none_survives_json_write_and_read_exactly),
        ("_ok_result (Mode A) carries aperture_stream, validated=True", check_ok_result_carries_aperture_stream_and_validated_true),
        ("_mode_b_result (Mode B) carries aperture_stream, validated=False", check_mode_b_result_carries_aperture_stream_and_validated_false),
        ("_failed_result defaults aperture_stream to [] , never omitted/None", check_failed_result_defaults_aperture_stream_to_empty_list),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"APERTURE EXPORT VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("APERTURE EXPORT VALIDATION: PASS")
