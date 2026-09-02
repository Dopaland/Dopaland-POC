"""
D0PA1 leakage harness validation (runnable directly, no pytest). Covers:
all four variants execute end to end on synthetic data and produce a
complete side-by-side table; the negative control is carried automatically
(verified the same way tests/test_precision.py verifies it -- calling the
harness as an unaware caller would); the data-source interface is
genuinely pluggable (a hand-built fake source, not simulation.generator,
still works); the underlying Delta mechanism actually responds to a real,
severe, deliberately-injected leak (proof the harness isn't vacuous);
config validation; and boundary/missing-value handling near session edges.
"""

import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from controls.leakage import (
    LeakageConfig, WINDOW_VARIANTS, synthetic_trial_source,
    run_leakage_diagnostics, format_leakage_table, _build_variant_records,
)
from simulation.generator import GeneratorConfig, generate
from simulation.precision import compute_delta, MACRO_F1_METRIC


def _small_generator_config(seed=1, effect_size=0.3):
    return GeneratorConfig(
        seed=seed, n_sessions=3, episodes_per_session=60, trials_per_episode=5, effect_size=effect_size,
    )


def check_all_four_variants_execute_end_to_end():
    source = synthetic_trial_source(_small_generator_config())
    result = run_leakage_diagnostics(source, n_classes=3, n_sessions=3, n_boot=100)
    variants_present = set(result["variants"].keys()) == set(WINDOW_VARIANTS)
    all_finite = all(
        np.isfinite(r["delta_point"]) and np.isfinite(r["ci_lo"]) and np.isfinite(r["ci_hi"])
        for r in result["variants"].values()
    )
    table = format_leakage_table(result)
    table_has_all_variants = all(v in table for v in WINDOW_VARIANTS)
    return variants_present and all_finite and table_has_all_variants, {
        "variants_present": variants_present, "all_finite": all_finite,
        "sample_table": table,
    }


def check_negative_control_carried_automatically():
    """Same verification pattern as tests/test_precision.py's
    check_negative_control_cannot_be_omitted -- call the harness the way
    a caller who has never heard of the negative control would (no
    mention of it anywhere in the call) and confirm delta_negative_control
    still comes back populated for EVERY variant, not just one."""
    source = synthetic_trial_source(_small_generator_config())
    result = run_leakage_diagnostics(source, 3, 3, n_boot=100)  # no config= passed -- uses LeakageConfig() default, no negative-control mention anywhere in this call
    all_populated = all(
        r["delta_negative_control"] is not None and r["u_with_negative_control"] is not None and r["negative_control_seed"] is not None
        for r in result["variants"].values()
    )
    return all_populated, {v: result["variants"][v]["delta_negative_control"] for v in WINDOW_VARIANTS}


def check_data_source_is_genuinely_pluggable():
    """A hand-built fake source -- NOT simulation.generator -- shaped like
    the same trial-record contract, run through the identical harness with
    zero code changes. Proves the interface actually decouples the harness
    from the generator, not just in documentation."""
    rng = np.random.default_rng(99)
    n_sessions, episodes_per_session, trials_per_episode = 2, 30, 4
    fake_records = []
    gid = 0
    for session_idx in range(n_sessions):
        for episode_idx in range(episodes_per_session):
            for trial_idx in range(trials_per_episode):
                fake_records.append({
                    "session_idx": session_idx, "episode_idx": episode_idx, "episode_id": session_idx * episodes_per_session + episode_idx,
                    "trial_idx_in_episode": trial_idx, "global_trial_idx": gid,
                    "t_in_session": trial_idx / max(1, trials_per_episode - 1),
                    "class_label": int(rng.integers(0, 3)), "prev_class_label": int(rng.integers(0, 3)),
                    "x_signal": float(rng.normal()), "missing": False,
                })
                gid += 1

    def fake_source():
        return fake_records

    result = run_leakage_diagnostics(fake_source, n_classes=3, n_sessions=n_sessions, n_boot=50)
    ok = set(result["variants"].keys()) == set(WINDOW_VARIANTS)
    return ok, {"used_generator": False, "variants_present": ok}


def check_injected_severe_leak_produces_large_delta():
    """Proof the harness isn't vacuous: a hand-injected, UNAMBIGUOUS leak
    (x_signal directly encodes class_label) run through the SAME
    compute_delta machinery the four variants use must produce a large,
    clearly-nonzero Delta -- confirming the underlying detection mechanism
    genuinely responds to a real leak when one exists, independent of
    whether the natural AR(1)-based post_action variant (in the reported
    four-variant table) happens to look mild on any given synthetic draw
    (see docs/CONTROLS.md's 1.5 caveat for why that natural case can look
    modest without meaning the mechanism is broken)."""
    cfg = _small_generator_config(seed=5, effect_size=0.0)  # effect_size=0: WITHOUT any injection, x_signal carries NO information
    records = generate(cfg)

    clean_delta = compute_delta(records, cfg.n_classes, cfg.n_sessions, metric=MACRO_F1_METRIC)

    leaked_records = []
    for r in records:
        leaked = dict(r)
        # Directly encodes the true class label into the "observed" signal
        # -- the textbook, maximally unambiguous leak: this could ONLY be
        # known after the action occurred.
        leaked["x_signal"] = float(r["class_label"]) + np.random.default_rng(r["global_trial_idx"]).normal(scale=0.01)
        leaked_records.append(leaked)
    leaked_delta = compute_delta(leaked_records, cfg.n_classes, cfg.n_sessions, metric=MACRO_F1_METRIC)

    ok = leaked_delta.delta_point > clean_delta.delta_point + 0.1 and leaked_delta.delta_point > 0.2
    return ok, {
        "clean_delta_point (effect_size=0, no injection)": clean_delta.delta_point,
        "leaked_delta_point (x_signal encodes class_label directly)": leaked_delta.delta_point,
    }


