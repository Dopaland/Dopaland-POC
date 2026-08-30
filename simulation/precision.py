"""
D6 precision simulation, Part B -- fit, evaluate, bootstrap, sweep.

G1 discipline: every function here COMPUTES AND STORES A NUMBER. None of
them compare that number to a threshold, decide RETAIN/DROP/INCONCLUSIVE,
or recommend a delta value. The primary metric (macro_f1 by default) and
any delta value are left as PARAMETERS/plain outputs for a human to read
and compare -- see B5.

Standalone; does not import from features/ and does not touch the
validated pipeline (G5).

NEGATIVE CONTROL, WIRED IN AUTOMATICALLY (D0PA1 Part 2.2): compute_delta()
below ALWAYS builds a third comparison -- baseline + a deliberately
meaningless negative-control signal (controls/negative_control.py) vs
baseline alone -- alongside the real candidate signal's with/without
comparison. There is NO flag to disable this; every DeltaResult and every
run_one/run_one_refit/sweep* row carries delta_negative_control next to
delta_point, so a negative control can never be skipped by forgetting an
optional argument in a test where it would be inconvenient. It decides
nothing (G1): a large delta_negative_control is reported for a human to
investigate, never auto-flagged as a kill condition -- see
controls/negative_control.py and docs/CONTROLS.md.
"""

from dataclasses import dataclass

import numpy as np

from simulation.models import fit_multinomial_logreg, predict, macro_f1
from controls.negative_control import NegativeControlConfig, generate_negative_control


# ============================================================
# B1 -- chronological split (episode-respecting: no episode's trials are
# ever split across train/val/test, since an episode is the exchangeability
# unit -- splitting it would leak within-episode autocorrelation across
# the boundary).
# ============================================================

def chronological_split(records, train_frac=0.6, val_frac=0.2):
    if not (0.0 < train_frac < 1.0) or not (0.0 < val_frac < 1.0) or train_frac + val_frac >= 1.0:
        raise ValueError("train_frac and val_frac must be in (0,1) and sum to less than 1")

    episode_ids_in_order = sorted({r["episode_id"] for r in records})
    n_ep = len(episode_ids_in_order)
    n_train = max(1, int(round(n_ep * train_frac)))
    n_val = max(1, int(round(n_ep * val_frac)))
    n_train = min(n_train, n_ep - 2)  # leave at least 1 episode each for val/test
    n_val = min(n_val, n_ep - n_train - 1)

    train_ids = set(episode_ids_in_order[:n_train])
    val_ids = set(episode_ids_in_order[n_train : n_train + n_val])
    test_ids = set(episode_ids_in_order[n_train + n_val :])

    train = [r for r in records if r["episode_id"] in train_ids]
    val = [r for r in records if r["episode_id"] in val_ids]
    test = [r for r in records if r["episode_id"] in test_ids]
    return train, val, test


# ============================================================
# B1/B2 -- feature construction. "without" = baseline/nuisance features
# only (never the candidate signal under test). "with" = baseline PLUS the
# candidate signal (mean-imputed on missing, using a TRAIN-only mean, plus
# a missingness indicator dummy -- standard practice, and the imputation
# statistic itself must never see val/test data, matching the "no future
# information reaching training" rule).
# ============================================================

def _one_hot(values, n_categories):
    values = np.asarray(values, dtype=int)
    out = np.zeros((len(values), n_categories))
    out[np.arange(len(values)), values] = 1.0
    return out


def build_features(records, n_classes, n_sessions, include_signal, signal_impute_mean=None, negative_control_values=None):
    """Returns (X, signal_impute_mean_used). If include_signal and
    signal_impute_mean is None, the mean is computed from THESE records
    (call this on the TRAIN split first to get the mean, then pass that
    same value in for val/test -- never recompute it on val/test).

    negative_control_values: optional (len(records),) array -- when given,
    appended as one extra column (D0PA1 Part 2.2's negative control is
    never missing, so no imputation/indicator dummy is needed for it,
    unlike the real candidate signal above)."""
    t = np.array([r["t_in_session"] for r in records]).reshape(-1, 1)
    prev_class_oh = _one_hot([r["prev_class_label"] for r in records], n_classes)
    cols = [t, prev_class_oh]

    if n_sessions > 1:
        session_oh = _one_hot([r["session_idx"] for r in records], n_sessions)
        cols.append(session_oh)

    if include_signal:
        raw = np.array([r["x_signal"] if r["x_signal"] is not None else np.nan for r in records])
        missing = np.isnan(raw).astype(float).reshape(-1, 1)
        if signal_impute_mean is None:
            observed = raw[~np.isnan(raw)]
            signal_impute_mean = float(observed.mean()) if len(observed) else 0.0
        filled = np.where(np.isnan(raw), signal_impute_mean, raw).reshape(-1, 1)
        cols.append(filled)
        cols.append(missing)

    if negative_control_values is not None:
        cols.append(np.asarray(negative_control_values).reshape(-1, 1))

    X = np.concatenate(cols, axis=1)
    return X, signal_impute_mean


