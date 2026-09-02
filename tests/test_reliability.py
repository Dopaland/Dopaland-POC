"""
D0PA1 D3 -- reliability machinery validation (runnable directly, no
pytest). ALL numbers in this file are SYNTHETIC (simulation/generator.py
or hand-constructed arrays with known ground truth) or machinery-internal
sanity checks -- see Part 3 of the task this file implements: the real
3-session reliability protocol has not been collected, and this file
produces NOTHING that could be read as a reliability finding for the
study. See tests/test_reliability_smoke_real_logs.py for the SEPARATE,
unambiguously-labeled smoke test against existing logs (execution only,
never a result).

Covers: SEM/RC/CV/Bland-Altman correctness on hand-computed and synthetic-
ground-truth cases, the ICC single-unit refusal (with its message), ICC
correctness on a >=2-unit synthetic case with a known high/low true ICC,
bootstrap CIs reusing simulation.precision's extracted resampling
machinery, the Bland-Altman SVG plot, and recovery of a KNOWN measurement-
noise level from simulation/generator.py (effect_size=0, so x_signal is
i.i.d. N(0,1) per trial by the generator's own documented construction --
see simulation/generator.py's A6 section).
"""

import os
import sys
import tempfile

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from analysis.reliability import (
    build_unit_session_matrix, compute_sem, compute_rc, compute_within_unit_cv,
    compute_bland_altman_pair, compute_bland_altman_all_pairs, plot_bland_altman_svg,
    bootstrap_ci_for_measure, compute_all_reliability_measures, compute_icc,
)
from simulation.generator import GeneratorConfig, generate


# ============================================================
# Hand-computed correctness checks
# ============================================================

def check_sem_hand_computed():
    # 3 units, 2 sessions -- within-unit variances: unit0: var([1,3])=2.0 (ddof=1);
    # unit1: var([2,2])=0.0; unit2: var([0,4])=8.0. Mean=(2.0+0.0+8.0)/3=3.333..., sqrt=1.8257...
    matrix = np.array([[1.0, 3.0], [2.0, 2.0], [0.0, 4.0]])
    result = compute_sem(matrix)
    expected_sem = np.sqrt((2.0 + 0.0 + 8.0) / 3.0)
    ok = result["n_units_used"] == 3 and abs(result["sem"] - expected_sem) < 1e-9
    return ok, {"result": result, "expected_sem": expected_sem}


def check_sem_excludes_incomplete_units():
    matrix = np.array([[1.0, 3.0], [2.0, np.nan], [0.0, 4.0]])  # unit1 has only 1 non-missing value
    result = compute_sem(matrix)
    ok = result["n_units_used"] == 2 and result["n_units_total"] == 3
    return ok, {"result": result}


def check_rc_formula_exact():
    sem = 0.5
    rc = compute_rc(sem)
    expected = 1.96 * np.sqrt(2) * 0.5
    return abs(rc - expected) < 1e-12, {"rc": rc, "expected": expected}


def check_bland_altman_hand_computed():
    # session_i - session_j for 4 units: [1,3,2,4] - [1,1,1,1] = [0,2,1,3]. mean=1.5, sd(ddof=1)=1.2909944...
    matrix = np.array([[1.0, 1.0], [3.0, 1.0], [2.0, 1.0], [4.0, 1.0]])
    result = compute_bland_altman_pair(matrix, 0, 1)
    expected_bias = 1.5
    expected_sd = float(np.std([0, 2, 1, 3], ddof=1))
    ok = (
        result["n_units"] == 4
        and abs(result["bias"] - expected_bias) < 1e-9
        and abs(result["sd_diff"] - expected_sd) < 1e-9
        and abs(result["loa_upper"] - (expected_bias + 1.96 * expected_sd)) < 1e-9
        and abs(result["loa_lower"] - (expected_bias - 1.96 * expected_sd)) < 1e-9
    )
    return ok, {"result": {k: v for k, v in result.items() if k not in ("diffs", "means")}, "expected_bias": expected_bias, "expected_sd": expected_sd}


def check_bland_altman_all_pairs_never_blended():
    rng = np.random.default_rng(11)
    matrix = rng.normal(size=(10, 3))
    session_ids = ["s0", "s1", "s2"]
    results = compute_bland_altman_all_pairs(matrix, session_ids)
    expected_pairs = {("s0", "s1"), ("s0", "s2"), ("s1", "s2")}
    ok = set(results.keys()) == expected_pairs and all(results[p]["bias"] is not None for p in expected_pairs)
    return ok, {"pairs": sorted(results.keys())}


