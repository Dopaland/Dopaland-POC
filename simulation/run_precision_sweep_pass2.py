"""
D6 precision simulation, PASS 2 (D0PA1). Fixes three sources of optimism
Pass 1 itself disclosed (see docs/D6_SIMULATION.md and
artefacts/precision_analysis_v1.md's own limitations section):

  1.1 REFIT PER BOOTSTRAP REPLICATE, not just re-evaluate a single fixed
      model against resampled test episodes.
  1.2 n_classes=5 (three forced-choice regions + ABANDON + NO_ACTION as
      real, rare classes), n_classes=3 retained for comparison.
  1.3 SESSION LENGTH as an explicit swept parameter (25/35/45 minutes),
      not a single invented number.

No verdict anywhere in this file (G1) -- 1.4's verdict-map function
computes arithmetic (RETAIN/DROP/INCONCLUSIVE as a MAPPING from
(true_delta, delta_threshold, precision) to an outcome), it does not
choose or recommend a delta_threshold.

This script does NOT modify simulation/run_precision_sweep.py or
artefacts/precision_analysis_v1.md -- Pass 1's code and artefact are left
exactly as they were, per the task's "keep v1 unchanged" instruction. It
writes its own outputs (artefacts/d6_sweep_pass2_results.json and Pass-2
plots) and artefacts/precision_analysis_v2.md documents the diff.
"""

import json
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.precision import sweep_multi_seed, sweep_multi_seed_refit

ARTEFACTS_DIR = os.path.join(REPO_ROOT, "artefacts")
os.makedirs(ARTEFACTS_DIR, exist_ok=True)

ALPHA = 0.05
RESAMPLE_UNIT = "episode"

# --- Replicate/seed counts -- REDUCED from Pass 1, and stated as such,
# not hidden. Profiled directly (simulation/run_precision_sweep_pass2.py's
# own dev process, not asserted): a single refit-bootstrap replicate at
# the realistic N (n_classes=5, 3 sessions x 270 episodes x 5 trials)
# costs ~0.44s (2 full model refits + prediction), vs Pass 1's fixed-model
# bootstrap doing ~800 replicates in well under a second combined (no
# refitting, just re-evaluating cached predictions). Running Pass 1's
# n_boot=800 with a full refit per replicate would cost ~6 minutes PER
# (config, seed) pair; across the configs and seeds this pass needs, that
# is not tractable in this environment. N_BOOT_REFIT and N_SEEDS below are
# the deliberately reduced numbers -- every reported CI from this pass
# states its n_boot and n_seeds explicitly so a smaller sample's extra
# noise is visible, not disguised as equal-quality to Pass 1's numbers.
N_BOOT_REFIT = 50
N_BOOT_FIXED = 800  # unchanged from Pass 1 -- used only for the 1.1 side-by-side
N_SEEDS = 5
SEEDS = list(range(1, N_SEEDS + 1))

# --- Realistic-N anchor, UNCHANGED from Pass 1 (docs/D6_SIMULATION.md
# section 7): 1 episode = the existing provisional 10s rolling window,
# trials_per_episode=5 (~2s/trial). Session LENGTH is now swept (1.3)
# rather than fixed at Pass 1's single 45-minute guess.
SECONDS_PER_EPISODE = 10.0
TRIALS_PER_EPISODE = 5
N_SESSIONS_REALISTIC = 3
REALISTIC_MISSINGNESS = 0.05
REALISTIC_EFFECT_SIZE = 0.3  # same moderate, clearly-nonzero anchor Pass 1 used for its N-curve


def episodes_for_minutes(minutes):
    return int(round(minutes * 60.0 / SECONDS_PER_EPISODE))


REALISTIC_MINUTES = 45  # Pass 1's single guess -- now one of three swept points, not the only one
REALISTIC_EPISODES = episodes_for_minutes(REALISTIC_MINUTES)  # 270, matches Pass 1 exactly