# ============================================================
# B1/B2 -- fit both models, evaluate on test. A small L2 grid is chosen
# per model on the VALIDATION split (never on test) -- documented model
# selection, not hyperparameter tuning against a real result (G2 concerns
# tuning against EXISTING DATA to make reported results look better; this
# is ordinary model selection on synthetic data generated fresh for this
# simulation, done identically regardless of what the eventual Δ turns
# out to be).
# ============================================================

L2_GRID = (0.1, 1.0, 10.0)


def _select_l2_and_fit(X_train, y_train, X_val, y_val, n_classes):
    best = None
    for l2 in L2_GRID:
        params = fit_multinomial_logreg(X_train, y_train, n_classes, l2=l2)
        val_f1 = macro_f1(y_val, predict(params, X_val), n_classes)
        if best is None or val_f1 > best[0]:
            best = (val_f1, l2, params)
    return best[2], best[1]


@dataclass
class DeltaResult:
    delta_point: float
    u_with: float
    u_without: float
    l2_with: float
    l2_without: float
    n_train_episodes: int
    n_val_episodes: int
    n_test_episodes: int
    n_test_trials: int
    y_test: np.ndarray
    pred_with: np.ndarray
    pred_without: np.ndarray
    test_episode_ids: np.ndarray
    test_session_ids: np.ndarray
    # D0PA1 Part 2.2 -- ALWAYS populated, never optional (see module
    # docstring): baseline+negative-control vs baseline alone, computed
    # identically to the real with/without comparison above but on a
    # signal that is DEFINITIONALLY meaningless (controls/negative_control.py).
    delta_negative_control: float = None
    u_with_negative_control: float = None
    negative_control_seed: int = None
    # Kept for bootstrap_ci_on_delta_refit (Pass 2, 1.1), which needs the
    # raw train/test records (to resample and REFIT, not just re-evaluate)
    # and the exact imputation mean fixed on the real, non-resampled train
    # split -- never left None for compute_delta's own callers, since it
    # costs nothing extra (no new computation, just retaining what was
    # already built).
    train: list = None
    test: list = None
    signal_impute_mean: float = None


