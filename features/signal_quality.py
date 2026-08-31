"""
D0PA1 Part C, C2 -- missingness and confidence on every signal.

docs/AUDIT_A_COLUMN.md Q2 found: V_bf, V_es, V_jc, V_pd had NEITHER a real
per-sample missingness field nor a real per-sample confidence field (only a
shared, non-signal-specific `quality.face_detected`/`pose_detected` flag,
and a STATIC module-level reliability label that never varies per sample).
This module closes that gap for the four X_core vectors.

SCOPE, stated plainly (not silently narrowed): this covers v_bf, v_es,
v_jc, v_pd -- the validated, Gate-2-scored signals docs/GATE2_FINDINGS.md
reports on, where the missingness/confidence gap has the clearest
consequence. The attention-block pilot signals (V_so, screen orientation,
gaze direction, blink) are NOT extended here -- they already carry their
own partial version (gaze_reliable/head_pose_only flags, an "unvalidated"
stamp on every record) documented in CLAUDE.md's "Attention /
screen-orientation -- PILOT, not POC" section, and are explicitly lower
priority than the four core vectors per that same section. Extending this
module's pattern to them is straightforward future work, not done here --
see docs/SIGNAL_COMPLETIONS.md for this stated as an explicit residual gap
rather than something a reader has to discover.

Deliberately a SEPARATE module, not a change to features/x_core.py: like
features/robust_baseline.py, this consumes already-computed values (a
signal's raw reading, the frame's detection quality flags) as plain
parameters and produces new, additive output -- it never touches
compute_v_bf/es/jc/pd, NeutralCalibrator, or VECTOR_RELIABILITY's own
definition (imported read-only, not modified).

MISSINGNESS REASON VOCABULARY: reused directly from
schema.canonical_log_writer.MISSINGNESS_REASONS (Part B) -- ONE fixed
enumerated vocabulary for the whole repository, not a second, independently
maintained list that could drift out of sync with Part B's schema.
"""

from features.x_core import VECTOR_RELIABILITY
from schema.canonical_log_writer import MISSINGNESS_REASONS

# Confidence is derived from the SAME static VECTOR_RELIABILITY labels
# stage3_demo_ui.py and map_to_valence_arousal() already surface --
# reusing the existing, Gate-2-grounded characterization (CLAUDE.md's
# STATUS section) rather than inventing a new, untested per-sample
# confidence measure (G2: no tuning without real cross-person data).
# "logged_only" (V_jc -- no reliable directional signal even at max
# effort, step 4 max-elicitation check) maps to None: there is no
# meaningful confidence number to report for a signal with no established
# reliability at all, and reporting a fabricated one would overclaim.
_RELIABILITY_TO_CONFIDENCE = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
    "logged_only": None,
}

# V_pd's missing-value cases stem from its OWN rolling buffer not yet
# holding enough samples (features.x_core.compute_v_pd returns None,
# components={"buffer_len": n} whenever len(pd_buffer) < 2) -- a
# structurally different cause from "no pose detected this frame" (pose
# WAS detected; the buffer just hasn't filled yet). Both reuse
# "insufficient_samples" from the fixed vocabulary (Part B) rather than
# a new near-duplicate reason -- same underlying concept ("not enough
# observations yet to compute"), stated here rather than silently reused.
_SIGNAL_TO_DETECTION_KEY = {
    "v_bf": "face_detected",
    "v_es": "face_detected",
    "v_jc": "face_detected",
    "v_pd": "pose_detected",
}

# Every reason this module can actually emit, checked against the single
# fixed vocabulary at import time -- if Part B's schema ever drops one of
# these (or is renamed), this fails loudly at import rather than silently
# emitting a reason string the canonical schema would reject.
_REASONS_THIS_MODULE_EMITS = {"no_face", "tracking_lost", "quality_gate_rejected", "insufficient_samples"}
assert _REASONS_THIS_MODULE_EMITS.issubset(set(MISSINGNESS_REASONS)), (
    f"signal_quality.py emits reason(s) not in schema.canonical_log_writer.MISSINGNESS_REASONS: "
    f"{_REASONS_THIS_MODULE_EMITS - set(MISSINGNESS_REASONS)}"
)


def signal_confidence(signal_name):
    """Static, per-signal confidence derived from VECTOR_RELIABILITY.
    Returns None for signals with no established reliability (V_jc).
    Deliberately NOT per-sample -- see module docstring; a live,
    per-sample confidence measure would need real cross-person validation
    data this codebase does not have (Pitfall #5)."""
    reliability = VECTOR_RELIABILITY.get(signal_name)
    return _RELIABILITY_TO_CONFIDENCE.get(reliability)


def classify_signal_missingness(signal_name, value, face_detected, pose_detected, pd_buffer_len=None):
    """Returns (missingness_flag: bool, missingness_reason: str|None).

    A present value ALWAYS returns (False, None) -- classification never
    runs on a value that's actually there. A missing value's reason is
    determined by the most specific applicable cause:
      - v_pd, buffer not yet full (pd_buffer_len is not None and < 2):
        "insufficient_samples" -- pose WAS detected, the formula just
        hasn't accumulated enough rolling-buffer history yet.
      - the relevant modality wasn't detected this frame (face_detected
        for v_bf/v_es/v_jc, pose_detected for v_pd): "no_face" or
        "tracking_lost" respectively.
      - modality WAS detected but the value is still missing for some
        other reason the caller hasn't disambiguated: "quality_gate_rejected"
        (the closest fit in the fixed vocabulary -- see module docstring)."""
    if value is not None:
        return False, None

    detection_key = _SIGNAL_TO_DETECTION_KEY.get(signal_name)
    if signal_name == "v_pd":
        if pd_buffer_len is not None and pd_buffer_len < 2:
            return True, "insufficient_samples"
        if not pose_detected:
            return True, "tracking_lost"
        return True, "quality_gate_rejected"

    if not face_detected:
        return True, "no_face"
    return True, "quality_gate_rejected"


def signal_quality_record(signal_name, value, face_detected, pose_detected, pd_buffer_len=None):
    """Convenience wrapper bundling confidence + missingness for one
    signal into the single dict shape a caller would want to log per
    sample: {"confidence", "missingness_flag", "missingness_reason"}."""
    missingness_flag, missingness_reason = classify_signal_missingness(
        signal_name, value, face_detected, pose_detected, pd_buffer_len
    )
    return {
        "confidence": signal_confidence(signal_name),
        "missingness_flag": missingness_flag,
        "missingness_reason": missingness_reason,
    }


def compute_coverage(missingness_flags):
    """C4 -- coverage metric: the fraction of a window's samples that
    produced a usable (non-missing) reading for ONE signal.
    missingness_flags: iterable of bool (True = missing) for that signal
    across the window/session. Returns {"n_samples", "n_present",
    "coverage_fraction"}. Never blended across signals -- call once per
    signal, per window/session (this task's explicit requirement)."""
    flags = list(missingness_flags)
    n_samples = len(flags)
    n_present = sum(1 for f in flags if not f)
    return {
        "n_samples": n_samples,
        "n_present": n_present,
        "coverage_fraction": (n_present / n_samples) if n_samples > 0 else None,
    }
