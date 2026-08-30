"""
D0PA1 Addendum 3 -- two analyses:

  TASK 1.3: does the log-loss clip epsilon actually move the reported
  half-width/decidability on REAL FITTED OUTPUT (not just the
  pathological single-trial case Addendum 2 demonstrated)? Re-runs the
  realistic cell (45 min, rare-class frequency 0.05) at
  eps in {1e-6, 1e-12, 1e-15}, n_boot=200, the SAME 5 seeds used
  throughout this pass, so the comparison is paired.

  TASK 2: three log-loss baseline levels (uniform, marginal/prior-
  frequency, M0b) at the realistic cell, so a candidate delta can be
  expressed as a REDUCTION against something interpretable, plus a
  conversion table (nats / relative reduction / perplexity) and whether
  each candidate delta is resolvable at the achievable precision.

No verdict, no recommended delta anywhere in this file (G1) -- Task 2's
"resolvable" column is a ratio (delta / half-width), reported as
arithmetic, never a RETAIN/DROP/INCONCLUSIVE label and never a claim that
any delta is appropriate or sufficient.
"""

import json
import os
import sys
import time
from functools import partial

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.generator import GeneratorConfig, generate
from simulation.models import neg_log_loss
from simulation.precision import (
    sweep_multi_seed_refit, compute_delta, chronological_split,
    Metric, NEG_LOG_LOSS_METRIC,
)
from simulation.run_precision_sweep_pass2 import (
    episodes_for_minutes, TRIALS_PER_EPISODE, N_SESSIONS_REALISTIC,
    REALISTIC_MISSINGNESS, REALISTIC_EFFECT_SIZE, PRIMARY_N_CLASSES, PRIMARY_N_RARE,
)

ARTEFACTS_DIR = os.path.join(REPO_ROOT, "artefacts")
os.makedirs(ARTEFACTS_DIR, exist_ok=True)

ALPHA = 0.05
RESAMPLE_UNIT = "episode"
N_BOOT = 200
SEEDS = list(range(1, 6))  # same 5 seeds used throughout this pass

REALISTIC_MINUTES = 45
REALISTIC_RARE_FREQ = 0.05
WORST_MINUTES = 25
WORST_RARE_FREQ = 0.02

EPS_GRID = [1e-6, 1e-12, 1e-15]


def _realistic_cell_config(minutes=REALISTIC_MINUTES, rare_freq=REALISTIC_RARE_FREQ):
    episodes = episodes_for_minutes(minutes)
    return dict(
        n_sessions=N_SESSIONS_REALISTIC, episodes_per_session=episodes,
        trials_per_episode=TRIALS_PER_EPISODE, n_classes=PRIMARY_N_CLASSES,
        n_rare_classes=PRIMARY_N_RARE, rare_class_frequency=rare_freq,
        effect_size=REALISTIC_EFFECT_SIZE, missingness_rate=REALISTIC_MISSINGNESS,
    )


# ============================================================
# TASK 1.3 -- eps sensitivity on REAL fitted output
# ============================================================

def run_eps_sensitivity():
    cfg = _realistic_cell_config()
    results = []
    t0 = time.time()
    for eps in EPS_GRID:
        metric = Metric(name=f"neg_log_loss_eps={eps}", needs_proba=True, fn=partial(neg_log_loss, eps=eps))
        row = sweep_multi_seed_refit(
            f"eps={eps}", cfg, SEEDS, RESAMPLE_UNIT, n_boot=N_BOOT, alpha=ALPHA, metric=metric
        )
        half_widths = np.array([r["ci_half_width"] for r in row["per_seed_rows"]])
        deltas = np.array([r["delta_point"] for r in row["per_seed_rows"]])
        with np.errstate(divide="ignore", invalid="ignore"):
            decidability = np.where(half_widths > 0, np.abs(deltas) / half_widths, np.inf)
        row["eps"] = eps
        row["half_width_mean"] = float(np.mean(half_widths))
        row["half_width_std"] = float(np.std(half_widths))
        row["delta_mean"] = float(np.mean(deltas))
        row["decidability_mean"] = float(np.mean(decidability[np.isfinite(decidability)]))
        results.append(row)
        print(
            f"  eps={eps:.0e}: half_width mean={row['half_width_mean']:.6f} std={row['half_width_std']:.6f} "
            f"delta_mean={row['delta_mean']:+.6f} decidability_mean={row['decidability_mean']:.4f}  "
            f"[{time.time()-t0:.0f}s elapsed]"
        )
    return results


