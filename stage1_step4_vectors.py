"""
Stage 1, steps 4+5, plus Stage 1.5 step 8 — 4 biometric vectors,
geometric, pose-normalized 3D (CLAUDE.md Decision 11 + MANDATORY
ARCHITECTURE #4); the 10s rolling window (avg/peak/variance, MANDATORY
ARCHITECTURE #5) with a window-validity gate; and per-person
within-session neutral calibration (Decision #5 / Pitfall #2 /
MANDATORY ARCHITECTURE #6), built deliberately BEFORE step 6's V/A
mapping so that mapping runs on calibrated (deviation-from-neutral)
vectors from the start, not raw magnitudes that would need redoing.

New file (not an edit of stage0_skeleton.py) so Stage 0's Gate-1 artifact
stays intact and reviewable on its own. Thread 1 (capture) is copied over
unchanged. Thread 2 changes in two ways from Stage 0:

1. Continuous sampling, not a 10s tick (CADENCE clarification — not new
   scope): the "every 10s" rule governs the summary/agent/DB step, which
   doesn't exist until Stage 2. Thread 2 loops at detection speed and
   logs every sample ("log per-frame", Decision 12) — required because
   V_pd is itself defined as a variance over a rolling ~1-2s buffer, and
   step 5's 10s window needs a real sample stream to summarize.
2. RunningMode.VIDEO instead of IMAGE: IMAGE mode has no inter-frame
   tracking, so min_tracking_confidence would be silently meaningless.
   VIDEO mode (detect_for_video, monotonically increasing ms timestamps)
   makes tracking — and therefore that confidence floor — real.

Step 4 validation found our facial vectors (V_bf, V_es) are direction-
reliable but magnitude-noisy under head rotation (io_dist, their shared
scale reference, carries residual yaw correlation ~0.25 at full range).
Step 5's window design leans on this finding rather than re-fighting it:
variance-per-window doubles as the confidence signal (a high-variance
window, e.g. mid head-turn, is a low-trust reading) rather than just a
logged stat — see WindowAccumulator.

Landmark indices below are verified against
mediapipe/python/solutions/face_mesh_connections.py (google-ai-edge/
mediapipe, master), not assumed from memory.

--- ATTENTION SIGNAL, Step 1 (V_so -- screen orientation) ---
A NEW, FIFTH geometric signal, added after Gate 2, using the exact same
discipline the four affect vectors were built with: reuse the existing
head-pose decomposition (yaw_pitch_roll_from_matrix, already computed
every cycle for the quality gate -- not recomputed here), a first-cut
threshold explicitly derived from the existing 35deg per-frame gate (not
invented, not tuned to one face), and an UNVALIDATED stamp on every
logged record until it is tested across real people the same way V_bf/
V_es/V_pd were at Gate 2 (see compute_v_so's docstring for the exact
validation hook this needs).

HONEST FRAMING (as strict as the V/A rules): V_so measures a geometric
fact -- is the head/gaze pointed at the screen -- and is labeled "screen
orientation" everywhere. It NEVER claims "attention" or "engagement":
those are mental-state inferences a camera cannot measure (a person can
be squarely oriented at the screen and mentally elsewhere). Any UI/log/
report text describing V_so must say "orientation", never "attention"/
"engagement".

GLASSES-ROBUST BY CONSTRUCTION: PRIMARY signal is head pose (yaw/pitch),
which glasses do not affect at all. SECONDARY signal is gaze (iris
position within the eye, from the same iris landmarks V_es already
reuses) -- a BONUS refinement applied ONLY when the iris landmarks pass
a geometric plausibility check, NEVER a dependency, because glasses are
exactly what corrupts iris tracking (Pitfall #4) via lens reflections.
If gaze is unusable this frame, V_so falls back to head-pose-only and
says so in its own logged record -- it never fails or goes silent just
because gaze isn't available.

V_so is NOT composited into Valence or Arousal (attention is not
affect) and needs NO per-person calibration (unlike V_bf/V_es/V_pd,
"oriented toward screen" is a universal geometric threshold, same
category as the quality gate's yaw>35deg check, not a deviation-from-
neutral concept) -- so it is measured and logged from frame 1, windowed
on its own independent 10s clock (AttentionWindowAccumulator), never
touching WindowAccumulator or NeutralCalibrator.

VALIDATION PREP: the cluster is exposed as THREE separate, independently
scoreable fields (sample records and window summaries alike), same
discipline as Gate 2 scoring V_bf/V_es/V_pd per-vector rather than as
one blended number -- "screen_orientation" (head/eyes toward screen),
"gaze_direction" (bonus, ALWAYS paired with a gaze_reliable flag so a
scorer can exclude unreliable-gaze windows), and "look_away_rate" (1 -
oriented_rate, an honestly-labeled proxy -- never "distraction" or
"disengagement"). All three carry "unvalidated": True until a Gate-2-
style directed capture ("look at screen"/"look away"/"look down" on
command) scores them across real people. This is a pure reshape of
values compute_v_so already produced -- no new per-frame computation.

--- PILOT STATUS (post-validation finding, documentation only) ---
V_so is a PILOT feature, NOT POC-ready, and is NOT wired into the demo
UI (stage3_demo_ui.py never imports or reads it). Directed testing
found: YAW (left/right) is detected reliably. PITCH (looking up/down)
is UNRELIABLE -- on a maximal, sustained, verified chin-to-chest
look-down, MediaPipe-derived pitch stayed ~0.1deg (indistinguishable
from looking straight at the screen) and oriented_rate stayed 1.0.
Root cause is STRUCTURAL, not a code bug: yaw_pitch_roll_from_matrix
is provably exact on synthetic rotations, but the face foreshortens
when looking down, degrading the landmark data the pitch calculation
depends on -- fixable only by a different sensing approach (gaze
tracking and/or better hardware), not by tuning this formula. DO NOT
attempt to "fix" pitch here. Since the most common disengagement cue
is looking down, a yaw-only reliable signal cannot honestly be
presented as "attention"/"engagement"/"focus"/"distraction" -- doing
so would overclaim, the same dishonesty the pain-axis rule (V_bf)
forbids. A reliably-pitched version is pilot work (see CLAUDE.md's
"Attention / screen-orientation -- PILOT, not POC" note).
"""

import cv2
import json
import mediapipe as mp
import numpy as np
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mp_vision

CAMERA_INDEX = 0
FPS_REPORT_INTERVAL_SECONDS = 3.0
CONFIDENCE_THRESHOLD = 0.7  # "detected" means "cleared 0.7", per instruction

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
FACE_MODEL_PATH = os.path.join(MODELS_DIR, "face_landmarker.task")
POSE_MODEL_PATH = os.path.join(MODELS_DIR, "pose_landmarker_full.task")

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
SCHEMA_VERSION = "1.6"  # 1.3 added va_point (step 6, untested hypothesis) to sample records;
                         # 1.4: va_point now uses the Decision 18 mapping (Valence=z_es only) --
                         # the retired (z_es-z_bf)/2 formula no longer appears. Historical records
                         # at 1.3 keep their old values; only new records use the new mapping.
                         # 1.5: ATTENTION SIGNAL Step 1 -- adds "screen_orientation" to sample
                         # records (new field, existing fields untouched) and a new
                         # "attention_window_summary" record type. UNVALIDATED (see module
                         # docstring) -- never composited into vectors/vectors_deviation/va_point.
                         # 1.6: orientation-cluster validation prep -- exposes the attention
                         # signal as THREE separate top-level fields (sample records AND window
                         # summaries): "screen_orientation" (unchanged in meaning, now leaner),
                         # NEW "gaze_direction" (was folded into screen_orientation's
                         # head_pose_only/gaze_reliable flags -- now its own field, always
                         # carrying gaze_reliable), NEW "look_away" per-sample / "look_away_rate"
                         # per-window (1 - oriented_rate, honestly labeled, never "distraction").
                         # No vector math changed -- pure reshape of values compute_v_so already
                         # produced. Historical 1.5 records keep their old flat shape; only new
                         # records use the 1.6 three-field shape.
SESSION_ID = str(uuid.uuid4())
# Set once by main() after consent (step 7), before any thread starts.
# One launch = one person = one session_id = one person_label -- no
# internal multi-person loop reads or writes this after that point.
PERSON_LABEL = None

WINDOW_SECONDS = 10.0  # Decision 12 / MANDATORY ARCHITECTURE #5: 10s avg+peak+variance

# Per-person within-session neutral calibration (Decision #5, Pitfall
# #2, MANDATORY ARCHITECTURE #6). Fixed, universal duration -- same for
# everyone, no per-person tuning of the calibration window itself
# (Pitfall #5). Within-session only: no cross-session persistence, no
# FAISS/re-identification (explicitly OUT of POC, Decision #5) -- this
# calibrator is recreated from scratch every time the process starts.
CALIBRATION_SECONDS = 25.0  # within Decision #5's ~20-30s window
CALIBRATION_DRIFT_EFFECT_SIZE = 0.8  # Cohen's "large effect" convention (Cohen 1988) -- external, not tuned to any face

# Window-validity gate (precursor to Stage 1.5's full quality gate,
# MANDATORY ARCHITECTURE #3). Binary, universal, session-quality facts
# -- NOT per-person expression thresholds, so safe to fix now on n=1
# (Pitfall #5). See classify_window_confidence() for the reasoning.
DETECT_RATE_FLOOR = 0.5           # <50% of the window had a detected face -> unreliable, for any face
YAW_VARIANCE_CEILING_DEG2 = 100.0  # yaw std ~10deg -- roughly a third of the existing 35deg per-frame gate

# --- ATTENTION SIGNAL (V_so, screen orientation) -- Step 1, UNVALIDATED ---
# Every threshold below is a first-cut estimate, explicitly derived from
# the ALREADY-EXISTING 35deg quality-gate bound (same discipline as
# YAW_VARIANCE_CEILING_DEG2 above), NOT fit to any one face (Pitfall #5).
# These are exactly the numbers a Gate-2-style directed test ("look at
# screen" vs "look away") is meant to validate or correct -- do not tune
# them against the developer's own footage.
ATTENTION_YAW_THRESHOLD_DEG = 20.0    # roughly half the 35deg gate -- past this, "trackable" no longer means "facing the screen"
ATTENTION_PITCH_THRESHOLD_DEG = 20.0  # same first-cut magnitude as yaw; no existing pitch precedent to derive from yet
ATTENTION_POSE_WEIGHT = 0.7           # gaze can only ever nudge the score by <=30% -- pose stays dominant so the signal keeps working with glasses (gaze unreliable) or gaze absent entirely
ATTENTION_ORIENTED_SCORE_THRESHOLD = 0.5  # score>=this -> the boolean "oriented" call
GAZE_PLAUSIBLE_SLACK = 0.5             # how far outside the raw [0,1] eye-corner span an iris ratio may sit before it's treated as corrupted (glasses reflection etc.) rather than "looking far to the side"

# --- Verified landmark indices (face_mesh_connections.py contour sets) ---
# IRIS_LEFT_CENTER/IRIS_RIGHT_CENTER: FIXED -- were swapped relative to their
# names (468/473 were assigned backwards) from Stage 1 until this fix. Found
# and root-caused during the attention-signal (V_so) build, confirmed
# empirically against real footage (pose-normalized coordinates), documented
# in IRIS_SWAP_DIAGNOSTIC.md. Verdict there was CONTAINED: only the logged-
# only cheek_raise covariate (compute_v_es) used these constants -- V_es's
# SCORED aperture/composite (via ear()) never referenced them, so the Gate-2
# 71.4% result was never affected and needs no re-scoring. This fix makes
# cheek_raise's own pairing correct going forward; it stays logged-only/
# excluded from Valence regardless (Decision 25) -- fixing the pairing does
# not change that status.
IRIS_LEFT_CENTER = 473
IRIS_RIGHT_CENTER = 468
BROW_INNER_R = 55       # member of FACEMESH_RIGHT_EYEBROW
BROW_INNER_L = 285      # member of FACEMESH_LEFT_EYEBROW
GLABELLA = 168          # member of FACEMESH_NOSE; between-eyebrows/nose-bridge point
EYE_R_OUTER, EYE_R_UPPER1, EYE_R_UPPER2, EYE_R_INNER, EYE_R_LOWER1, EYE_R_LOWER2 = 33, 160, 158, 133, 153, 144
EYE_L_OUTER, EYE_L_UPPER1, EYE_L_UPPER2, EYE_L_INNER, EYE_L_LOWER1, EYE_L_LOWER2 = 263, 385, 387, 362, 373, 380
LIP_UPPER_INNER = 13
LIP_LOWER_INNER = 14
LIP_CORNER_R = 61
LIP_CORNER_L = 291
JAW_ANGLE_R = 172        # FACEMESH_FACE_OVAL, jaw/masseter region
JAW_ANGLE_L = 397        # FACEMESH_FACE_OVAL, jaw/masseter region

