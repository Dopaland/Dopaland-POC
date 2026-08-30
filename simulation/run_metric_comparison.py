"""
D0PA1 PRIMARY-METRIC COMPARISON (docs/D6_SIMULATION.md section 11). Does
adopting multiclass log loss (a proper scoring rule, uses the full
predicted probability distribution) as the primary metric materially
improve the DECIDABILITY of this study over macro-F1 (a hard-argmax
statistic)? It might not -- this script reports what happens, on the same
generated data, with the same true effect size, for both metrics.

No verdict, no recommendation of which metric to adopt anywhere in this
file (G1). Decidability = |Delta| / half-width(Delta) is a dimensionless
signal-to-noise ratio -- the ONLY comparison that is unit-free between a
macro-F1-point CI and a nats-of-log-loss CI, which are otherwise not
comparable numbers (see the task's own warning, restated in
docs/D6_SIMULATION.md section 11.1).

TWO RUNS, TWO RIGOR LEVELS, BOTH STATED EXPLICITLY:

  RUN 1 (run_grid_comparison) -- the SAME six-cell grid the finalisation
  pass used (session length x rare-class frequency), BOTH metrics, at
  n_boot=200 and the SAME 5 seeds as the finalisation pass, effect_size
  fixed at 0.3 (the existing "realistic" anchor). Full rigor, directly
  comparable cell-by-cell to artefacts/d6_finalisation_results.json's
  macro-F1 numbers (macro-F1 is RE-RUN here rather than reusing that
  file's saved aggregates, because per-seed (Delta, half-width) PAIRS are
  needed for decidability and the finalisation JSON only kept aggregated
  stats, not per-seed rows).

  RUN 2 (run_effect_size_correspondence) -- at the single realistic cell
  (45 minutes, rare-class frequency 0.05) only, across a range of true
  effect sizes, BOTH metrics. Deliberately REDUCED rigor (n_boot=100,
  3 seeds instead of 200/5) because this is a wider sweep along a new
  dimension (effect size) on top of an already-expensive double
  bootstrap -- stated here and in every place these numbers are reported,
  not hidden behind a same-looking table.

This script does NOT modify simulation/generator.py, run_precision_sweep.py,
run_precision_sweep_pass2.py, run_precision_sweep_finalisation.py, or any
existing artefact's prior content.
"""

import json
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.precision import sweep_multi_seed_refit, MACRO_F1_METRIC, NEG_LOG_LOSS_METRIC
from simulation.run_precision_sweep_pass2 import (
    episodes_for_minutes,
    TRIALS_PER_EPISODE,
    N_SESSIONS_REALISTIC,
    REALISTIC_MISSINGNESS,
    REALISTIC_EFFECT_SIZE,
    PRIMARY_N_CLASSES,
    PRIMARY_N_RARE,
)

ARTEFACTS_DIR = os.path.join(REPO_ROOT, "artefacts")
os.makedirs(ARTEFACTS_DIR, exist_ok=True)

ALPHA = 0.05
RESAMPLE_UNIT = "episode"

# --- RUN 1: matches the finalisation pass exactly (same n_boot, same
# seeds, same grid) so the two are directly comparable cell-by-cell. ---
N_BOOT_MAIN = 200
N_SEEDS_MAIN = 5
SEEDS_MAIN = list(range(1, N_SEEDS_MAIN + 1))
SESSION_MINUTES_GRID = [25, 35, 45]
RARE_FREQ_GRID = [0.02, 0.05]
METRICS = [MACRO_F1_METRIC, NEG_LOG_LOSS_METRIC]

# --- RUN 2: reduced rigor, stated explicitly (see module docstring). ---
N_BOOT_EFFECT_SIZE = 100
N_SEEDS_EFFECT_SIZE = 3
SEEDS_EFFECT_SIZE = list(range(1, N_SEEDS_EFFECT_SIZE + 1))
EFFECT_SIZE_GRID = [0.0, 0.15, 0.25, 0.3, 0.5, 0.8]


def _cell_config(minutes, rare_freq, effect_size=REALISTIC_EFFECT_SIZE):
    episodes = episodes_for_minutes(minutes)
    return episodes, dict(
        n_sessions=N_SESSIONS_REALISTIC,
        episodes_per_session=episodes,
        trials_per_episode=TRIALS_PER_EPISODE,
        n_classes=PRIMARY_N_CLASSES,
        n_rare_classes=PRIMARY_N_RARE,
        rare_class_frequency=rare_freq,
        effect_size=effect_size,
        missingness_rate=REALISTIC_MISSINGNESS,
    )


