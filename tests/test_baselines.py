"""
D0PA1 D7 -- three baseline representations validation (runnable directly,
no pytest). Covers: the leakage invariant (1.2/1.3) as an actual BIT-
IDENTICAL assertion, session 1's no-fallback missing-with-reason behavior
(1.4), MAD==0 / zero_dispersion handling reused from
features.robust_baseline (1.5), session-pair counting (1.6), estimator/
window_rule validation, and basic raw/session_z correctness.
"""

import copy
import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from analysis.baselines import (
    compute_raw, compute_session_z, compute_persistent_z, compute_all_baselines,
    BASELINE_ESTIMATORS, BASELINE_WINDOW_RULES, NO_PRIOR_HISTORY_REASON, ZERO_DISPERSION_REASON,
)
from simulation.config import PreRegisteredConfig


def _make_sample(value):
    return {"value": value, "missingness_reason": None if value is not None else "no_face"}


def _make_session(values):
    return [_make_sample(v) for v in values]


# ============================================================
# 1.3 -- THE LEAKAGE TEST. This is the evidence, not the invariant's prose.
# ============================================================

def check_leakage_test_bit_identical():
    """Three sessions. Session index 2 (0-indexed -- the 3rd session) is
    evaluated under TWO datasets that are IDENTICAL except for session 2's
    OWN raw values, which are replaced with extreme outliers in the second
    dataset -- values that would visibly drag a median/MAD computed from
    them. If session 2 ever contributed to its own baseline/scale, B and S
    for session 2 would differ between the two runs. They must not."""
    rng = np.random.default_rng(20260901)

    session_0 = _make_session(list(rng.normal(0.0, 1.0, 40)))
    session_1 = _make_session(list(rng.normal(0.5, 1.0, 40)))
    session_2_original = _make_session(list(rng.normal(1.0, 1.0, 40)))
    # Deliberately extreme -- would massively shift session 2's OWN median/MAD
    # if computed from itself, and would shift the pooled prior-session pool
    # too if the leak reached backward (it must not, since this is session 2's
    # OWN data, evaluated as session 2, never fed into anyone else's baseline).
    session_2_mutated = _make_session([99999.0] * 40)

    dataset_original = [("s0", session_0), ("s1", session_1), ("s2", session_2_original)]
    dataset_mutated = [("s0", session_0), ("s1", session_1), ("s2", session_2_mutated)]

    result_original = compute_persistent_z(dataset_original, estimator="robust_mad", window_rule="expanding")
    result_mutated = compute_persistent_z(dataset_mutated, estimator="robust_mad", window_rule="expanding")

    def _session2_baseline(result):
        rows = [r for r in result["records"] if r["session_id"] == "s2"]
        centers = {r["baseline_center"] for r in rows}
        scales = {r["baseline_scale"] for r in rows}
        assert len(centers) == 1 and len(scales) == 1, "all rows in one session must share one baseline_center/scale"
        return centers.pop(), scales.pop()

    center_original, scale_original = _session2_baseline(result_original)
    center_mutated, scale_mutated = _session2_baseline(result_mutated)

    # BIT-IDENTICAL, not approximately equal.
    bit_identical = (center_original == center_mutated) and (scale_original == scale_mutated)

    return bit_identical, {
        "center_original": center_original, "center_mutated": center_mutated,
        "scale_original": scale_original, "scale_mutated": scale_mutated,
    }