# BlazePose topology (stable across mediapipe versions, not re-derived here)
POSE_NOSE = 0
POSE_SHOULDER_L = 11
POSE_SHOULDER_R = 12

PD_BUFFER_SECONDS = 1.5  # "short ~1-2s rolling buffer" (CLAUDE.md V_pd definition)

stop_event = threading.Event()
frame_lock = threading.Lock()
latest_frame = None

readings_lock = threading.Lock()
latest_readings = {"overlay_lines": [], "face_detected": False, "calibrated": False, "va_point": None, "window_flagged": False}


def apply_clahe(frame_bgr):
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_equalized = clahe.apply(l_channel)
    lab_equalized = cv2.merge((l_equalized, a_channel, b_channel))
    return cv2.cvtColor(lab_equalized, cv2.COLOR_LAB2BGR)


def yaw_pitch_roll_from_matrix(matrix_4x4):
    r = np.asarray(matrix_4x4)[:3, :3]
    pitch = np.degrees(np.arctan2(-r[2, 0], np.sqrt(r[0, 0] ** 2 + r[1, 0] ** 2)))
    yaw = np.degrees(np.arctan2(r[1, 0], r[0, 0]))
    roll = np.degrees(np.arctan2(r[2, 1], r[2, 2]))
    return float(yaw), float(pitch), float(roll)


def pose_normalize(face_landmarks, transform_matrix, img_w, img_h):
    """
    Undo head rotation on face landmarks, in a single self-consistent
    coordinate system (isotropic pixel-like units), NOT by mixing
    image-normalized landmarks with the transform matrix's metric
    canonical-model translation (those are different coordinate systems).

    1. Aspect-correct to isotropic units: X=x*W, Y=y*H, Z=z*W (z already
       shares x's normalization base per MediaPipe convention).
    2. Center on the landmark centroid — self-consistent, unlike the
       matrix's translation which lives in the canonical model's frame.
    3. Apply R^T to undo rotation. R is confirmed orthonormal (verified
       empirically: R @ R^T ~= I), so R^T = R^-1 exactly — a clean,
       distortion-free un-rotation.
    """
    pts = np.array([[lm.x * img_w, lm.y * img_h, lm.z * img_w] for lm in face_landmarks])
    centroid = pts.mean(axis=0)
    centered = pts - centroid
    r = np.asarray(transform_matrix)[:3, :3]
    return (r.T @ centered.T).T


def _dist(pts, i, j):
    return float(np.linalg.norm(pts[i] - pts[j]))


def interocular_distance(pts):
    return _dist(pts, IRIS_LEFT_CENTER, IRIS_RIGHT_CENTER)


def compute_v_bf(pts, io_dist):
    """Brow furrow: drop toward the glabella (composite), inner-brow
    convergence logged as a secondary component.

    Rebuild #2, composite = drop_ratio. Rebuild #1 (ratio vs
    eye_outer_span / same-side eye width — a same-extent denominator,
    chosen for yaw-tolerance) was confirmed INVERTED by the
    max-elicitation validity check: 3/3 maximal-furrow reps moved the
    composite the WRONG way. Root cause: eye-width denominators shrink
    under real furrowing too (co-occurring squint at high effort), so
    the ratio divided out the very signal it was meant to measure —
    over-normalization, not weak elicitation.

    This version normalizes by io_dist (inter-ocular iris-center
    distance) instead — expression-independent (iris centers don't move
    with brow/eyelid action). Distance-controlled re-test (holding
    camera distance fixed — the first uncontrolled attempt showed
    escalating wrong-direction drift traced to lean-in during
    concentration, not a formula fault) confirmed BOTH candidates move
    correctly, 3/3 reps:
      drop_ratio        — inner-brow-to-glabella distance / io_dist  (chosen: 3.1-4.4 sigma, more consistent)
      convergence_ratio — inner-brow-to-inner-brow distance / io_dist (logged only: 1.9-4.3 sigma, more variable)

    KNOWN LIMITATION: unlike rebuild #1, this denominator choice
    reintroduces moderate yaw sensitivity (r~=0.25 over a 0-34deg sweep,
    both candidates similar) -- io_dist (a narrow, near-center span)
    doesn't share the same lever-arm as the wide brow-to-glabella span,
    so it doesn't fully cancel yaw-linked landmark bias the way a
    same-extent denominator would. Accepted trade-off: direction-correct
    with moderate yaw noise beats yaw-clean but always-inverted. Watch
    this at Gate 2 -- if real-person validation shows yaw confounding
    genuine furrow reads, this formula needs revisiting, not re-tuning.
    """
    inner_brow_dist = _dist(pts, BROW_INNER_R, BROW_INNER_L)
    convergence_ratio = inner_brow_dist / io_dist

    drop_r = _dist(pts, BROW_INNER_R, GLABELLA) / io_dist
    drop_l = _dist(pts, BROW_INNER_L, GLABELLA) / io_dist
    drop_ratio = (drop_r + drop_l) / 2.0

    # both SHRINK when furrowing; flip sign so higher = more furrow
    composite = -drop_ratio
    return composite, {"convergence_ratio": convergence_ratio, "drop_ratio": drop_ratio}


def compute_v_es(pts, io_dist):
    """Eye crinkle (Duchenne). Composite = aperture only.

    Max-elicitation validity check (3 reps, exaggerated smiles):
    aperture moved correctly and consistently (-2.0 to -2.6 sigma vs
    neutral, 3/3 reps) -- validated as the Duchenne-specific term.
    cheek_raise (iris-to-same-side-lip-corner span, meant to proxy
    midface/cheek compression) moved in the WRONG direction on 3/3 reps
    and was diluting the composite's otherwise-clean signal, so it's
    demoted to a logged-only covariate here, not part of the composite.
    CLAUDE.md's V_es spec calls for "BOTH" aperture and cheek/lower-lid
    tightening -- aperture alone carries V_es for now because it's the
    only piece that's actually validated; a second valid Duchenne term
    can be added later if one is found (a different geometric proxy,
    not a re-tuned version of this one -- the failure was directional,
    not a scale/threshold issue).

    V_es's real validation is still a genuine-vs-posed smile test at
    Stage 1.5, not this max-elicitation check, which only confirms the
    geometry moves the right way at all -- not that it distinguishes
    real from fake smiles.
    """

    def ear(outer, upper1, upper2, inner, lower1, lower2):
        vert = (_dist(pts, upper1, lower1) + _dist(pts, upper2, lower2)) / 2.0
        horiz = _dist(pts, outer, inner)
        return vert / horiz if horiz > 1e-6 else 0.0

    aperture = (
        ear(EYE_R_OUTER, EYE_R_UPPER1, EYE_R_UPPER2, EYE_R_INNER, EYE_R_LOWER1, EYE_R_LOWER2)
        + ear(EYE_L_OUTER, EYE_L_UPPER1, EYE_L_UPPER2, EYE_L_INNER, EYE_L_LOWER1, EYE_L_LOWER2)
    ) / 2.0

    def cheek_raise_side(iris_idx, lip_corner_idx, eye_outer, eye_inner):
        span = _dist(pts, iris_idx, lip_corner_idx)
        local_scale = _dist(pts, eye_outer, eye_inner)
        return span / local_scale if local_scale > 1e-6 else 0.0

    # logged-only covariate, not composited -- see docstring
    cheek_raise_avg = (
        cheek_raise_side(IRIS_RIGHT_CENTER, LIP_CORNER_R, EYE_R_OUTER, EYE_R_INNER)
        + cheek_raise_side(IRIS_LEFT_CENTER, LIP_CORNER_L, EYE_L_OUTER, EYE_L_INNER)
    ) / 2.0

    # aperture shrinks when crinkling; flip sign so higher = more crinkle
    composite = -aperture
    return composite, {"aperture": aperture, "cheek_raise": cheek_raise_avg}


def compute_v_jc(pts, io_dist):
    """Jaw compression — LOGGED-ONLY, not a POC-reliable vector.

    Max-elicitation validity check (3 max-effort jaw-clench reps) found
    no repeatable directional signal: rep1 moved 8.86 sigma in the WRONG
    direction (likely the mouth opened rather than pressed shut for that
    attempt), reps 2-3 stayed within noise either direction. This
    confirms CLAUDE.md's own prediction that jaw compression is largely
    invisible to surface landmark geometry (muscle tension, beard
    occlusion) — now shown empirically even under maximal, repeated
    effort, not just casual attempts.

    Do NOT try to extract more signal here (no new landmark, no new
    ratio) — the data says the surface geometry doesn't carry it, not
    that the formula is wrong. inter_lip_dist and masseter_width keep
    being logged raw as a Track-B covariate; a trained model may
    eventually strengthen this signal from cues geometry can't isolate.
    lip_corner_dist is exploratory, also logged raw.
    """
    inter_lip_dist = _dist(pts, LIP_UPPER_INNER, LIP_LOWER_INNER) / io_dist
    lip_corner_dist = _dist(pts, LIP_CORNER_R, LIP_CORNER_L) / io_dist
    masseter_width = _dist(pts, JAW_ANGLE_R, JAW_ANGLE_L) / io_dist
    composite = -inter_lip_dist
    return composite, {
        "inter_lip_dist": inter_lip_dist,
        "lip_corner_dist": lip_corner_dist,
        "masseter_width": masseter_width,
    }


def compute_v_pd(pd_buffer, nose_world, shoulder_mid_world, now):
    """Postural volatility: variance of nose + shoulder-midpoint world
    position over its own short rolling buffer (distinct from the later
    10s summary window built in step 5)."""
    pd_buffer.append((now, nose_world, shoulder_mid_world))
    while pd_buffer and now - pd_buffer[0][0] > PD_BUFFER_SECONDS:
        pd_buffer.popleft()
    if len(pd_buffer) < 2:
        return None, {"buffer_len": len(pd_buffer)}
    noses = np.array([b[1] for b in pd_buffer])
    shoulders = np.array([b[2] for b in pd_buffer])
    nose_var = float(np.var(noses, axis=0).sum())
    shoulder_var = float(np.var(shoulders, axis=0).sum())
    return nose_var + shoulder_var, {
        "nose_pos_variance": nose_var,
        "shoulder_pos_variance": shoulder_var,
        "buffer_len": len(pd_buffer),
    }