def check_cv_near_zero_mean_not_applicable():
    matrix = np.array([[1e-12, 2e-12], [-1e-12, 1e-12], [0.0, -1e-12]])  # tiny values -> grand mean ~ 0
    result = compute_within_unit_cv(matrix)
    ok = result["cv_percent"] is None and result["missingness_reason"] == "not_applicable"
    return ok, {"result": result}


def check_cv_normal_case():
    matrix = np.array([[10.0, 12.0], [9.0, 11.0], [10.5, 9.5]])
    result = compute_within_unit_cv(matrix)
    expected_grand_mean = float(matrix.mean())
    sem = compute_sem(matrix)["sem"]
    expected_cv = (sem / expected_grand_mean) * 100.0
    ok = abs(result["cv_percent"] - expected_cv) < 1e-9 and abs(result["grand_mean"] - expected_grand_mean) < 1e-9
    return ok, {"result": result}


# ============================================================
# Bootstrap CI -- reuses simulation.precision's extracted machinery.
# ============================================================

def check_bootstrap_ci_reuses_precision_machinery_and_rejects_single_unit():
    rng = np.random.default_rng(12)
    matrix = np.array([[5.0, 5.2, 4.9]])  # single unit
    raised = False
    try:
        bootstrap_ci_for_measure(matrix, lambda m: compute_sem(m)["sem"], n_boot=50, alpha=0.05, rng=rng)
    except ValueError as e:
        raised = "unit" in str(e).lower()
    return raised, {"raised": raised}


def check_bootstrap_ci_reasonable_on_synthetic_data():
    rng_data = np.random.default_rng(13)
    true_unit_means = rng_data.normal(0, 5, 30)
    matrix = np.column_stack([true_unit_means + rng_data.normal(0, 1.0, 30) for _ in range(3)])
    rng_boot = np.random.default_rng(14)
    ci = bootstrap_ci_for_measure(matrix, lambda m: compute_sem(m)["sem"], n_boot=500, alpha=0.05, rng=rng_boot)
    ok = ci["ci_lo"] is not None and ci["ci_lo"] <= ci["point"] <= ci["ci_hi"] and ci["n_invalid_replicates"] == 0
    return ok, {"ci": {k: v for k, v in ci.items()}}


# ============================================================
# 2.2 -- ICC refuses on single-unit structure, correct on a valid one.
# ============================================================

def check_icc_raises_on_single_unit():
    matrix = np.array([[5.0, 5.2, 4.9]])  # ONE unit, 3 sessions -- the exact "single subject, one value per session" shape
    raised = False
    message = None
    try:
        compute_icc(matrix, unit_ids=["only_unit"], session_ids=["s0", "s1", "s2"])
    except ValueError as e:
        raised = True
        message = str(e)
    ok = raised and "between-unit variance" in message and "uninterpretable" in message.lower()
    return ok, {"raised": raised, "message": message}


def check_icc_high_when_units_dominate_noise():
    """Synthetic ground truth: large between-unit spread, small
    measurement noise -> TRUE ICC should be close to 1."""
    rng = np.random.default_rng(15)
    n_units, k_sessions = 20, 4
    unit_true_values = rng.normal(0, 10.0, n_units)  # large between-unit spread
    matrix = np.column_stack([unit_true_values + rng.normal(0, 0.5, n_units) for _ in range(k_sessions)])  # small noise
    result = compute_icc(matrix, unit_ids=list(range(n_units)), session_ids=list(range(k_sessions)))
    ok = result["icc"] > 0.9
    return ok, {"icc_result": result}


def check_icc_low_when_noise_dominates_units():
    """Synthetic ground truth: near-identical unit means, large
    measurement noise -> TRUE ICC should be close to 0."""
    rng = np.random.default_rng(16)
    n_units, k_sessions = 20, 4
    unit_true_values = rng.normal(0, 0.01, n_units)  # negligible between-unit spread
    matrix = np.column_stack([unit_true_values + rng.normal(0, 5.0, n_units) for _ in range(k_sessions)])  # large noise
    result = compute_icc(matrix, unit_ids=list(range(n_units)), session_ids=list(range(k_sessions)))
    ok = abs(result["icc"]) < 0.3
    return ok, {"icc_result": result}