def check_leakage_test_actually_fails_on_a_leaky_implementation():
    """Demonstrates the leakage test is not vacuous: a DELIBERATELY leaky
    prior-pool selector (includes the session's own data, sessions_in_order[:t_idx+1]
    instead of [:t_idx]) makes THIS SAME comparison FAIL. Implemented as a
    local reimplementation of just the leaky selection step (not a
    monkeypatch of the real module -- the real module is never mutated by
    this test), so this function proves the STRUCTURE of the test would
    catch a real regression, without ever running broken code against the
    committed implementation."""
    rng = np.random.default_rng(20260901)
    session_0 = _make_session(list(rng.normal(0.0, 1.0, 40)))
    session_1 = _make_session(list(rng.normal(0.5, 1.0, 40)))
    session_2_original = _make_session(list(rng.normal(1.0, 1.0, 40)))
    session_2_mutated = _make_session([99999.0] * 40)

    from features.robust_baseline import mad_stats

    def leaky_persistent_baseline_for_session2(dataset):
        # LEAKY: pools sessions_in_order[:t_idx + 1] -- includes session 2 itself.
        pooled = []
        for _sid, samples in dataset[: 2 + 1]:
            pooled.extend(e["value"] for e in samples)
        stats = mad_stats(pooled)
        return stats["median"], stats["mad_scaled"]

    dataset_original = [("s0", session_0), ("s1", session_1), ("s2", session_2_original)]
    dataset_mutated = [("s0", session_0), ("s1", session_1), ("s2", session_2_mutated)]

    center_original, scale_original = leaky_persistent_baseline_for_session2(dataset_original)
    center_mutated, scale_mutated = leaky_persistent_baseline_for_session2(dataset_mutated)

    leaky_bit_identical = (center_original == center_mutated) and (scale_original == scale_mutated)
    # The leaky version MUST NOT be bit-identical -- if it were, the test
    # wouldn't be capable of catching a real leak, and this whole check
    # would be meaningless.
    caught_the_leak = not leaky_bit_identical
    return caught_the_leak, {
        "leaky_center_original": center_original, "leaky_center_mutated": center_mutated,
        "leaky_scale_original": scale_original, "leaky_scale_mutated": scale_mutated,
    }


# ============================================================
# 1.4 -- session 1 has no persistent baseline, no fallback.
# ============================================================

def check_session_1_emits_missing_no_fallback():
    rng = np.random.default_rng(1)
    s0 = _make_session(list(rng.normal(0.0, 1.0, 20)))
    s1 = _make_session(list(rng.normal(0.0, 1.0, 20)))
    result = compute_persistent_z([("s0", s0), ("s1", s1)], estimator="robust_mad", window_rule="expanding")

    s0_rows = [r for r in result["records"] if r["session_id"] == "s0"]
    all_missing = all(r["missingness_flag"] is True for r in s0_rows)
    all_reason_correct = all(r["missingness_reason"] == NO_PRIOR_HISTORY_REASON for r in s0_rows)
    all_value_none = all(r["value"] is None for r in s0_rows)
    all_n_prior_zero = all(r["n_prior_sessions_used"] == 0 for r in s0_rows)
    row_not_dropped = len(s0_rows) == len(s0)  # every row STILL EMITTED, not dropped

    s1_rows = [r for r in result["records"] if r["session_id"] == "s1"]
    s1_has_real_values = any(r["value"] is not None for r in s1_rows)

    ok = all_missing and all_reason_correct and all_value_none and all_n_prior_zero and row_not_dropped and s1_has_real_values
    return ok, {
        "n_s0_rows": len(s0_rows), "n_s0_expected": len(s0),
        "all_missing": all_missing, "all_reason_correct": all_reason_correct,
        "s1_has_real_values": s1_has_real_values,
    }


# ============================================================
# 1.5 -- zero_dispersion, reused from features.robust_baseline.
# ============================================================

def check_zero_dispersion_persistent_z():
    """Prior sessions all share the identical value -> MAD exactly zero ->
    persistent_z must report zero_dispersion, never a divide-by-zero or a
    fabricated huge z."""
    s0 = _make_session([5.0] * 30)  # identical -- MAD will be exactly 0
    s1 = _make_session(list(np.random.default_rng(2).normal(5.0, 0.1, 20)))
    result = compute_persistent_z([("s0", s0), ("s1", s1)], estimator="robust_mad", window_rule="expanding")

    s1_rows = [r for r in result["records"] if r["session_id"] == "s1"]
    all_zero_dispersion_reason = all(r["missingness_reason"] == ZERO_DISPERSION_REASON for r in s1_rows)
    all_value_none = all(r["value"] is None for r in s1_rows)
    return all_zero_dispersion_reason and all_value_none, {
        "n_s1_rows": len(s1_rows), "sample_row": s1_rows[0] if s1_rows else None,
    }