def _decidability_stats(per_seed_rows):
    """decidability = |Delta| / half-width, computed PER SEED (same
    generated data, same true effect size, just the two metrics' own
    Delta/half-width pair) -- then aggregated. Returns mean/std/min/max of
    both decidability and half-width across seeds, plus the raw per-seed
    decidability values for inspection."""
    half_widths = np.array([r["ci_half_width"] for r in per_seed_rows])
    deltas = np.array([r["delta_point"] for r in per_seed_rows])
    # A half-width of exactly 0 with a nonzero Delta would make
    # decidability infinite -- report it as such rather than silently
    # dividing (numerical honesty, same spirit as the null-input control's
    # zero_dispersion flag) rather than crashing or silently coercing.
    with np.errstate(divide="ignore", invalid="ignore"):
        decidability = np.where(half_widths > 0, np.abs(deltas) / half_widths, np.inf)
    finite = decidability[np.isfinite(decidability)]
    return {
        "half_width_mean": float(np.mean(half_widths)),
        "half_width_std": float(np.std(half_widths)),
        "half_width_min": float(np.min(half_widths)),
        "half_width_max": float(np.max(half_widths)),
        "delta_mean": float(np.mean(deltas)),
        "delta_std": float(np.std(deltas)),
        "decidability_mean": float(np.mean(finite)) if len(finite) else None,
        "decidability_std": float(np.std(finite)) if len(finite) else None,
        "decidability_min": float(np.min(finite)) if len(finite) else None,
        "decidability_max": float(np.max(finite)) if len(finite) else None,
        "n_infinite_decidability": int(np.sum(~np.isfinite(decidability))),
        "decidability_per_seed": [float(d) if np.isfinite(d) else None for d in decidability],
        "zero_width_ci_count": int(np.sum(half_widths == 0.0)),
    }


def run_grid_comparison():
    """TASK 2.1/2.2/2.3/2.4: full 3x2 grid, both metrics, n_boot=200,
    5 seeds, effect_size=0.3 (fixed)."""
    results = []
    t0 = time.time()
    for minutes in SESSION_MINUTES_GRID:
        for rare_freq in RARE_FREQ_GRID:
            episodes, cfg = _cell_config(minutes, rare_freq)
            for metric in METRICS:
                label = f"{minutes}min_x_rare{rare_freq}_x_{metric.name}"
                row = sweep_multi_seed_refit(
                    label, cfg, SEEDS_MAIN, RESAMPLE_UNIT, n_boot=N_BOOT_MAIN, alpha=ALPHA, metric=metric
                )
                stats = _decidability_stats(row["per_seed_rows"])
                row.update(stats)
                row["session_minutes"] = minutes
                row["rare_class_frequency"] = rare_freq
                row["metric_name"] = metric.name
                results.append(row)
                print(
                    f"  {minutes:2d}min x rare={rare_freq:.2f} x {metric.name:12s}: "
                    f"half_width mean={stats['half_width_mean']:.4f} std={stats['half_width_std']:.4f} | "
                    f"decidability mean={stats['decidability_mean']:.3f} "
                    f"(min={stats['decidability_min']:.3f}, max={stats['decidability_max']:.3f})  "
                    f"[{time.time()-t0:.0f}s elapsed]"
                )
    return results


def run_effect_size_correspondence():
    """TASK 3 (+ supplementary decidability-vs-effect-size for TASK 2.2):
    realistic cell only (45min, rare=0.05), swept over EFFECT_SIZE_GRID,
    both metrics, REDUCED rigor (n_boot=100, 3 seeds) -- see module
    docstring."""
    results = []
    t0 = time.time()
    for effect_size in EFFECT_SIZE_GRID:
        episodes, base_cfg = _cell_config(45, 0.05, effect_size=effect_size)
        for metric in METRICS:
            label = f"effect_size={effect_size}_x_{metric.name}"
            row = sweep_multi_seed_refit(
                label, base_cfg, SEEDS_EFFECT_SIZE, RESAMPLE_UNIT,
                n_boot=N_BOOT_EFFECT_SIZE, alpha=ALPHA, metric=metric,
            )
            stats = _decidability_stats(row["per_seed_rows"])
            row.update(stats)
            row["effect_size"] = effect_size
            row["metric_name"] = metric.name
            results.append(row)
            print(
                f"  effect_size={effect_size:.2f} x {metric.name:12s}: "
                f"delta mean={stats['delta_mean']:+.4f} half_width mean={stats['half_width_mean']:.4f} "
                f"decidability mean={stats['decidability_mean']}  [{time.time()-t0:.0f}s elapsed]"
            )
    return results