# ============================================================
# SVG plot -- G4: never PNG.
# ============================================================

def check_bland_altman_svg_written():
    matrix = np.array([[1.0, 1.2], [2.0, 1.9], [3.0, 3.3], [4.0, 3.8]])
    ba = compute_bland_altman_pair(matrix, 0, 1)
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "bland_altman_test.svg")
        plot_bland_altman_svg(ba, out_path, title="test plot")
        exists = os.path.exists(out_path)
        with open(out_path, "rb") as f:
            head = f.read(200)
        is_svg = b"<svg" in head or b"<?xml" in head
    return exists and is_svg, {"exists": exists, "is_svg": is_svg, "path_ext": os.path.splitext(out_path)[1]}


# ============================================================
# SYNTHETIC VALIDATION against simulation/generator.py -- KNOWN ground
# truth. effect_size=0.0 + missingness_rate=0.0 makes x_signal EXACTLY
# i.i.d. N(0,1) per trial (see generator.py's own A6 docstring: "noise ~
# N(0,1), pure noise, independent of z" when effect_size==0). An
# episode-level mean of T such i.i.d. draws has TRUE distribution
# N(0, 1/T) -- fully independent across BOTH episodes and sessions (z is
# never used at all when effect_size=0), so the resulting (n_units,
# n_sessions) matrix's cells are i.i.d. draws from a KNOWN distribution.
# compute_sem() should recover sqrt(1/T) = 1/sqrt(T).
# ============================================================

def _build_matrix_from_generator(seed, n_sessions, episodes_per_session, trials_per_episode, effect_size=0.0):
    cfg = GeneratorConfig(
        seed=seed, n_sessions=n_sessions, episodes_per_session=episodes_per_session,
        trials_per_episode=trials_per_episode, effect_size=effect_size, missingness_rate=0.0,
    )
    records = generate(cfg)
    rows = []
    sums = {}
    counts = {}
    for r in records:
        key = (r["episode_idx"], r["session_idx"])
        sums[key] = sums.get(key, 0.0) + r["x_signal"]
        counts[key] = counts.get(key, 0) + 1
    for (episode_idx, session_idx), total in sums.items():
        rows.append({"unit_id": episode_idx, "session_id": session_idx, "value": total / counts[(episode_idx, session_idx)]})
    matrix, unit_ids, session_ids = build_unit_session_matrix(rows)
    return matrix, unit_ids, session_ids


def check_sem_recovers_known_noise_level_from_generator():
    trials_per_episode = 30
    matrix, unit_ids, session_ids = _build_matrix_from_generator(
        seed=42, n_sessions=3, episodes_per_session=300, trials_per_episode=trials_per_episode,
    )
    result = compute_sem(matrix)
    expected_sem = 1.0 / np.sqrt(trials_per_episode)
    relative_error = abs(result["sem"] - expected_sem) / expected_sem
    # Generous tolerance (15%) -- this is a finite-sample Monte Carlo
    # estimate, not an exact closed form; the point is recovering the
    # right ORDER and approximate VALUE, not machine precision.
    ok = relative_error < 0.15
    return ok, {"computed_sem": result["sem"], "expected_sem_1_over_sqrt_T": expected_sem, "relative_error": relative_error, "n_units_used": result["n_units_used"]}


def check_rc_and_cv_consistent_with_recovered_sem_on_generator_data():
    """RC must match the formula exactly. CV is a REPORTED-BEHAVIOR check,
    not a pass/fail on magnitude: x_signal is zero-mean BY CONSTRUCTION
    (generator.py A6, effect_size=0), so the sample grand_mean here lands
    close to zero by chance (finite-sample noise around the true zero),
    but not within PRE_REGISTERED_CONFIG.zero_dispersion_epsilon (1e-9) --
    that epsilon is a numerical-safety floor for genuinely-degenerate
    values, not a statistical closeness threshold, so it correctly does
    NOT fire here. The observed consequence, reported rather than
    smoothed over: CV% becomes very large and sensitive to exactly which
    finite sample was drawn, because it is a ratio against a small-but-real
    denominator -- a REAL property of the CV formula on a
    near-zero-mean signal, not a bug in compute_within_unit_cv. Confirmed
    here to match its own formula exactly (sem/|grand_mean|*100), whatever
    that value turns out to be."""
    trials_per_episode = 30
    matrix, unit_ids, session_ids = _build_matrix_from_generator(
        seed=43, n_sessions=3, episodes_per_session=300, trials_per_episode=trials_per_episode,
    )
    sem = compute_sem(matrix)["sem"]
    rc = compute_rc(sem)
    cv = compute_within_unit_cv(matrix)
    expected_rc = 1.96 * np.sqrt(2) * sem
    rc_ok = abs(rc - expected_rc) < 1e-9

    if cv["missingness_reason"] == "not_applicable":
        cv_formula_ok = cv["cv_percent"] is None
    else:
        expected_cv = (sem / abs(cv["grand_mean"])) * 100.0
        cv_formula_ok = abs(cv["cv_percent"] - expected_cv) < 1e-6

    ok = rc_ok and cv_formula_ok
    return ok, {"sem": sem, "rc": rc, "expected_rc": expected_rc, "cv_result": cv, "note": "CV magnitude is a reported behavior (near-zero true mean), not asserted -- see this check's docstring"}