# --- 1.2: class structure. The client's task harness presents THREE
# REGIONS, FORCED CHOICE, plus ABANDON and NO_ACTION as REAL classes -- 5
# total. ABANDON/NO_ACTION modeled as RARE relative to the three choice
# classes (INVENTED frequencies, swept at two plausible values -- see
# docs/D6_SIMULATION.md Pass 2 section for why these two numbers and no
# others).
PRIMARY_N_CLASSES = 5
PRIMARY_N_RARE = 2
PRIMARY_RARE_FREQ = 0.05   # "moderately rare" -- e.g. abandoning/declining to act ~1 in 20 trials
SECONDARY_RARE_FREQ = 0.02  # "very rare" -- e.g. ~1 in 50 trials


def run_1_1_comparison():
    """Side-by-side: Pass 1's fixed-model bootstrap vs Pass 2's refit
    bootstrap, on the IDENTICAL config (n_classes=5, 45-minute sessions)
    so the comparison isolates the effect of the bootstrap correction
    itself, not a confound with the n_classes/session-length changes
    covered separately in 1.2/1.3."""
    config_kwargs = dict(
        n_sessions=N_SESSIONS_REALISTIC,
        episodes_per_session=REALISTIC_EPISODES,
        trials_per_episode=TRIALS_PER_EPISODE,
        n_classes=PRIMARY_N_CLASSES,
        n_rare_classes=PRIMARY_N_RARE,
        rare_class_frequency=PRIMARY_RARE_FREQ,
        effect_size=REALISTIC_EFFECT_SIZE,
        missingness_rate=REALISTIC_MISSINGNESS,
    )
    t0 = time.time()
    fixed = sweep_multi_seed(
        "1.1_fixed_model_bootstrap_pass1_method", config_kwargs, SEEDS, RESAMPLE_UNIT, n_boot=N_BOOT_FIXED, alpha=ALPHA
    )
    print(f"  1.1 fixed-model bootstrap: half_width_median={fixed['ci_half_width_median']:.4f} [{time.time()-t0:.0f}s]")
    t0 = time.time()
    refit = sweep_multi_seed_refit(
        "1.1_refit_per_replicate_pass2_method", config_kwargs, SEEDS, RESAMPLE_UNIT, n_boot=N_BOOT_REFIT, alpha=ALPHA
    )
    print(f"  1.1 refit-per-replicate:   half_width_median={refit['ci_half_width_median']:.4f} [{time.time()-t0:.0f}s]")
    return fixed, refit


def run_1_2_n_classes_sweep():
    """n_classes=3 (Pass 1's structure, for comparison) vs n_classes=5 at
    two rare-class frequencies, all at the realistic 45-minute session
    length, all using the corrected refit bootstrap."""
    results = []
    t0 = time.time()

    cfg3 = dict(
        n_sessions=N_SESSIONS_REALISTIC, episodes_per_session=REALISTIC_EPISODES,
        trials_per_episode=TRIALS_PER_EPISODE, n_classes=3, n_rare_classes=0,
        effect_size=REALISTIC_EFFECT_SIZE, missingness_rate=REALISTIC_MISSINGNESS,
    )
    row3 = sweep_multi_seed_refit("1.2_n_classes=3_comparison", cfg3, SEEDS, RESAMPLE_UNIT, n_boot=N_BOOT_REFIT, alpha=ALPHA)
    results.append(row3)
    print(f"  1.2 n_classes=3: half_width_median={row3['ci_half_width_median']:.4f} [{time.time()-t0:.0f}s elapsed]")

    for rare_freq, label in ((PRIMARY_RARE_FREQ, "primary_0.05"), (SECONDARY_RARE_FREQ, "secondary_0.02")):
        cfg5 = dict(
            n_sessions=N_SESSIONS_REALISTIC, episodes_per_session=REALISTIC_EPISODES,
            trials_per_episode=TRIALS_PER_EPISODE, n_classes=PRIMARY_N_CLASSES,
            n_rare_classes=PRIMARY_N_RARE, rare_class_frequency=rare_freq,
            effect_size=REALISTIC_EFFECT_SIZE, missingness_rate=REALISTIC_MISSINGNESS,
        )
        row5 = sweep_multi_seed_refit(
            f"1.2_n_classes=5_rare_freq={rare_freq}_{label}", cfg5, SEEDS, RESAMPLE_UNIT, n_boot=N_BOOT_REFIT, alpha=ALPHA
        )
        row5["rare_class_frequency"] = rare_freq
        results.append(row5)
        print(f"  1.2 n_classes=5, rare_freq={rare_freq}: half_width_median={row5['ci_half_width_median']:.4f} [{time.time()-t0:.0f}s elapsed]")

    return results