def check_config_validation():
    raised_on_bad_starved_lag = False
    try:
        LeakageConfig(valid_lag_trials=5, pre_action_starved_lag_trials=3)  # starved must be > valid
    except ValueError:
        raised_on_bad_starved_lag = True

    raised_on_zero_valid_lag = False
    try:
        LeakageConfig(valid_lag_trials=0)
    except ValueError:
        raised_on_zero_valid_lag = True

    ok = raised_on_bad_starved_lag and raised_on_zero_valid_lag
    return ok, {"raised_on_bad_starved_lag": raised_on_bad_starved_lag, "raised_on_zero_valid_lag": raised_on_zero_valid_lag}


def check_boundary_trials_get_missing_not_a_crash():
    """The very first trials of a session cannot have a valid 'lag trials
    back' source (nothing exists before trial 0) -- must become x_signal=None,
    never an index error or a wrapped-around value from a DIFFERENT
    session."""
    cfg = GeneratorConfig(seed=2, n_sessions=2, episodes_per_session=5, trials_per_episode=3, effect_size=0.2)
    records = generate(cfg)
    config = LeakageConfig(valid_lag_trials=3)
    variant_records = _build_variant_records(records, "valid", config)

    by_session = {}
    for r in variant_records:
        by_session.setdefault(r["session_idx"], []).append(r)
    first_session = sorted(by_session[0], key=lambda r: r["global_trial_idx"])

    # first valid_lag_trials=3 trials of session 0 must be missing (no
    # session before session 0 to borrow from, and no trial before index 0
    # within it either).
    first_three_missing = all(first_session[i]["x_signal"] is None and first_session[i]["missing"] is True for i in range(3))
    fourth_present = first_session[3]["x_signal"] is not None  # trial index 3 CAN look back to trial 0

    # session 1's first trials must NOT borrow from session 0's tail (no
    # cross-session lag).
    second_session = sorted(by_session[1], key=lambda r: r["global_trial_idx"])
    second_session_first_missing = second_session[0]["x_signal"] is None

    ok = first_three_missing and fourth_present and second_session_first_missing
    return ok, {"first_three_missing": first_three_missing, "fourth_present": fourth_present, "second_session_first_missing": second_session_first_missing}


def check_only_x_signal_and_missing_change_between_variants():
    """Confirms _build_variant_records never touches class_label or any
    other outcome-adjacent field -- ONLY the feature moves."""
    cfg = _small_generator_config(seed=3)
    records = generate(cfg)
    config = LeakageConfig()
    valid_records = _build_variant_records(records, "valid", config)
    post_records = _build_variant_records(records, "post_action", config)

    labels_match = all(v["class_label"] == p["class_label"] == o["class_label"] for v, p, o in zip(valid_records, post_records, records))
    episode_ids_match = all(v["episode_id"] == p["episode_id"] == o["episode_id"] for v, p, o in zip(valid_records, post_records, records))
    x_signal_actually_differs_somewhere = any(v["x_signal"] != p["x_signal"] for v, p in zip(valid_records, post_records))

    ok = labels_match and episode_ids_match and x_signal_actually_differs_somewhere
    return ok, {"labels_match": labels_match, "episode_ids_match": episode_ids_match, "x_signal_differs": x_signal_actually_differs_somewhere}


if __name__ == "__main__":
    checks = [
        ("ALL FOUR VARIANTS EXECUTE END TO END, PRODUCE A COMPLETE TABLE", check_all_four_variants_execute_end_to_end),
        ("1.4 NEGATIVE CONTROL CARRIED AUTOMATICALLY (unaware-caller pattern)", check_negative_control_carried_automatically),
        ("1.1 DATA SOURCE IS GENUINELY PLUGGABLE (fake, non-generator source)", check_data_source_is_genuinely_pluggable),
        ("PROOF: injected severe leak produces a large Delta (mechanism isn't vacuous)", check_injected_severe_leak_produces_large_delta),
        ("LeakageConfig VALIDATION", check_config_validation),
        ("BOUNDARY TRIALS: missing, never a crash, never cross-session leak", check_boundary_trials_get_missing_not_a_crash),
        ("ONLY x_signal/missing CHANGE BETWEEN VARIANTS, NEVER THE OUTCOME", check_only_x_signal_and_missing_change_between_variants),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"LEAKAGE HARNESS VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("LEAKAGE HARNESS VALIDATION: PASS")
