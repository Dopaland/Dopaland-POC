"""
D6 precision simulation, FINALISATION PASS (D0PA1). Addresses two gaps in
Pass 2 that affect a number a human is about to sign a threshold against:

  TASK 1 -- STABILISE THE ESTIMATE. Pass 2's n_boot=50 (refit-per-replicate
  double bootstrap) is too few for the half-width itself to be trusted as
  a stable number. This raises n_boot to >=200 and reports the Monte Carlo
  spread of the resulting half-width across independent seeds (mean, std,
  min, max) -- not just a single point estimate.

  TASK 2 -- THE JOINT GRID. Pass 2 swept session length and rare-class
  frequency ONE AT A TIME, at whichever value was "primary" for the other
  factor. This runs the FULL 3x2 grid (25/35/45 minutes crossed with
  rare-class frequency 0.02/0.05) so the governing number -- the one that
  actually applies once the client supplies real values for both factors
  -- exists as a lookup table, not something re-derived later.

  TASK 3 -- VERDICT MAP AT THE WORST CELL. Reproduces Pass 2's verdict-map
  arithmetic (imported unchanged from run_precision_sweep_pass2.py) at the
  worst grid cell's half-width, alongside Pass 2's original (45min, 0.05)
  map, so the gap between optimistic and pessimistic planning assumptions
  is visible in one place. No recommendation anywhere (G1).

This script does NOT modify simulation/run_precision_sweep.py,
run_precision_sweep_pass2.py, artefacts/precision_analysis_v1.md, or
artefacts/precision_analysis_v2.md's existing content -- v2 gets a NEW,
clearly-headed addendum section appended, never a rewrite of what's
already there (per this task's own instruction).
"""