def run_1_3_session_length_sweep():
    """Session duration swept at 25/35/45 minutes, at n_classes=5 with the
    PRIMARY rare-class frequency, all using the corrected refit bootstrap."""
    results = []
    t0 = time.time()
    for minutes in (25, 35, 45):
        episodes = episodes_for_minutes(minutes)
        cfg = dict(
            n_sessions=N_SESSIONS_REALISTIC, episodes_per_session=episodes,
            trials_per_episode=TRIALS_PER_EPISODE, n_classes=PRIMARY_N_CLASSES,
            n_rare_classes=PRIMARY_N_RARE, rare_class_frequency=PRIMARY_RARE_FREQ,
            effect_size=REALISTIC_EFFECT_SIZE, missingness_rate=REALISTIC_MISSINGNESS,
        )
        row = sweep_multi_seed_refit(f"1.3_session={minutes}min", cfg, SEEDS, RESAMPLE_UNIT, n_boot=N_BOOT_REFIT, alpha=ALPHA)
        row["session_minutes"] = minutes
        row["episodes_per_session"] = episodes
        results.append(row)
        print(
            f"  1.3 session={minutes}min ({episodes} episodes, n_trials={row['n_trials_total']}): "
            f"half_width_median={row['ci_half_width_median']:.4f} [{time.time()-t0:.0f}s elapsed]"
        )
    return results


def verdict_map(ci_half_width, true_deltas, delta_thresholds):
    """1.4 -- PURE ARITHMETIC. No simulation runs here beyond the already-
    computed ci_half_width (from 1.1's corrected, realistic-N result).
    Models the observed CI as [true_delta - ci_half_width, true_delta +
    ci_half_width] -- a symmetric approximation around an unbiased point
    estimate, consistent with Pass 1's finding that delta_point tracked
    the configured true effect closely (see
    artefacts/precision_analysis_v1.md section 3.2). This function
    computes RETAIN/DROP/INCONCLUSIVE for each (true_delta,
    delta_threshold) pair per the pre-registered decision rule -- it does
    NOT choose, prefer, or recommend any delta_threshold (G1)."""
    rows = []
    for true_delta in true_deltas:
        lo = true_delta - ci_half_width
        hi = true_delta + ci_half_width
        for delta_threshold in delta_thresholds:
            if lo > delta_threshold:
                verdict = "RETAIN"
            elif hi < delta_threshold:
                verdict = "DROP"
            else:
                verdict = "INCONCLUSIVE"
            rows.append(
                {
                    "true_delta": true_delta,
                    "delta_threshold": delta_threshold,
                    "ci_lo": lo,
                    "ci_hi": hi,
                    "verdict": verdict,
                }
            )
    return rows


def _strip(results):
    return [{k: v for k, v in r.items() if k != "per_seed_rows"} for r in results]


