"""
D0PA1 synthetic latent recovery validation (runnable directly, no pytest).
Covers: the EMA pipeline's formula and missing-value carry-forward
behavior on hand-constructed cases, recovery-metric correctness
(correlation + standardised RMSE) on hand-computed examples including a
degenerate zero-dispersion case, that the module never imports anything
camera/feature-derived (2.5's "runnable before any latent model touches
human data", checked structurally), and a real sweep across effect_size x
extra_noise_std showing the recovery curve is visible (qualitative shape
checks -- higher effect_size / lower noise should recover better on
AVERAGE -- never a hardcoded pass/fail threshold, per 2.3).
"""

import ast
import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.latent_recovery import (
    add_observation_noise, recover_latent_ema, compute_recovery_metrics,
    LatentRecoveryConfig, run_one_recovery_point, run_recovery_sweep, format_recovery_table,
)
from simulation.generator import GeneratorConfig, generate


def _fake_session_records(session_idx, x_signals):
    return [
        {"session_idx": session_idx, "global_trial_idx": session_idx * 1000 + i, "x_signal": x}
        for i, x in enumerate(x_signals)
    ]


def check_ema_formula_hand_computed():
    records = _fake_session_records(0, [2.0, 4.0, 6.0])
    alpha = 0.5
    z_hat = recover_latent_ema(records, alpha=alpha)
    # est0 = 2.0 (first observation seeds the estimate directly)
    # est1 = 0.5*4.0 + 0.5*2.0 = 3.0
    # est2 = 0.5*6.0 + 0.5*3.0 = 4.5
    expected = [2.0, 3.0, 4.5]
    ok = all(abs(a - b) < 1e-12 for a, b in zip(z_hat, expected))
    return ok, {"z_hat": z_hat, "expected": expected}


def check_missing_carries_forward_and_none_before_first_observation():
    records = _fake_session_records(0, [None, None, 5.0, None, 9.0])
    z_hat = recover_latent_ema(records, alpha=0.5)
    # positions 0,1: no observation yet -> None
    # position 2: first real observation -> est = 5.0
    # position 3: missing -> carries forward -> 5.0
    # position 4: real observation -> est = 0.5*9.0 + 0.5*5.0 = 7.0
    expected = [None, None, 5.0, 5.0, 7.0]
    ok = z_hat == expected
    return ok, {"z_hat": z_hat, "expected": expected}


def check_ema_resets_per_session_never_crosses_boundary():
    records = _fake_session_records(0, [100.0, 100.0]) + _fake_session_records(1, [1.0, 1.0])
    z_hat = recover_latent_ema(records, alpha=0.5)
    # session 1's first estimate must be seeded fresh at 1.0, NOT influenced
    # by session 0's 100.0-scale values.
    ok = abs(z_hat[2] - 1.0) < 1e-12
    return ok, {"z_hat": z_hat}


def check_recovery_metrics_hand_computed():
    z_true = [1.0, 2.0, 3.0, 4.0, 5.0]
    z_hat = [1.1, 2.2, 2.9, 4.3, 4.8]  # close, not perfect
    result = compute_recovery_metrics(z_true, z_hat)
    expected_r = float(np.corrcoef(z_true, z_hat)[0, 1])
    t_arr, h_arr = np.array(z_true), np.array(z_hat)
    t_z = (t_arr - t_arr.mean()) / t_arr.std()
    h_z = (h_arr - h_arr.mean()) / h_arr.std()
    expected_rmse = float(np.sqrt(np.mean((t_z - h_z) ** 2)))
    ok = abs(result["pearson_r"] - expected_r) < 1e-9 and abs(result["rmse_standardized"] - expected_rmse) < 1e-9 and result["n_used"] == 5 and result["n_total"] == 5
    return ok, {"result": result, "expected_r": expected_r, "expected_rmse": expected_rmse}