import json
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.precision import sweep_multi_seed_refit
from simulation.run_precision_sweep_pass2 import (
    episodes_for_minutes,
    verdict_map,
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

# --- TASK 1.1: raised from Pass 2's 50 to >=200, per instruction. Profiled
# directly before committing to this number (see docs/D6_SIMULATION.md
# section 10 for the exact timings measured): a single double-bootstrap
# replicate costs ~0.11s at 25 minutes (150 episodes), ~0.39-0.41s at 35/45
# minutes (210/270 episodes). At n_boot=200 that is ~22-83s per
# (config, seed) cell -- the full 6-cell x 5-seed grid below was estimated
# at ~30 minutes wall-clock before running, and the ACTUAL measured
# wall-clock is reported in the final report and in the addendum (not
# silently kept at Pass 2's cheaper 50 because it was faster).
N_BOOT = 200

# SAME 5 seeds as Pass 2 (simulation/run_precision_sweep_pass2.py's
# SEEDS = [1..5]) -- deliberate, so the "n_boot=50 vs n_boot>=200"
# comparison in Task 1.3 isolates the effect of the replicate count alone,
# not a confound with different data realizations.
N_SEEDS = 5
SEEDS = list(range(1, N_SEEDS + 1))

SESSION_MINUTES_GRID = [25, 35, 45]
RARE_FREQ_GRID = [0.02, 0.05]

PASS2_RESULTS_PATH = os.path.join(ARTEFACTS_DIR, "d6_sweep_pass2_results.json")


def _cell_config(minutes, rare_freq):
    episodes = episodes_for_minutes(minutes)
    return episodes, dict(
        n_sessions=N_SESSIONS_REALISTIC,
        episodes_per_session=episodes,
        trials_per_episode=TRIALS_PER_EPISODE,
        n_classes=PRIMARY_N_CLASSES,
        n_rare_classes=PRIMARY_N_RARE,
        rare_class_frequency=rare_freq,
        effect_size=REALISTIC_EFFECT_SIZE,
        missingness_rate=REALISTIC_MISSINGNESS,
    )


def run_joint_grid():
    """TASK 2.1/2.2: the full 3x2 grid, each cell's half-width reported
    with mean/std/min/max across the 5 seeds (TASK 1.2's Monte Carlo
    spread), all at n_boot=N_BOOT."""
    results = []
    t0 = time.time()
    for minutes in SESSION_MINUTES_GRID:
        for rare_freq in RARE_FREQ_GRID:
            episodes, cfg = _cell_config(minutes, rare_freq)
            label = f"{minutes}min_x_rare{rare_freq}"
            row = sweep_multi_seed_refit(label, cfg, SEEDS, RESAMPLE_UNIT, n_boot=N_BOOT, alpha=ALPHA)

            half_widths = np.array([r["ci_half_width"] for r in row["per_seed_rows"]])
            row["session_minutes"] = minutes
            row["episodes_per_session"] = episodes
            row["rare_class_frequency"] = rare_freq
            row["ci_half_width_mean"] = float(np.mean(half_widths))
            row["ci_half_width_std"] = float(np.std(half_widths))
            row["ci_half_width_min"] = float(np.min(half_widths))
            row["ci_half_width_max"] = float(np.max(half_widths))
            results.append(row)
            print(
                f"  {minutes:2d}min x rare={rare_freq:.2f} (n_trials={row['n_trials_total']}): "
                f"half_width mean={row['ci_half_width_mean']:.4f} std={row['ci_half_width_std']:.4f} "
                f"min={row['ci_half_width_min']:.4f} max={row['ci_half_width_max']:.4f}  "
                f"[{time.time()-t0:.0f}s elapsed]"
            )
    return results


def _strip(results):
    return [{k: v for k, v in r.items() if k != "per_seed_rows"} for r in results]


def load_pass2_comparison_cell():
    """TASK 1.3: pull Pass 2's own (45min, rare=0.05) n_boot=50 numbers
    from its saved JSON for a direct side-by-side -- never recomputed,
    read verbatim from what Pass 2 already produced and committed."""
    with open(PASS2_RESULTS_PATH, "r", encoding="utf-8") as f:
        pass2 = json.load(f)
    for row in pass2["1_2_n_classes_sweep"]:
        if row.get("rare_class_frequency") == 0.05 and row.get("n_classes") == PRIMARY_N_CLASSES:
            return row
    raise ValueError("could not find Pass 2's n_classes=5, rare_freq=0.05 row in its saved JSON")


def make_plot(grid_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = {0.02: "tab:red", 0.05: "tab:blue"}
    for rare_freq in RARE_FREQ_GRID:
        pts = [r for r in grid_results if r["rare_class_frequency"] == rare_freq]
        pts.sort(key=lambda r: r["session_minutes"])
        x = [r["session_minutes"] for r in pts]
        y = [r["ci_half_width_mean"] for r in pts]
        yerr = [r["ci_half_width_std"] for r in pts]
        ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, color=colors[rare_freq], label=f"rare_class_frequency={rare_freq}")
    ax.set_xlabel("Session length (minutes)")
    ax.set_ylabel("Bootstrap CI half-width on Δ (macro-F1 points)\nmean ± 1 std across 5 seeds")
    ax.set_title(f"Finalisation: joint grid, session length x rare-class frequency\n(refit double bootstrap, n_boot={N_BOOT}, n_classes=5)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(ARTEFACTS_DIR, "d6_finalisation_joint_grid.svg"))
    plt.close(fig)


if __name__ == "__main__":
    t_start = time.time()

    print(f"Running joint grid (n_boot={N_BOOT}, seeds={SEEDS})...")
    grid_results = run_joint_grid()

    worst_cell = max(grid_results, key=lambda r: r["ci_half_width_mean"])
    print(f"\nWorst cell: {worst_cell['label']} -> mean half_width={worst_cell['ci_half_width_mean']:.4f}")

    pass2_cell = load_pass2_comparison_cell()
    finalisation_realistic_cell = next(
        r for r in grid_results if r["session_minutes"] == 45 and r["rare_class_frequency"] == 0.05
    )

    true_deltas = [round(0.01 * i, 2) for i in range(0, 12)]  # 0.00 .. 0.11 (wider than Pass 2 to cover the worst cell's larger half-width)
    delta_thresholds = [0.03, 0.05]
    verdict_optimistic = verdict_map(pass2_cell["ci_half_width_median"], true_deltas, delta_thresholds)
    verdict_pessimistic = verdict_map(worst_cell["ci_half_width_mean"], true_deltas, delta_thresholds)

    print("\nWriting plot...")
    make_plot(grid_results)

    out = {
        "config": {
            "n_boot": N_BOOT,
            "n_seeds": N_SEEDS,
            "seeds": SEEDS,
            "alpha": ALPHA,
            "resample_unit": RESAMPLE_UNIT,
            "session_minutes_grid": SESSION_MINUTES_GRID,
            "rare_freq_grid": RARE_FREQ_GRID,
        },
        "joint_grid": _strip(grid_results),
        "worst_cell_label": worst_cell["label"],
        "pass2_comparison_cell_n_boot_50": pass2_cell,
        "finalisation_realistic_cell_n_boot_200": {k: v for k, v in finalisation_realistic_cell.items() if k != "per_seed_rows"},
        "verdict_map_optimistic_45min_0.05_pass2_half_width": {
            "half_width_used": pass2_cell["ci_half_width_median"],
            "rows": verdict_optimistic,
        },
        "verdict_map_pessimistic_worst_cell_half_width": {
            "half_width_used": worst_cell["ci_half_width_mean"],
            "worst_cell_label": worst_cell["label"],
            "rows": verdict_pessimistic,
        },
        "wall_clock_seconds": time.time() - t_start,
    }
    out_path = os.path.join(ARTEFACTS_DIR, "d6_finalisation_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\nDone in {time.time()-t_start:.0f}s. Wrote {out_path} and 1 SVG to {ARTEFACTS_DIR}.")
