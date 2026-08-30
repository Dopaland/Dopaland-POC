"""
D6 precision simulation, Part A -- synthetic trial-sequence generator.

Produces a single subject's synthetic session -> episode -> trial hierarchy,
so that resampling downstream (simulation/precision.py) can operate at the
episode level, per CLAUDE.md's D0PA1 hard constraint #4 ("resample at
episode/session/day level, never bootstrap frames or individual trials as
if independent").

This module NEVER touches real action data, never imports from features/,
and never modifies anything on the validated path (G5). It is a standalone,
fully synthetic generator built so the same code can later be reused for
synthetic latent recovery (D6's second deliverable).

GENERATIVE MODEL, ONE PARAGRAPH: a single continuous latent state z_t
follows an AR(1) process, restarted fresh each session (A1). The action
class at each trial is drawn from a softmax whose logits combine a slowly
drifting base rate (A4) with a contribution from z_t whose strength grows
across the study as the subject "learns" the task (A2) and whose underlying
noise inflates within a session as the subject "fatigues" (A3). The
candidate representation under test -- the synthetic stand-in for a
signal like V_es or V_pd -- is an observation of z_t corrupted by noise at
a configurable strength (A6): effect_size=0 means the candidate signal
carries NO information about the action class (a true null); effect_size
near 1 means it is nearly a direct read of the state that drives the class.
Missingness is a bursty two-state Markov chain (A5), not IID coin flips, so
that a tracking-loss run lasting several consecutive trials is represented
correctly rather than being smoothed away by independent per-trial dropout.

Every numeric default below is an INVENTED assumption (no real data exists
yet to inform it) and is listed, with justification, in
docs/D6_SIMULATION.md. Nothing here is tuned to make any result look better
(G2) -- these are the assumptions BEFORE any output was inspected.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class GeneratorConfig:
    """One synthetic subject's full generative parameterization. Every
    field has a default so a sweep can vary one field at a time -- but the
    seed has no meaningful default and should always be passed explicitly."""

    seed: int

    # --- hierarchy ---
    n_sessions: int = 3
    episodes_per_session: int = 270
    trials_per_episode: int = 5
    n_classes: int = 3

    # --- A1: serial dependence -- AR(1) on a latent propensity ---
    # z_t = ar1_phi * z_{t-1} + eps_t,  eps_t ~ N(0, sigma_t^2)
    # phi in (-1, 1) for stationarity. Restarted at z=0 at the start of
    # EVERY session (no cross-session persistence of the raw latent path --
    # see docs/D6_SIMULATION.md on why this is a documented simplification,
    # not a claim about the real subject).
    ar1_phi: float = 0.6
    ar1_innovation_sigma: float = 1.0

    # --- A2: learning -- z's influence on the class (gamma) grows with
    # CUMULATIVE trials across the whole study (persists across sessions,
    # unlike fatigue), saturating via 1 - exp(-n/half_life). ---
    gamma_base: float = 1.0
    learning_gain: float = 0.5
    learning_half_life_trials: float = 200.0

    # --- A3: fatigue -- the AR(1) innovation std inflates linearly across
    # a session (t_in_session in [0, 1]) and resets at the start of the
    # next session. Opposite mechanism from learning: fatigue makes the
    # latent path NOISIER (less predictable), learning makes its effect on
    # the class MORE predictable -- two distinct, oppositely-signed levers,
    # not mirror images of the same knob. ---
    fatigue_gain: float = 0.5

    # --- A4: class-frequency drift within a session -- a fixed per-class
    # random direction (zero-mean, generated once per generate() call) is
    # added to the base logits, scaled linearly by t_in_session. ---
    class_drift_rate: float = 0.3

    # --- A5: missingness -- bursty, two-state (present/missing) Markov
    # chain, NOT independent per-trial dropout. Parameterized by the target
    # stationary missing RATE and the target mean RUN LENGTH (in trials)
    # while missing; the two transition probabilities are solved exactly
    # from those two numbers (see _markov_missingness_params). Restarted
    # (drawn from the stationary distribution) at the start of each
    # session. ---
    missingness_rate: float = 0.05
    missingness_mean_run_length: float = 5.0

    # --- A6: true effect size -- the candidate signal x_signal is a noisy
    # observation of z_t: x_signal = effect_size * z_t + sqrt(1 -
    # effect_size^2) * noise, noise ~ N(0,1) independent of z. This is a
    # correlation-coefficient parameterization: effect_size IS (in
    # expectation, for standardized z) the correlation between the
    # observed candidate signal and the true class-driving latent state.
    # effect_size = 0 is the true null: x_signal is pure noise, carrying
    # zero information about the class. Must be in [0, 1). ---
    effect_size: float = 0.0

    def __post_init__(self):
        if not (-1.0 < self.ar1_phi < 1.0):
            raise ValueError(f"ar1_phi must be in (-1, 1) for stationarity, got {self.ar1_phi}")
        if not (0.0 <= self.effect_size < 1.0):
            raise ValueError(f"effect_size must be in [0, 1), got {self.effect_size}")
        if not (0.0 <= self.missingness_rate < 1.0):
            raise ValueError(f"missingness_rate must be in [0, 1), got {self.missingness_rate}")
        if self.missingness_mean_run_length < 1.0:
            raise ValueError("missingness_mean_run_length must be >= 1 trial")
        if self.n_classes < 2:
            raise ValueError("n_classes must be >= 2")


def _softmax(logits):
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / exp.sum()


def _zero_mean_unit_vector(rng, n):
    v = rng.normal(size=n)
    return v - v.mean()


def _markov_missingness_params(missingness_rate, mean_run_length):
    """Exact 2-state Markov chain parameters for a target stationary
    missing rate and a target mean run length (in trials) while missing.

    For a 2-state chain with P(missing -> present) = p_recover, the
    expected run length while missing is a geometric distribution's mean,
    1 / p_recover (each trial while missing "survives" to the next missing
    trial with probability (1 - p_recover)). Solving for p_recover from the
    target mean run length, then using the stationary-distribution identity
    pi_missing = p_enter / (p_enter + p_recover) to solve for
    P(present -> missing) = p_enter given the target pi_missing.

    Returns (p_enter_missing, p_recover).
    """
    if missingness_rate <= 0.0:
        return 0.0, 1.0
    p_recover = 1.0 / mean_run_length
    pi_m = missingness_rate
    p_enter_missing = p_recover * pi_m / (1.0 - pi_m)
    p_enter_missing = min(1.0, p_enter_missing)
    return p_enter_missing, p_recover


def generate(config: GeneratorConfig):
    """Returns a list of trial-record dicts, one per trial, in chronological
    order. Fields:

      session_idx, episode_idx (within session), episode_id (global,
      chronological), trial_idx_in_episode, global_trial_idx,
      t_in_session (0..1), z (the TRUE latent state -- generator-internal,
      would NOT exist in a real pipeline; kept here only so
      tests/test_generator.py can validate the generator itself against its
      own documented model), class_label (int, 0..n_classes-1),
      prev_class_label (int -- the previous trial's class; a legitimate
      baseline predictor, unrelated to the candidate signal under test),
      x_signal (float or None if missing this trial), missing (bool).

    Deterministic given config.seed -- same config, same seed, same output
    (verified by tests/test_generator.py running generate() twice).
    """
    rng = np.random.default_rng(config.seed)
    n_classes = config.n_classes

    base_logits = rng.normal(scale=0.5, size=n_classes)
    drift_direction = _zero_mean_unit_vector(rng, n_classes)
    z_loading = _zero_mean_unit_vector(rng, n_classes)  # how z_t maps onto each class's logit

    # A6 calibration: z's stationary std is sigma/sqrt(1-phi^2), NOT 1 -- an
    # AR(1) is not unit-variance in general. x_signal's mixture below needs
    # z RESCALED to unit variance for effect_size to actually equal the
    # population correlation between x_signal and z (the docstring's
    # promised interpretation). This uses the BASE (non-fatigued)
    # innovation sigma; A3 fatigue inflates the true variance somewhat
    # above this by late session, so effect_size is exact at session start
    # and a slight underestimate of the true achieved correlation by
    # session end -- documented as an approximation in docs/D6_SIMULATION.md,
    # not silently absorbed.
    z_stationary_std = config.ar1_innovation_sigma / np.sqrt(1.0 - config.ar1_phi ** 2)

    p_enter_missing, p_recover = _markov_missingness_params(
        config.missingness_rate, config.missingness_mean_run_length
    )

    records = []
    global_episode_id = 0
    global_trial_idx = 0
    prev_class = int(rng.integers(0, n_classes))

    for session_idx in range(config.n_sessions):
        z = 0.0  # A1: AR(1) restarts fresh each session -- see class docstring
        trials_in_session = config.episodes_per_session * config.trials_per_episode
        # A5: start each session's missingness state drawn from the
        # stationary distribution (a session doesn't necessarily start
        # mid-tracking-loss, but also isn't guaranteed to start clean).
        is_missing = bool(rng.random() < config.missingness_rate)
        trial_in_session = 0

        for episode_idx in range(config.episodes_per_session):
            for trial_idx_in_episode in range(config.trials_per_episode):
                t_frac = trial_in_session / max(1, trials_in_session - 1)

                # A3 fatigue: inflate this trial's innovation std within-session.
                sigma_t = config.ar1_innovation_sigma * (1.0 + config.fatigue_gain * t_frac)
                eps = rng.normal(scale=sigma_t)
                z = config.ar1_phi * z + eps

                # A2 learning: gamma grows (saturating) with CUMULATIVE
                # trials across the whole study, not reset per session.
                learning_factor = 1.0 + config.learning_gain * (
                    1.0 - np.exp(-global_trial_idx / config.learning_half_life_trials)
                )
                gamma_t = config.gamma_base * learning_factor

                # A4 class-frequency drift within this session.
                logits = base_logits + config.class_drift_rate * t_frac * drift_direction
                logits = logits + gamma_t * z * z_loading
                probs = _softmax(logits)
                class_label = int(rng.choice(n_classes, p=probs))

                # A5 missingness: bursty 2-state Markov transition.
                if is_missing:
                    is_missing = bool(rng.random() >= p_recover)
                else:
                    is_missing = bool(rng.random() < p_enter_missing)

                # A6 true effect size: x_signal is a noisy observation of
                # z, RESCALED to unit variance first (z_stationary_std) so
                # effect_size means what its docstring promises: the
                # correlation between x_signal and the true class-driving
                # state, not between x_signal and an arbitrarily-scaled z.
                if config.effect_size > 0.0:
                    noise = rng.normal()
                    z_unit = z / z_stationary_std
                    x_signal_true = (
                        config.effect_size * z_unit
                        + np.sqrt(max(0.0, 1.0 - config.effect_size ** 2)) * noise
                    )
                else:
                    x_signal_true = rng.normal()  # pure noise, independent of z (true null)

                records.append(
                    {
                        "session_idx": session_idx,
                        "episode_idx": episode_idx,
                        "episode_id": global_episode_id,
                        "trial_idx_in_episode": trial_idx_in_episode,
                        "global_trial_idx": global_trial_idx,
                        "t_in_session": t_frac,
                        "z": float(z),
                        "class_label": class_label,
                        "prev_class_label": prev_class,
                        "x_signal": None if is_missing else float(x_signal_true),
                        "missing": is_missing,
                    }
                )

                prev_class = class_label
                trial_in_session += 1
                global_trial_idx += 1
            global_episode_id += 1

    return records