def _gaze_centering_score(pts):
    """SECONDARY/bonus input to compute_v_so -- never a dependency (see
    module docstring's GLASSES-ROBUST section). Reuses the SAME iris
    and eye-corner landmark indices interocular_distance/compute_v_es
    already read (IRIS_LEFT/RIGHT_CENTER, EYE_*_OUTER/INNER) -- no new
    landmarks, no new detection.

    For each eye, computes where the iris sits between that eye's outer
    (temple-side) and inner (nose-side) corner, as a 0..1 ratio (0.5 =
    centered). Deviation-from-0.5 is what's averaged across eyes, NOT
    the raw ratio -- the two eyes' outer->inner axes point in opposite
    literal directions (confirmed by hand-tracing the geometry: gazing
    to one side moves one eye's ratio toward 0 and the other's toward 1
    for the SAME physical gaze shift), so averaging raw ratios would
    cancel out and hide lateral gaze. Averaging |deviation| instead
    sidesteps that entirely, since both eyes' deviation grows together
    regardless of which raw direction each one moved.

    Reliability is judged geometrically, not via any confidence score
    (Tasks output carries none per-landmark, Decision 14): MediaPipe
    doesn't report "the iris is disappearing behind a glasses reflection"
    -- it silently returns a landmark position, which glasses corrupt
    into being far outside the anatomically plausible eye-corner span.
    A ratio further than GAZE_PLAUSIBLE_SLACK past [0, 1] is treated as
    corrupted and excluded, not as "an extreme side-glance".

    Returns (score, reliable). score is only meaningful when
    reliable=True -- same "ignore the value when the flag says so"
    convention as every other None-on-uncomputable value in this file.
    Never raises: a degenerate (zero-width) eye span for either eye is
    just excluded, same as an implausible ratio.

    IRIS_LEFT_CENTER/IRIS_RIGHT_CENTER pair with their same-named
    EYE_L_*/EYE_R_* corners directly below -- no workaround needed here.
    (Historical note: this function originally had to invert that
    pairing locally because the two constants were defined backwards at
    the time; that has since been fixed at the constant definitions
    themselves -- see IRIS_SWAP_DIAGNOSTIC.md -- so the natural, named
    pairing is correct again.)
    """

    def eye_ratio(outer_idx, inner_idx, iris_idx):
        outer_x, inner_x = pts[outer_idx][0], pts[inner_idx][0]
        span = inner_x - outer_x
        if abs(span) < 1e-6:
            return None
        return (pts[iris_idx][0] - outer_x) / span

    r_ratio = eye_ratio(EYE_R_OUTER, EYE_R_INNER, IRIS_RIGHT_CENTER)
    l_ratio = eye_ratio(EYE_L_OUTER, EYE_L_INNER, IRIS_LEFT_CENTER)

    deviations = []
    for ratio in (r_ratio, l_ratio):
        if ratio is not None and -GAZE_PLAUSIBLE_SLACK <= ratio <= 1.0 + GAZE_PLAUSIBLE_SLACK:
            deviations.append(min(abs(ratio - 0.5) / 0.5, 1.0))  # 0 = centered, 1 = at/past either corner

    if not deviations:
        return None, False

    avg_deviation = sum(deviations) / len(deviations)
    # float(...): pts is a numpy array, so every value above is numpy-typed
    # (np.float64) -- cast to native Python here, same discipline
    # WindowAccumulator._stats already uses, so this can never trip up
    # json.dumps() when it's logged (numpy scalars are not JSON-serializable).
    return float(max(0.0, 1.0 - avg_deviation)), True


def compute_v_so(normalized_pts, yaw_deg, pitch_deg):
    """Screen orientation (V_so) -- ATTENTION SIGNAL Step 1. See the
    module docstring's ATTENTION SIGNAL section for the full design
    rationale (glasses-robust-by-construction, no calibration needed,
    honest-framing rule). Summary:

    PILOT-ONLY, NOT POC-ready (documentation only, see module docstring's
    PILOT STATUS section): pitch_deg's contribution below is UNRELIABLE
    by structural limit of single-camera landmark head-pose (face
    foreshortening on look-down degrades the landmark data, not a bug in
    this formula or in yaw_pitch_roll_from_matrix) -- do NOT attempt to
    "fix" pitch. yaw_deg's contribution is reliable. Do not change the
    computation below on the strength of this comment.

    PRIMARY = head pose. yaw_deg/pitch_deg are NOT recomputed here --
    passed in straight from yaw_pitch_roll_from_matrix(matrix), the
    SAME decomposition the quality gate already runs every cycle.
    Reduces linearly from 1.0 at dead-center to 0.0 at
    ATTENTION_YAW_THRESHOLD_DEG / ATTENTION_PITCH_THRESHOLD_DEG,
    whichever axis is further off-center.

    SECONDARY = gaze (_gaze_centering_score), blended in at
    ATTENTION_POSE_WEIGHT:(1-ATTENTION_POSE_WEIGHT) ONLY when
    geometrically plausible -- otherwise the score is pose alone and
    components["head_pose_only"] is stamped True so every consumer
    (overlay, log, a future validation pass) can see the fallback
    engaged, never silently.

    Returns (orientation_score, components) -- same 2-tuple shape as
    compute_v_bf/v_es/v_jc/v_pd. components["oriented"] is the
    thresholded boolean call (score >= ATTENTION_ORIENTED_SCORE_THRESHOLD),
    included for direct use in a Gate-2-style commanded-direction check
    ("look at screen" should read oriented=True; "look away"/"look
    down" should read oriented=False) -- see AttentionWindowAccumulator
    for the per-window rollup this feeds (oriented_rate) that a human
    scorer would actually compare against the commanded label. Every
    caller must treat this as UNVALIDATED (module docstring) -- it is
    not auto-scored anywhere in this codebase.
    """
    yaw_frac = min(abs(yaw_deg) / ATTENTION_YAW_THRESHOLD_DEG, 1.0) if yaw_deg is not None else 1.0
    pitch_frac = min(abs(pitch_deg) / ATTENTION_PITCH_THRESHOLD_DEG, 1.0) if pitch_deg is not None else 1.0
    pose_score = max(0.0, 1.0 - max(yaw_frac, pitch_frac))

    gaze_score, gaze_reliable = _gaze_centering_score(normalized_pts)

    if gaze_reliable:
        orientation_score = ATTENTION_POSE_WEIGHT * pose_score + (1.0 - ATTENTION_POSE_WEIGHT) * gaze_score
        head_pose_only = False
    else:
        orientation_score = pose_score
        head_pose_only = True

    oriented = orientation_score >= ATTENTION_ORIENTED_SCORE_THRESHOLD

    components = {
        "oriented": oriented,
        "pose_score": pose_score,
        "gaze_score": gaze_score if gaze_reliable else None,
        "gaze_reliable": gaze_reliable,
        "head_pose_only": head_pose_only,
        "yaw_deg": yaw_deg,
        "pitch_deg": pitch_deg,
    }
    return orientation_score, components


# ============================================================
# EXPERIMENTAL SIGNALS, PART 2 -- gaze direction (L/R/C) + blink rate.
# NEW, ISOLATED, UNVALIDATED additions (distinct from V_so above, though
# compute_gaze_direction reuses the SAME landmarks/ratio approach
# _gaze_centering_score uses). Neither is composited into any affect
# vector, neither touches WindowAccumulator/NeutralCalibrator/
# AttentionWindowAccumulator, and neither has been validated across
# people -- same "keep the code, mark it clearly, don't wire it into
# anything it hasn't earned" discipline as CLAUDE.md's "Attention /
# screen-orientation -- PILOT, not POC" note. Horizontal gaze only:
# vertical/up-down gaze is NEVER computed, here or anywhere -- it would
# degrade under the exact same face-foreshortening failure mode already
# confirmed for head pitch.
# ============================================================
GAZE_DIRECTION_DEVIATION_THRESHOLD = 0.25  # first-cut estimate (0=centered..1=at eye corner, same deviation metric _gaze_centering_score uses internally) -- NOT tuned to one face, pending the same kind of cross-person directed-capture validation V_so itself is still waiting on
GAZE_LABEL_SIGN = -1  # which sign of (r_ratio - l_ratio) maps to the word "RIGHT" vs "LEFT". CONFIRMED BACKWARDS at +1 by live on-camera testing (looking to the person's own left read "RIGHT") and flipped to -1 to fix it -- the direction is now reported from the PERSON'S OWN perspective (their own left reads "LEFT"), same convention as everyday mirror-vs-camera intuition. Only relabels the word, never changes raw_shift, reliability, or the CENTER/UNKNOWN calls -- if a future camera/setup shows it backwards again, flip this single constant back rather than touching the ratio math above.


def compute_gaze_direction(pts):
    """EXPERIMENTAL / UNVALIDATED -- coarse horizontal gaze label: one
    of "LEFT" / "RIGHT" / "CENTER" / "UNKNOWN". Reuses the exact
    landmarks and per-eye ratio formula _gaze_centering_score already
    uses (IRIS_LEFT_CENTER/IRIS_RIGHT_CENTER against EYE_*_OUTER/INNER,
    same GAZE_PLAUSIBLE_SLACK corruption gate) -- this is a NEW,
    separate function rather than a change to that one because
    _gaze_centering_score deliberately discards direction (it only
    needs "how far off center" for V_so's blended score, never "which
    way"): it averages each eye's |ratio-0.5| deviation, which cancels
    sign. Its own docstring explains why that cancellation is correct
    for ITS purpose but wrong for this one: a real lateral gaze shift
    moves the two eyes' RAW ratios in OPPOSITE directions (one toward 0,
    the other toward 1) for the same physical shift, so the SIGNED
    difference (r_ratio - l_ratio) grows/shrinks consistently with real
    gaze direction, where an average-of-magnitudes would erase it.

    Reliability uses the SAME corruption gate _gaze_centering_score
    already applies (a ratio further than GAZE_PLAUSIBLE_SLACK outside
    [0,1] is glasses-reflection/occlusion corruption, not a real extreme
    glance) -- reused unchanged, not re-derived. Returns
    ("UNKNOWN", False, None) whenever either eye's ratio is missing or
    implausible: never guesses a direction from a single eye, never
    reports a stale/guessed label.

    Returns (label, reliable, raw_shift). raw_shift is the signed
    geometric value (real, kept for Track-B logging richness) -- NEVER
    surfaced in the UI as a precise angle; display only ever shows the
    discrete label, per this feature's own "coarse, not precise" rule.
    """

    def eye_ratio(outer_idx, inner_idx, iris_idx):
        outer_x, inner_x = pts[outer_idx][0], pts[inner_idx][0]
        span = inner_x - outer_x
        if abs(span) < 1e-6:
            return None
        return (pts[iris_idx][0] - outer_x) / span

    def plausible(ratio):
        return ratio is not None and -GAZE_PLAUSIBLE_SLACK <= ratio <= 1.0 + GAZE_PLAUSIBLE_SLACK

    r_ratio = eye_ratio(EYE_R_OUTER, EYE_R_INNER, IRIS_RIGHT_CENTER)
    l_ratio = eye_ratio(EYE_L_OUTER, EYE_L_INNER, IRIS_LEFT_CENTER)

    if not (plausible(r_ratio) and plausible(l_ratio)):
        return "UNKNOWN", False, None

    shift = float(r_ratio - l_ratio)
    if abs(shift) < GAZE_DIRECTION_DEVIATION_THRESHOLD:
        return "CENTER", True, shift
    return ("RIGHT" if (shift * GAZE_LABEL_SIGN) > 0 else "LEFT"), True, shift


# --- Blink rate (blinks/min) -- EXPERIMENTAL / UNVALIDATED ---
# Reuses V_es's own eye-aperture value (compute_v_es's returned
# es_components["aperture"], read-only): this section computes NO new
# landmark geometry and does not reimplement or touch ear()/aperture
# itself, per this feature's own hard constraint.

