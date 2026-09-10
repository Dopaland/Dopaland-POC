"""
Consent module audio-independence validation (D0PA1 audio acquisition
task, Task 2.2). Covers: the consent module imports no audio library (same
style/standard as its own existing camera-free property, machine-checked
for the first time here -- no prior test file asserted the video property
either); the consent module never imports any audio ACQUISITION module
(architecturally cannot reach a microphone from consent code, same as it
architecturally cannot reach a camera); run_consent_gate's new 3-tuple
return shape and audio-decline reason logging (Task 2.1/2.3).
"""

import ast
import json
import os
import sys
import tempfile
from io import StringIO
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

CONSENT_MODULE_PATH = os.path.join(REPO_ROOT, "stage1_step7_consent.py")

# Any of these appearing as an imported module name (top-level or nested,
# `import X` or `from X import ...`) in stage1_step7_consent.py is a
# violation -- these are the audio-library names this repository could
# plausibly ever use for microphone access, checked broadly on purpose.
FORBIDDEN_AUDIO_IMPORT_NAMES = {
    "sounddevice", "pyaudio", "pyaudioo", "wave", "audioop", "simpleaudio",
    "soundfile", "portaudio",
}
# Same idea for video/camera libraries -- re-asserted here (not previously
# machine-checked anywhere) since this task extends the exact same module.
FORBIDDEN_VIDEO_IMPORT_NAMES = {"cv2", "mediapipe"}


def _imported_module_names(path):
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def check_no_audio_library_imported():
    imported = _imported_module_names(CONSENT_MODULE_PATH)
    violations = imported & FORBIDDEN_AUDIO_IMPORT_NAMES
    return not violations, {"imported": sorted(imported), "violations": sorted(violations)}


def check_no_video_library_imported():
    """Re-confirms the pre-existing, previously-only-documented camera-free
    property, now machine-checked for the first time."""
    imported = _imported_module_names(CONSENT_MODULE_PATH)
    violations = imported & FORBIDDEN_VIDEO_IMPORT_NAMES
    return not violations, {"imported": sorted(imported), "violations": sorted(violations)}


def check_no_audio_acquisition_module_imported():
    """audio_acquisition.py (the real capture module, Task 3) must never be
    imported by the consent module either -- consent deciding TO allow
    audio is not the same as consent CONTAINING a path to a microphone."""
    imported = _imported_module_names(CONSENT_MODULE_PATH)
    return "audio_acquisition" not in imported, {"imported": sorted(imported)}


def _run_consent_gate_with_inputs(inputs):
    """Drives run_consent_gate() with a scripted stdin, isolated to a temp
    log directory so this test never touches the repo's real
    logs/consent_log.jsonl."""
    import stage1_step7_consent as consent_mod

    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "consent_log.jsonl")
        with mock.patch.object(consent_mod, "LOG_DIR", tmp), \
             mock.patch.object(consent_mod, "CONSENT_LOG_PATH", log_path), \
             mock.patch("builtins.input", side_effect=inputs), \
             mock.patch("sys.stdout", new_callable=StringIO):
            result = consent_mod.run_consent_gate("test-session-id")
        records = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                records = [json.loads(line) for line in f if line.strip()]
        return result, records


def check_video_decline_returns_none_none_and_logs_nothing():
    result, records = _run_consent_gate_with_inputs(["no"])
    ok = result == (False, None, None) and records == []
    return ok, {"result": result, "n_records": len(records)}


def check_video_yes_audio_yes():
    result, records = _run_consent_gate_with_inputs(["yes", "P01", "yes"])
    ok = (
        result == (True, True, "P01")
        and len(records) == 1
        and records[0]["video_consent"] is True
        and records[0]["audio_consent"] is True
        and records[0]["audio_consent_reason"] is None
    )
    return ok, {"result": result, "record": records[0] if records else None}


def check_video_yes_audio_declined_has_explicit_reason():
    """The core Task 2.3 proof: declining audio is an explicit false with a
    reason, never a silently missing field."""
    result, records = _run_consent_gate_with_inputs(["yes", "P02", "no"])
    ok = (
        result == (True, False, "P02")
        and len(records) == 1
        and "audio_consent" in records[0]
        and records[0]["audio_consent"] is False
        and records[0].get("audio_consent_reason") == "declined_by_participant"
    )
    return ok, {"result": result, "record": records[0] if records else None}


def check_video_yes_audio_blank_input_declines():
    """Pressing Enter (blank) on the audio question must decline, same
    convention as the video question's own blank-declines behaviour."""
    result, records = _run_consent_gate_with_inputs(["yes", "P03", ""])
    ok = result == (True, False, "P03") and records[0]["audio_consent"] is False
    return ok, {"result": result}


def run_all():
    checks = [
        ("NO AUDIO LIBRARY IMPORTED BY CONSENT MODULE", check_no_audio_library_imported),
        ("NO VIDEO LIBRARY IMPORTED BY CONSENT MODULE (re-confirmed)", check_no_video_library_imported),
        ("NO AUDIO ACQUISITION MODULE IMPORTED BY CONSENT MODULE", check_no_audio_acquisition_module_imported),
        ("VIDEO DECLINE -> (False, None, None), NOTHING LOGGED", check_video_decline_returns_none_none_and_logs_nothing),
        ("VIDEO YES + AUDIO YES", check_video_yes_audio_yes),
        ("VIDEO YES + AUDIO DECLINED -- EXPLICIT REASON LOGGED", check_video_yes_audio_declined_has_explicit_reason),
        ("VIDEO YES + AUDIO BLANK INPUT -> DECLINED", check_video_yes_audio_blank_input_declines),
    ]
    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"CONSENT AUDIO-GATE VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("CONSENT AUDIO-GATE VALIDATION: PASS")


if __name__ == "__main__":
    run_all()
