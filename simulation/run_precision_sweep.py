"""
D6 precision simulation -- concrete sweep grid and report artefacts (Part
B4/B6/C). This is the DRIVER: it calls simulation/generator.py and
simulation/precision.py (which are the reusable, generic pipeline) with a
specific grid of configurations chosen for this report, and writes:

  artefacts/d6_sweep_results.json    -- full per-seed and aggregated results
  artefacts/d6_sweep_n_curve.png     -- CI half-width vs N, several effect sizes
  artefacts/d6_sweep_effect_size.png -- CI half-width & delta vs effect size, realistic N
  artefacts/d6_sweep_missingness.png -- CI half-width vs missingness rate, realistic N

No verdict, no PASS/FAIL, no comparison against any delta value anywhere in
this file (G1) -- artefacts/precision_analysis_v1.md does that comparison,
as arithmetic, for a human to read.

COMMON RANDOM NUMBERS: the SAME set of seeds is reused across every point
within one sweep dimension (e.g., every episodes_per_session value in the
N-curve sweep uses seeds 1..N_SEEDS). This is a standard variance-reduction
technique for simulation studies -- it makes the resulting curve smoother
and more directly comparable point-to-point, because each seed represents
"the same underlying random subject", extended or shortened, rather than an
independent draw at every point.
"""

import json
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.precision import sweep_multi_seed

ARTEFACTS_DIR = os.path.join(REPO_ROOT, "artefacts")
os.makedirs(ARTEFACTS_DIR, exist_ok=True)

N_BOOT = 800
ALPHA = 0.05
RESAMPLE_UNIT = "episode"
N_SEEDS = 10
SEEDS = list(range(1, N_SEEDS + 1))

# "Realistic" anchor per docs/D6_SIMULATION.md section 7 -- INVENTED,
# anchored to the existing (provisional) 10s rolling-window episode unit.
REALISTIC_TRIALS_PER_EPISODE = 5
REALISTIC_EPISODES_PER_SESSION = 270
REALISTIC_N_SESSIONS = 3
REALISTIC_MISSINGNESS = 0.05
REALISTIC_EFFECT_SIZE_FOR_N_CURVE = 0.3  # a moderate, clearly-nonzero effect for the headline N-curve (see docs: exact-zero effect can degenerate to a zero-width CI under hard-argmax macro-F1, which would misrepresent precision if used as the curve's only effect size)


def run_n_curve():
    """CI half-width vs N (episodes_per_session), for n_sessions in
    {1, 2, 3} and effect_size in {0.0, 0.3} (null reference + moderate),
    at realistic missingness."""
    episodes_grid = [25, 50, 100, 150, 200, 270]
    results = []
    t0 = time.time()
    for n_sessions in (1, 2, 3):
        for effect_size in (0.0, REALISTIC_EFFECT_SIZE_FOR_N_CURVE):
            for episodes_per_session in episodes_grid:
                label = f"n_sessions={n_sessions},episodes={episodes_per_session},effect={effect_size}"
                row = sweep_multi_seed(
                    label,
                    dict(
                        n_sessions=n_sessions,
                        episodes_per_session=episodes_per_session,
                        trials_per_episode=REALISTIC_TRIALS_PER_EPISODE,
                        effect_size=effect_size,
                        missingness_rate=REALISTIC_MISSINGNESS,
                    ),
                    SEEDS,
                    RESAMPLE_UNIT,
                    n_boot=N_BOOT,
                    alpha=ALPHA,
                )
                row["n_sessions"] = n_sessions
                row["episodes_per_session"] = episodes_per_session
                row["effect_size"] = effect_size
                results.append(row)
                print(
                    f"  N-curve: sessions={n_sessions} episodes/session={episodes_per_session:3d} "
                    f"effect={effect_size:.1f} -> ci_half_width_median={row['ci_half_width_median']:.4f} "
                    f"(n_trials_total={row['n_trials_total']})  [{time.time()-t0:.0f}s elapsed]"
                )
    return results