# ============================================================
# 1.6 -- session-pair count.
# ============================================================

def check_session_pair_counts():
    rng = np.random.default_rng(3)
    sessions = [(f"s{i}", _make_session(list(rng.normal(0, 1, 15)))) for i in range(5)]

    raw = compute_raw(sessions)
    session_z = compute_session_z(sessions)
    persistent_expanding = compute_persistent_z(sessions, estimator="robust_mad", window_rule="expanding")
    persistent_preceding = compute_persistent_z(sessions, estimator="robust_mad", window_rule="preceding_session_only")

    raw_is_zero = raw["n_session_pairs_total"] == 0
    session_z_is_zero = session_z["n_session_pairs_total"] == 0
    # Expanding, 5 sessions: session i (0-indexed) pools i prior sessions ->
    # total = 0+1+2+3+4 = 10.
    expanding_total_correct = persistent_expanding["n_session_pairs_total"] == 10
    # preceding_session_only: every session except the first pools EXACTLY 1
    # prior session -> total = 4 (sessions 1,2,3,4 each contribute 1).
    preceding_total_correct = persistent_preceding["n_session_pairs_total"] == 4
    # persistent_z necessarily rests on fewer session-pairs than it WOULD if it
    # were like-for-like with raw/session_z's zero -- the comparison this
    # requirement exists for.
    persistent_exceeds_others = persistent_expanding["n_session_pairs_total"] > raw["n_session_pairs_total"]

    ok = raw_is_zero and session_z_is_zero and expanding_total_correct and preceding_total_correct and persistent_exceeds_others
    return ok, {
        "raw_n_session_pairs_total": raw["n_session_pairs_total"],
        "session_z_n_session_pairs_total": session_z["n_session_pairs_total"],
        "persistent_expanding_n_session_pairs_total": persistent_expanding["n_session_pairs_total"],
        "persistent_preceding_n_session_pairs_total": persistent_preceding["n_session_pairs_total"],
    }


# ============================================================
# Estimator/window_rule validation + basic raw/session_z correctness +
# config-hash coverage.
# ============================================================

def check_invalid_estimator_and_window_rule_rejected():
    rng = np.random.default_rng(4)
    sessions = [(f"s{i}", _make_session(list(rng.normal(0, 1, 10)))) for i in range(3)]
    bad_estimator_raised = False
    try:
        compute_persistent_z(sessions, estimator="not_a_real_estimator", window_rule="expanding")
    except ValueError:
        bad_estimator_raised = True
    bad_window_rule_raised = False
    try:
        compute_persistent_z(sessions, estimator="robust_mad", window_rule="not_a_real_rule")
    except ValueError:
        bad_window_rule_raised = True
    return bad_estimator_raised and bad_window_rule_raised, {
        "bad_estimator_raised": bad_estimator_raised, "bad_window_rule_raised": bad_window_rule_raised,
    }


def check_raw_is_pure_passthrough():
    sessions = [("s0", [_make_sample(1.0), _make_sample(None)])]
    result = compute_raw(sessions)
    r0, r1 = result["records"]
    ok = r0["value"] == 1.0 and r0["missingness_flag"] is False and r1["value"] is None and r1["missingness_flag"] is True and r1["missingness_reason"] == "no_face"
    return ok, {"records": result["records"]}