def compute_delta(records, n_classes, n_sessions, train_frac=0.6, val_frac=0.2, metric_fn=macro_f1, negative_control_seed=0):
    """B1 + B2. metric_fn(y_true, y_pred, n_classes) -> float is a
    parameter (B5: the primary metric is never hardcoded) -- defaults to
    macro_f1 but any higher-is-better classification metric with this
    signature can be substituted.

    negative_control_seed has a DEFAULT (0) rather than being required --
    the point of D0PA1 Part 2.2 is that the negative control is computed
    on EVERY call regardless of whether the caller thinks to pass anything;
    a required argument could still be "forgotten" as an omission error,
    a default value cannot be forgotten because there is nothing to
    remember to pass. run_one/run_one_refit override it with a seed
    derived from the generator's own config.seed, so a multi-seed sweep
    gets a genuinely different negative-control realization per seed
    rather than reusing one fixed draw everywhere.
    """
    train, val, test = chronological_split(records, train_frac, val_frac)

    y_train = np.array([r["class_label"] for r in train])
    y_val = np.array([r["class_label"] for r in val])
    y_test = np.array([r["class_label"] for r in test])

    X_train_w, impute_mean = build_features(train, n_classes, n_sessions, include_signal=True)
    X_val_w, _ = build_features(val, n_classes, n_sessions, include_signal=True, signal_impute_mean=impute_mean)
    X_test_w, _ = build_features(test, n_classes, n_sessions, include_signal=True, signal_impute_mean=impute_mean)

    X_train_wo, _ = build_features(train, n_classes, n_sessions, include_signal=False)
    X_val_wo, _ = build_features(val, n_classes, n_sessions, include_signal=False)
    X_test_wo, _ = build_features(test, n_classes, n_sessions, include_signal=False)

    params_with, l2_with = _select_l2_and_fit(X_train_w, y_train, X_val_w, y_val, n_classes)
    params_without, l2_without = _select_l2_and_fit(X_train_wo, y_train, X_val_wo, y_val, n_classes)

    pred_with = predict(params_with, X_test_w)
    pred_without = predict(params_without, X_test_wo)

    u_with = metric_fn(y_test, pred_with, n_classes)
    u_without = metric_fn(y_test, pred_without, n_classes)

    # D0PA1 Part 2.2 -- negative control, ALWAYS computed (see docstring).
    # Its own AR(1) autocorrelation is matched to simulation/generator.py's
    # own A1 default (ar1_phi=0.6) so it is a fair, hard-to-distinguish
    # nuisance signal, not an easy-to-spot white-noise strawman.
    nc_config = NegativeControlConfig(seed=negative_control_seed, n_samples=len(records))
    nc_values = generate_negative_control(nc_config)
    nc_train = nc_values[[r["global_trial_idx"] for r in train]]
    nc_test = nc_values[[r["global_trial_idx"] for r in test]]
    nc_val = nc_values[[r["global_trial_idx"] for r in val]]

    X_train_nc, _ = build_features(train, n_classes, n_sessions, include_signal=False, negative_control_values=nc_train)
    X_val_nc, _ = build_features(val, n_classes, n_sessions, include_signal=False, negative_control_values=nc_val)
    X_test_nc, _ = build_features(test, n_classes, n_sessions, include_signal=False, negative_control_values=nc_test)
    params_nc, l2_nc = _select_l2_and_fit(X_train_nc, y_train, X_val_nc, y_val, n_classes)
    pred_nc = predict(params_nc, X_test_nc)
    u_with_negative_control = metric_fn(y_test, pred_nc, n_classes)

    return DeltaResult(
        delta_point=u_with - u_without,
        u_with=u_with,
        u_without=u_without,
        l2_with=l2_with,
        l2_without=l2_without,
        delta_negative_control=u_with_negative_control - u_without,
        u_with_negative_control=u_with_negative_control,
        negative_control_seed=negative_control_seed,
        n_train_episodes=len({r["episode_id"] for r in train}),
        n_val_episodes=len({r["episode_id"] for r in val}),
        n_test_episodes=len({r["episode_id"] for r in test}),
        n_test_trials=len(test),
        y_test=y_test,
        pred_with=pred_with,
        pred_without=pred_without,
        test_episode_ids=np.array([r["episode_id"] for r in test]),
        test_session_ids=np.array([r["session_idx"] for r in test]),
        train=train,
        test=test,
        signal_impute_mean=impute_mean,
    )


# ============================================================
# B3 -- bootstrap CI on Delta, resampled at an EXPLICIT, REQUIRED unit
# (episode or session -- never trial/frame, per CLAUDE.md's D0PA1 hard
# constraint #4). Resamples the TEST set's units (with the already-fitted
# models' predictions) rather than refitting per replicate -- this is a
# documented computational simplification (bootstrapping the EVALUATION,
# not the full train-then-evaluate procedure) stated in docs/D6_SIMULATION.md.
# ============================================================

VALID_RESAMPLE_UNITS = ("episode", "session")


