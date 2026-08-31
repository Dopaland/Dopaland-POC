"""
D0PA1 Part C, C2 -- missingness/confidence classification validation
(runnable directly, no pytest). Covers: a present value always classifies
as not-missing regardless of detection flags, each missing-value cause maps
to the expected reason (no_face, tracking_lost, insufficient_samples for
V_pd's own buffer, quality_gate_rejected as the fallback), confidence is
derived consistently from VECTOR_RELIABILITY (never fabricated for V_jc),
every reason this module can emit is a real member of the shared fixed
vocabulary (Part B), and compute_coverage's arithmetic (including the
n_samples=0 edge case).
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from features.signal_quality import (
    classify_signal_missingness, signal_confidence, signal_quality_record,
    compute_coverage, _REASONS_THIS_MODULE_EMITS,
)
from features.x_core import VECTOR_RELIABILITY
from schema.canonical_log_writer import MISSINGNESS_REASONS


def check_present_value_never_flagged_missing():
    # Even with face_detected=False, a present value must classify as present --
    # missingness is about the VALUE, not a proxy for the detection flag alone.
    flag, reason = classify_signal_missingness("v_es", 0.42, face_detected=False, pose_detected=False)
    ok = flag is False and reason is None
    return ok, {"flag": flag, "reason": reason}


def check_facial_signal_missing_no_face():
    for signal in ("v_bf", "v_es", "v_jc"):
        flag, reason = classify_signal_missingness(signal, None, face_detected=False, pose_detected=True)
        if not (flag is True and reason == "no_face"):
            return False, {"signal": signal, "flag": flag, "reason": reason}
    return True, {"checked": ["v_bf", "v_es", "v_jc"], "reason": "no_face"}


def check_v_pd_missing_reasons_disambiguated():
    # Buffer not full yet (pose WAS detected) -> insufficient_samples, distinct from tracking_lost.
    flag_buf, reason_buf = classify_signal_missingness("v_pd", None, face_detected=True, pose_detected=True, pd_buffer_len=1)
    # Pose not detected at all -> tracking_lost.
    flag_lost, reason_lost = classify_signal_missingness("v_pd", None, face_detected=True, pose_detected=False, pd_buffer_len=None)
    ok = (flag_buf, reason_buf) == (True, "insufficient_samples") and (flag_lost, reason_lost) == (True, "tracking_lost")
    return ok, {"buffer_case": (flag_buf, reason_buf), "lost_case": (flag_lost, reason_lost)}


def check_quality_gate_rejected_fallback():
    # Modality WAS detected but value still missing for an undisambiguated reason.
    flag, reason = classify_signal_missingness("v_bf", None, face_detected=True, pose_detected=True)
    ok = flag is True and reason == "quality_gate_rejected"
    return ok, {"flag": flag, "reason": reason}


def check_confidence_matches_vector_reliability():
    expected_nonNone = {"v_bf": VECTOR_RELIABILITY["v_bf"], "v_es": VECTOR_RELIABILITY["v_es"], "v_pd": VECTOR_RELIABILITY["v_pd"]}
    results = {s: signal_confidence(s) for s in ("v_bf", "v_es", "v_jc", "v_pd")}
    # v_jc is "logged_only" -- must be None, never a fabricated number.
    v_jc_is_none = results["v_jc"] is None
    # v_bf (high) > v_pd (medium) > v_es (low), ordering matches VECTOR_RELIABILITY's own ranking.
    ordering_ok = results["v_bf"] > results["v_pd"] > results["v_es"]
    all_others_numeric = all(isinstance(results[s], float) for s in ("v_bf", "v_es", "v_pd"))
    ok = v_jc_is_none and ordering_ok and all_others_numeric
    return ok, {"confidence": results, "vector_reliability": VECTOR_RELIABILITY}


def check_signal_quality_record_bundles_correctly():
    present = signal_quality_record("v_es", 0.3, face_detected=True, pose_detected=True)
    missing = signal_quality_record("v_es", None, face_detected=False, pose_detected=True)
    ok = (
        present["missingness_flag"] is False and present["missingness_reason"] is None and present["confidence"] is not None
        and missing["missingness_flag"] is True and missing["missingness_reason"] == "no_face"
    )
    return ok, {"present": present, "missing": missing}


def check_all_emitted_reasons_in_fixed_vocabulary():
    ok = _REASONS_THIS_MODULE_EMITS.issubset(set(MISSINGNESS_REASONS))
    return ok, {"emitted": sorted(_REASONS_THIS_MODULE_EMITS), "vocabulary": sorted(MISSINGNESS_REASONS)}


def check_coverage_arithmetic():
    full_coverage = compute_coverage([False, False, False])  # nothing missing
    half_coverage = compute_coverage([False, True, False, True])  # 2/4 present
    empty_window = compute_coverage([])

    full_ok = full_coverage == {"n_samples": 3, "n_present": 3, "coverage_fraction": 1.0}
    half_ok = half_coverage == {"n_samples": 4, "n_present": 2, "coverage_fraction": 0.5}
    empty_ok = empty_window["n_samples"] == 0 and empty_window["coverage_fraction"] is None  # never a ZeroDivisionError

    ok = full_ok and half_ok and empty_ok
    return ok, {"full": full_coverage, "half": half_coverage, "empty": empty_window}


if __name__ == "__main__":
    checks = [
        ("PRESENT VALUE NEVER FLAGGED MISSING, REGARDLESS OF DETECTION FLAGS", check_present_value_never_flagged_missing),
        ("FACIAL SIGNALS (v_bf/v_es/v_jc) MISSING -> no_face WHEN FACE NOT DETECTED", check_facial_signal_missing_no_face),
        ("V_PD MISSING REASONS DISAMBIGUATED: insufficient_samples vs tracking_lost", check_v_pd_missing_reasons_disambiguated),
        ("QUALITY_GATE_REJECTED FALLBACK WHEN MODALITY DETECTED BUT VALUE STILL MISSING", check_quality_gate_rejected_fallback),
        ("CONFIDENCE DERIVED FROM VECTOR_RELIABILITY, v_jc NEVER FABRICATED", check_confidence_matches_vector_reliability),
        ("signal_quality_record BUNDLES CONFIDENCE+MISSINGNESS CORRECTLY", check_signal_quality_record_bundles_correctly),
        ("EVERY EMITTED REASON IS IN THE SHARED FIXED VOCABULARY (Part B)", check_all_emitted_reasons_in_fixed_vocabulary),
        ("COVERAGE ARITHMETIC, INCLUDING EMPTY-WINDOW EDGE CASE", check_coverage_arithmetic),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"SIGNAL QUALITY VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("SIGNAL QUALITY VALIDATION: PASS")
