"""
D0PA1 time-shuffle control validation (runnable directly, no pytest;
synthetic data only -- simulation/generator.py -- 1.5: this control has
NOT been run on real trials, because real trials do not exist yet).

Covers: shuffle_episode_order() preserves every trial's own content
exactly (only position moves), session slot sizes are preserved, prev_class_label
and t_in_session are recomputed self-consistently, the shuffle is
deterministic given a seed and genuinely different from the identity
permutation; the full diagnostic executes end to end; the negative control
is carried automatically (verified the unaware-caller way, same pattern
as tests/test_precision.py and tests/test_leakage.py); and the
diagnostic-only / not-a-p-value labeling is present both in the returned
data structure AND in the printed table (1.3).
"""

import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from controls.time_shuffle import (
    TimeShuffleConfig, shuffle_episode_order, run_time_shuffle_diagnostic, format_time_shuffle_table,
)
from simulation.generator import GeneratorConfig, generate


def _small_generator_config(seed=1, effect_size=0.3, fatigue_gain=0.5, class_drift_rate=0.3):
    return GeneratorConfig(
        seed=seed, n_sessions=3, episodes_per_session=60, trials_per_episode=5,
        effect_size=effect_size, fatigue_gain=fatigue_gain, class_drift_rate=class_drift_rate,
    )


def check_shuffle_preserves_trial_content_exactly():
    """The MULTISET of (x_signal, class_label, z, missing) across all
    trials must be IDENTICAL before and after shuffling -- only WHICH
    trial occupies which position changes."""
    records = generate(_small_generator_config())
    rng = np.random.default_rng(7)
    shuffled = shuffle_episode_order(records, rng)

    def _content_multiset(recs):
        # x_signal can be None (missing) -- sort by a tuple that never
        # compares None against a float directly.
        return sorted(
            (r["x_signal"] is None, r["x_signal"] if r["x_signal"] is not None else 0.0, r["class_label"], r["z"], r["missing"])
            for r in recs
        )

    same_content = _content_multiset(records) == _content_multiset(shuffled)
    same_count = len(records) == len(shuffled)
    return same_content and same_count, {"n_original": len(records), "n_shuffled": len(shuffled), "same_content_multiset": same_content}


def check_shuffle_preserves_session_slot_sizes():
    records = generate(_small_generator_config())
    rng = np.random.default_rng(8)
    shuffled = shuffle_episode_order(records, rng)

    def _episodes_per_session(recs):
        by_session = {}
        for r in recs:
            by_session.setdefault(r["session_idx"], set()).add(r["episode_id"])
        return {s: len(eps) for s, eps in by_session.items()}

    original_counts = sorted(_episodes_per_session(records).values())
    shuffled_counts = sorted(_episodes_per_session(shuffled).values())
    ok = original_counts == shuffled_counts
    return ok, {"original_counts": original_counts, "shuffled_counts": shuffled_counts}


def check_shuffle_is_genuinely_not_identity_and_deterministic():
    records = generate(_small_generator_config())
    rng_a = np.random.default_rng(9)
    shuffled_a = shuffle_episode_order(records, rng_a)
    rng_a2 = np.random.default_rng(9)  # SAME seed
    shuffled_a2 = shuffle_episode_order(records, rng_a2)
    rng_b = np.random.default_rng(10)  # DIFFERENT seed
    shuffled_b = shuffle_episode_order(records, rng_b)

    order_a = [r["global_trial_idx"] for r in shuffled_a]
    identical_sequence_for_same_seed = [r["x_signal"] for r in shuffled_a] == [r["x_signal"] for r in shuffled_a2]
    different_from_original_order = [r["x_signal"] for r in shuffled_a] != [r["x_signal"] for r in records]
    different_from_other_seed = [r["x_signal"] for r in shuffled_a] != [r["x_signal"] for r in shuffled_b]
    sequential_global_idx = order_a == list(range(len(order_a)))

    ok = identical_sequence_for_same_seed and different_from_original_order and different_from_other_seed and sequential_global_idx
    return ok, {
        "identical_sequence_for_same_seed": identical_sequence_for_same_seed,
        "different_from_original_order": different_from_original_order,
        "different_from_other_seed": different_from_other_seed,
        "sequential_global_idx": sequential_global_idx,
    }