def bootstrap_ci_on_delta(delta_result: DeltaResult, resample_unit, n_boot, alpha, rng, metric_fn=macro_f1, n_classes=None):
    """resample_unit has NO DEFAULT and must be 'episode' or 'session' --
    resampling at the trial level would understate variance under A1's
    serial dependence and is refused outright."""
    if resample_unit not in VALID_RESAMPLE_UNITS:
        raise ValueError(
            f"resample_unit must be one of {VALID_RESAMPLE_UNITS} (never 'trial' -- "
            "these data are autocorrelated; trial-level resampling badly understates variance). "
            f"Got: {resample_unit!r}"
        )
    if n_classes is None:
        n_classes = int(max(delta_result.y_test.max(), delta_result.pred_with.max(), delta_result.pred_without.max()) + 1)

    unit_ids = delta_result.test_episode_ids if resample_unit == "episode" else delta_result.test_session_ids
    unique_units = np.unique(unit_ids)
    if len(unique_units) < 2:
        raise ValueError(
            f"only {len(unique_units)} unique {resample_unit}(s) in the test split -- "
            "cannot bootstrap a CI from fewer than 2 resampling units."
        )

    # Precompute, for each unit, the row indices belonging to it -- avoids
    # rescanning the full array on every bootstrap replicate.
    unit_to_rows = {u: np.where(unit_ids == u)[0] for u in unique_units}

    deltas = np.empty(n_boot)
    for b in range(n_boot):
        sampled_units = rng.choice(unique_units, size=len(unique_units), replace=True)
        rows = np.concatenate([unit_to_rows[u] for u in sampled_units])
        y_b = delta_result.y_test[rows]
        u_with = metric_fn(y_b, delta_result.pred_with[rows], n_classes)
        u_without = metric_fn(y_b, delta_result.pred_without[rows], n_classes)
        deltas[b] = u_with - u_without

    lo = float(np.percentile(deltas, 100 * (alpha / 2)))
    hi = float(np.percentile(deltas, 100 * (1 - alpha / 2)))
    return {
        "delta_point": delta_result.delta_point,
        "ci_lo": lo,
        "ci_hi": hi,
        "ci_half_width": (hi - lo) / 2.0,
        "resample_unit": resample_unit,
        "n_resample_units": len(unique_units),
        "n_boot": n_boot,
        "alpha": alpha,
        "bootstrap_deltas": deltas,
    }


# ============================================================
# PASS 2, 1.1 -- REFIT PER BOOTSTRAP REPLICATE. Pass 1's bootstrap_ci_on_delta
# above resamples the TEST set's evaluation against a single, fixed fitted
# model -- disclosed in docs/D6_SIMULATION.md as understating true CI width,
# because it captures only "how much would Delta move under a different
# draw of test episodes", not "how much would Delta move under a different
# draw of TRAINING episodes, which would have fit a different model."
#
# This function fixes that with a DOUBLE bootstrap: for every replicate, it
# (a) resamples TRAINING episodes (or sessions) WITH REPLACEMENT and REFITS
# both models from scratch on that resampled training set, AND (b)
# independently resamples TEST episodes WITH REPLACEMENT and evaluates the
# freshly refit models on that resampled test set. Both sources of
# variability are captured together in the same replicate.
#
# THIS MATTERS AND WAS VERIFIED, NOT ASSUMED: an earlier version of this
# function resampled train (and refit) while holding the test set FIXED --
# that captures ONLY train-refit variability and OMITS test-resampling
# variability entirely; it is not "Pass 1's method plus more", it is a
# DIFFERENT, narrower quantity that happened to produce a SMALLER CI than
# Pass 1's fixed-model bootstrap on the same data (0.0088 vs 0.0113),
# which is the wrong direction given Pass 1's own disclosed concern.
# Resampling both train and test together is what actually captures MORE
# of the true uncertainty than Pass 1's method, not less -- see
# docs/D6_SIMULATION.md's Pass 2 section for the full account of this,
# including the numbers from the version that had to be corrected.
#
# COST-SAVING SIMPLIFICATIONS (disclosed, not hidden -- see
# docs/D6_SIMULATION.md Pass 2 section):
#   - L2 for both models is FIXED at the value chosen once on the real
#     (non-resampled) train/val split, not re-selected via the L2_GRID
#     search on every replicate. Re-selecting would multiply cost ~3x for
#     a source of variability (regularization-strength uncertainty) this
#     correction is not targeting.
#   - The signal imputation mean is likewise fixed at the real train
#     split's value, not recomputed per replicate.
#   - n_boot is far smaller than bootstrap_ci_on_delta's default (Pass 1
#     used 800; Pass 2's refit variant uses far fewer -- see the calling
#     code for the exact number and the profiled reason) because a full
#     refit is ~1-2 orders of magnitude more expensive per replicate than
#     re-evaluating a fixed model. This is REPORTED, not absorbed: fewer
#     replicates means a noisier CI estimate, and that tradeoff is stated
#     plainly everywhere this function's output is used.
# ============================================================