def check_session_z_within_session_only():
    """session_z for session 1 must be UNAFFECTED by session 0's values --
    confirms it truly never looks outside its own session (0 session-pairs,
    verified structurally, not just by the counter)."""
    s0 = _make_session([100.0, 200.0, 300.0])  # wildly different scale
    s1 = _make_session([1.0, 1.1, 0.9, 1.05, 0.95])
    result_with_s0 = compute_session_z([("s0", s0), ("s1", s1)])
    result_without_s0 = compute_session_z([("s1", s1)])

    s1_rows_with = [r["value"] for r in result_with_s0["records"] if r["session_id"] == "s1"]
    s1_rows_without = [r["value"] for r in result_without_s0["records"] if r["session_id"] == "s1"]
    ok = s1_rows_with == s1_rows_without
    return ok, {"s1_with_s0_present": s1_rows_with, "s1_without_s0": s1_rows_without}


def check_config_hash_covers_baseline_params():
    c1 = PreRegisteredConfig(baseline_estimator="robust_mad", baseline_window_rule="expanding")
    c2 = PreRegisteredConfig(baseline_estimator="robust_mad", baseline_window_rule="expanding")
    c3 = PreRegisteredConfig(baseline_estimator="historical_sd", baseline_window_rule="expanding")
    c4 = PreRegisteredConfig(baseline_estimator="robust_mad", baseline_window_rule="rolling")
    same = c1.config_hash() == c2.config_hash()
    estimator_changes_hash = c1.config_hash() != c3.config_hash()
    window_rule_changes_hash = c1.config_hash() != c4.config_hash()
    ok = same and estimator_changes_hash and window_rule_changes_hash
    return ok, {"c1": c1.config_hash(), "c2": c2.config_hash(), "c3": c3.config_hash(), "c4": c4.config_hash()}


def check_compute_all_baselines_end_to_end():
    rng = np.random.default_rng(5)
    sessions = [(f"s{i}", _make_session(list(rng.normal(0, 1, 20)))) for i in range(4)]
    result = compute_all_baselines(sessions)
    ok = (
        set(result.keys()) == {"raw", "session_z", "persistent_z", "config_hash"}
        and result["persistent_z"]["estimator"] == PreRegisteredConfig().baseline_estimator
        and result["persistent_z"]["window_rule"] == PreRegisteredConfig().baseline_window_rule
        and len(result["raw"]["records"]) == len(result["session_z"]["records"]) == len(result["persistent_z"]["records"])
    )
    return ok, {"keys": list(result.keys()), "n_records_each": len(result["raw"]["records"])}


if __name__ == "__main__":
    checks = [
        ("1.3 LEAKAGE TEST: B/S FOR A SESSION ARE BIT-IDENTICAL REGARDLESS OF ITS OWN DATA", check_leakage_test_bit_identical),
        ("1.3 PROOF THE LEAKAGE TEST ACTUALLY CATCHES A LEAK (deliberately-leaky selector)", check_leakage_test_actually_fails_on_a_leaky_implementation),
        ("1.4 SESSION 1: MISSING WITH REASON no_prior_history, NO FALLBACK, ROW NOT DROPPED", check_session_1_emits_missing_no_fallback),
        ("1.5 ZERO_DISPERSION (MAD==0 in prior sessions) -> missing, never divide-by-zero", check_zero_dispersion_persistent_z),
        ("1.6 SESSION-PAIR COUNTS: raw/session_z=0, persistent_z real totals", check_session_pair_counts),
        ("INVALID estimator/window_rule REJECTED", check_invalid_estimator_and_window_rule_rejected),
        ("RAW IS A PURE PASSTHROUGH", check_raw_is_pure_passthrough),
        ("SESSION_Z NEVER LOOKS OUTSIDE ITS OWN SESSION", check_session_z_within_session_only),
        ("CONFIG_HASH COVERS baseline_estimator/window_rule (D7 1.1)", check_config_hash_covers_baseline_params),
        ("compute_all_baselines END TO END", check_compute_all_baselines_end_to_end),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"BASELINES VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("BASELINES VALIDATION: PASS")
