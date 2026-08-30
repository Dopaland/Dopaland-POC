"""
D0PA1 control, Part 2.1 -- NULL-INPUT CONTROL.

Runs the FULL EXISTING, VALIDATED pipeline (features/geometry.py,
features/x_core.py -- imported and used UNMODIFIED, G5) against a person
sitting still in front of a blank screen, for a configurable duration
(default 10 minutes). Computes and stores numbers. Decides NOTHING (G1):
no pass/fail, no threshold comparison, no verdict, anywhere in this file.

WHY THIS RUNS BEFORE ANY delta THRESHOLD IS SIGNED
---------------------------------------------------
One of our signals, V_pd (postural volatility), has a neutral dispersion
of roughly 0.0001 (CLAUDE.md's own STATUS section, confirmed by
stage1_step8_calibration_repeat_test.py). A near-zero denominator makes
every z-score enormous -- a threshold expressed on the z-scale may be
comparing noise to noise and calling it signal. Switching to a
MAD-based robust estimator does not fix this on its own: the MAD of a
near-constant signal is ALSO near-zero (CLAUDE.md's D0PA1 hard constraint
#5 says so explicitly: "MAD == 0 must be handled explicitly -- emit
missing with reason zero_dispersion. Do not divide by zero, do not add a
silent epsilon."). This control is how we find out what the dispersion
actually is, under conditions where the true answer for every signal is
"nothing is happening" -- BEFORE any pre-registered threshold is signed
against these units.

WHAT THIS CANNOT ESTABLISH (see docs/CONTROLS.md for the full statement):
this control tells us about SENSOR/PIPELINE NOISE under a genuinely null
condition. It says nothing about whether a real signal exists during real
task performance -- that is what the negative control (controls/negative_control.py)
and the real study data are for.

REQUIRED CAMERA + HUMAN OPERATOR: this script needs a live webcam and a
person sitting still in front of a blank screen for the full configured
duration. It cannot be run unattended or without a camera. Operator
instructions are printed at start -- see print_operator_instructions()
and README-style guidance in docs/CONTROLS.md.
"""

import argparse
import hashlib
import json
import os
import platform
import sys
import time
import uuid
from collections import deque
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mp_vision

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# G5: reused UNMODIFIED from the validated path. This file never redefines
# a formula, a threshold, or the calibration procedure -- it only calls
# these functions/classes.
from features.geometry import (
    apply_clahe,
    pose_normalize,
    interocular_distance,
    yaw_pitch_roll_from_matrix,
    POSE_NOSE,
    POSE_SHOULDER_L,
    POSE_SHOULDER_R,
)
from features.x_core import (
    compute_v_bf,
    compute_v_es,
    compute_v_jc,
    compute_v_pd,
    NeutralCalibrator,
    CALIBRATION_SECONDS,
    _z_score,
)
from stage1_step4_vectors import FACE_MODEL_PATH, POSE_MODEL_PATH, CONFIDENCE_THRESHOLD, CAMERA_INDEX

LOG_DIR = os.path.join(REPO_ROOT, "logs")
SCHEMA_VERSION = "1.0"

ALL_SIGNALS = ("v_bf", "v_es", "v_jc", "v_pd")  # every signal reported SEPARATELY, never blended (task requirement)

ZERO_DISPERSION_EPSILON = 1e-9  # numerical-safety floor ONLY (CLAUDE.md hard constraint #5) -- NOT a scientific threshold; see module docstring


@dataclass
class NullInputConfig:
    """The excursion rule is PARAMETERIZED here, not hardcoded, so it is
    inspectable and hashed (config_hash below) into every log this control
    writes -- CLAUDE.md's Gate 0 provenance discipline applied to a control
    run, same as any other experiment."""

    duration_minutes: float = 10.0
    calibration_seconds: float = CALIBRATION_SECONDS  # reused from the REAL constant, not re-guessed
    excursion_z_threshold: float = 2.0
    excursion_min_duration_seconds: float = 1.0
    camera_index: int = CAMERA_INDEX
    subject_id: str = "UNSET_OPERATOR_MUST_PROVIDE"
    context_id: str = "null_input_control"
    device_id: str = field(default_factory=platform.node)

    def config_hash(self):
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


