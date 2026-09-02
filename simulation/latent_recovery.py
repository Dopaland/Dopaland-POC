"""
D0PA1 -- SYNTHETIC LATENT RECOVERY.

    Z_true -> observation generator -> pipeline -> Z_hat
    recovery_error = d(Z_true, Z_hat)

MUST be runnable BEFORE any latent model touches human data (2.5's
prerequisite, restated as code: this module never imports anything camera-
or feature-derived; it operates entirely on simulation.generator's
synthetic z/x_signal streams).

WHY THIS IS A PREREQUISITE, NOT AN EXTRA (2.5): without this check, a
near-zero measured latent contribution on REAL data is ambiguous between
two completely different explanations -- "the latent state genuinely adds
nothing" (a real, valuable negative result -- one of the outcomes this
study is explicitly designed to be able to report) and "the recovery
implementation is silently broken" (a bug, not a finding). Those two
explanations require completely different responses, and nothing about a
near-zero number on its own tells you which one you're looking at. This
module removes that ambiguity in the one place it CAN be removed -- on
synthetic data where the true latent state is known -- so that a later
near-zero result on real data can be read as a finding about the world
rather than a question about the code.

G1: this module reports two numbers per sweep point (correlation, RMSE).
It sets NO success threshold anywhere. The proposed values (correlation
>= 0.7, standardised RMSE <= 0.5) are NOT implemented here as a
pass/fail -- see run_and_report()'s own docstring. That comparison is for
a human to make, against numbers this module computes and prints.

G2: nothing here is tuned to make the recovery curve look better. The
recovery pipeline (a simple exponential moving average, see
recover_latent_ema()) is the simplest defensible choice consistent with
"simple model families" (the client's own scope constraint, see
simulation/models.py's docstring) -- not a sophisticated filter selected
because it produced a nicer curve.

2.4 -- STATED PLAINLY, HERE AND IN docs/D6_SIMULATION.md's latent-recovery
section: this validates the MACHINERY (does correlation/RMSE computation,
missing-data handling, and a plausible simple recovery procedure behave
correctly on data with a KNOWN generative process) under KNOWN, STATED
assumptions (AR(1) latent state, Gaussian observation noise, the
generator's own A1-A6 model). It establishes NOTHING about whether a
human latent state is psychologically real, or whether this particular
recovery procedure is the right one for real data. That distinction is
CONTRACTUAL, not stylistic -- do not present a result from this module as
evidence about the subject.
"""

from dataclasses import dataclass

import numpy as np

from simulation.config import PRE_REGISTERED_CONFIG
from simulation.generator import GeneratorConfig, generate


# ============================================================
# THE PIPELINE: Z_true -> observation generator -> pipeline -> Z_hat
# ============================================================

def add_observation_noise(records, extra_noise_std, rng):
    """Corrupts x_signal with ADDITIONAL i.i.d. Gaussian noise (std=
    extra_noise_std), simulating measurement/sensor noise ON TOP OF the
    generator's own effect_size-controlled mixing. This is a genuinely
    DIFFERENT axis from effect_size: effect_size governs how much the true
    state z contributes to the observation IN THE GENERATIVE MODEL ITSELF
    (a property of the simulated subject/task); extra_noise_std simulates
    additional corruption a real sensor might add AFTERWARD, independent
    of that. Missing values stay missing -- no noise is added to a value
    that was never observed."""
    out = []
    for r in records:
        new_r = dict(r)
        if r["x_signal"] is not None and extra_noise_std > 0:
            new_r["x_signal"] = r["x_signal"] + float(rng.normal(scale=extra_noise_std))
        out.append(new_r)
    return out


def recover_latent_ema(records, alpha=0.3):
    """THE PIPELINE. A simple exponential moving average over x_signal,
    reset at the start of every session (matching z's own per-session
    reset, generator.py A1) -- the simplest defensible recovery procedure
    consistent with "simple model families" (G2: not chosen because it
    produces a nicer curve; chosen because it is the simplest thing that
    exploits the SAME serial-dependence assumption (A1) the generator
    itself uses, without needing to know the generator's exact ar1_phi/
    sigma -- a real analysis would not know those either).

    Missing x_signal: NO UPDATE -- the estimate carries forward from the
    last real observation (no new information means no reason to move the
    estimate). Before the FIRST real observation in a session, there is no
    estimate at all -- those positions return z_hat=None, never a
    fabricated 0.0.

    Returns a list of z_hat values, ONE PER RECORD, in the SAME order as
    the input `records` (not grouped/reordered) -- so callers can zip it
    directly against the corresponding z_true sequence."""
    by_session = {}
    for idx, r in enumerate(records):
        by_session.setdefault(r["session_idx"], []).append((idx, r))
    for group in by_session.values():
        group.sort(key=lambda pair: pair[1]["global_trial_idx"])

    z_hat = [None] * len(records)
    for group in by_session.values():
        est = None
        for idx, r in group:
            if r["x_signal"] is not None:
                est = float(r["x_signal"]) if est is None else float(alpha * r["x_signal"] + (1 - alpha) * est)
            z_hat[idx] = est
    return z_hat


# ============================================================
# recovery_error = d(Z_true, Z_hat) -- 2.1, BOTH metrics, never one blended
# number: correlation alone can look healthy under a systematic scale
# error (a model that outputs 5*z_true correlates perfectly with z_true
# but is badly wrong in an absolute sense); RMSE alone conflates a pure
# scale/offset error with genuine noise -- reporting both is what lets a
# reader tell those apart.
# ============================================================