BLINK_ROLLING_MAX_SECONDS = 3.0      # "recent eyes-open" reference window -- adapts to lighting/face-size drift instead of needing its own calibration pass
# BLINK_CLOSE_FRACTION / BLINK_REOPEN_FRACTION -- RE-TUNED against REAL
# logged aperture data from this user (not a generic EAR-literature
# guess): open-eye baseline ~0.45-0.50; a real blink dips only to
# ~0.38-0.41, i.e. ~0.80-0.85x of baseline, before tracking typically
# LOSES the eye entirely (reads None) at full closure -- this formula/
# geometry never approaches the near-zero values classic EAR literature
# describes. The OLD close_fraction (0.6) required aperture to fall
# below 0.6x baseline (~0.28 at a 0.47 baseline) to register as
# "closing" -- a real blink here never gets remotely that low, so
# "closing" was never entered at all and the count stayed 0 no matter
# what the plausibility floor was set to (that was a red herring for
# THIS user's data, even though it was a real fix for the generic case).
# close_fraction=0.87 sits just above the shallowest observed dip ratio
# (0.85), so a 0.38-0.41 dip from a ~0.45-0.50 baseline reliably crosses
# it (0.40/0.47=0.851 < 0.87), while staying comfortably below normal
# open-eye stability (small frame-to-frame jitter, not a 13%+ dip).
# reopen_fraction=0.90 sits above close_fraction (proper hysteresis --
# harder to CONFIRM than to START, so a value that merely wobbles near
# the close boundary can't complete a false blink cycle) while still
# being a realistic recovery target given the same 0.45-0.50 open range.
BLINK_CLOSE_FRACTION = 0.87
BLINK_REOPEN_FRACTION = 0.90
BLINK_MIN_DURATION_SECONDS = 0.05    # a closure shorter than this is more likely landmark jitter than a real blink
BLINK_MAX_DURATION_SECONDS = 0.6     # a closure longer than this looks like eyes-closed/looking away, not a blink. Sits in the middle of the ~500-700ms range real-world blink-detection tolerance suggests -- generous enough for a real ~150-300ms blink plus this pipeline's ~10-15Hz sampling/tracking latency, short enough to firmly exclude a deliberate multi-second eyes-closed pause or sustained occlusion. This cap is now the PRIMARY safeguard against miscounting sustained no-face/occlusion as a blink (see update()'s None-handling below) -- not tuned to one face.
BLINK_REFRACTORY_SECONDS = 0.15      # after a confirmed blink, suppress a NEW "closing" entry for this long -- debounces one physical blink into being counted exactly once even if tracking noise wobbles right at the close/reopen boundary while settling back to steady "open". Short enough to not suppress a genuine rapid double-blink (physiologically those can be a few hundred ms apart).
# BLINK_APERTURE_PLAUSIBLE_MIN/MAX -- a sanity range on the raw aperture
# ratio, NOT the close/reopen logic (that's fraction-of-baseline, see
# above). This user's real data shows full closure typically reads as
# None (tracking lost) rather than a very small positive number, which
# is now handled explicitly in update() rather than by this floor --
# see the None-tolerance comment there. 0.01 remains a reasonable safety
# net for a genuinely degenerate near-zero reading (corrupted landmarks,
# not a closed eye) on setups where closure DOES read as a tiny number
# instead of None.
BLINK_APERTURE_PLAUSIBLE_MIN = 0.01
BLINK_APERTURE_PLAUSIBLE_MAX = 0.6
BLINK_RATE_WINDOW_SECONDS = 30.0     # rolling window the reported rate is computed over
BLINK_MIN_OBSERVATION_SECONDS = 20.0  # below this much reliable observation time, report "measuring" instead of a number -- a rate computed from a handful of seconds swings wildly per additional blink
BLINK_JUST_BLINKED_FLASH_SECONDS = 0.3  # how long snapshot()'s "just_blinked" diagnostic flag stays True after a confirmed blink -- purely a UI-flash duration, not part of detection logic


class BlinkDetector:
    """EXPERIMENTAL / UNVALIDATED. Simple relative-threshold state
    machine (open -> closing -> confirmed-or-abandoned), not a trained
    classifier -- deliberately coarse, matching this feature's own
    "simple, honest, not fabricated" brief. Isolated: never touches
    NeutralCalibrator, WindowAccumulator, or any affect vector; feeds
    nothing into Valence/Arousal.

    update(aperture, now) must be called every processing cycle,
    including with aperture=None when no face is detected.

    None-HANDLING, REVISED against real evidence: an EARLIER version
    treated any None/implausible reading as an immediate abort of an
    in-progress "closing" state. Real logged data showed the deepest
    part of a genuine blink frequently reads as None (tracking loses the
    eye at full closure) -- aborting on that discarded real blinks
    before they could ever be confirmed, which was BUG 2 behind the
    count staying 0 (alongside BUG 1, BLINK_CLOSE_FRACTION being far too
    strict -- see its own comment above).

    Now: a None/implausible reading while OPEN does nothing (there is no
    closing episode to abort or start -- it is simply "no reliable data
    this cycle"). A None/implausible reading while CLOSING is TOLERATED
    -- the state simply stays "closing" and keeps waiting for a plausible
    reopen reading, bounded ONLY by BLINK_MAX_DURATION_SECONDS (measured
    in real wall-clock time since the closing episode started, so a
    None-gap's duration counts against that cap same as a low-but-
    plausible reading would). This is what correctly tells apart a SHORT
    tracking-loss gap in the middle of a real blink (confirmed once
    tracking returns and recovers, well inside the cap) from a LONG
    None run -- occlusion, looking away, the person leaving -- which
    still gets abandoned, never confirmed, once duration exceeds the cap.
    Phantom blinks are still impossible: nothing is ever counted from a
    None reading itself, only from a real recovery-above-baseline
    reading that arrives before the cap expires.

    A BLINK_REFRACTORY_SECONDS debounce after each confirmed blink
    prevents a single physical blink's own tracking noise (settling back
    toward "open") from immediately re-triggering a second false count.

    Returns True the one time a blink is confirmed on that call, else
    False -- callers that want a per-window blink COUNT (for logging)
    should tally these return values themselves rather than reaching
    into this class's internals.

    snapshot(now) reports the rolling rate PLUS diagnostic fields
    (last_aperture, current_state, rolling_max, just_blinked) added
    specifically so a human can watch real aperture/state live and
    verify detection against real behavior, instead of trusting a
    tuned-in-the-dark threshold. Returns measuring=True (rate_per_min=
    None) until BLINK_MIN_OBSERVATION_SECONDS of reliable observation
    have accumulated -- never a number computed from too little data.
    """

    def __init__(self):
        self._recent = deque()       # (t, aperture) pairs, trimmed to BLINK_ROLLING_MAX_SECONDS -- this detector's own rolling "eyes open" reference
        self._state = "open"         # or "closing"
        self._closing_start_t = None
        self._blink_times = deque()  # confirmed-blink timestamps, trimmed to BLINK_RATE_WINDOW_SECONDS
        self._first_observation_t = None
        self._last_aperture = None          # diagnostic only -- most recent raw aperture seen, live, never carried-forward-stale (None means "no current reading", not "unknown")
        self._last_blink_confirmed_t = None  # drives BOTH snapshot()'s transient just_blinked flag AND the refractory debounce above

    def update(self, aperture, now):
        self._last_aperture = aperture  # diagnostic: reflects the RAW value every call, even None/implausible, so a human watching can see exactly what the detector saw
        plausible = aperture is not None and BLINK_APERTURE_PLAUSIBLE_MIN <= aperture <= BLINK_APERTURE_PLAUSIBLE_MAX

        if plausible:
            if self._first_observation_t is None:
                self._first_observation_t = now
            self._recent.append((now, aperture))
            while self._recent and now - self._recent[0][0] > BLINK_ROLLING_MAX_SECONDS:
                self._recent.popleft()
        rolling_max = max((a for _, a in self._recent), default=None)

        blink_confirmed = False
        if self._state == "open":
            # A None/implausible reading here is simply "no data this
            # cycle" -- nothing to start. Only a real, plausible dip
            # below the close threshold begins a closing episode.
            if plausible and rolling_max is not None and rolling_max > 1e-6 and aperture < BLINK_CLOSE_FRACTION * rolling_max:
                in_refractory = self._last_blink_confirmed_t is not None and (now - self._last_blink_confirmed_t) < BLINK_REFRACTORY_SECONDS
                if not in_refractory:
                    self._state = "closing"
                    self._closing_start_t = now
        else:  # closing
            duration = now - self._closing_start_t
            if duration > BLINK_MAX_DURATION_SECONDS:
                # Been "closing" too long -- whether that time was spent
                # at a low-but-plausible reading or a None tracking-loss
                # gap (or both), this now looks like sustained occlusion/
                # eyes-closed/looking away, not a blink. Checked BEFORE
                # the reopen check below on purpose: a late reopen after
                # already exceeding the cap should still NOT count.
                self._state = "open"
                self._closing_start_t = None
            elif plausible and rolling_max is not None and rolling_max > 1e-6 and aperture >= BLINK_REOPEN_FRACTION * rolling_max:
                if duration >= BLINK_MIN_DURATION_SECONDS:
                    self._blink_times.append(now)
                    self._last_blink_confirmed_t = now
                    blink_confirmed = True
                # else: reopened suspiciously fast to be a real blink --
                # more likely a single noisy sample; not counted
                self._state = "open"
                self._closing_start_t = None
            # else: still below the recovery bar, or this sample is
            # None/implausible (tracking still lost mid-blink) -- remain
            # "closing" and keep waiting, bounded by the max-duration
            # check above on the NEXT call.

        while self._blink_times and now - self._blink_times[0] > BLINK_RATE_WINDOW_SECONDS:
            self._blink_times.popleft()
        return blink_confirmed

    def snapshot(self, now):
        just_blinked = self._last_blink_confirmed_t is not None and (now - self._last_blink_confirmed_t) < BLINK_JUST_BLINKED_FLASH_SECONDS
        rolling_max = max((a for _, a in self._recent), default=None)
        # float(...): aperture values originate from a numpy-array-backed
        # computation (compute_v_es's ear()), so these can be numpy
        # scalars -- cast to native Python here, same discipline
        # WindowAccumulator._stats already uses, so this can never trip
        # up json.dumps() when logged.
        diagnostic = {
            "last_aperture": float(self._last_aperture) if self._last_aperture is not None else None,
            "current_state": self._state,
            "rolling_max": float(rolling_max) if rolling_max is not None else None,
            "just_blinked": just_blinked,
        }
        if self._first_observation_t is None or (now - self._first_observation_t) < BLINK_MIN_OBSERVATION_SECONDS:
            return {"rate_per_min": None, "measuring": True, "blinks_in_rate_window": len(self._blink_times), "unvalidated": True, **diagnostic}
        elapsed = min(now - self._first_observation_t, BLINK_RATE_WINDOW_SECONDS)
        rate = (len(self._blink_times) / elapsed) * 60.0 if elapsed > 0 else None
        return {"rate_per_min": rate, "measuring": False, "blinks_in_rate_window": len(self._blink_times), "unvalidated": True, **diagnostic}


def classify_window_confidence(detection_rate, yaw_variance_deg2):
    """Binary window-validity gate. Deliberately dumb: either condition
    alone marks the window low-confidence (OR, not a weighted score) --
    no combining, no weighting, no per-person tuning (Pitfall #5). This
    is a session-quality fact true for any face, same spirit as the
    existing face<80px/yaw>35deg per-frame gate, just measured over a
    10s window instead of one frame:

      detect_rate < DETECT_RATE_FLOOR: the face wasn't reliably tracked
      for at least half the window -- unreliable regardless of who's in
      frame.

      yaw_variance > YAW_VARIANCE_CEILING_DEG2: the head moved through
      an unstable range within this one window (std ~10deg+) -- this is
      what the step-4 finding (facial vectors are direction-reliable but
      magnitude-noisy under rotation) means downstream: don't trust the
      avg/peak from a window where yaw itself was this unsettled.

    Returns (is_low_confidence: bool, reasons: list[str]). Flagged, not
    suppressed -- step 6 should show "reading unstable" rather than
    silently going blank, per the flag-not-suppress call already made
    for this gate.
    """
    reasons = []
    if detection_rate < DETECT_RATE_FLOOR:
        reasons.append(f"detect_rate {detection_rate:.2f} < floor {DETECT_RATE_FLOOR}")
    if yaw_variance_deg2 is not None and yaw_variance_deg2 > YAW_VARIANCE_CEILING_DEG2:
        reasons.append(f"yaw_variance {yaw_variance_deg2:.1f} > ceiling {YAW_VARIANCE_CEILING_DEG2}")
    return (len(reasons) > 0), reasons