def run_effect_size_sweep():
    """delta and CI half-width vs effect_size, at the realistic N."""
    effect_grid = [0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8]
    results = []
    t0 = time.time()
    for effect_size in effect_grid:
        label = f"effect={effect_size}"
        row = sweep_multi_seed(
            label,
            dict(
                n_sessions=REALISTIC_N_SESSIONS,
                episodes_per_session=REALISTIC_EPISODES_PER_SESSION,
                trials_per_episode=REALISTIC_TRIALS_PER_EPISODE,
                effect_size=effect_size,
                missingness_rate=REALISTIC_MISSINGNESS,
            ),
            SEEDS,
            RESAMPLE_UNIT,
            n_boot=N_BOOT,
            alpha=ALPHA,
        )
        row["effect_size"] = effect_size
        results.append(row)
        print(
            f"  Effect sweep: effect={effect_size:.2f} -> delta_median={row['delta_point_median']:+.4f} "
            f"ci_half_width_median={row['ci_half_width_median']:.4f} "
            f"frac_excludes_zero={row['frac_seeds_ci_excludes_zero']:.2f}  [{time.time()-t0:.0f}s elapsed]"
        )
    return results


def run_missingness_sweep():
    """CI half-width vs missingness_rate, at the realistic N and a
    moderate, clearly-nonzero effect size."""
    missingness_grid = [0.0, 0.05, 0.15, 0.30]
    results = []
    t0 = time.time()
    for missingness_rate in missingness_grid:
        label = f"missing={missingness_rate}"
        row = sweep_multi_seed(
            label,
            dict(
                n_sessions=REALISTIC_N_SESSIONS,
                episodes_per_session=REALISTIC_EPISODES_PER_SESSION,
                trials_per_episode=REALISTIC_TRIALS_PER_EPISODE,
                effect_size=REALISTIC_EFFECT_SIZE_FOR_N_CURVE,
                missingness_rate=missingness_rate,
            ),
            SEEDS,
            RESAMPLE_UNIT,
            n_boot=N_BOOT,
            alpha=ALPHA,
        )
        row["missingness_rate"] = missingness_rate
        results.append(row)
        print(
            f"  Missingness sweep: rate={missingness_rate:.2f} -> ci_half_width_median={row['ci_half_width_median']:.4f} "
            f"[{time.time()-t0:.0f}s elapsed]"
        )
    return results


def _strip_per_seed_rows(results):
    """Per-seed rows are useful for JSON archival but bulky/irrelevant for
    the summary CSV-style table -- keep them in the full JSON dump, drop
    them from the lightweight table structure used for plotting."""
    return [{k: v for k, v in r.items() if k != "per_seed_rows"} for r in results]


