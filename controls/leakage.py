"""
D0PA1 control -- LEAKAGE HARNESS.

Four window variants over the SAME trial stream, compared side by side:

    VALID            features strictly BEFORE the action
    POST-ACTION      window deliberately includes POST-action information
    PRE-ACTION       window ends well before the action (deliberately starved)
    TIMESTAMP-SHIFT  action timestamps shifted back ~2s, then re-run

G1: every variant computes and reports a NUMBER (Delta + CI). NOTHING in
this file decides pass/fail, labels a variant "clean" or "leaky", or
aborts a run based on what it finds. See run_leakage_diagnostics()'s own
docstring and 1.3's instruction, restated there.

PLUGGABLE DATA SOURCE (1.1): run_leakage_diagnostics() takes a
`trial_source` -- any zero-argument callable returning a list of trial-
record dicts shaped like simulation.generator.generate()'s output
(session_idx, episode_id, global_trial_idx, t_in_session, class_label,
prev_class_label, x_signal, missing -- see that module's own docstring
for the exact field list). synthetic_trial_source() below is the ONLY
implementation that exists today, wrapping simulation.generator.generate().
A future RealLoggedTrialSource reading from schema/canonical_log_writer.py's
output would implement the SAME interface and could be substituted for
`trial_source` without any change to run_leakage_diagnostics() or the
window-construction logic below -- not built here, because real action
data does not exist yet (the client's task harness that would produce it
is under separate acceptance review, and D2 -- action classes, horizon --
is explicitly BLOCKED per CLAUDE.md).

WINDOW CONSTRUCTION, made concrete against the ONLY temporal structure
this synthetic generator actually has: trial-to-trial position WITHIN a
session (z resets every session -- generator.py A1 -- so a lag never
crosses a session boundary here). Each variant re-points trial t's
`x_signal` at a DIFFERENT trial's x_signal within the same session,
leaving class_label/prev_class_label/t_in_session/episode_id untouched --
only the observed FEATURE moves, never the outcome being predicted:

    valid:            trial t's feature <- trial (t - valid_lag_trials)'s x_signal      (looks BACK)
    post_action:       trial t's feature <- trial (t + valid_lag_trials)'s x_signal      (looks FORWARD -- the leak)
    pre_action:         trial t's feature <- trial (t - pre_action_starved_lag_trials)'s x_signal  (looks FURTHER back)
    timestamp_shift:  trial t's feature <- trial (t - valid_lag_trials - shift_trials)'s x_signal  (valid's own alignment, offset by ~2s worth of trials)

A trial whose source index falls outside [0, session_length) gets
x_signal=None (missing) -- the SAME missing-value convention
simulation/precision.py's build_features() already handles (mean-imputed
on train, missingness indicator dummy), not a new one invented here.

WHY REUSE simulation.precision.compute_delta/bootstrap_ci_on_delta
DIRECTLY, RATHER THAN A NEW FIT/EVAL LOOP: each variant is, structurally,
EXACTLY compute_delta's existing "with signal vs. without signal"
comparison -- only WHICH trial's x_signal is used as "with" changes
between variants. Calling compute_delta() on four differently-windowed
copies of the SAME record list gets the episode-level resampling
(1.2), the negative control (1.4, automatic -- compute_delta ALWAYS
builds it, no flag to disable), and the primary-metric abstraction for
free, with zero new fit/eval code. See docs/CONTROLS.md section 3 for
the 1.5 task-conditional caveat this task asked to be stated there.
"""

from dataclasses import asdict, dataclass
import hashlib
import json

import numpy as np

from simulation.precision import compute_delta, bootstrap_ci_on_delta, MACRO_F1_METRIC

WINDOW_VARIANTS = ("valid", "post_action", "pre_action", "timestamp_shift")


@dataclass(frozen=True)
class LeakageConfig:
    """Every field here is PARAMETERIZED, not a literal buried in the
    window-construction logic -- so the exact window definitions that
    produced a given diagnostic table are always inspectable and
    reproducible from config_hash() alone (same pattern as every other
    *Config class in this codebase)."""

    valid_lag_trials: int = 3
    pre_action_starved_lag_trials: int = 15
    timestamp_shift_seconds: float = 2.0
    # Matches controls/negative_control.py's own default -- same assumed
    # cadence, not re-derived, so "~2 seconds" means the same number of
    # trials everywhere this codebase converts time to trial-count.
    sampling_rate_hz: float = 25.0
    negative_control_seed: int = 0

    def __post_init__(self):
        if self.valid_lag_trials < 1:
            raise ValueError("valid_lag_trials must be >= 1")
        if self.pre_action_starved_lag_trials <= self.valid_lag_trials:
            raise ValueError("pre_action_starved_lag_trials must be > valid_lag_trials (it must be MORE starved than valid, not less)")

    def shift_trials(self):
        return round(self.timestamp_shift_seconds * self.sampling_rate_hz)

    def config_hash(self):
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


def synthetic_trial_source(generator_config):
    """The ONLY TrialDataSource implementation that exists today (1.1).
    Returns a zero-argument callable -- `run_leakage_diagnostics(source, ...)`
    calls it once to obtain the trial-record list, exactly the shape a
    future real-data source would also return."""
    from simulation.generator import generate

    return lambda: generate(generator_config)