def classify_calibration_quality(samples, composite_keys, yaw_vals):
    """In-capture contamination flag for the neutral-calibration window.
    Same pattern as classify_window_confidence: binary flags, universal
    thresholds, NOT tuned to any one person's face (Pitfall #5), and a
    FLAG not an auto-reject -- a contaminated "neutral" should be
    surfaced for the operator to consider redoing, not silently
    discarded or silently accepted.

    Two checks:
      1. Movement: reuses the SAME yaw_variance ceiling already
         established for the window-validity gate (not a new number) --
         head movement during "neutral" holding is a session-quality
         fact regardless of who's in frame.
      2. Expression drift: splits the capture in half and compares each
         composite vector's mean between halves, standardized by the
         pooled within-half std (a scale-free effect size, so it works
         identically regardless of a vector's raw magnitude). Trigger is
         Cohen's conventional "large effect" (d=0.8, Cohen 1988) -- an
         external, domain-standard convention, not reverse-engineered
         from this session's own data. Catches "started neutral,
         drifted into and held an expression" during the capture --
         exactly what a genuinely stable neutral capture should NOT
         show, and exactly what a hard variance-magnitude cutoff
         couldn't catch cleanly across vectors of very different scale.

    KNOWN BLIND SPOT (confirmed empirically, not theoretical): a
    contamination held CONSTANT from the very first sample is
    invisible to both checks. Tested directly in
    stage1_step8_calibration_repeat_test.py round 4 (a deliberate faint
    smile held for the full 25s) -- the flag returned OK. Root cause:
    both checks are WITHIN-CAPTURE statistics (movement variance,
    first-half-vs-second-half drift); a uniform bias present from t=0
    produces low variance and zero drift, identical to a genuinely
    calm, stable neutral. Detecting it would require an external
    reference -- either cross-session/population data on what "normal"
    neutral values look like (out of POC scope, Decision #5) or a
    per-face tuned reference (Pitfall #5). Both are the wrong fix right
    now. Do NOT try to close this gap in software -- the mitigation is
    procedural: the calibration UX shows live raw values on-screen
    specifically so a human running Gate 2 can eyeball a resting face
    that looks off, which this flag structurally cannot.

    PER-VECTOR REPORTING (not just a session-level yes/no): the drift
    check fired on 3 of 4 real calibration attempts in this session
    (v_es, then v_pd, then v_bf, across separate runs) -- this is NOT
    the threshold being oversensitive. For v_es specifically, it's the
    SAME neutral-drift already found independently by the repeat-
    calibration test (~0.02 spread across back-to-back captures,
    Decision 44) showing up from a second angle, inside a single
    capture instead of across several. Loosening the threshold would
    hide that real instability, not fix it. So this returns WHICH
    vector(s) drifted, tagged with their VECTOR_RELIABILITY, so a
    consumer (console output, future Gate 2 tooling) can read a v_es
    flag as "expected -- known-noisy vector, not a protocol problem"
    and a v_bf flag as "unexpected -- investigate, this vector's
    neutral is otherwise stable" (repeat-calibration range 0.0005).
    Same flag, different meaning depending on which vector tripped it.
    """
    reasons = []
    drifted_vectors = []  # structured, per-vector: [{"vector","effect_size","reliability","interpretation"}]

    yaw_variance = float(np.var(yaw_vals)) if len(yaw_vals) >= 2 else None
    if yaw_variance is not None and yaw_variance > YAW_VARIANCE_CEILING_DEG2:
        reasons.append(f"head movement during capture: yaw_variance={yaw_variance:.1f} > ceiling {YAW_VARIANCE_CEILING_DEG2}")

    n = len(samples)
    if n >= 20:
        mid = n // 2
        first_half, second_half = samples[:mid], samples[mid:]
        for key in composite_keys:
            v1 = np.array([v for v in (s["composite"].get(key) for s in first_half) if v is not None])
            v2 = np.array([v for v in (s["composite"].get(key) for s in second_half) if v is not None])
            if len(v1) < 5 or len(v2) < 5:
                continue
            pooled_std = np.sqrt((v1.var() + v2.var()) / 2.0)
            if pooled_std < 1e-9:
                continue
            effect_size = abs(v1.mean() - v2.mean()) / pooled_std
            if effect_size >= CALIBRATION_DRIFT_EFFECT_SIZE:
                reliability = VECTOR_RELIABILITY.get(key)
                interpretation = (
                    "expected -- known-noisy vector, not a protocol problem"
                    if reliability == "low"
                    else "unexpected -- investigate, this vector's neutral is otherwise stable"
                )
                drifted_vectors.append(
                    {"vector": key, "effect_size": effect_size, "reliability": reliability, "interpretation": interpretation}
                )
                reasons.append(
                    f"{key} drifted mid-capture: effect_size={effect_size:.2f} >= {CALIBRATION_DRIFT_EFFECT_SIZE} ({interpretation})"
                )

    return (len(reasons) > 0), reasons, drifted_vectors


class NeutralCalibrator:
    """Stage 1.5, step 8: per-person within-session neutral calibration.

    Runs ONCE at session start, for a fixed CALIBRATION_SECONDS -- same
    duration for everyone, no per-person tuning of the calibration
    procedure itself (Pitfall #5).

    Before completion: system is UNCALIBRATED. Per Gap 2 L1 / Pitfall
    #3, there is no confident reading to report yet during this phase
    -- callers must check is_calibrated() and surface an explicit
    "calibrating" state (cold-start), never a reading built on an
    incomplete or absent baseline.

    After completion: the neutral reference is FROZEN for the rest of
    the process. Within-session only -- no cross-session persistence,
    no FAISS/re-identification, no re-calibration trigger (Decision #5:
    explicitly OUT of POC scope). deviation() reports every subsequent
    sample relative to THIS person's own resting values, not a raw
    magnitude -- this is the fix for Pitfall #2 (one person's neutral
    brow is another's furrow): only the deviation is comparable across
    people, never the raw number alone.

    Keeps mean AND spread (std) per vector. The spread is this person's
    own noise floor -- logged so Gate 2 can later judge whether a
    deviation is a real signal or within this person's own natural
    jitter. Not used as a threshold here: that judgment needs real
    multi-person data (Pitfall #5) -- calibration only hands off the
    raw ingredient (mean, std, n), it does not decide what counts as
    "significant".

    Covariates (V_jc, V_bf's convergence_ratio, V_es's cheek_raise) get
    a neutral reference too (for Track-B completeness) but are not
    reported as deviation anywhere -- they're logged-only, same as
    their windowed raw values in step 5.
    """

    COMPOSITE_KEYS = ("v_bf", "v_es", "v_pd")
    COVARIATE_KEYS = ("v_jc", "v_bf_convergence_ratio", "v_es_cheek_raise")

    def __init__(self, calibration_seconds=CALIBRATION_SECONDS):
        self.calibration_seconds = calibration_seconds
        self.start_ts = None
        self.samples = []
        self.reference = None  # frozen once complete

    def is_calibrated(self):
        return self.reference is not None

    def seconds_remaining(self, now):
        if self.start_ts is None:
            return self.calibration_seconds
        return max(0.0, self.calibration_seconds - (now - self.start_ts))

    def add_sample(self, ts, composite, covariate, yaw_deg=None):
        if self.is_calibrated():
            return
        if self.start_ts is None:
            self.start_ts = ts
        self.samples.append({"composite": composite, "covariate": covariate, "yaw_deg": yaw_deg})

    def should_complete(self, now):
        return (
            not self.is_calibrated()
            and self.start_ts is not None
            and (now - self.start_ts) >= self.calibration_seconds
        )

    @staticmethod
    def _stats(samples, bucket, key):
        vals = [v for v in (s[bucket].get(key) for s in samples) if v is not None]
        if not vals:
            return {"mean": None, "std": None, "n": 0}
        arr = np.array(vals)
        return {"mean": float(arr.mean()), "std": float(arr.std()), "n": len(vals)}

    def complete(self, now):
        yaw_vals = [s["yaw_deg"] for s in self.samples if s["yaw_deg"] is not None]
        possibly_not_neutral, reasons, drifted_vectors = classify_calibration_quality(
            self.samples, self.COMPOSITE_KEYS, yaw_vals
        )
        self.reference = {
            "person_label": PERSON_LABEL,
            "calibrated_at_monotonic": now,
            "calibration_seconds": now - self.start_ts,
            "composite": {k: self._stats(self.samples, "composite", k) for k in self.COMPOSITE_KEYS},
            "covariates": {k: self._stats(self.samples, "covariate", k) for k in self.COVARIATE_KEYS},
            # in-capture contamination flag -- see classify_calibration_quality.
            # Flagged, not auto-rejected: the operator decides whether to redo.
            # drifted_vectors is the structured, per-vector form (machine-
            # readable for future Gate 2 tooling); reasons is the same
            # information as human-readable strings.
            "quality": {"possibly_not_neutral": possibly_not_neutral, "reasons": reasons, "drifted_vectors": drifted_vectors},
        }
        return self.reference

    def deviation(self, key, raw_value):
        """Deviation from this person's own neutral -- what step 6 must
        consume, never the raw value (Pitfall #2)."""
        if not self.is_calibrated() or raw_value is None:
            return None
        mean = self.reference["composite"].get(key, {}).get("mean")
        if mean is None:
            return None
        return raw_value - mean


class WindowAccumulator:
    """Step 5: the 10s rolling window (avg + peak + variance).

    Two-clock cadence (CADENCE): continuous sampling (add_sample, called
    every processing cycle) feeds this buffer; a 10s tick (should_flush/
    flush, checked once per cycle against the same clock) emits one
    summary and resets — a tumbling, non-overlapping window. This is
    what makes Gap 1 hold: "a 5s spike then neutral at s10 must still
    show in peak" needs every sample in [0s,10s) considered together,
    not just whatever's live at the 10s mark.

    Composite vectors (V_bf, V_es, V_pd) and logged-only covariates
    (V_jc, V_bf's convergence_ratio, V_es's cheek_raise) are collected
    into two SEPARATE, hardcoded buckets — not one generic "window
    every key" loop — specifically so a logged-only signal can't drift
    into this summary by accident. "Composite" here means "gets its own
    deviation/z-score tracked", NOT "feeds the V/A formula": per Decision
    18 (Gate 2), only V_es and V_pd actually feed
    map_to_valence_arousal()'s Valence/Arousal -- V_bf stays in this
    bucket so its own calibrated reading keeps getting logged and shown
    (Stage 3's demo bars, Track-B), but is excluded from the formula
    itself (Decision 17: did not generalize). Add a new covariate here
    explicitly if one shows up; never widen the composite set without a
    validity check backing it (see step 4 history).

    Peak policy (explicit, per CLAUDE.md CADENCE — decide and document,
    don't leave implicit): all three composites use plain max() over
    the window, which IS "max in the expression direction" here,
    because every composite was deliberately sign-flipped during step 4
    so higher = more expression (V_bf: more furrow: V_es: more crinkle;
    V_pd: more postural volatility, already non-negative by
    construction, so max-abs and max coincide anyway). Pre-calibration,
    there's no neutral baseline to deviate below zero from, so there is
    no separate "negative-direction spike" to also catch with
    max-absolute-deviation — that distinction only becomes real once
    Stage 1.5 turns these into deviation-from-neutral values, where an
    unusually-relaxed low reading could also be informative. Revisit
    peak policy there; max() is correct for the current raw-value
    schema.

    variance is the confidence signal for that window, not just a
    logged stat: a high-variance window (mid head-turn, unstable
    tracking) is a low-trust reading, by the direction-reliable/
    magnitude-noisy-under-rotation finding from step 4 validation.
    yaw_variance_deg2 and detection_rate are logged alongside each
    window as the raw ingredients a future confidence gate/weight needs.
    They are deliberately NOT combined into one hardcoded confidence
    number here — that combination should be calibrated across the
    8-12 person Gate 2 set (Stage 1.5), not guessed from n=1 data
    (Pitfall #5).
    """

    def __init__(self):
        self.window_start = None
        self.samples = []

    def add_sample(self, ts, detected, yaw_deg, composite, covariate):
        if self.window_start is None:
            self.window_start = ts
        self.samples.append(
            {"ts": ts, "detected": detected, "yaw_deg": yaw_deg, "composite": composite, "covariate": covariate}
        )

    def should_flush(self, now, window_seconds=WINDOW_SECONDS):
        return self.window_start is not None and (now - self.window_start) >= window_seconds

    @staticmethod
    def _stats(samples, getter):
        vals = [v for v in (getter(s) for s in samples) if v is not None]
        if not vals:
            return {"avg": None, "peak": None, "variance": None, "n": 0}
        arr = np.array(vals)
        return {"avg": float(arr.mean()), "peak": float(arr.max()), "variance": float(arr.var()), "n": len(vals)}

    def flush(self, now):
        window_start = self.window_start
        samples = self.samples
        n_samples = len(samples)
        n_detected = sum(1 for s in samples if s["detected"])

        yaw_vals = [s["yaw_deg"] for s in samples if s["yaw_deg"] is not None]
        detection_rate = (n_detected / n_samples) if n_samples else 0.0
        yaw_variance_deg2 = float(np.var(yaw_vals)) if len(yaw_vals) >= 2 else None
        low_confidence, reasons = classify_window_confidence(detection_rate, yaw_variance_deg2)

        summary = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "window_summary",
            "session_id": SESSION_ID,
            "person_label": PERSON_LABEL,
            "window_start_monotonic": window_start,
            "window_end_monotonic": now,
            "window_seconds": now - window_start,
            "n_samples": n_samples,
            "n_detected": n_detected,
            "detection_rate": detection_rate,
            "yaw_mean_deg": float(np.mean(yaw_vals)) if yaw_vals else None,
            "yaw_variance_deg2": yaw_variance_deg2,
            # window-validity gate: flagged, not suppressed -- step 6
            # should render "reading unstable", not silently drop the
            # window. See classify_window_confidence() docstring.
            "window_quality": {"low_confidence": low_confidence, "reasons": reasons},
            # composite: vectors with their own deviation/z-score tracking.
            # Only v_es and v_pd actually feed step 6's V/A mapping (Decision
            # 18); v_bf is tracked here logged-only (Decision 17) -- see class
            # docstring on why this must never be a generic loop.
            "composite": {
                "v_bf": self._stats(samples, lambda s: s["composite"].get("v_bf")),
                "v_es": self._stats(samples, lambda s: s["composite"].get("v_es")),
                "v_pd": self._stats(samples, lambda s: s["composite"].get("v_pd")),
            },
            # covariates: Track-B logging only. Never read by step 6.
            "covariates": {
                "v_jc": self._stats(samples, lambda s: s["covariate"].get("v_jc")),
                "v_bf_convergence_ratio": self._stats(samples, lambda s: s["covariate"].get("v_bf_convergence_ratio")),
                "v_es_cheek_raise": self._stats(samples, lambda s: s["covariate"].get("v_es_cheek_raise")),
            },
        }
        self.window_start = None
        self.samples = []
        return summary