def bootstrap_ci_on_delta_refit(
    delta_result: DeltaResult, n_classes, n_sessions, resample_unit, n_boot, alpha, rng, metric_fn=macro_f1
):
    """Same resample_unit contract as bootstrap_ci_on_delta (required, no
    default, 'episode' or 'session' only -- never 'trial'). Requires
    delta_result.train/test/signal_impute_mean to be populated (they are,
    by compute_delta). Double bootstrap: resamples TRAIN (refit) and TEST
    (re-evaluate) independently in every replicate -- see module comment
    above for why resampling train alone is a different, narrower quantity
    that must not be mistaken for a strict improvement on Pass 1's method."""
    if resample_unit not in VALID_RESAMPLE_UNITS:
        raise ValueError(
            f"resample_unit must be one of {VALID_RESAMPLE_UNITS} (never 'trial' -- "
            "these data are autocorrelated; trial-level resampling badly understates variance). "
            f"Got: {resample_unit!r}"
        )
    if delta_result.train is None or delta_result.test is None:
        raise ValueError("delta_result.train/test are required for refit bootstrapping -- got None")

    unit_key = "episode_id" if resample_unit == "episode" else "session_idx"

    train_units = sorted({r[unit_key] for r in delta_result.train})
    if len(train_units) < 2:
        raise ValueError(
            f"only {len(train_units)} unique {resample_unit}(s) in the train split -- "
            "cannot bootstrap a CI from fewer than 2 resampling units."
        )
    train_unit_to_records = {}
    for r in delta_result.train:
        train_unit_to_records.setdefault(r[unit_key], []).append(r)

    test_units = sorted({r[unit_key] for r in delta_result.test})
    if len(test_units) < 2:
        raise ValueError(
            f"only {len(test_units)} unique {resample_unit}(s) in the test split -- "
            "cannot bootstrap a CI from fewer than 2 resampling units."
        )
    test_unit_to_indices = {}
    for i, r in enumerate(delta_result.test):
        test_unit_to_indices.setdefault(r[unit_key], []).append(i)

    y_test_full = np.array([r["class_label"] for r in delta_result.test])
    X_test_w_full, _ = build_features(
        delta_result.test, n_classes, n_sessions, include_signal=True,
        signal_impute_mean=delta_result.signal_impute_mean,
    )
    X_test_wo_full, _ = build_features(delta_result.test, n_classes, n_sessions, include_signal=False)

    deltas = np.empty(n_boot)
    for b in range(n_boot):
        # (a) resample TRAIN, refit.
        sampled_train_units = rng.choice(train_units, size=len(train_units), replace=True)
        boot_train = []
        for u in sampled_train_units:
            boot_train.extend(train_unit_to_records[u])
        y_boot = np.array([r["class_label"] for r in boot_train])

        X_boot_w, _ = build_features(
            boot_train, n_classes, n_sessions, include_signal=True,
            signal_impute_mean=delta_result.signal_impute_mean,
        )
        X_boot_wo, _ = build_features(boot_train, n_classes, n_sessions, include_signal=False)

        params_with = fit_multinomial_logreg(X_boot_w, y_boot, n_classes, l2=delta_result.l2_with)
        params_without = fit_multinomial_logreg(X_boot_wo, y_boot, n_classes, l2=delta_result.l2_without)

        # (b) resample TEST (independently of (a)), evaluate the freshly
        # refit models on the resampled test rows.
        sampled_test_units = rng.choice(test_units, size=len(test_units), replace=True)
        test_rows = np.concatenate([test_unit_to_indices[u] for u in sampled_test_units])

        pred_with = predict(params_with, X_test_w_full[test_rows])
        pred_without = predict(params_without, X_test_wo_full[test_rows])
        y_test = y_test_full[test_rows]
        u_with = metric_fn(y_test, pred_with, n_classes)
        u_without = metric_fn(y_test, pred_without, n_classes)
        deltas[b] = u_with - u_without

    lo = float(np.percentile(deltas, 100 * (alpha / 2)))
    hi = float(np.percentile(deltas, 100 * (1 - alpha / 2)))
    return {
        "delta_point": delta_result.delta_point,
        "ci_lo": lo,
        "ci_hi": hi,
        "ci_half_width": (hi - lo) / 2.0,
        "resample_unit": resample_unit,
        "n_resample_units_train": len(train_units),
        "n_resample_units_test": len(test_units),
        "n_boot": n_boot,
        "alpha": alpha,
        "bootstrap_deltas": deltas,
        "method": "refit_per_replicate_double_bootstrap",
    }


