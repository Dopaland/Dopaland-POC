"""
D0PA1 "AFTER THE PHYSICAL RUN" Task 1.3 -- NeutralCalibrator's unreachable-
calibration fix (runnable directly, no pytest).

Found by the prior "PHYSICAL RUN SESSION" task, from a real 10-minute
null-input run whose 25s calibration window fell entirely inside a
no-face-detected stretch: should_complete() fires on WALL-CLOCK elapsed
time alone, independent of whether any real (non-None) sample was ever
collected. Before this fix, is_calibrated() returned True the moment
complete() ran at all -- even when every composite vector's reference was
{mean: None, std: None, n: 0} -- so a session that never got a real
baseline silently reported itself as "calibrated" to every caller
(map_to_valence_arousal's gate, controls/null_input.py's ExcursionDetector
gate, stage1_step4_vectors.py's calibration_status field).

This file checks the fix: an unreachable (all-None) calibration window
completes with an explicit missingness_flag/missingness_reason
("not_yet_calibrated", the pipeline's existing fixed vocabulary --
schema/canonical_log_v1.json) and is_calibrated() correctly reports False
for it, while a normal (real-sample) calibration and a partial (some
signals real, some never detected) calibration are both unaffected.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from features.x_core import NeutralCalibrator


def _all_none_composite():
    return {"v_bf": None, "v_es": None, "v_pd": None}


def _all_none_covariate():
    return {"v_jc": None, "v_bf_convergence_ratio": None, "v_es_cheek_raise": None}


def check_normal_calibration_unaffected():
    """Real samples throughout -- must still complete and report calibrated,
    exactly as before this fix (no behaviour change for the working case)."""
    calib = NeutralCalibrator(calibration_seconds=1.0)
    t0 = 100.0
    for i in range(30):
        composite = {"v_bf": -0.30 + 0.001 * i, "v_es": -0.25 + 0.001 * i, "v_pd": 0.0004 + 0.00001 * i}
        covariate = {"v_jc": 0.55, "v_bf_convergence_ratio": 0.18, "v_es_cheek_raise": 0.40}
        calib.add_sample(t0 + i * 0.03, composite, covariate, yaw_deg=1.0)

    not_yet = calib.is_calibrated() is False  # elapsed time hasn't reached 1.0s yet after 30*0.03s=0.9s
    assert_should_complete = calib.should_complete(t0 + 1.01)
    ref = calib.complete(t0 + 1.01)

    ok = (
        not_yet
        and assert_should_complete
        and calib.is_calibrated() is True
        and ref["missingness_flag"] is False
        and ref["missingness_reason"] is None
        and ref["composite"]["v_bf"]["n"] == 30
        and calib.deviation("v_bf", -0.29) is not None
    )
    return ok, {"is_calibrated": calib.is_calibrated(), "missingness_flag": ref["missingness_flag"], "n_v_bf": ref["composite"]["v_bf"]["n"]}


def check_unreachable_calibration_reports_missing_not_calibrated():
    """THE BUG: a calibration window that elapses with zero real (non-None)
    samples for every composite vector -- e.g. no face/pose detected the
    whole window. Before the fix, is_calibrated() returned True for this.
    This check FAILS against the pre-fix code (is_calibrated() ==
    'self.reference is not None') and PASSES against the fix."""
    calib = NeutralCalibrator(calibration_seconds=1.0)
    t0 = 200.0
    for i in range(30):
        calib.add_sample(t0 + i * 0.03, _all_none_composite(), _all_none_covariate(), yaw_deg=None)

    should_complete = calib.should_complete(t0 + 1.01)
    ref = calib.complete(t0 + 1.01)

    ok = (
        should_complete is True  # wall-clock trigger itself is unchanged
        and ref is not None  # complete() still runs and returns a reference dict
        and all(v["n"] == 0 for v in ref["composite"].values())
        and ref["missingness_flag"] is True
        and ref["missingness_reason"] == "not_yet_calibrated"
        # the actual bug: this must be False, not True
        and calib.is_calibrated() is False
        # deviation() already checked is_calibrated() first -- confirm it
        # stays None rather than fabricating a number from a null mean
        and calib.deviation("v_bf", -0.29) is None
    )
    return ok, {
        "should_complete": should_complete,
        "missingness_flag": ref["missingness_flag"] if ref else None,
        "missingness_reason": ref["missingness_reason"] if ref else None,
        "is_calibrated": calib.is_calibrated(),
    }


def check_partial_calibration_not_treated_as_degenerate():
    """Some signals got real samples, one never did (e.g. pose never
    detected while face was) -- this is ordinary partial missingness,
    already handled per-key by deviation()/map_to_valence_arousal, and
    must NOT be flagged as the whole-session degenerate case."""
    calib = NeutralCalibrator(calibration_seconds=1.0)
    t0 = 300.0
    for i in range(30):
        composite = {"v_bf": -0.30 + 0.001 * i, "v_es": -0.25 + 0.001 * i, "v_pd": None}
        covariate = {"v_jc": 0.55, "v_bf_convergence_ratio": 0.18, "v_es_cheek_raise": 0.40}
        calib.add_sample(t0 + i * 0.03, composite, covariate, yaw_deg=1.0)

    ref = calib.complete(t0 + 1.01)

    ok = (
        ref["missingness_flag"] is False
        and ref["missingness_reason"] is None
        and calib.is_calibrated() is True
        and ref["composite"]["v_bf"]["n"] == 30
        and ref["composite"]["v_pd"]["n"] == 0  # this one signal is genuinely missing
        and calib.deviation("v_bf", -0.29) is not None
        and calib.deviation("v_pd", 0.0005) is None  # per-key None mean -- already-correct existing behaviour
    )
    return ok, {"missingness_flag": ref["missingness_flag"], "is_calibrated": calib.is_calibrated(), "v_pd_n": ref["composite"]["v_pd"]["n"]}


def check_should_complete_stays_one_shot_no_log_spam():
    """The fix must not turn should_complete() into a repeating trigger --
    that would be a real window-logic change (log-spam risk, unbounded
    samples growth), and this task explicitly did not authorise touching
    window logic. Confirm should_complete() returns False on every
    subsequent call once complete() has run, degenerate or not."""
    calib = NeutralCalibrator(calibration_seconds=1.0)
    t0 = 400.0
    for i in range(30):
        calib.add_sample(t0 + i * 0.03, _all_none_composite(), _all_none_covariate(), yaw_deg=None)
    calib.complete(t0 + 1.01)

    still_fires_1 = calib.should_complete(t0 + 2.0)
    still_fires_2 = calib.should_complete(t0 + 100.0)
    n_samples_before = len(calib.samples)
    calib.add_sample(t0 + 2.0, _all_none_composite(), _all_none_covariate(), yaw_deg=None)
    n_samples_after = len(calib.samples)

    ok = (
        still_fires_1 is False
        and still_fires_2 is False
        and n_samples_after == n_samples_before  # add_sample is a no-op once _completed
    )
    return ok, {"still_fires_1": still_fires_1, "still_fires_2": still_fires_2, "n_before": n_samples_before, "n_after": n_samples_after}


if __name__ == "__main__":
    checks = [
        ("NORMAL CALIBRATION -- unaffected by the fix", check_normal_calibration_unaffected),
        ("UNREACHABLE (ALL-NONE) CALIBRATION -- missingness_flag set, is_calibrated() False", check_unreachable_calibration_reports_missing_not_calibrated),
        ("PARTIAL CALIBRATION -- one missing signal does not trip the whole-session flag", check_partial_calibration_not_treated_as_degenerate),
        ("should_complete() STAYS ONE-SHOT -- no log-spam / unbounded growth side effect", check_should_complete_stays_one_shot_no_log_spam),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"NEUTRAL CALIBRATOR TEST: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("NEUTRAL CALIBRATOR TEST: PASS")