# ============================================================
# TASK 2.1 -- three baseline log-loss levels
# ============================================================

def uniform_predictor_log_loss(y_test, n_classes):
    """The theoretical ceiling: a predictor that assigns 1/n_classes to
    every class regardless of input. Every trial's true-class probability
    is identically 1/n_classes, so log loss = ln(n_classes) EXACTLY, with
    ZERO variance across trials or seeds -- this is a closed-form fact,
    not an empirical measurement, and is reported that way."""
    proba = np.full((len(y_test), n_classes), 1.0 / n_classes)
    return -neg_log_loss(y_test, proba, n_classes)  # neg_log_loss returns U=-log_loss; flip back to plain log loss for baseline reporting


def marginal_predictor_log_loss(train, test, n_classes):
    """Predicts the TRAIN split's empirical class frequency (a constant
    vector, ignoring all per-trial features) for every test trial -- the
    'know the base rates, nothing else' baseline. Estimated from train
    only (temporal rule: the same no-leakage discipline as the real
    signal's imputation mean elsewhere in this codebase)."""
    y_train = np.array([r["class_label"] for r in train])
    counts = np.bincount(y_train, minlength=n_classes).astype(float)
    freqs = counts / counts.sum()
    y_test_arr = np.array([r["class_label"] for r in test])
    proba = np.tile(freqs, (len(y_test_arr), 1))
    return -neg_log_loss(y_test_arr, proba, n_classes), freqs


def m0b_log_loss(records, n_classes, n_sessions, train_frac=0.6, val_frac=0.2):
    """M0b -- the baseline model AS CURRENTLY SPECIFIED in
    simulation/precision.py: the 'without' model (baseline/nuisance
    features only -- t_in_session, prev_class, session one-hot -- never
    the candidate signal), fit and scored via the EXACT same pipeline
    (_select_l2_and_fit, predict_proba, neg_log_loss) every other result
    in this codebase uses. Reuses compute_delta's own internals rather
    than re-implementing the fit, so 'M0b' here is guaranteed to be the
    SAME model object every Delta in this study is computed against, not
    a separately-maintained approximation of it."""
    delta_result = compute_delta(records, n_classes, n_sessions, train_frac, val_frac, metric=NEG_LOG_LOSS_METRIC)
    return -delta_result.u_without  # u_without = U = -log_loss for the "without"/M0b model; flip back to plain log loss


def run_baseline_levels():
    cfg_kwargs = _realistic_cell_config()
    uniform_vals, marginal_vals, m0b_vals = [], [], []
    marginal_freqs_all = []
    n_classes = cfg_kwargs["n_classes"]
    for seed in SEEDS:
        config = GeneratorConfig(seed=seed, **cfg_kwargs)
        records = generate(config)
        train, val, test = chronological_split(records, 0.6, 0.2)
        y_test = np.array([r["class_label"] for r in test])

        uniform_vals.append(uniform_predictor_log_loss(y_test, n_classes))
        marg_ll, freqs = marginal_predictor_log_loss(train, test, n_classes)
        marginal_vals.append(marg_ll)
        marginal_freqs_all.append(freqs.tolist())
        m0b_vals.append(m0b_log_loss(records, n_classes, config.n_sessions))

    def _stats(vals):
        arr = np.array(vals)
        return {"mean": float(np.mean(arr)), "std": float(np.std(arr)), "min": float(np.min(arr)), "max": float(np.max(arr)), "per_seed": vals}

    return {
        "uniform": _stats(uniform_vals),
        "marginal": _stats(marginal_vals),
        "m0b": _stats(m0b_vals),
        "marginal_freqs_per_seed": marginal_freqs_all,
        "n_classes": n_classes,
        "ln_n_classes": float(np.log(n_classes)),
    }