# ============================================================
# B4 -- sweep. Generic: caller supplies a list of (label, GeneratorConfig)
# pairs; this function generates, fits, and bootstraps each one and
# returns a list of result dicts. No verdict, no PASS/FAIL, no threshold
# comparison anywhere in this function (G1) -- see simulation/run_precision_sweep.py
# for the concrete grid used in the report, and
# artefacts/precision_analysis_v1.md for the human-read comparison against
# candidate delta values.
# ============================================================

def run_one(config, resample_unit, n_boot=1000, alpha=0.05, train_frac=0.6, val_frac=0.2, metric_fn=macro_f1):
    from simulation.generator import generate

    records = generate(config)
    # D0PA1 Part 2.2: negative control seed derived from config.seed so a
    # multi-seed sweep gets a genuinely different negative-control draw per
    # seed (see compute_delta's docstring) -- never omitted, never the same
    # fixed draw reused everywhere.
    delta_result = compute_delta(
        records, config.n_classes, config.n_sessions, train_frac, val_frac, metric_fn,
        negative_control_seed=config.seed + 5_000_003,
    )
    boot_rng = np.random.default_rng(config.seed + 1_000_003)  # derived, distinct from the generator's own seed
    ci = bootstrap_ci_on_delta(delta_result, resample_unit, n_boot, alpha, boot_rng, metric_fn, config.n_classes)

    # Realized correlation between the candidate signal and the true
    # latent state, for the records where the signal was observed --
    # reported because effect_size is an approximate calibration (see
    # docs/D6_SIMULATION.md) and this is the ground-truth check against it.
    observed = [(r["x_signal"], r["z"]) for r in records if r["x_signal"] is not None]
    if len(observed) >= 2:
        xs, zs = zip(*observed)
        realized_corr = float(np.corrcoef(xs, zs)[0, 1])
    else:
        realized_corr = float("nan")

    n_trials_total = len(records)
    n_missing = sum(1 for r in records if r["missing"])

    return {
        "seed": config.seed,
        "n_sessions": config.n_sessions,
        "episodes_per_session": config.episodes_per_session,
        "trials_per_episode": config.trials_per_episode,
        "n_trials_total": n_trials_total,
        "effect_size_nominal": config.effect_size,
        "effect_size_realized_corr": realized_corr,
        "missingness_rate_nominal": config.missingness_rate,
        "missingness_rate_realized": n_missing / n_trials_total if n_trials_total else float("nan"),
        "u_with": delta_result.u_with,
        "u_without": delta_result.u_without,
        "delta_point": delta_result.delta_point,
        "delta_negative_control": delta_result.delta_negative_control,
        "u_with_negative_control": delta_result.u_with_negative_control,
        "negative_control_seed": delta_result.negative_control_seed,
        "ci_lo": ci["ci_lo"],
        "ci_hi": ci["ci_hi"],
        "ci_half_width": ci["ci_half_width"],
        "resample_unit": resample_unit,
        "n_resample_units_test": ci["n_resample_units"],
        "n_test_episodes": delta_result.n_test_episodes,
        "n_test_trials": delta_result.n_test_trials,
    }


def sweep(named_configs, resample_unit, n_boot=1000, alpha=0.05, **kwargs):
    """named_configs: list of (label: str, GeneratorConfig). Returns a list
    of result dicts (see run_one), each carrying its label under 'label'."""
    results = []
    for label, config in named_configs:
        row = run_one(config, resample_unit, n_boot=n_boot, alpha=alpha, **kwargs)
        row["label"] = label
        results.append(row)
    return results