# ============================================================
# V_pd-SHAPED SYNTHETIC EXPLORATION -- NOT a pass/fail check. The task
# explicitly asks: real V_pd dispersion runs ~1.6e-4 with a heavy tail,
# MAD ~16x smaller than SD -- "if that shape causes any of the four
# measures to behave oddly, report the behaviour; do not adjust the
# measure to smooth it." This constructs a SYNTHETIC matrix with matching
# characteristics (never real V_pd data -- Part 3 forbids treating real
# logs as a reliability finding) and reports what SEM/RC/CV/Bland-Altman
# and their bootstrap CIs actually do, compared against a Gaussian matrix
# with the IDENTICAL population std, so any difference is attributable to
# the heavy tail, not to a different overall scale.
# ============================================================

def explore_v_pd_shaped_heavy_tailed_behavior():
    from scipy import stats

    rng = np.random.default_rng(2026)
    n_units, k_sessions = 40, 3
    target_std = 1.6e-4

    # Student's t, df=3 (heavy tail): population variance = df/(df-2) = 3,
    # so std = sqrt(3) -- scale to hit target_std exactly.
    t_scale = target_std / np.sqrt(3.0)
    heavy_tailed = stats.t.rvs(df=3, loc=0.0, scale=t_scale, size=(n_units, k_sessions), random_state=rng)

    # Matched-std Gaussian control -- same target_std, no heavy tail.
    gaussian_matched = rng.normal(loc=0.0, scale=target_std, size=(n_units, k_sessions))

    empirical_std_heavy = float(np.std(heavy_tailed))
    empirical_std_gauss = float(np.std(gaussian_matched))

    sem_heavy = compute_sem(heavy_tailed)
    sem_gauss = compute_sem(gaussian_matched)
    rc_heavy = compute_rc(sem_heavy["sem"])
    rc_gauss = compute_rc(sem_gauss["sem"])
    cv_heavy = compute_within_unit_cv(heavy_tailed)
    cv_gauss = compute_within_unit_cv(gaussian_matched)
    ba_heavy = compute_bland_altman_pair(heavy_tailed, 0, 1)
    ba_gauss = compute_bland_altman_pair(gaussian_matched, 0, 1)

    boot_rng_heavy = np.random.default_rng(3000)
    boot_rng_gauss = np.random.default_rng(3000)  # SAME seed -- isolates the tail's effect, not RNG luck
    sem_ci_heavy = bootstrap_ci_for_measure(heavy_tailed, lambda m: compute_sem(m)["sem"], n_boot=1000, alpha=0.05, rng=boot_rng_heavy)
    sem_ci_gauss = bootstrap_ci_for_measure(gaussian_matched, lambda m: compute_sem(m)["sem"], n_boot=1000, alpha=0.05, rng=boot_rng_gauss)

    print("    [V_pd-shaped synthetic exploration -- SYNTHETIC DATA, not a reliability result]")
    print(f"      target population std: {target_std}")
    print(f"      empirical std -- heavy-tailed (t, df=3): {empirical_std_heavy:.3e}  |  Gaussian control: {empirical_std_gauss:.3e}")
    print(f"      SEM            -- heavy-tailed: {sem_heavy['sem']:.3e}  |  Gaussian: {sem_gauss['sem']:.3e}  (ratio {sem_heavy['sem']/sem_gauss['sem']:.2f}x)")
    print(f"      RC             -- heavy-tailed: {rc_heavy:.3e}  |  Gaussian: {rc_gauss:.3e}")
    print(f"      CV%            -- heavy-tailed: {cv_heavy['cv_percent']}  |  Gaussian: {cv_gauss['cv_percent']}  (grand_mean near 0 in both -- see cv missingness_reason)")
    print(f"      CV missingness_reason -- heavy-tailed: {cv_heavy['missingness_reason']}  |  Gaussian: {cv_gauss['missingness_reason']}")
    print(f"      Bland-Altman SD(diff) -- heavy-tailed: {ba_heavy['sd_diff']:.3e}  |  Gaussian: {ba_gauss['sd_diff']:.3e}  (ratio {ba_heavy['sd_diff']/ba_gauss['sd_diff']:.2f}x)")
    print(f"      SEM bootstrap CI half-width -- heavy-tailed: {sem_ci_heavy['ci_half_width']:.3e}  |  Gaussian: {sem_ci_gauss['ci_half_width']:.3e}  (ratio {sem_ci_heavy['ci_half_width']/sem_ci_gauss['ci_half_width']:.2f}x)")

    all_finite = all(np.isfinite(v) for v in (sem_heavy["sem"], sem_gauss["sem"], rc_heavy, rc_gauss, ba_heavy["sd_diff"], ba_gauss["sd_diff"]))
    return all_finite, {
        "empirical_std_heavy": empirical_std_heavy, "empirical_std_gauss": empirical_std_gauss,
        "sem_heavy": sem_heavy["sem"], "sem_gauss": sem_gauss["sem"],
        "sem_ratio_heavy_over_gauss": sem_heavy["sem"] / sem_gauss["sem"],
        "ba_sd_diff_ratio_heavy_over_gauss": ba_heavy["sd_diff"] / ba_gauss["sd_diff"],
        "sem_ci_half_width_ratio_heavy_over_gauss": sem_ci_heavy["ci_half_width"] / sem_ci_gauss["ci_half_width"],
    }