def compute_recovery_metrics(z_true, z_hat):
    """z_true, z_hat: equal-length sequences, z_hat may contain None
    (before-any-observation positions, see recover_latent_ema). Pairs
    with z_hat=None are excluded, counted (n_used vs n_total), never
    silently treated as agreement or disagreement. Both series are
    z-scored (each against its OWN mean/std over the used pairs) before
    RMSE -- "RMSE in standardised units" (2.1's exact phrase): otherwise
    RMSE would just restate whatever arbitrary scale z_hat happens to be
    in, which carries no information about recovery QUALITY on its own."""
    n_total = len(z_true)
    pairs = [(t, h) for t, h in zip(z_true, z_hat) if h is not None]
    n_used = len(pairs)
    if n_used < 2:
        return {
            "pearson_r": None, "rmse_standardized": None,
            "n_used": n_used, "n_total": n_total, "missingness_reason": "insufficient_samples",
        }

    t_arr = np.array([p[0] for p in pairs], dtype=float)
    h_arr = np.array([p[1] for p in pairs], dtype=float)

    t_std_dev = float(t_arr.std())
    h_std_dev = float(h_arr.std())
    epsilon = PRE_REGISTERED_CONFIG.zero_dispersion_epsilon
    degenerate = t_std_dev < epsilon or h_std_dev < epsilon

    if degenerate:
        # Neither correlation nor a standardised RMSE is meaningful when
        # either series has ~zero spread over the window -- NEVER divide
        # by a ~zero std to standardise, and NEVER silently add an
        # epsilon (same rule as everywhere else in this codebase).
        return {
            "pearson_r": None, "rmse_standardized": None,
            "n_used": n_used, "n_total": n_total, "missingness_reason": "zero_dispersion",
        }

    pearson_r = float(np.corrcoef(t_arr, h_arr)[0, 1])
    t_z = (t_arr - t_arr.mean()) / t_std_dev
    h_z = (h_arr - h_arr.mean()) / h_std_dev
    rmse_standardized = float(np.sqrt(np.mean((t_z - h_z) ** 2)))

    return {
        "pearson_r": pearson_r, "rmse_standardized": rmse_standardized,
        "n_used": n_used, "n_total": n_total, "missingness_reason": None,
    }


# ============================================================
# 2.2 -- sweep across noise levels AND effect sizes, so the recovery
# curve is visible rather than a single point.
# ============================================================

@dataclass(frozen=True)
class LatentRecoveryConfig:
    """Parameterizes the recovery pipeline itself (ema_alpha) and the
    synthetic-generation side (n_sessions/episodes_per_session/
    trials_per_episode) -- not the sweep AXES themselves (effect_sizes,
    extra_noise_stds), which are supplied directly to run_recovery_sweep
    since a sweep's grid is a property of a specific run, not a
    pre-registered constant."""

    seed: int = 0
    n_sessions: int = 3
    episodes_per_session: int = 200
    trials_per_episode: int = 5
    ema_alpha: float = 0.3


def run_one_recovery_point(effect_size, extra_noise_std, config: LatentRecoveryConfig):
    """One (effect_size, extra_noise_std) sweep point: generate synthetic
    trials at this effect_size, corrupt x_signal with extra_noise_std of
    additional observation noise, recover Z_hat via the EMA pipeline,
    compute both recovery metrics against the generator's own known
    Z_true (the `z` field -- generator-internal, exists ONLY for this
    kind of machinery validation, per simulation/generator.py's own
    docstring)."""
    gen_config = GeneratorConfig(
        seed=config.seed, n_sessions=config.n_sessions, episodes_per_session=config.episodes_per_session,
        trials_per_episode=config.trials_per_episode, effect_size=effect_size,
    )
    records = generate(gen_config)
    noise_rng = np.random.default_rng(config.seed + 7_000_003 + round(extra_noise_std * 10_000))
    noisy_records = add_observation_noise(records, extra_noise_std, noise_rng)

    z_true = [r["z"] for r in records]
    z_hat = recover_latent_ema(noisy_records, alpha=config.ema_alpha)
    metrics = compute_recovery_metrics(z_true, z_hat)

    return {"effect_size": effect_size, "extra_noise_std": extra_noise_std, **metrics}


def run_recovery_sweep(effect_sizes, extra_noise_stds, config=None):
    """2.2: the full grid, effect_sizes x extra_noise_stds. Returns a flat
    list of run_one_recovery_point() results -- the recovery CURVE, not a
    single point."""
    if config is None:
        config = LatentRecoveryConfig()
    return [
        run_one_recovery_point(effect_size, extra_noise_std, config)
        for effect_size in effect_sizes
        for extra_noise_std in extra_noise_stds
    ]


def format_recovery_table(rows):
    """No verdict column, no pass/fail highlighting (G1/2.3) -- the
    proposed values (correlation >= 0.7, standardised RMSE <= 0.5) are
    NOT printed here as a threshold; a human reading this table brings
    those numbers themselves and compares."""
    lines = []
    header = f"{'effect_size':>11s} {'extra_noise_std':>15s} {'pearson_r':>10s} {'rmse_std':>9s} {'n_used':>7s} {'n_total':>7s}"
    lines.append(header)
    lines.append("-" * len(header))
    for r in rows:
        pr = f"{r['pearson_r']:+.4f}" if r["pearson_r"] is not None else f"MISSING({r['missingness_reason']})"
        rm = f"{r['rmse_standardized']:.4f}" if r["rmse_standardized"] is not None else "n/a"
        lines.append(f"{r['effect_size']:>11.2f} {r['extra_noise_std']:>15.2f} {pr:>10s} {rm:>9s} {r['n_used']:>7d} {r['n_total']:>7d}")
    return "\n".join(lines)