# ============================================================
# TASK 2.2/2.3 -- conversion table (pure arithmetic)
# ============================================================

def build_conversion_table(m0b_log_loss_mean, delta_grid, realistic_half_width, worst_half_width):
    rows = []
    for delta in delta_grid:
        relative_pct = 100.0 * delta / m0b_log_loss_mean
        perplexity_m0b = float(np.exp(m0b_log_loss_mean))
        perplexity_after = float(np.exp(m0b_log_loss_mean - delta))
        ratio_realistic = delta / realistic_half_width
        ratio_worst = delta / worst_half_width
        rows.append({
            "delta_nats": delta,
            "relative_reduction_pct": relative_pct,
            "perplexity_m0b": perplexity_m0b,
            "perplexity_after_delta": perplexity_after,
            "perplexity_reduction": perplexity_m0b - perplexity_after,
            "ratio_to_realistic_half_width": ratio_realistic,
            "resolvable_at_realistic": ratio_realistic > 1.0,
            "ratio_to_worst_half_width": ratio_worst,
            "resolvable_at_worst": ratio_worst > 1.0,
        })
    return rows


if __name__ == "__main__":
    t_start = time.time()

    print("TASK 1.3: eps sensitivity on real fitted output...")
    eps_results = run_eps_sensitivity()

    print("\nTASK 2.1: baseline log-loss levels...")
    baselines = run_baseline_levels()
    print(f"  uniform:  mean={baselines['uniform']['mean']:.6f} std={baselines['uniform']['std']:.6f}")
    print(f"  marginal: mean={baselines['marginal']['mean']:.6f} std={baselines['marginal']['std']:.6f}")
    print(f"  M0b:      mean={baselines['m0b']['mean']:.6f} std={baselines['m0b']['std']:.6f}")

    # Half-widths from Addendum 2's already-computed grid (not re-run):
    # realistic cell (45min/0.05) = 0.0166, worst cell (25min/0.02) = 0.0246.
    REALISTIC_HALF_WIDTH_FROM_ADDENDUM2 = 0.0166
    WORST_HALF_WIDTH_FROM_ADDENDUM2 = 0.0246

    delta_grid = [0.02, 0.05, 0.10, 0.15, 0.20]
    print("\nTASK 2.2/2.3: conversion table...")
    conversion_table = build_conversion_table(
        baselines["m0b"]["mean"], delta_grid, REALISTIC_HALF_WIDTH_FROM_ADDENDUM2, WORST_HALF_WIDTH_FROM_ADDENDUM2
    )
    for row in conversion_table:
        print(
            f"  delta={row['delta_nats']:.2f} nats -> {row['relative_reduction_pct']:.1f}% of M0b | "
            f"perplexity {row['perplexity_m0b']:.3f} -> {row['perplexity_after_delta']:.3f} | "
            f"ratio@realistic={row['ratio_to_realistic_half_width']:.2f} ratio@worst={row['ratio_to_worst_half_width']:.2f}"
        )

    out = {
        "config": {
            "n_boot": N_BOOT,
            "seeds": SEEDS,
            "eps_grid": EPS_GRID,
            "realistic_cell": {"minutes": REALISTIC_MINUTES, "rare_freq": REALISTIC_RARE_FREQ},
            "worst_cell": {"minutes": WORST_MINUTES, "rare_freq": WORST_RARE_FREQ},
            "realistic_half_width_from_addendum2": REALISTIC_HALF_WIDTH_FROM_ADDENDUM2,
            "worst_half_width_from_addendum2": WORST_HALF_WIDTH_FROM_ADDENDUM2,
            "delta_grid": delta_grid,
        },
        "eps_sensitivity": [{k: v for k, v in r.items() if k != "per_seed_rows"} for r in eps_results],
        "baseline_levels": baselines,
        "conversion_table": conversion_table,
        "wall_clock_seconds": time.time() - t_start,
    }
    out_path = os.path.join(ARTEFACTS_DIR, "d6_eps_and_baseline_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\nDone in {time.time()-t_start:.0f}s. Wrote {out_path}.")