def check_prev_class_label_and_t_in_session_self_consistent():
    records = generate(_small_generator_config())
    rng = np.random.default_rng(11)
    shuffled = shuffle_episode_order(records, rng)

    by_session = {}
    for r in shuffled:
        by_session.setdefault(r["session_idx"], []).append(r)
    for s in by_session:
        by_session[s].sort(key=lambda r: r["global_trial_idx"])

    prev_class_consistent = True
    t_in_session_valid = True
    for s, recs in by_session.items():
        for i in range(1, len(recs)):
            if recs[i]["prev_class_label"] != recs[i - 1]["class_label"]:
                prev_class_consistent = False
        for r in recs:
            if not (0.0 <= r["t_in_session"] <= 1.0):
                t_in_session_valid = False
        if recs[0]["t_in_session"] != 0.0:
            t_in_session_valid = False

    ok = prev_class_consistent and t_in_session_valid
    return ok, {"prev_class_consistent": prev_class_consistent, "t_in_session_valid": t_in_session_valid}


def check_full_diagnostic_executes_end_to_end():
    def source():
        return generate(_small_generator_config(effect_size=0.4, fatigue_gain=1.5, class_drift_rate=1.0))

    result = run_time_shuffle_diagnostic(source, n_classes=3, n_sessions=3, n_boot=100)
    table = format_time_shuffle_table(result)

    has_both_conditions = "ordered" in result and "shuffled" in result
    all_finite = all(
        np.isfinite(result[c]["delta_point"]) and np.isfinite(result[c]["ci_lo"]) and np.isfinite(result[c]["ci_hi"])
        for c in ("ordered", "shuffled")
    )
    diff_finite = np.isfinite(result["difference"]["delta_point_diff"]) and np.isfinite(result["difference"]["ci_lo"]) and np.isfinite(result["difference"]["ci_hi"])
    return has_both_conditions and all_finite and diff_finite, {"result_keys": list(result.keys()), "sample_table_head": table[:300]}


def check_negative_control_carried_automatically():
    """Same unaware-caller pattern as tests/test_precision.py and
    tests/test_leakage.py -- no mention of negative controls anywhere in
    this call."""
    def source():
        return generate(_small_generator_config())

    result = run_time_shuffle_diagnostic(source, 3, 3, n_boot=100)
    ok = (
        result["ordered"]["delta_negative_control"] is not None
        and result["shuffled"]["delta_negative_control"] is not None
    )
    return ok, {"ordered_delta_negative_control": result["ordered"]["delta_negative_control"], "shuffled_delta_negative_control": result["shuffled"]["delta_negative_control"]}


def check_diagnostic_only_label_present_in_data_and_table():
    def source():
        return generate(_small_generator_config())

    result = run_time_shuffle_diagnostic(source, 3, 3, n_boot=50)
    table = format_time_shuffle_table(result)

    data_labeled = result.get("diagnostic_only") is True and result.get("not_a_permutation_test_pvalue") is True
    table_labeled = "DIAGNOSTIC ONLY" in table and "NOT A PERMUTATION-TEST P-VALUE" in table
    return data_labeled and table_labeled, {"data_labeled": data_labeled, "table_labeled": table_labeled}


def check_config_hash_and_reproducibility():
    c1 = TimeShuffleConfig(shuffle_seed=5, negative_control_seed=5)
    c2 = TimeShuffleConfig(shuffle_seed=5, negative_control_seed=5)
    c3 = TimeShuffleConfig(shuffle_seed=6, negative_control_seed=5)
    same = c1.config_hash() == c2.config_hash()
    different = c1.config_hash() != c3.config_hash()
    return same and different, {"c1": c1.config_hash(), "c2": c2.config_hash(), "c3": c3.config_hash()}


if __name__ == "__main__":
    checks = [
        ("SHUFFLE PRESERVES TRIAL CONTENT EXACTLY (multiset unchanged)", check_shuffle_preserves_trial_content_exactly),
        ("SHUFFLE PRESERVES SESSION SLOT SIZES", check_shuffle_preserves_session_slot_sizes),
        ("SHUFFLE DETERMINISTIC GIVEN SEED, GENUINELY NOT IDENTITY", check_shuffle_is_genuinely_not_identity_and_deterministic),
        ("prev_class_label / t_in_session SELF-CONSISTENT AFTER SHUFFLE", check_prev_class_label_and_t_in_session_self_consistent),
        ("FULL DIAGNOSTIC EXECUTES END TO END", check_full_diagnostic_executes_end_to_end),
        ("1.4 NEGATIVE CONTROL CARRIED AUTOMATICALLY (unaware-caller pattern)", check_negative_control_carried_automatically),
        ("1.3 DIAGNOSTIC-ONLY LABEL IN BOTH DATA AND PRINTED TABLE", check_diagnostic_only_label_present_in_data_and_table),
        ("TimeShuffleConfig HASH: reproducible + sensitive to change", check_config_hash_and_reproducibility),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"TIME-SHUFFLE CONTROL VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("TIME-SHUFFLE CONTROL VALIDATION: PASS (synthetic only -- not run on real trials, see docs/CONTROLS.md)")