class AttentionWindowAccumulator:
    """Same rolling-window PATTERN as WindowAccumulator above (tumbling
    WINDOW_SECONDS window, avg+peak+variance, MANDATORY ARCHITECTURE
    #5's cadence) -- but a fully INDEPENDENT object, not a new bucket
    bolted onto WindowAccumulator itself. Two reasons:

    1. V_so needs NO per-person calibration (module docstring) -- it
       must accumulate from frame 1, regardless of calibrator.is_calibrated(),
       so it cannot share WindowAccumulator's calibration-gated lifecycle.
    2. It keeps this new, UNVALIDATED signal from ever touching the
       existing (Gate-2-tested) V_bf/V_es/V_pd windowing code at all --
       nothing here can regress it.

    add_sample() takes a single per-sample dict rather than the
    composite/covariate split WindowAccumulator uses, because V_so has
    no composite-vs-covariate distinction to make (Decision 17/18's
    "which vectors feed Valence/Arousal" split doesn't apply -- V_so
    feeds neither, ever)."""

    def __init__(self):
        self.window_start = None
        self.samples = []

    def add_sample(self, ts, sample):
        if self.window_start is None:
            self.window_start = ts
        self.samples.append(sample)

    def should_flush(self, now, window_seconds=WINDOW_SECONDS):
        return self.window_start is not None and (now - self.window_start) >= window_seconds

    def flush(self, now):
        """Returns the window summary as THREE separate, honestly-labeled
        signals (validation-prep requirement) -- each independently
        scoreable against a commanded direction, exactly like Gate 2
        scored V_bf/V_es/V_pd per-vector rather than as one blended
        number. No new computation: every number below is derived from
        the same per-sample orientation_score/oriented/gaze_score/
        gaze_reliable values compute_v_so already produces each cycle --
        this method only reshapes and aggregates them.

          screen_orientation -- avg/peak/variance of V_so's 0..1 score
            + oriented_rate (the stat a human scorer compares against
            "look at screen" vs "look away"/"look down").
          gaze_direction -- avg/peak/variance of the gaze score, computed
            ONLY over samples where gaze was geometrically plausible
            (never averages in a corrupted/unreliable reading), plus
            gaze_reliable_rate so a scorer can exclude low-reliability
            windows the same way Gate 2 excludes flagged baselines.
          look_away_rate -- 1 - oriented_rate, computed directly from the
            same oriented flags (not re-derived from the rounded
            oriented_rate above, so there's no double-rounding drift) --
            an honestly-labeled "distraction proxy", never "distraction"
            or "disengagement" itself.
        """
        window_start = self.window_start
        samples = self.samples
        n_samples = len(samples)
        n_detected = sum(1 for s in samples if s["detected"])
        detection_rate = (n_detected / n_samples) if n_samples else 0.0

        scores = [s["orientation_score"] for s in samples if s["orientation_score"] is not None]
        oriented_flags = [s["oriented"] for s in samples if s["oriented"] is not None]
        gaze_scores = [s["gaze_score"] for s in samples if s["gaze_score"] is not None]
        gaze_reliable_flags = [s["gaze_reliable"] for s in samples if s["gaze_reliable"] is not None]

        oriented_rate = (sum(oriented_flags) / len(oriented_flags)) if oriented_flags else None

        summary = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "attention_window_summary",
            "session_id": SESSION_ID,
            "person_label": PERSON_LABEL,
            "window_start_monotonic": window_start,
            "window_end_monotonic": now,
            "window_seconds": now - window_start,
            "n_samples": n_samples,
            "n_detected": n_detected,
            "detection_rate": detection_rate,
            # SIGNAL 1/3 -- head/eyes oriented toward screen (V_so itself).
            "screen_orientation": {
                "avg": float(np.mean(scores)) if scores else None,
                "peak": float(np.max(scores)) if scores else None,
                "variance": float(np.var(scores)) if scores else None,
                "n": len(scores),
                # The stat a Gate-2-style human scorer actually compares
                # against the commanded label ("look at screen" -> expect
                # high, "look away"/"look down" -> expect low).
                "oriented_rate": oriented_rate,
                "unvalidated": True,
                "label": "screen orientation (geometric) -- NOT attention/engagement (mental state)",
            },
            # SIGNAL 2/3 -- bonus refinement, ONLY when geometrically
            # plausible. gaze_reliable_rate ALWAYS travels with it so a
            # scorer can exclude low-reliability windows, same spirit as
            # Gate 2's low-confidence exclusion -- never trust gaze
            # silently (module docstring's GLASSES-ROBUST section).
            "gaze_direction": {
                "avg": float(np.mean(gaze_scores)) if gaze_scores else None,
                "peak": float(np.max(gaze_scores)) if gaze_scores else None,
                "variance": float(np.var(gaze_scores)) if gaze_scores else None,
                "n": len(gaze_scores),
                "gaze_reliable_rate": (sum(gaze_reliable_flags) / len(gaze_reliable_flags)) if gaze_reliable_flags else None,
                "unvalidated": True,
                "label": "gaze direction (when reliable) -- bonus signal, NOT a mental-state read; ignore avg/peak/variance when gaze_reliable_rate is low",
            },
            # SIGNAL 3/3 -- fraction of the window NOT oriented.
            "look_away_rate": {
                "value": (1.0 - oriented_rate) if oriented_rate is not None else None,
                "unvalidated": True,
                "label": "look-away rate (geometric) -- fraction of window not oriented toward screen; NOT distraction/disengagement",
            },
            "unvalidated": True,
            "label": "orientation signals (geometric) -- NOT attention/engagement/focus/distraction (mental state); UNVALIDATED pending cross-person testing",
        }
        self.window_start = None
        self.samples = []
        return summary


# Step 6: Valence/Arousal mapping — POST-GATE-2 (Decision 18, supersedes
# retired Decision 50). map_to_valence_arousal() below is the CANONICAL
# implementation used everywhere in this codebase (stage3_demo_ui.py
# imports it rather than keeping its own copy) -- one formula, one place.
#
# Reliability tags carried forward from what Stage 1 + Stage 1.5
# characterization actually established (not vibes):
#   v_bf = high    -- repeat-calibration range 0.0005 across 3 back-to-back
#                     captures (stage1_step8_calibration_repeat_test.py)
#   v_es = low     -- neutral drift ~0.02 across the same test, comparable
#                     in size to a small genuine expression; shares the
#                     yaw-noisy io_dist denominator; only ONE validated
#                     component (aperture) after cheek_raise was demoted
#   v_pd = medium  -- world-frame (camera-distance invariant by
#                     construction) but far less repeat-tested than v_bf
#   v_jc = logged_only -- never composited, no reliable directional signal
#                         even at max effort (step 4 max-elicitation check)
#
# This is METADATA for a consumer (this file's own overlay/plot right
# now, a real demo later) to caveat with -- e.g. "V_es contribution:
# LOW CONFIDENCE". It is NOT used to reweight the mapping formula below:
# that weighting needs Gate 2's multi-person data to justify, not a
# guess baked in now (Pitfall #5).
VECTOR_RELIABILITY = {
    "v_bf": "high",
    "v_es": "low",
    "v_pd": "medium",
    "v_jc": "logged_only",
}


def _z_score(deviation, std):
    """Deviation standardized by THIS PERSON's own neutral spread (std
    from calibration) -- reuses calibration's own output as the scale,
    rather than inventing a new constant (Pitfall #5)."""
    if deviation is None or std is None or std < 1e-9:
        return None
    return deviation / std


def map_to_valence_arousal(v_bf_dev, v_es_dev, v_pd_dev, neutral_ref):
    """Step 6 — rule-based V/A mapping. CANONICAL implementation of
    Decision 18, the Gate 2 result: this is the ONLY place Valence/
    Arousal get computed -- stage3_demo_ui.py imports this function
    rather than keeping its own copy, so there is exactly one formula.

      Valence = z_es only  -- SINGLE-SOURCE, pleasure-side only. There
                               is NO validated pain axis. A near-zero or
                               negative value means "no detected
                               pleasure signal", not "detected pain" --
                               label it that way everywhere this is
                               surfaced (log, overlay, demo).
      Arousal = z_pd only  -- more postural volatility = higher arousal.
    tanh(z/2) saturates the plotted point into a bounded square; 2 std
    devs is a common, domain-general statistical convention (unchanged
    from the pre-Gate-2 version, not reverse-engineered from any
    session's data).

    RETIRED: Valence = (z_es - z_bf) / 2 (Decision 50, pre-Gate-2). Gate
    2 (B-series) found V_bf's furrow direction did NOT generalize across
    faces (0/7 correct-signed, opposite-signed vs. its own concentrate
    reading -- see Decision 17 / VECTOR_RELIABILITY history): V_bf can
    no longer stand for pain, and this formula must never be
    reintroduced. v_bf_dev is still accepted and z-scored below purely
    so callers (this file's own overlay, Track-B logs) can keep showing
    V_bf's own calibrated reading alongside the V/A point for
    transparency -- it is logged-only and plays no part in the valence/
    arousal values themselves.

    Returns None components (not zeros) wherever a vector is
    uncalibrated or undetected this cycle -- never fabricate a point
    from a missing input.
    """
    if neutral_ref is None:
        return {"valence": None, "arousal": None, "components": {}}

    z_bf = _z_score(v_bf_dev, neutral_ref["composite"]["v_bf"]["std"])
    z_es = _z_score(v_es_dev, neutral_ref["composite"]["v_es"]["std"])
    z_pd = _z_score(v_pd_dev, neutral_ref["composite"]["v_pd"]["std"])

    valence = float(np.tanh(z_es / 2.0)) if z_es is not None else None
    arousal = float(np.tanh(z_pd / 2.0)) if z_pd is not None else None

    return {
        "valence": valence,
        "arousal": arousal,
        "components": {
            # logged-only, not used in valence/arousal above -- see docstring
            "v_bf": {"z": z_bf, "reliability": VECTOR_RELIABILITY["v_bf"]},
            "v_es": {"z": z_es, "reliability": VECTOR_RELIABILITY["v_es"]},
            "v_pd": {"z": z_pd, "reliability": VECTOR_RELIABILITY["v_pd"]},
        },
    }