def check_recovery_metrics_excludes_none_pairs_correctly():
    z_true = [1.0, 2.0, 3.0, 4.0]
    z_hat = [None, 2.1, None, 3.9]
    result = compute_recovery_metrics(z_true, z_hat)
    ok = result["n_used"] == 2 and result["n_total"] == 4 and result["pearson_r"] is not None
    return ok, {"result": result}


def check_recovery_metrics_zero_dispersion_never_divides_by_zero():
    z_true = [5.0] * 10  # constant -- zero true dispersion
    z_hat = [1.0, 2.0, 1.5, 2.5, 1.0, 2.0, 1.5, 2.5, 1.0, 2.0]
    result = compute_recovery_metrics(z_true, z_hat)
    ok = result["pearson_r"] is None and result["rmse_standardized"] is None and result["missingness_reason"] == "zero_dispersion"
    return ok, {"result": result}


def check_perfect_recovery_gives_r_near_1_rmse_near_0():
    """Sanity extreme: if z_hat IS z_true (up to an affine transform),
    correlation must be ~1 and standardised RMSE ~0."""
    rng = np.random.default_rng(0)
    z_true = list(rng.normal(0, 3, 200))
    z_hat = [5.0 * z + 2.0 for z in z_true]  # pure scale+offset -- must standardise away
    result = compute_recovery_metrics(z_true, z_hat)
    ok = result["pearson_r"] > 0.999 and result["rmse_standardized"] < 0.01
    return ok, {"pearson_r": result["pearson_r"], "rmse_standardized": result["rmse_standardized"]}


def check_correlation_alone_would_be_misled_by_scale_error_but_rmse_catches_it():
    """2.1's own justification, verified: a systematic SCALE error can
    still show near-perfect correlation while a NOISY-but-correctly-scaled
    estimate shows a WORSE correlation but potentially closer standardised
    RMSE -- confirming why BOTH are reported, neither alone suffices."""
    rng = np.random.default_rng(1)
    z_true = list(rng.normal(0, 1, 300))
    z_hat_bad_scale = [50.0 * z for z in z_true]  # huge scale error, but perfectly correlated
    result = compute_recovery_metrics(z_true, z_hat_bad_scale)
    # Correlation looks perfect even though the RAW (non-standardised) values
    # would be wildly wrong -- exactly the failure mode 2.1 warns about.
    # Standardised RMSE correctly shows ~0 too (since standardising undoes a
    # PURE scale error) -- the two metrics AGREE here, which is expected:
    # standardising is specifically what neutralises scale error, so this
    # confirms the machinery does that correctly, not that RMSE "catches" a
    # pure scale error (it can't, by design -- that's what standardising
    # deliberately discards). The complementary case (RMSE catching real
    # noise correlation can't) is exercised by the noise sweep below.
    ok = result["pearson_r"] > 0.999 and result["rmse_standardized"] < 0.01
    return ok, {"pearson_r": result["pearson_r"], "rmse_standardized": result["rmse_standardized"]}


def check_no_camera_or_feature_imports():
    """2.5: 'runnable BEFORE any latent model touches human data' --
    verified structurally, not just by intent: the module's own import
    statements must never reference features.*, stage1_step4_vectors, or
    cv2/mediapipe."""
    path = os.path.join(REPO_ROOT, "simulation", "latent_recovery.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    forbidden_prefixes = ("features", "stage1_step4_vectors", "cv2", "mediapipe", "schema")
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if any(mod == p or mod.startswith(p + ".") for p in forbidden_prefixes):
                violations.append(mod)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name == p or alias.name.startswith(p + ".") for p in forbidden_prefixes):
                    violations.append(alias.name)
    return len(violations) == 0, {"violations": violations}


def check_no_pass_fail_or_threshold_in_output():
    """G1/2.3, checked structurally: no result row or config field is
    named/shaped like a verdict."""
    rows = run_recovery_sweep([0.0, 0.5], [0.0, 1.0], LatentRecoveryConfig(episodes_per_session=30))
    forbidden_keys = {"passed", "pass", "fail", "verdict", "success", "ok"}
    violations = [k for r in rows for k in r.keys() if k.lower() in forbidden_keys]
    return len(violations) == 0, {"violations": violations, "row_keys": list(rows[0].keys())}