def _strip(results):
    return [{k: v for k, v in r.items() if k not in ("per_seed_rows", "decidability_per_seed")} for r in results]


def make_plots(grid_results, effect_size_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Plot 1: decidability by cell, both metrics, grouped bars.
    fig, ax = plt.subplots(figsize=(9, 5.5))
    cells = [(m, f) for m in SESSION_MINUTES_GRID for f in RARE_FREQ_GRID]
    x = np.arange(len(cells))
    width = 0.35
    for i, metric in enumerate(METRICS):
        vals = []
        errs = []
        for minutes, rare_freq in cells:
            row = next(r for r in grid_results if r["session_minutes"] == minutes and r["rare_class_frequency"] == rare_freq and r["metric_name"] == metric.name)
            vals.append(row["decidability_mean"])
            errs.append(row["decidability_std"])
        ax.bar(x + (i - 0.5) * width, vals, width, yerr=errs, capsize=3, label=metric.name)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}min\nrare={f}" for m, f in cells], fontsize=8)
    ax.set_ylabel("Decidability = |Δ| / half-width\n(mean ± std across seeds)")
    ax.set_title(f"Metric comparison: decidability by cell (effect_size={REALISTIC_EFFECT_SIZE}, n_boot={N_BOOT_MAIN})")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(ARTEFACTS_DIR, "d6_metric_comparison_decidability.svg"))
    plt.close(fig)

    # Plot 2: Delta correspondence, both metrics, vs effect size.
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for metric, ax in zip(METRICS, axes):
        xs = sorted({r["effect_size"] for r in effect_size_results})
        ys = []
        yerr = []
        for es in xs:
            row = next(r for r in effect_size_results if r["effect_size"] == es and r["metric_name"] == metric.name)
            ys.append(row["delta_mean"])
            yerr.append(row["delta_std"])
        ax.errorbar(xs, ys, yerr=yerr, marker="o", capsize=4)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xlabel("Configured effect_size (generator parameter)")
        ax.set_ylabel(f"Δ ({metric.name})")
        ax.set_title(metric.name)
        ax.grid(alpha=0.3)
    fig.suptitle(f"Δ vs. true effect size, both metrics (realistic cell, n_boot={N_BOOT_EFFECT_SIZE}, {N_SEEDS_EFFECT_SIZE} seeds)")
    fig.tight_layout()
    fig.savefig(os.path.join(ARTEFACTS_DIR, "d6_metric_comparison_effect_size.svg"))
    plt.close(fig)


if __name__ == "__main__":
    t_start = time.time()

    print(f"RUN 1: grid comparison (n_boot={N_BOOT_MAIN}, seeds={SEEDS_MAIN}, both metrics)...")
    grid_results = run_grid_comparison()

    print(f"\nRUN 2: effect-size correspondence (n_boot={N_BOOT_EFFECT_SIZE}, seeds={SEEDS_EFFECT_SIZE}, both metrics)...")
    effect_size_results = run_effect_size_correspondence()

    print("\nWriting plots...")
    make_plots(grid_results, effect_size_results)

    out = {
        "config": {
            "run1_n_boot": N_BOOT_MAIN,
            "run1_seeds": SEEDS_MAIN,
            "run1_effect_size": REALISTIC_EFFECT_SIZE,
            "run2_n_boot": N_BOOT_EFFECT_SIZE,
            "run2_seeds": SEEDS_EFFECT_SIZE,
            "run2_effect_size_grid": EFFECT_SIZE_GRID,
            "log_loss_clip_eps": 1e-15,
            "session_minutes_grid": SESSION_MINUTES_GRID,
            "rare_freq_grid": RARE_FREQ_GRID,
        },
        "grid_comparison": _strip(grid_results),
        "grid_comparison_full_per_seed": [
            {"label": r["label"], "metric": r["metric_name"], "session_minutes": r["session_minutes"],
             "rare_class_frequency": r["rare_class_frequency"], "decidability_per_seed": r["decidability_per_seed"],
             "per_seed_delta": [s["delta_point"] for s in r["per_seed_rows"]],
             "per_seed_half_width": [s["ci_half_width"] for s in r["per_seed_rows"]]}
            for r in grid_results
        ],
        "effect_size_correspondence": _strip(effect_size_results),
        "wall_clock_seconds": time.time() - t_start,
    }
    out_path = os.path.join(ARTEFACTS_DIR, "d6_metric_comparison_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\nDone in {time.time()-t_start:.0f}s. Wrote {out_path} and 2 SVGs to {ARTEFACTS_DIR}.")