def capture_thread():
    global latest_frame
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        print("[Capture] ERROR: could not open webcam.")
        stop_event.set()
        return

    frame_count = 0
    fps_window_start = time.perf_counter()
    print("[Capture] thread started.")
    while not stop_event.is_set():
        ok, frame = cap.read()
        if not ok:
            continue
        with frame_lock:
            latest_frame = frame
        frame_count += 1
        elapsed = time.perf_counter() - fps_window_start
        if elapsed >= FPS_REPORT_INTERVAL_SECONDS:
            print(f"[Capture] sustained FPS: {frame_count / elapsed:.1f}")
            frame_count = 0
            fps_window_start = time.perf_counter()

    cap.release()
    print("[Capture] thread stopped.")


def processing_thread():
    global latest_readings
    print("[Processing] thread started.")

    face_landmarker = mp_vision.FaceLandmarker.create_from_options(
        mp_vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=FACE_MODEL_PATH),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,  # unchanged; not the requested gate
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

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"session_{SESSION_ID}.jsonl")
    print(f"[Processing] logging to {log_path}")

    pd_buffer = deque()
    window_acc = WindowAccumulator()
    attention_window_acc = AttentionWindowAccumulator()  # V_so -- independent clock, no calibration gate (see class docstring)
    calibrator = NeutralCalibrator()
    stream_start = time.perf_counter()
    cycle_count = 0
    fps_window_start = time.perf_counter()
    # step 6: confidence context comes from the LAST COMPLETED window
    # (10s cadence, per the two-clock design), not recomputed per-sample --
    # a flagged window means "don't trust readings right now", persisting
    # until the next window completes.
    last_window_low_confidence = False
    print(f"[Calibration] starting -- relax your face completely (jaw loose, as if resting alone) for {CALIBRATION_SECONDS:.0f}s...")

    with open(log_path, "a", encoding="utf-8") as log_file:
        while not stop_event.is_set():
            with frame_lock:
                frame = latest_frame
            if frame is None:
                time.sleep(0.01)
                continue

            cycle_start = time.perf_counter()
            timestamp_ms = int((cycle_start - stream_start) * 1000)

            clahe_frame = apply_clahe(frame)
            rgb_frame = cv2.cvtColor(clahe_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms)
            pose_result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)

            h, w = frame.shape[:2]
            record = {
                "schema_version": SCHEMA_VERSION,
                "record_type": "sample",
                "session_id": SESSION_ID,
                "person_label": PERSON_LABEL,
                "ts_utc": datetime.now(timezone.utc).isoformat(),
                "ts_monotonic": cycle_start,
                "vectors": {"v_bf": None, "v_es": None, "v_jc": None, "v_pd": None},
                "vectors_deviation": {"v_bf": None, "v_es": None, "v_pd": None},
                "vector_components": {},
                # ATTENTION SIGNAL -- THREE separate, own-namespace fields (never
                # touch "vectors"/"vectors_deviation" above, so they structurally
                # cannot be composited into Valence/Arousal). UNVALIDATED (module
                # docstring) until tested across real people. Kept as three
                # distinct top-level keys, not nested under one wrapper, so each
                # can be read/scored independently (validation-prep requirement).
                "screen_orientation": {
                    "score": None,
                    "oriented": None,
                    "unvalidated": True,
                    "label": "screen orientation (geometric) -- NOT attention/engagement",
                },
                "gaze_direction": {
                    "score": None,
                    "gaze_reliable": None,
                    "unvalidated": True,
                    "label": "gaze direction (when reliable) -- bonus signal, NOT a mental-state read; ignore unless gaze_reliable is true",
                },
                "look_away": {
                    "value": None,
                    "unvalidated": True,
                    "label": "look-away flag (geometric) -- per-frame input to the window's look_away_rate; NOT distraction/disengagement",
                },
                "head_pose": {"yaw_deg": None, "pitch_deg": None, "roll_deg": None},
                "quality": {
                    "face_detected": False,
                    "pose_detected": False,
                    "face_width_px": None,
                    "z_cm": None,
                    "min_face_presence_confidence": CONFIDENCE_THRESHOLD,
                    "min_tracking_confidence": CONFIDENCE_THRESHOLD,
                },
                "person_id": None,
                # cold-start (Gap 2 L1 / Pitfall #3): "calibrating" until the
                # neutral-capture phase completes -- no confident reading
                # exists yet, so vectors_deviation stays all-None until then.
                "calibration_status": "calibrated" if calibrator.is_calibrated() else "calibrating",
                "calibration_neutral_ref": calibrator.reference,
                "cycle_time_ms": None,
            }
            overlay_lines = []
            # step 5 window inputs: composite (own deviation/z-score tracked;
            # only v_es/v_pd feed V/A, Decision 18) vs covariate (Track-B
            # logging only) -- see WindowAccumulator
            window_composite = {"v_bf": None, "v_es": None, "v_pd": None}
            window_covariate = {"v_jc": None, "v_bf_convergence_ratio": None, "v_es_cheek_raise": None}
            window_yaw = None

            if face_result.face_landmarks and face_result.facial_transformation_matrixes:
                lms = face_result.face_landmarks[0]
                matrix = face_result.facial_transformation_matrixes[0]
                normalized_pts = pose_normalize(lms, matrix, w, h)
                io_dist = interocular_distance(normalized_pts)

                yaw, pitch, roll = yaw_pitch_roll_from_matrix(matrix)
                v_bf, bf_components = compute_v_bf(normalized_pts, io_dist)
                v_es, es_components = compute_v_es(normalized_pts, io_dist)
                v_jc, jc_components = compute_v_jc(normalized_pts, io_dist)
                # ATTENTION SIGNAL Step 1 -- reuses yaw/pitch already decomposed
                # above (no recomputation) and normalized_pts already built above
                # (no new landmark work); see compute_v_so's docstring.
                v_so, so_components = compute_v_so(normalized_pts, yaw, pitch)

                record["vectors"]["v_bf"] = v_bf
                record["vectors"]["v_es"] = v_es
                record["vectors"]["v_jc"] = v_jc
                record["vector_components"]["v_bf"] = bf_components
                record["vector_components"]["v_es"] = es_components
                record["vector_components"]["v_jc"] = jc_components
                record["screen_orientation"] = {
                    "score": v_so,
                    "oriented": so_components["oriented"],
                    "unvalidated": True,
                    "label": "screen orientation (geometric) -- NOT attention/engagement",
                }
                record["gaze_direction"] = {
                    "score": so_components["gaze_score"],  # None unless gaze_reliable -- never a silent zero
                    "gaze_reliable": so_components["gaze_reliable"],
                    "unvalidated": True,
                    "label": "gaze direction (when reliable) -- bonus signal, NOT a mental-state read; ignore unless gaze_reliable is true",
                }
                record["look_away"] = {
                    "value": not so_components["oriented"],
                    "unvalidated": True,
                    "label": "look-away flag (geometric) -- per-frame input to the window's look_away_rate; NOT distraction/disengagement",
                }
                record["head_pose"] = {"yaw_deg": yaw, "pitch_deg": pitch, "roll_deg": roll}
                record["quality"]["face_detected"] = True
                record["quality"]["face_width_px"] = io_dist
                record["quality"]["z_cm"] = float(np.asarray(matrix)[2, 3])

                window_composite["v_bf"] = v_bf
                window_composite["v_es"] = v_es
                window_covariate["v_jc"] = v_jc
                window_covariate["v_bf_convergence_ratio"] = bf_components["convergence_ratio"]
                window_covariate["v_es_cheek_raise"] = es_components["cheek_raise"]
                window_yaw = yaw

                overlay_lines.append(f"V_bf={v_bf:+.3f}  (convergence_ratio={bf_components['convergence_ratio']:.3f})")
                overlay_lines.append(f"V_es={v_es:+.3f}  (aperture={es_components['aperture']:.3f})")
                overlay_lines.append(f"V_jc={v_jc:+.3f}  (inter_lip={jc_components['inter_lip_dist']:.3f})")
                overlay_lines.append(f"yaw={yaw:+.1f} pitch={pitch:+.1f} roll={roll:+.1f}")
                overlay_lines.append(
                    f"V_so={v_so:.2f} {'ORIENTED' if so_components['oriented'] else 'not-oriented'}"
                    f"{' [head-pose-only]' if so_components['head_pose_only'] else ''}  (UNVALIDATED)"
                )

            if pose_result.pose_world_landmarks:
                world = pose_result.pose_world_landmarks[0]
                nose_pos = np.array([world[POSE_NOSE].x, world[POSE_NOSE].y, world[POSE_NOSE].z])
                shoulder_mid = np.array(
                    [
                        (world[POSE_SHOULDER_L].x + world[POSE_SHOULDER_R].x) / 2.0,
                        (world[POSE_SHOULDER_L].y + world[POSE_SHOULDER_R].y) / 2.0,
                        (world[POSE_SHOULDER_L].z + world[POSE_SHOULDER_R].z) / 2.0,
                    ]
                )
                v_pd, pd_components = compute_v_pd(pd_buffer, nose_pos, shoulder_mid, cycle_start)
                record["vectors"]["v_pd"] = v_pd
                record["vector_components"]["v_pd"] = pd_components
                record["quality"]["pose_detected"] = True
                window_composite["v_pd"] = v_pd
                overlay_lines.append(f"V_pd={'n/a' if v_pd is None else f'{v_pd:.5f}'}")

            # ATTENTION SIGNAL Step 1 -- fed EVERY cycle, unconditionally
            # (unlike window_acc below, which only starts once calibrated):
            # V_so needs no per-person baseline, so its window should cover
            # the whole session from frame 1, including the calibration
            # phase -- see AttentionWindowAccumulator's docstring for why.
            attention_window_acc.add_sample(
                cycle_start,
                {
                    "detected": record["quality"]["face_detected"],
                    "orientation_score": record["screen_orientation"]["score"],
                    "oriented": record["screen_orientation"]["oriented"],
                    "gaze_score": record["gaze_direction"]["score"],
                    "gaze_reliable": record["gaze_direction"]["gaze_reliable"],
                },
            )

            cycle_ms = (time.perf_counter() - cycle_start) * 1000.0
            record["cycle_time_ms"] = cycle_ms

            # feed calibration BEFORE checking status, so this cycle's own
            # sample counts toward its own completion
            calibrator.add_sample(cycle_start, window_composite, window_covariate, window_yaw)
            if calibrator.should_complete(cycle_start):
                reference = calibrator.complete(cycle_start)
                log_file.write(json.dumps({
                    "schema_version": SCHEMA_VERSION,
                    "record_type": "calibration_complete",
                    "session_id": SESSION_ID,
                    "person_label": PERSON_LABEL,
                    "reference": reference,
                }) + "\n")
                tag = "POSSIBLY NOT NEUTRAL" if reference["quality"]["possibly_not_neutral"] else "OK"
                print(f"\n=== CALIBRATION COMPLETE ({reference['calibration_seconds']:.1f}s) [{tag}] ===")
                if reference["quality"]["reasons"]:
                    for r in reference["quality"]["reasons"]:
                        print(f"  FLAG: {r}")
                for k, s in reference["composite"].items():
                    print(f"  {k:6s} neutral: mean={s['mean']:+.4f} std={s['std']:.4f} n={s['n']}")
                for k, s in reference["covariates"].items():
                    print(f"  {k:26s} neutral: mean={s['mean']}  std={s['std']}  n={s['n']}")
                print()

            record["calibration_status"] = "calibrated" if calibrator.is_calibrated() else "calibrating"
            record["calibration_neutral_ref"] = calibrator.reference

            deviation_composite = {"v_bf": None, "v_es": None, "v_pd": None}
            va_point = None
            if calibrator.is_calibrated():
                for key in ("v_bf", "v_es", "v_pd"):
                    deviation_composite[key] = calibrator.deviation(key, window_composite.get(key))
                record["vectors_deviation"] = deviation_composite
                # step 6 -- UNTESTED HYPOTHESIS (see map_to_valence_arousal
                # docstring). Computed per-sample for a live-updating point;
                # trustworthiness of that point is a separate question,
                # answered by last_window_low_confidence below, not by
                # anything in this function.
                va_point = map_to_valence_arousal(
                    deviation_composite["v_bf"], deviation_composite["v_es"], deviation_composite["v_pd"], calibrator.reference
                )
            record["va_point"] = va_point

            if not calibrator.is_calibrated():
                remaining = calibrator.seconds_remaining(cycle_start)
                # Procedural mitigation for the contamination flag's known
                # blind spot (see classify_calibration_quality docstring):
                # the flag cannot see a bias held constant from the start,
                # so (1) the instruction is explicit about full relaxation,
                # not just "neutral" (which people interpret as "posed
                # still", not "actually slack"), and (2) raw values stay
                # visible so a human running Gate 2 can eyeball a resting
                # face that looks off, which the flag structurally can't.
                overlay_lines = [
                    "CALIBRATING -- relax your face completely: jaw loose, as if resting alone",
                    f"{remaining:.0f}s remaining",
                    "(no reading yet -- Gap 2 L1: uncalibrated = no confident reading)",
                ]
                if record["quality"]["face_detected"]:
                    overlay_lines.append(f"raw: V_bf={window_composite['v_bf']:+.3f}  V_es={window_composite['v_es']:+.3f}")
                if record["quality"]["pose_detected"] and window_composite["v_pd"] is not None:
                    overlay_lines.append(f"raw: V_pd={window_composite['v_pd']:+.5f}")
                # V_so needs no calibration (module docstring) -- shown during
                # the calibration phase too, unlike the affect vectors above.
                if record["quality"]["face_detected"]:
                    so = record["screen_orientation"]
                    gz = record["gaze_direction"]
                    overlay_lines.append(
                        f"V_so={so['score']:.2f} {'ORIENTED' if so['oriented'] else 'not-oriented'}"
                        f"{'' if gz['gaze_reliable'] else ' [head-pose-only]'}  (UNVALIDATED)"
                    )
            else:
                overlay_lines = []
                if record["quality"]["face_detected"]:
                    overlay_lines.append(f"V_bf(dev)={deviation_composite['v_bf']:+.3f}  raw={window_composite['v_bf']:+.3f}")
                    overlay_lines.append(f"V_es(dev)={deviation_composite['v_es']:+.3f}  raw={window_composite['v_es']:+.3f}")
                    overlay_lines.append(f"yaw={window_yaw:+.1f}" if window_yaw is not None else "yaw=n/a")
                if record["quality"]["pose_detected"]:
                    dev_pd = deviation_composite["v_pd"]
                    overlay_lines.append(f"V_pd(dev)={'n/a' if dev_pd is None else f'{dev_pd:+.5f}'}")
                if record["quality"]["face_detected"]:
                    so = record["screen_orientation"]
                    gz = record["gaze_direction"]
                    overlay_lines.append(
                        f"V_so={so['score']:.2f} {'ORIENTED' if so['oriented'] else 'not-oriented'}"
                        f"{'' if gz['gaze_reliable'] else ' [head-pose-only]'}  (UNVALIDATED)"
                    )
                if not overlay_lines:
                    overlay_lines = ["waiting for detection..."]

            log_file.write(json.dumps(record) + "\n")

            # step 5's window operates on DEVIATION values once calibrated --
            # step 6 must consume calibrated vectors (Pitfall #2), not raw
            # magnitudes. During calibration there is no deviation yet, so
            # the window simply does not start until calibration completes.
            if calibrator.is_calibrated():
                window_acc.add_sample(cycle_start, record["quality"]["face_detected"], window_yaw, deviation_composite, window_covariate)
            if window_acc.should_flush(cycle_start):
                summary = window_acc.flush(cycle_start)
                last_window_low_confidence = summary["window_quality"]["low_confidence"]
                log_file.write(json.dumps(summary) + "\n")
                tag = "LOW-CONFIDENCE" if summary["window_quality"]["low_confidence"] else "valid"
                print(
                    f"\n[Window: {tag}] n={summary['n_samples']} detect_rate={summary['detection_rate']:.2f} "
                    f"yaw_var={summary['yaw_variance_deg2']}"
                    + (f"  reasons={summary['window_quality']['reasons']}" if summary["window_quality"]["reasons"] else "")
                )
                print(
                    f"  V_bf(avg={summary['composite']['v_bf']['avg']}, peak={summary['composite']['v_bf']['peak']}, var={summary['composite']['v_bf']['variance']}) "
                    f"V_es(avg={summary['composite']['v_es']['avg']}, peak={summary['composite']['v_es']['peak']}, var={summary['composite']['v_es']['variance']}) "
                    f"V_pd(avg={summary['composite']['v_pd']['avg']}, peak={summary['composite']['v_pd']['peak']}, var={summary['composite']['v_pd']['variance']})"
                )

            # ATTENTION SIGNAL Step 1 -- own independent flush, own clock
            # (see AttentionWindowAccumulator docstring); never gated on
            # calibrator.is_calibrated() the way window_acc's flush above is.
            if attention_window_acc.should_flush(cycle_start):
                so_summary = attention_window_acc.flush(cycle_start)
                log_file.write(json.dumps(so_summary) + "\n")
                so_win, gz_win, la_win = so_summary["screen_orientation"], so_summary["gaze_direction"], so_summary["look_away_rate"]
                print(
                    f"[Attention window -- UNVALIDATED] n={so_summary['n_samples']} "
                    f"detect_rate={so_summary['detection_rate']:.2f} "
                    f"screen_orientation(avg={so_win['avg']}, peak={so_win['peak']}, oriented_rate={so_win['oriented_rate']}) "
                    f"gaze_direction(avg={gz_win['avg']}, gaze_reliable_rate={gz_win['gaze_reliable_rate']}) "
                    f"look_away_rate={la_win['value']}"
                )

            log_file.flush()

            with readings_lock:
                latest_readings = {
                    "overlay_lines": overlay_lines,
                    "face_detected": record["quality"]["face_detected"],
                    "calibrated": calibrator.is_calibrated(),
                    "va_point": va_point,
                    "window_flagged": last_window_low_confidence,
                }

            cycle_count += 1
            elapsed = time.perf_counter() - fps_window_start
            if elapsed >= FPS_REPORT_INTERVAL_SECONDS:
                print(f"[Processing] {cycle_count / elapsed:.1f} samples/sec, last cycle {cycle_ms:.0f}ms")
                cycle_count = 0
                fps_window_start = time.perf_counter()

    face_landmarker.close()
    pose_landmarker.close()
    print("[Processing] thread stopped.")