def _lag_for_variant(variant, config: LeakageConfig):
    """Positive lag = the feature is drawn from a trial BEFORE the one
    being predicted; negative = AFTER (the post-action leak)."""
    if variant == "valid":
        return config.valid_lag_trials
    if variant == "post_action":
        return -config.valid_lag_trials
    if variant == "pre_action":
        return config.pre_action_starved_lag_trials
    if variant == "timestamp_shift":
        return config.valid_lag_trials + config.shift_trials()
    raise ValueError(f"unknown window variant {variant!r}, must be one of {WINDOW_VARIANTS}")


def _build_variant_records(records, variant, config: LeakageConfig):
    """Returns a NEW list of record dicts (shallow copies) with x_signal/
    missing re-pointed at a different trial's observation per
    _lag_for_variant -- everything else (class_label, prev_class_label,
    episode_id, session_idx, t_in_session, global_trial_idx) is UNCHANGED,
    so only the FEATURE moves, never the outcome being predicted."""
    lag = _lag_for_variant(variant, config)

    by_session = {}
    for r in records:
        by_session.setdefault(r["session_idx"], []).append(r)
    for session_records in by_session.values():
        session_records.sort(key=lambda r: r["global_trial_idx"])

    out = []
    for session_records in by_session.values():
        n = len(session_records)
        for i, r in enumerate(session_records):
            src_i = i - lag
            new_r = dict(r)
            if 0 <= src_i < n:
                src = session_records[src_i]
                new_r["x_signal"] = src["x_signal"]
                new_r["missing"] = src["missing"]
            else:
                new_r["x_signal"] = None
                new_r["missing"] = True
            out.append(new_r)
    out.sort(key=lambda r: r["global_trial_idx"])
    return out


def run_leakage_diagnostics(
    trial_source, n_classes, n_sessions, config=None,
    resample_unit="episode", n_boot=1000, alpha=0.05,
    train_frac=0.6, val_frac=0.2, metric=MACRO_F1_METRIC, bootstrap_seed=0,
):
    """Runs all four window variants over the SAME trial stream (one call
    to trial_source()) and returns one dict keyed by variant name, each
    carrying delta_point, its bootstrap CI (episode-level resampling,
    reused from simulation.precision -- 1.2), AND delta_negative_control
    (1.4, always present -- compute_delta's own unconditional wiring, not
    re-implemented here).

    G1, restated as code: this function returns NUMBERS. It contains no
    comparison of any variant's Delta against any other, no threshold, no
    "leaky"/"clean" label, and no branch that changes behavior based on a
    computed value. 1.3's instruction: report direction and magnitude:
    every returned row's delta_point already carries its own sign and
    scale, and the CI already carries the uncertainty -- printing/reading
    those IS the report; nothing here decides what they mean.

    The SAME bootstrap seed (bootstrap_seed) is used, fresh, for every
    variant -- the four variants therefore resample the IDENTICAL sequence
    of episode sets, so any difference in CI width or Delta between
    variants is attributable to the window construction itself, not to
    which episodes happened to get resampled. The SAME negative_control_seed
    (from config) is used across variants for the same reason."""
    if config is None:
        config = LeakageConfig()

    base_records = trial_source()

    results = {}
    for variant in WINDOW_VARIANTS:
        variant_records = _build_variant_records(base_records, variant, config)
        delta_result = compute_delta(
            variant_records, n_classes, n_sessions, train_frac, val_frac, metric,
            negative_control_seed=config.negative_control_seed,
        )
        rng = np.random.default_rng(bootstrap_seed)
        ci = bootstrap_ci_on_delta(delta_result, resample_unit, n_boot, alpha, rng, metric, n_classes)

        results[variant] = {
            "variant": variant,
            "lag_trials": _lag_for_variant(variant, config),
            "delta_point": delta_result.delta_point,
            "u_with": delta_result.u_with,
            "u_without": delta_result.u_without,
            "ci_lo": ci["ci_lo"],
            "ci_hi": ci["ci_hi"],
            "ci_half_width": ci["ci_half_width"],
            "resample_unit": resample_unit,
            "n_resample_units_test": ci["n_resample_units"],
            "delta_negative_control": delta_result.delta_negative_control,
            "u_with_negative_control": delta_result.u_with_negative_control,
            "negative_control_seed": delta_result.negative_control_seed,
            "n_test_trials": delta_result.n_test_trials,
            "n_test_episodes": delta_result.n_test_episodes,
        }

    return {
        "variants": results,
        "config_hash": config.config_hash(),
        "metric": metric.name,
        "n_boot": n_boot,
        "alpha": alpha,
    }


def format_leakage_table(result):
    """1.2 -- one table, all four variants side by side, with the CI on
    each Delta. Plain text, no verdict column, no highlighting of any row
    as better/worse -- a human reads the numbers."""
    lines = []
    header = f"{'variant':16s} {'lag(trials)':>11s} {'delta_point':>12s} {'ci_lo':>10s} {'ci_hi':>10s} {'delta_negctrl':>14s} {'n_test_trials':>13s}"
    lines.append(header)
    lines.append("-" * len(header))
    for variant in WINDOW_VARIANTS:
        r = result["variants"][variant]
        lines.append(
            f"{variant:16s} {r['lag_trials']:>11d} {r['delta_point']:>+12.4f} "
            f"{r['ci_lo']:>+10.4f} {r['ci_hi']:>+10.4f} {r['delta_negative_control']:>+14.4f} "
            f"{r['n_test_trials']:>13d}"
        )
    lines.append("")
    lines.append(f"config_hash={result['config_hash']}  metric={result['metric']}  n_boot={result['n_boot']}  alpha={result['alpha']}")
    return "\n".join(lines)