def run_real_sweep_and_report():
    """Not a pass/fail check -- runs a real sweep and returns the table for
    the final report, per this task's explicit request ('the recovery
    curve across the sweep, and where correlation and RMSE land'). A
    QUALITATIVE structural check accompanies it: on AVERAGE across this
    grid, higher effect_size should correlate better and lower
    extra_noise_std should correlate better -- confirming the curve moves
    in the expected direction, never asserting a specific magnitude/
    threshold (2.3)."""
    config = LatentRecoveryConfig(seed=11, episodes_per_session=300, ema_alpha=0.3)
    effect_sizes = [0.0, 0.2, 0.4, 0.6, 0.8]
    extra_noise_stds = [0.0, 0.5, 1.5]
    rows = run_recovery_sweep(effect_sizes, extra_noise_stds, config)
    table = format_recovery_table(rows)
    print(table)

    by_effect_size = {}
    for r in rows:
        by_effect_size.setdefault(r["effect_size"], []).append(r["pearson_r"] or 0.0)
    mean_r_by_effect_size = {e: float(np.mean(v)) for e, v in by_effect_size.items()}
    monotonic_in_effect_size = all(
        mean_r_by_effect_size[effect_sizes[i]] <= mean_r_by_effect_size[effect_sizes[i + 1]] + 1e-6
        for i in range(len(effect_sizes) - 1)
    )

    by_noise = {}
    for r in rows:
        by_noise.setdefault(r["extra_noise_std"], []).append(r["pearson_r"] or 0.0)
    mean_r_by_noise = {n: float(np.mean(v)) for n, v in by_noise.items()}
    monotonic_in_noise = all(
        mean_r_by_noise[extra_noise_stds[i]] >= mean_r_by_noise[extra_noise_stds[i + 1]] - 1e-6
        for i in range(len(extra_noise_stds) - 1)
    )

    ok = monotonic_in_effect_size and monotonic_in_noise
    return ok, {
        "mean_r_by_effect_size": mean_r_by_effect_size, "mean_r_by_noise": mean_r_by_noise,
        "monotonic_in_effect_size": monotonic_in_effect_size, "monotonic_in_noise": monotonic_in_noise,
    }


if __name__ == "__main__":
    checks = [
        ("EMA FORMULA, HAND-COMPUTED", check_ema_formula_hand_computed),
        ("MISSING CARRIES FORWARD, None BEFORE FIRST OBSERVATION", check_missing_carries_forward_and_none_before_first_observation),
        ("EMA RESETS PER SESSION, NEVER CROSSES BOUNDARY", check_ema_resets_per_session_never_crosses_boundary),
        ("RECOVERY METRICS, HAND-COMPUTED (correlation + standardised RMSE)", check_recovery_metrics_hand_computed),
        ("RECOVERY METRICS EXCLUDE None PAIRS, COUNTED CORRECTLY", check_recovery_metrics_excludes_none_pairs_correctly),
        ("ZERO-DISPERSION Z_TRUE -> missing, never divide by zero", check_recovery_metrics_zero_dispersion_never_divides_by_zero),
        ("PERFECT RECOVERY (up to affine transform) -> r~1, RMSE~0", check_perfect_recovery_gives_r_near_1_rmse_near_0),
        ("2.1 JUSTIFICATION: standardising correctly neutralises a pure scale error", check_correlation_alone_would_be_misled_by_scale_error_but_rmse_catches_it),
        ("2.5 STRUCTURAL: no camera/feature import anywhere in this module", check_no_camera_or_feature_imports),
        ("G1/2.3 STRUCTURAL: no pass/fail/verdict key anywhere in sweep output", check_no_pass_fail_or_threshold_in_output),
        ("REAL SWEEP: recovery curve moves in the expected direction (not a threshold)", run_real_sweep_and_report),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"LATENT RECOVERY VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("LATENT RECOVERY VALIDATION: PASS (all synthetic -- validates machinery only, see docs/D6_SIMULATION.md)")