class ExcursionDetector:
    """One instance PER SIGNAL (never shared/blended across signals --
    task requirement). Sustained-threshold state machine: an excursion is
    confirmed when |z| >= excursion_z_threshold holds CONTINUOUSLY for at
    least excursion_min_duration_seconds of WALL-CLOCK time.

    DESIGN CHOICE, stated plainly: a missing/None z-reading (no face
    detected, or this signal's dispersion is zero_dispersion and cannot be
    z-scored at all) ENDS any in-progress excursion timer immediately --
    it does not toggle "excursion" state on its own, and it does not
    receive the same None-tolerance BlinkDetector (features/attention.py)
    uses for blink detection. This is a deliberately SIMPLER, more
    conservative rule for a new diagnostic control: it can undercount an
    excursion that happens to straddle a brief tracking gap, but it can
    never manufacture one from a gap, which is the safer error direction
    for a control whose entire purpose is establishing a trustworthy
    false-event rate.
    """

    def __init__(self, name, z_threshold, min_duration_seconds):
        self.name = name
        self.z_threshold = z_threshold
        self.min_duration_seconds = min_duration_seconds
        self._above_since = None
        self._confirmed_count = 0
        self._currently_confirmed = False  # avoids double-counting one long excursion every cycle it's checked

    def update(self, z, now):
        if z is None or not np.isfinite(z):
            self._above_since = None
            self._currently_confirmed = False
            return
        if abs(z) >= self.z_threshold:
            if self._above_since is None:
                self._above_since = now
                self._currently_confirmed = False
            elif not self._currently_confirmed and (now - self._above_since) >= self.min_duration_seconds:
                self._confirmed_count += 1
                self._currently_confirmed = True
        else:
            self._above_since = None
            self._currently_confirmed = False

    @property
    def confirmed_count(self):
        return self._confirmed_count


def compute_dispersion(values):
    """values: list/array of floats (already excluding None/missing).
    Returns std, MAD, 1.4826*MAD, and an explicit zero_dispersion flag --
    CLAUDE.md D0PA1 hard constraint #5, verbatim: "MAD == 0 must be
    handled explicitly -- emit missing with reason zero_dispersion. Do not
    divide by zero, do not add a silent epsilon." """
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    n = len(arr)
    if n < 2:
        return {"std": None, "mad": None, "mad_scaled": None, "zero_dispersion": None, "zero_dispersion_reason": "insufficient_samples", "n": n}

    std = float(arr.std())
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    mad_scaled = 1.4826 * mad

    is_zero = std < ZERO_DISPERSION_EPSILON or mad < ZERO_DISPERSION_EPSILON
    return {
        "std": std,
        "mad": mad,
        "mad_scaled": mad_scaled,
        "zero_dispersion": is_zero,
        "zero_dispersion_reason": "zero_dispersion" if is_zero else None,
        "n": n,
    }


def print_operator_instructions(config: NullInputConfig):
    print("=" * 70)
    print("D0PA1 NULL-INPUT CONTROL -- OPERATOR INSTRUCTIONS")
    print("=" * 70)
    print(f"""
WHAT TO DO:
  1. Sit in front of the camera as you normally would for a real session.
  2. Display a BLANK SCREEN (no content, no task) for the entire run.
  3. Sit as STILL and RELAXED as you can -- no deliberate expression, no
     deliberate movement. This is meant to capture what "nothing is
     happening" looks like to the sensor, not a posed-still performance.
  4. Do NOT talk, do NOT check your phone, do NOT get up.

HOW LONG:
  {config.duration_minutes:.1f} minutes total, including a {config.calibration_seconds:.0f}s
  neutral-calibration phase at the very start (same calibration the real
  pipeline runs) -- keep sitting still through that phase too, it is part
  of the run, not a separate step.

WHAT WOULD INVALIDATE THIS RUN:
  - Leaving the frame, or a second person entering the frame.
  - Talking, eating, drinking, or checking a phone.
  - Deliberately holding a fixed expression (this can silently bias the
    calibration -- see features/x_core.py's classify_calibration_quality
    docstring on this exact blind spot).
  - A real interruption (phone call, someone entering the room) --
    if this happens, stop and re-run rather than continuing through it.
  - Poor/changing lighting during the run (turn on your normal lighting
    and don't change it mid-run).

Press Ctrl+C at any time to stop early -- a partial run is still logged
with its actual duration, never silently discarded.
""")
    print("=" * 70)