# ============================================================
# MULTI-SEED AGGREGATION -- a single realization's bootstrap CI is itself
# a noisy estimate of "typical achievable precision" at a given N. This is
# NOT an edge case to special-case away: with hard-argmax classification
# and macro-F1 (the task-specified metric), a candidate signal that is
# genuinely weak or null can produce IDENTICAL predictions between the
# "with" and "without" models on a given draw of data (verified directly:
# at effect_size=0.0, both models collapsed to predicting the majority
# class on every test trial, giving delta_point EXACTLY 0.0 with an EXACT
# zero-width bootstrap CI on that one draw -- not a bug, a real property
# of comparing hard decisions rather than continuous scores). Reporting a
# single such draw's zero-width CI as "this N resolves arbitrarily small
# deltas" would be actively misleading in the opposite direction from the
# truth. Averaging over independent seeds is the honest fix: it reports
# the TYPICAL precision achievable at a given N, not one lucky (or
# unlucky) draw's discreteness artifact.
# ============================================================

def sweep_multi_seed(label, config_kwargs, seeds, resample_unit, n_boot=1000, alpha=0.05, **kwargs):
    """config_kwargs: dict of GeneratorConfig fields EXCLUDING seed (seed is
    supplied per-replicate from `seeds`). Returns one aggregated dict:
    median/mean/min/max of delta_point and ci_half_width across seeds, the
    fraction of seeds whose CI excluded zero (a simple, non-decisional
    diagnostic -- NOT a verdict, just "how often did zero fall outside the
    interval on this draw"), plus the full per-seed rows for inspection."""
    from simulation.generator import GeneratorConfig

    per_seed_rows = []
    for seed in seeds:
        config = GeneratorConfig(seed=seed, **config_kwargs)
        row = run_one(config, resample_unit, n_boot=n_boot, alpha=alpha, **kwargs)
        per_seed_rows.append(row)

    half_widths = np.array([r["ci_half_width"] for r in per_seed_rows])
    deltas = np.array([r["delta_point"] for r in per_seed_rows])
    excludes_zero = np.array([r["ci_lo"] > 0.0 or r["ci_hi"] < 0.0 for r in per_seed_rows])
    realized_corrs = np.array([r["effect_size_realized_corr"] for r in per_seed_rows])
    nc_deltas = np.array([r["delta_negative_control"] for r in per_seed_rows])

    return {
        "label": label,
        "n_seeds": len(seeds),
        "seeds": list(seeds),
        **{k: v for k, v in config_kwargs.items()},
        "n_trials_total": per_seed_rows[0]["n_trials_total"],
        "effect_size_realized_corr_mean": float(np.mean(realized_corrs)),
        "delta_point_median": float(np.median(deltas)),
        "delta_point_mean": float(np.mean(deltas)),
        "ci_half_width_median": float(np.median(half_widths)),
        "ci_half_width_mean": float(np.mean(half_widths)),
        "ci_half_width_min": float(np.min(half_widths)),
        "ci_half_width_max": float(np.max(half_widths)),
        "frac_seeds_ci_excludes_zero": float(np.mean(excludes_zero)),
        # D0PA1 Part 2.2 -- reported, never decided upon (G1): a large
        # median/max here means the negative control looked informative on
        # this sweep point and warrants a human look, not an automatic
        # exclusion (see controls/negative_control.py's module docstring).
        "delta_negative_control_median": float(np.median(nc_deltas)),
        "delta_negative_control_max_abs": float(np.max(np.abs(nc_deltas))),
        "per_seed_rows": per_seed_rows,
    }


# ============================================================
# PASS 2 -- run_one/sweep_multi_seed equivalents using the REFIT-per-
# replicate bootstrap (bootstrap_ci_on_delta_refit) instead of Pass 1's
# fixed-model evaluation-only bootstrap. Kept as SEPARATE functions rather
# than a mode flag on the Pass 1 functions so Pass 1's code path is
# untouched or ambiguous nowhere (the artefact's "keep v1 unchanged, no
# retroactive edits" principle applies to the code paths that produced it,
# not just the markdown file).
# ============================================================