if __name__ == "__main__":
    checks = [
        ("SEM: hand-computed pooled within-unit variance", check_sem_hand_computed),
        ("SEM: incomplete units excluded from pool, counted not dropped", check_sem_excludes_incomplete_units),
        ("RC: 1.96*sqrt(2)*SEM, exact", check_rc_formula_exact),
        ("BLAND-ALTMAN: hand-computed bias/limits of agreement", check_bland_altman_hand_computed),
        ("BLAND-ALTMAN: every session pair, never blended", check_bland_altman_all_pairs_never_blended),
        ("CV: near-zero grand mean -> not_applicable, never a fabricated ratio", check_cv_near_zero_mean_not_applicable),
        ("CV: normal case matches SEM/grand_mean*100 by hand", check_cv_normal_case),
        ("BOOTSTRAP CI: reuses precision.py machinery, rejects single unit", check_bootstrap_ci_reuses_precision_machinery_and_rejects_single_unit),
        ("BOOTSTRAP CI: reasonable interval on synthetic data (point inside CI)", check_bootstrap_ci_reasonable_on_synthetic_data),
        ("2.2 ICC: RAISES on single-unit structure, with the message", check_icc_raises_on_single_unit),
        ("2.2 ICC: recovers HIGH true ICC (units dominate noise)", check_icc_high_when_units_dominate_noise),
        ("2.2 ICC: recovers LOW true ICC (noise dominates units)", check_icc_low_when_noise_dominates_units),
        ("SVG: Bland-Altman plot written as real SVG (G4, never PNG)", check_bland_altman_svg_written),
        ("SYNTHETIC VALIDATION: SEM recovers KNOWN 1/sqrt(T) noise level (simulation/generator.py, effect_size=0)", check_sem_recovers_known_noise_level_from_generator),
        ("SYNTHETIC VALIDATION: RC/CV consistent with recovered SEM on generator data", check_rc_and_cv_consistent_with_recovered_sem_on_generator_data),
        ("EXPLORATION (not pass/fail): V_pd-shaped heavy-tailed synthetic behavior, vs matched-std Gaussian", explore_v_pd_shaped_heavy_tailed_behavior),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"RELIABILITY MACHINERY VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("RELIABILITY MACHINERY VALIDATION: PASS (all synthetic -- see docs/RELIABILITY.md)")
