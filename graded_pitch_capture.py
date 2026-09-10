"""
D0PA1 "PHYSICAL RUN SESSION" task, Task 3 -- graded-intensity directed pitch
capture with independent ground truth.

DUMB CAPTURE TOOL, same discipline as orientation_capture.py and
stage1_step9_gate2_capture.py: computes NO pass/fail, NO score, NO
mechanism verdict anywhere in this file. It records the commanded label
and the real schema-1.1 raw_head_pose_deg output (reusing
orientation_capture.py's own record_segment/build_trial_record
UNMODIFIED, not reimplemented). Which mechanism (M1/M2/M3) the data
supports is decided afterward, by a human reading the table this script's
caller assembles, not by this file.

Reuses, does not reimplement: consent (stage1_step7_consent.run_consent_gate),
T1 capture_thread (stage1_step4_vectors.capture_thread, unmodified),
record_segment/build_trial_record/FaceLandmarker setup
(orientation_capture.py, unmodified). The ONLY new things here are (a) a
PHASE LIST run one-at-a-time per process invocation (so the operator's
independent judgement can be collected between phases, in real time, by
whatever is driving this script -- see module docstring's "why one phase
per invocation" note below) and (b) a render_fn that shows NO raw angle
numbers during recording -- unlike orientation_capture.py's own
_live_render_and_check_abort, which deliberately DOES show live
yaw/pitch/v_so for ITS OWN Decision-45 "operator watches live" purpose.
Here, showing the live number during the attempt would contaminate the
independent judgement this task exists to collect, so this render_fn is
headless (no window, no overlay, nothing derived from the estimator).

WHY ONE PHASE PER PROCESS INVOCATION: this script cannot itself pause
mid-run to collect a chat-based judgement from the operator -- that
coordination happens OUTSIDE this process, between invocations. Consent
happens on the FIRST invocation only (no --participant-code given);
subsequent invocations pass --participant-code to skip re-consenting for
the same already-consented session, matching orientation_capture.py's own
"one consent covers the whole session" model as closely as running this as
several short, human-judgement-gated processes allows.

Appends real trial records to the SAME logs/orientation_trials.jsonl file
orientation_capture.py writes, same schema (schema_version "1.1",
record_type "orientation_trial") -- not a new file format.
"""

import argparse
import json
import os
import threading
import time
import uuid

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mp_vision

import stage1_step4_vectors as s1
from stage1_step4_vectors import FACE_MODEL_PATH, CONFIDENCE_THRESHOLD
from stage1_step7_consent import run_consent_gate
from orientation_capture import record_segment, build_trial_record, TRIALS_PATH

SESSION_ID = str(uuid.uuid4())


def headless_render(frame, f, remaining, instruction_lines):
    """No window, no display, no raw-angle overlay -- deliberately, so the
    operator's independent judgement (collected right after this process
    exits, before the next phase runs) cannot be anchored by watching the
    live estimator output. No abort key is available without a window;
    Ctrl+C is this script's abort path, same convention as
    controls/null_input.py."""
    return False


def main():
    parser = argparse.ArgumentParser(description="D0PA1 graded-intensity directed pitch capture, one phase per run.")
    parser.add_argument("--label", required=True, help="commanded_label for this phase, e.g. look_down_medium_1")
    parser.add_argument("--instruction", required=True, help="the single instruction line shown/printed for this phase")
    parser.add_argument("--participant-code", default=None, help="skip consent, reuse an already-consented session's code")
    args = parser.parse_args()

    if args.participant_code:
        participant_code = args.participant_code
        print(f"[graded_pitch_capture] reusing already-consented participant code '{participant_code}' -- skipping consent gate.")
    else:
        consented, audio_consented, participant_code = run_consent_gate(SESSION_ID)
        if not consented:
            print("No consent -- exiting, nothing recorded.")
            return
        print(f"PARTICIPANT_CODE={participant_code}")

    face_landmarker = mp_vision.FaceLandmarker.create_from_options(
        mp_vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=FACE_MODEL_PATH),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=CONFIDENCE_THRESHOLD,
            min_tracking_confidence=CONFIDENCE_THRESHOLD,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=True,
        )
    )

    t1 = threading.Thread(target=s1.capture_thread, name="CaptureThread")
    t1.start()
    time.sleep(1.0)  # let T1 populate at least one real frame before reading it

    stream_start = time.perf_counter()
    instruction_lines = [args.instruction, "Hold it."]

    print(f"\n{'='*70}")
    print(f"PHASE: {args.label}")
    print(f"  {args.instruction}")
    print("Starting in 8 seconds -- get positioned in frame now...")
    time.sleep(8)
    print(">>> RECORDING NOW (10s) <<<")
    summary, raw_angle_samples = record_segment(face_landmarker, stream_start, instruction_lines, render_fn=headless_render)
    print(">>> DONE <<<")

    face_landmarker.close()
    s1.stop_event.set()
    t1.join(timeout=3)

    trial = build_trial_record(participant_code, args.label, 0, summary, raw_angle_samples)

    os.makedirs(os.path.dirname(TRIALS_PATH), exist_ok=True)
    with open(TRIALS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(trial) + "\n")

    rhp = trial["raw_head_pose_deg"]
    print(f"\nRAW RESULT for '{args.label}' (written to {TRIALS_PATH}):")
    print(f"  yaw:   avg={rhp['yaw']['avg']}  min={rhp['yaw']['min']}  max={rhp['yaw']['max']}")
    print(f"  pitch: avg={rhp['pitch']['avg']}  min={rhp['pitch']['min']}  max={rhp['pitch']['max']}")
    print(f"  screen_orientation.oriented_rate: {trial['screen_orientation']['oriented_rate']}")


if __name__ == "__main__":
    main()