def run_one_refit(config, resample_unit, n_boot, alpha=0.05, train_frac=0.6, val_frac=0.2, metric_fn=macro_f1):
    from simulation.generator import generate

    records = generate(config)
    delta_result = compute_delta(
        records, config.n_classes, config.n_sessions, train_frac, val_frac, metric_fn,
        negative_control_seed=config.seed + 5_000_003,
    )
    boot_rng = np.random.default_rng(config.seed + 2_000_003)  # distinct offset from run_one's fixed-model bootstrap
    ci = bootstrap_ci_on_delta_refit(delta_result, config.n_classes, config.n_sessions, resample_unit, n_boot, alpha, boot_rng, metric_fn)

    observed = [(r["x_signal"], r["z"]) for r in records if r["x_signal"] is not None]
    if len(observed) >= 2:
        xs, zs = zip(*observed)
        realized_corr = float(np.corrcoef(xs, zs)[0, 1])
    else:
        realized_corr = float("nan")

    n_trials_total = len(records)
    n_missing = sum(1 for r in records if r["missing"])

    return {
        "seed": config.seed,
        "n_sessions": config.n_sessions,
        "episodes_per_session": config.episodes_per_session,
        "trials_per_episode": config.trials_per_episode,
        "n_classes": config.n_classes,
        "n_rare_classes": config.n_rare_classes,
        "rare_class_frequency": config.rare_class_frequency if config.n_rare_classes > 0 else None,
        "n_trials_total": n_trials_total,
        "effect_size_nominal": config.effect_size,
        "effect_size_realized_corr": realized_corr,
        "missingness_rate_nominal": config.missingness_rate,
        "missingness_rate_realized": n_missing / n_trials_total if n_trials_total else float("nan"),
        "u_with": delta_result.u_with,
        "u_without": delta_result.u_without,
        "delta_point": delta_result.delta_point,
        "delta_negative_control": delta_result.delta_negative_control,
        "u_with_negative_control": delta_result.u_with_negative_control,
        "negative_control_seed": delta_result.negative_control_seed,
        "ci_lo": ci["ci_lo"],
        "ci_hi": ci["ci_hi"],
        "ci_half_width": ci["ci_half_width"],
        "resample_unit": resample_unit,
        "n_resample_units_train": ci["n_resample_units_train"],
        "n_resample_units_test": ci["n_resample_units_test"],
        "n_train_episodes": delta_result.n_train_episodes,
        "n_test_episodes": delta_result.n_test_episodes,
        "n_test_trials": delta_result.n_test_trials,
        "n_boot": n_boot,
        "method": ci["method"],
    }


def sweep_multi_seed_refit(label, config_kwargs, seeds, resample_unit, n_boot, alpha=0.05, **kwargs):
    """Same contract as sweep_multi_seed, using run_one_refit instead of
    run_one. n_boot has NO DEFAULT here (unlike sweep_multi_seed's 1000) --
    the refit bootstrap's cost per replicate makes a large default
    dangerous to fall into by accident; the caller must state the number
    deliberately."""
    from simulation.generator import GeneratorConfig

    per_seed_rows = []
    for seed in seeds:
        config = GeneratorConfig(seed=seed, **config_kwargs)
        row = run_one_refit(config, resample_unit, n_boot=n_boot, alpha=alpha, **kwargs)
        per_seed_rows.append(row)

    half_widths = np.array([r["ci_half_width"] for r in per_seed_rows])
    deltas = np.array([r["delta_point"] for r in per_seed_rows])
    excludes_zero = np.array([r["ci_lo"] > 0.0 or r["ci_hi"] < 0.0 for r in per_seed_rows])
    realized_corrs = np.array([r["effect_size_realized_corr"] for r in per_seed_rows])
    nc_deltas = np.array([r["delta_negative_control"] for r in per_seed_rows])

    return {
        "label": label,
        "n_seeds": len(seeds),
        "seeds": list(seeds),
        "n_boot": n_boot,
        "method": "refit_per_replicate",
        **{k: v for k, v in config_kwargs.items()},
        "n_trials_total": per_seed_rows[0]["n_trials_total"],
        "effect_size_realized_corr_mean": float(np.mean(realized_corrs)),
        "delta_point_median": float(np.median(deltas)),
        "delta_point_mean": float(np.mean(deltas)),
        "ci_half_width_median": float(np.median(half_widths)),
        "ci_half_width_mean": float(np.mean(half_widths)),
        "ci_half_width_min": float(np.min(half_widths)),
        "ci_half_width_max": float(np.max(half_widths)),
        "frac_seeds_ci_excludes_zero": float(np.mean(excludes_zero)),
        "delta_negative_control_median": float(np.median(nc_deltas)),
        "delta_negative_control_max_abs": float(np.max(np.abs(nc_deltas))),
        "per_seed_rows": per_seed_rows,
    }