def make_plots(n_curve_results, effect_size_results, missingness_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # --- Plot 1: CI half-width vs N (episodes/session), one line per (n_sessions, effect_size) ---
    fig, ax = plt.subplots(figsize=(8, 5.5))
    styles = {0.0: "--", REALISTIC_EFFECT_SIZE_FOR_N_CURVE: "-"}
    colors = {1: "tab:blue", 2: "tab:orange", 3: "tab:green"}
    for n_sessions in (1, 2, 3):
        for effect_size in (0.0, REALISTIC_EFFECT_SIZE_FOR_N_CURVE):
            pts = [r for r in n_curve_results if r["n_sessions"] == n_sessions and r["effect_size"] == effect_size]
            pts.sort(key=lambda r: r["episodes_per_session"])
            x = [r["n_trials_total"] for r in pts]
            y = [r["ci_half_width_median"] for r in pts]
            ax.plot(
                x, y, marker="o", linestyle=styles[effect_size], color=colors[n_sessions],
                label=f"{n_sessions} session(s), effect_size={effect_size}",
            )
    ax.set_xlabel("Total trials (across all sessions)")
    ax.set_ylabel("Bootstrap CI half-width on Δ (macro-F1 points)")
    ax.set_title("D6: CI half-width on Δ vs. N\n(episode-level bootstrap, median over 10 seeds)")
    ax.axvline(
        REALISTIC_N_SESSIONS * REALISTIC_EPISODES_PER_SESSION * REALISTIC_TRIALS_PER_EPISODE,
        color="gray", linestyle=":", label="realistic 3-session N (this doc's assumption)",
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(ARTEFACTS_DIR, "d6_sweep_n_curve.png"), dpi=150)
    plt.close(fig)

    # --- Plot 2: delta and CI half-width vs effect_size, realistic N ---
    fig, ax = plt.subplots(figsize=(8, 5.5))
    pts = sorted(effect_size_results, key=lambda r: r["effect_size"])
    x = [r["effect_size"] for r in pts]
    delta = [r["delta_point_median"] for r in pts]
    hw = [r["ci_half_width_median"] for r in pts]
    ax.plot(x, delta, marker="o", color="tab:purple", label="median Δ_point")
    ax.fill_between(
        x, [d - h for d, h in zip(delta, hw)], [d + h for d, h in zip(delta, hw)],
        alpha=0.2, color="tab:purple", label="median bootstrap CI half-width band",
    )
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel("Configured effect_size (nominal correlation between candidate signal and true latent state)")
    ax.set_ylabel("Δ (macro-F1 points)")
    ax.set_title(
        f"D6: Δ and its CI vs. true effect size\n"
        f"(realistic N: {REALISTIC_N_SESSIONS} sessions x {REALISTIC_EPISODES_PER_SESSION} episodes x "
        f"{REALISTIC_TRIALS_PER_EPISODE} trials, median over 10 seeds)"
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(ARTEFACTS_DIR, "d6_sweep_effect_size.png"), dpi=150)
    plt.close(fig)

    # --- Plot 3: CI half-width vs missingness, realistic N ---
    fig, ax = plt.subplots(figsize=(8, 5.5))
    pts = sorted(missingness_results, key=lambda r: r["missingness_rate"])
    x = [r["missingness_rate"] for r in pts]
    hw = [r["ci_half_width_median"] for r in pts]
    ax.plot(x, hw, marker="o", color="tab:red")
    ax.set_xlabel("Missingness rate (bursty, 2-state Markov)")
    ax.set_ylabel("Bootstrap CI half-width on Δ (macro-F1 points)")
    ax.set_title(
        f"D6: CI half-width vs. missingness rate\n"
        f"(realistic N, effect_size={REALISTIC_EFFECT_SIZE_FOR_N_CURVE}, median over 10 seeds)"
    )
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(ARTEFACTS_DIR, "d6_sweep_missingness.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    t_start = time.time()
    print("Running N-curve sweep...")
    n_curve_results = run_n_curve()
    print("Running effect-size sweep...")
    effect_size_results = run_effect_size_sweep()
    print("Running missingness sweep...")
    missingness_results = run_missingness_sweep()

    print("Writing plots...")
    make_plots(n_curve_results, effect_size_results, missingness_results)

    out = {
        "config": {
            "n_boot": N_BOOT,
            "alpha": ALPHA,
            "resample_unit": RESAMPLE_UNIT,
            "seeds": SEEDS,
            "realistic_trials_per_episode": REALISTIC_TRIALS_PER_EPISODE,
            "realistic_episodes_per_session": REALISTIC_EPISODES_PER_SESSION,
            "realistic_n_sessions": REALISTIC_N_SESSIONS,
            "realistic_missingness": REALISTIC_MISSINGNESS,
        },
        "n_curve": _strip_per_seed_rows(n_curve_results),
        "effect_size_sweep": _strip_per_seed_rows(effect_size_results),
        "missingness_sweep": _strip_per_seed_rows(missingness_results),
    }
    out_path = os.path.join(ARTEFACTS_DIR, "d6_sweep_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\nDone in {time.time()-t_start:.0f}s. Wrote {out_path} and 3 PNGs to {ARTEFACTS_DIR}.")