def make_plots(n_classes_results, session_length_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5.5))
    labels = [r["label"] for r in n_classes_results]
    half_widths = [r["ci_half_width_median"] for r in n_classes_results]
    mins = [r["ci_half_width_min"] for r in n_classes_results]
    maxs = [r["ci_half_width_max"] for r in n_classes_results]
    x = np.arange(len(labels))
    ax.bar(x, half_widths, yerr=[np.array(half_widths) - np.array(mins), np.array(maxs) - np.array(half_widths)], capsize=4, color="tab:blue", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(["n_classes=3\n(Pass 1)", "n_classes=5\nrare=0.05", "n_classes=5\nrare=0.02"], fontsize=9)
    ax.set_ylabel("Median bootstrap CI half-width on Δ (macro-F1 points)")
    ax.set_title(f"Pass 2, 1.2: CI half-width vs. class structure\n(refit bootstrap, n_boot={N_BOOT_REFIT}, median over {N_SEEDS} seeds; error bars = min/max)")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(ARTEFACTS_DIR, "d6_pass2_n_classes.svg"))
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    minutes = [r["session_minutes"] for r in session_length_results]
    half_widths = [r["ci_half_width_median"] for r in session_length_results]
    n_trials = [r["n_trials_total"] for r in session_length_results]
    ax.plot(minutes, half_widths, marker="o", color="tab:green")
    for m, h, n in zip(minutes, half_widths, n_trials):
        ax.annotate(f"N={n}", (m, h), textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax.set_xlabel("Session length (minutes)")
    ax.set_ylabel("Median bootstrap CI half-width on Δ (macro-F1 points)")
    ax.set_title(f"Pass 2, 1.3: CI half-width vs. session length\n(3 sessions, refit bootstrap, n_boot={N_BOOT_REFIT}, median over {N_SEEDS} seeds)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(ARTEFACTS_DIR, "d6_pass2_session_length.svg"))
    plt.close(fig)


if __name__ == "__main__":
    t_start = time.time()

    print("Running 1.1 fixed-vs-refit comparison...")
    fixed_result, refit_result = run_1_1_comparison()

    print("Running 1.2 n_classes sweep...")
    n_classes_results = run_1_2_n_classes_sweep()

    print("Running 1.3 session-length sweep...")
    session_length_results = run_1_3_session_length_sweep()

    # 1.4: verdict map, built from the PRIMARY corrected half-width (5
    # classes, primary rare frequency, 45-minute sessions -- the realistic
    # config used throughout 1.1/1.2/1.3's "primary" row).
    primary_half_width = n_classes_results[1]["ci_half_width_median"]  # n_classes=5, rare_freq=0.05
    true_deltas = [round(0.01 * i, 2) for i in range(0, 10)]  # 0.00 .. 0.09
    delta_thresholds = [0.03, 0.05]
    verdict_rows = verdict_map(primary_half_width, true_deltas, delta_thresholds)

    print("Writing plots...")
    make_plots(n_classes_results, session_length_results)

    out = {
        "config": {
            "n_boot_refit": N_BOOT_REFIT,
            "n_boot_fixed": N_BOOT_FIXED,
            "n_seeds": N_SEEDS,
            "seeds": SEEDS,
            "alpha": ALPHA,
            "resample_unit": RESAMPLE_UNIT,
            "realistic_minutes": REALISTIC_MINUTES,
            "realistic_episodes": REALISTIC_EPISODES,
            "n_sessions_realistic": N_SESSIONS_REALISTIC,
            "realistic_missingness": REALISTIC_MISSINGNESS,
            "realistic_effect_size": REALISTIC_EFFECT_SIZE,
            "primary_n_classes": PRIMARY_N_CLASSES,
            "primary_n_rare": PRIMARY_N_RARE,
            "primary_rare_freq": PRIMARY_RARE_FREQ,
            "secondary_rare_freq": SECONDARY_RARE_FREQ,
        },
        "1_1_comparison": {
            "fixed_model_bootstrap": _strip([fixed_result])[0],
            "refit_per_replicate": _strip([refit_result])[0],
        },
        "1_2_n_classes_sweep": _strip(n_classes_results),
        "1_3_session_length_sweep": _strip(session_length_results),
        "1_4_verdict_map": {
            "primary_half_width_used": primary_half_width,
            "rows": verdict_rows,
        },
    }
    out_path = os.path.join(ARTEFACTS_DIR, "d6_sweep_pass2_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\nDone in {time.time()-t_start:.0f}s. Wrote {out_path} and 2 SVGs to {ARTEFACTS_DIR}.")