def run(config: NullInputConfig):
    print_operator_instructions(config)

    session_id = str(uuid.uuid4())
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"null_input_{session_id}.jsonl")
    print(f"[NullInput] logging to {log_path}")
    print(f"[NullInput] config_hash={config.config_hash()}")

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
    pose_landmarker = mp_vision.PoseLandmarker.create_from_options(
        mp_vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=POSE_MODEL_PATH),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=CONFIDENCE_THRESHOLD,
            min_tracking_confidence=CONFIDENCE_THRESHOLD,
        )
    )

    cap = cv2.VideoCapture(config.camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        print("[NullInput] ERROR: could not open webcam.")
        return None

    calibrator = NeutralCalibrator(calibration_seconds=config.calibration_seconds)
    pd_buffer = deque()
    detectors = {name: ExcursionDetector(name, config.excursion_z_threshold, config.excursion_min_duration_seconds) for name in ALL_SIGNALS}

    raw_values = {name: [] for name in ALL_SIGNALS}  # ALL samples this run, for the dispersion report (never blended)
    n_frames = 0
    n_detected = 0
    stream_start = time.perf_counter()
    run_end = stream_start + config.duration_minutes * 60.0

    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "record_type": "null_input_run_start",
            "session_id": session_id,
            "subject_id": config.subject_id,
            "context_id": config.context_id,
            "device_id": config.device_id,
            "config": asdict(config),
            "config_hash": config.config_hash(),
            "ts_utc": datetime.now(timezone.utc).isoformat(),
        }) + "\n")

        try:
            while True:
                now_wall = time.perf_counter()
                if now_wall >= run_end:
                    break
                ok, frame = cap.read()
                if not ok:
                    continue

                cycle_start = time.perf_counter()
                timestamp_ms = int((cycle_start - stream_start) * 1000)
                n_frames += 1

                clahe_frame = apply_clahe(frame)
                rgb_frame = cv2.cvtColor(clahe_frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms)
                pose_result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)
                h, w = frame.shape[:2]

                composite = {"v_bf": None, "v_es": None, "v_pd": None}
                covariate = {"v_jc": None, "v_bf_convergence_ratio": None, "v_es_cheek_raise": None}
                yaw = None
                face_detected = False

                if face_result.face_landmarks and face_result.facial_transformation_matrixes:
                    lms = face_result.face_landmarks[0]
                    matrix = face_result.facial_transformation_matrixes[0]
                    normalized_pts = pose_normalize(lms, matrix, w, h)
                    io_dist = interocular_distance(normalized_pts)
                    yaw, pitch, roll = yaw_pitch_roll_from_matrix(matrix)

                    v_bf, bf_components = compute_v_bf(normalized_pts, io_dist)
                    v_es, es_components = compute_v_es(normalized_pts, io_dist)
                    v_jc, jc_components = compute_v_jc(normalized_pts, io_dist)

                    composite["v_bf"] = v_bf
                    composite["v_es"] = v_es
                    covariate["v_jc"] = v_jc
                    covariate["v_bf_convergence_ratio"] = bf_components["convergence_ratio"]
                    covariate["v_es_cheek_raise"] = es_components["cheek_raise"]
                    face_detected = True
                    n_detected += 1

                    raw_values["v_bf"].append(v_bf)
                    raw_values["v_es"].append(v_es)
                    raw_values["v_jc"].append(v_jc)

                if pose_result.pose_world_landmarks:
                    world = pose_result.pose_world_landmarks[0]
                    nose_pos = np.array([world[POSE_NOSE].x, world[POSE_NOSE].y, world[POSE_NOSE].z])
                    shoulder_mid = np.array([
                        (world[POSE_SHOULDER_L].x + world[POSE_SHOULDER_R].x) / 2.0,
                        (world[POSE_SHOULDER_L].y + world[POSE_SHOULDER_R].y) / 2.0,
                        (world[POSE_SHOULDER_L].z + world[POSE_SHOULDER_R].z) / 2.0,
                    ])
                    v_pd, _pd_components = compute_v_pd(pd_buffer, nose_pos, shoulder_mid, cycle_start)
                    composite["v_pd"] = v_pd
                    if v_pd is not None:
                        raw_values["v_pd"].append(v_pd)

                calibrator.add_sample(cycle_start, composite, covariate, yaw)
                if calibrator.should_complete(cycle_start):
                    reference = calibrator.complete(cycle_start)
                    log_file.write(json.dumps({
                        "schema_version": SCHEMA_VERSION,
                        "record_type": "null_input_calibration_complete",
                        "session_id": session_id,
                        "reference": reference,
                    }) + "\n")
                    print(f"[NullInput] calibration complete at {cycle_start - stream_start:.0f}s -- monitoring for excursions now.")

                # Excursion detection -- ONLY once calibrated (need a
                # mean/std reference to z-score against at all); per
                # ExcursionDetector's own docstring, a None z (uncalibrated,
                # no detection, or zero_dispersion) simply cannot sustain
                # or start an excursion.
                if calibrator.is_calibrated():
                    ref = calibrator.reference
                    for key in ("v_bf", "v_es", "v_pd"):
                        std = ref["composite"][key]["std"]
                        mean = ref["composite"][key]["mean"]
                        z = None
                        if composite[key] is not None and mean is not None and std is not None and std >= ZERO_DISPERSION_EPSILON:
                            z = _z_score(composite[key] - mean, std)
                        detectors[key].update(z, cycle_start)

                    jc_mean = ref["covariates"]["v_jc"]["mean"]
                    jc_std = ref["covariates"]["v_jc"]["std"]
                    z_jc = None
                    if covariate["v_jc"] is not None and jc_mean is not None and jc_std is not None and jc_std >= ZERO_DISPERSION_EPSILON:
                        z_jc = _z_score(covariate["v_jc"] - jc_mean, jc_std)
                    detectors["v_jc"].update(z_jc, cycle_start)

                log_file.write(json.dumps({
                    "schema_version": SCHEMA_VERSION,
                    "record_type": "null_input_sample",
                    "session_id": session_id,
                    "ts_monotonic": cycle_start,
                    "elapsed_seconds": cycle_start - stream_start,
                    "face_detected": face_detected,
                    "pose_detected": composite["v_pd"] is not None,
                    "composite": composite,
                    "covariate": covariate,
                    "yaw_deg": yaw,
                    "calibrated": calibrator.is_calibrated(),
                }) + "\n")

                if n_frames % 90 == 0:  # roughly every 3s at ~30fps
                    elapsed = cycle_start - stream_start
                    remaining = config.duration_minutes * 60.0 - elapsed
                    print(f"[NullInput] {elapsed:.0f}s elapsed, {remaining:.0f}s remaining, "
                          f"detect_rate={n_detected/n_frames:.2f}")

        except KeyboardInterrupt:
            print("\n[NullInput] stopped early by operator (Ctrl+C) -- logging partial run.")

        finally:
            cap.release()
            face_landmarker.close()
            pose_landmarker.close()

    actual_duration_seconds = time.perf_counter() - stream_start
    monitoring_seconds = max(0.0, actual_duration_seconds - config.calibration_seconds) if calibrator.is_calibrated() else 0.0
    monitoring_minutes = monitoring_seconds / 60.0

    summary = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "null_input_summary",
        "session_id": session_id,
        "subject_id": config.subject_id,
        "context_id": config.context_id,
        "device_id": config.device_id,
        "config": asdict(config),
        "config_hash": config.config_hash(),
        "actual_duration_seconds": actual_duration_seconds,
        "monitoring_seconds": monitoring_seconds,
        "n_frames": n_frames,
        "n_detected": n_detected,
        "detect_rate": (n_detected / n_frames) if n_frames else None,
        "calibration_completed": calibrator.is_calibrated(),
        "signals": {},
    }

    for name in ALL_SIGNALS:
        dispersion = compute_dispersion(raw_values[name])
        excursion_count = detectors[name].confirmed_count
        false_event_rate_per_minute = (
            (excursion_count / monitoring_minutes) if monitoring_minutes > 0 else None
        )
        summary["signals"][name] = {
            "dispersion": dispersion,
            "excursion_count": excursion_count,
            "monitoring_minutes": monitoring_minutes,
            "false_event_rate_per_minute": false_event_rate_per_minute,
        }

    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(summary) + "\n")

    print("\n" + "=" * 70)
    print("NULL-INPUT CONTROL SUMMARY (no verdict -- numbers only)")
    print("=" * 70)
    for name in ALL_SIGNALS:
        s = summary["signals"][name]
        d = s["dispersion"]
        if d["std"] is None:
            print(f"  {name}: insufficient samples ({d['n']})")
            continue
        zd = " [ZERO_DISPERSION]" if d["zero_dispersion"] else ""
        print(
            f"  {name}: std={d['std']:.6g} mad={d['mad']:.6g} mad_scaled={d['mad_scaled']:.6g}{zd} "
            f"| excursions={s['excursion_count']} rate/min={s['false_event_rate_per_minute']}"
        )
    print(f"\nFull log: {log_path}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="D0PA1 null-input control")
    parser.add_argument("--duration-minutes", type=float, default=10.0)
    parser.add_argument("--subject-id", type=str, required=True, help="Anonymous subject/participant code, e.g. P01 -- required, never a name")
    parser.add_argument("--z-threshold", type=float, default=2.0)
    parser.add_argument("--min-duration-seconds", type=float, default=1.0)
    args = parser.parse_args()

    cfg = NullInputConfig(
        duration_minutes=args.duration_minutes,
        subject_id=args.subject_id,
        excursion_z_threshold=args.z_threshold,
        excursion_min_duration_seconds=args.min_duration_seconds,
    )
    run(cfg)