def draw_overlay(frame):
    with readings_lock:
        lines = list(latest_readings["overlay_lines"])
        detected = latest_readings["face_detected"]

    if not lines:
        cv2.putText(frame, "waiting for detection...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        return frame

    color = (0, 200, 0) if detected else (0, 0, 255)
    for i, line in enumerate(lines):
        y = 25 + i * 22
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)
    return frame


def draw_va_plot(frame):
    """Step 6 live V/A plot. Drawn directly with OpenCV (no matplotlib)
    to avoid a second GUI event loop fighting cv2's own window/thread.

    Low-confidence windows (window-validity gate, step 5) must NOT plot
    a confident point -- per instruction, flagged rather than
    suppressed, matching the same choice already made for the window
    gate itself: render the point in red with an "UNSTABLE" label
    instead of hiding it outright, so the demo shows the failure mode
    rather than a suspicious blank.

    Honest framing (Decision 18): Valence is z_es only, pleasure-side,
    single-source -- there is NO validated pain axis. The negative-
    valence half is greyed/hatched and labeled so a negative reading
    can never be mistaken for a measured "pain" signal, matching the
    same treatment stage3_demo_ui.py's larger V/A panel uses.
    """
    with readings_lock:
        calibrated = latest_readings["calibrated"]
        va_point = latest_readings["va_point"]
        window_flagged = latest_readings["window_flagged"]

    size = 160
    margin = 10
    h, w = frame.shape[:2]
    ox, oy = w - size - margin, margin
    cx, cy = ox + size // 2, oy + size // 2

    cv2.rectangle(frame, (ox, oy), (ox + size, oy + size), (40, 40, 40), -1)

    # Negative-valence (pain) half: greyed + hatched + labeled unvalidated --
    # must never read as a measurement, same rule as stage3_demo_ui.py.
    overlay = frame.copy()
    cv2.rectangle(overlay, (ox, oy), (cx, oy + size), (12, 12, 12), -1)
    for offset in range(-size, size, 10):
        x_a, y_a = ox + offset, oy + size
        x_b, y_b = ox + offset + size, oy
        cv2.line(overlay, (x_a, y_a), (x_b, y_b), (60, 60, 60), 1, cv2.LINE_AA)
    frame[oy:oy + size, ox:cx] = cv2.addWeighted(frame[oy:oy + size, ox:cx], 0.15, overlay[oy:oy + size, ox:cx], 0.85, 0)

    cv2.rectangle(frame, (ox, oy), (ox + size, oy + size), (200, 200, 200), 1)
    cv2.line(frame, (ox, cy), (ox + size, cy), (110, 110, 110), 1)
    cv2.line(frame, (cx, oy), (cx, oy + size), (110, 110, 110), 1)
    cv2.putText(frame, "V/A (pleasure-side only)", (ox, oy - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)
    cv2.putText(frame, "no pain axis", (ox + 4, cy - 26), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (150, 150, 150), 1)
    cv2.putText(frame, "not measured", (ox + 4, cy - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (150, 150, 150), 1)
    cv2.putText(frame, "+valence", (ox + size - 58, cy - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 140, 140), 1)
    cv2.putText(frame, "+arousal", (cx + 4, oy + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 140, 140), 1)

    valence = va_point.get("valence") if va_point else None
    arousal = va_point.get("arousal") if va_point else None

    if not calibrated or valence is None or arousal is None:
        cv2.putText(frame, "n/a", (cx - 14, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        return frame

    px = int(cx + valence * (size // 2 - 8))
    py = int(cy - arousal * (size // 2 - 8))  # screen y is inverted vs. arousal-up

    if window_flagged:
        cv2.circle(frame, (px, py), 6, (0, 0, 255), -1)
        cv2.putText(frame, "UNSTABLE", (ox, oy + size + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    else:
        cv2.circle(frame, (px, py), 6, (0, 220, 0), -1)

    return frame


def main():
    global PERSON_LABEL

    # Stage 1.5 step 7 (Decision #6): consent gate runs BEFORE anything
    # else in this function -- no thread, no camera, no model load
    # happens above this line. Opting out returns here with nothing
    # started and nothing recorded.
    from stage1_step7_consent import run_consent_gate

    consented, person_label = run_consent_gate(SESSION_ID)
    if not consented:
        return
    PERSON_LABEL = person_label

    t1 = threading.Thread(target=capture_thread, name="CaptureThread")
    t2 = threading.Thread(target=processing_thread, name="ProcessingThread")
    t1.start()
    t2.start()

    print("Press 'q' in the preview window to quit.")
    while not stop_event.is_set():
        with frame_lock:
            frame = latest_frame

        if frame is not None:
            display_frame = draw_overlay(frame.copy())
            display_frame = draw_va_plot(display_frame)
            cv2.imshow("Stage 1 step 4 - vectors (press Q to quit)", display_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            stop_event.set()
            break

    cv2.destroyAllWindows()
    t1.join()
    t2.join()
    print("Clean shutdown complete.")


if __name__ == "__main__":
    main()
