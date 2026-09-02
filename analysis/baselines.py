"""
D0PA1 D7 -- three baseline representations, computed on the same recordings.

    raw            raw signal values, no standardisation
    session_z      z = (x_t - median_s) / (1.4826 * MAD_s)      WITHIN-SESSION
    persistent_z   z = (x_t - B_person,t) / S_person,t           CROSS-SESSION,
                   B/S computed ONLY from sessions strictly before t

G1: this module computes and stores numbers. It never decides pass/fail,
never labels a signal reliable/unreliable, and never compares a
representation's output to a threshold.

REUSE, not reimplementation (this task's explicit instruction):
  - features.robust_baseline.mad_stats / mad_z_score -- the MAD math
    (including zero_dispersion handling against
    simulation.config.PRE_REGISTERED_CONFIG.zero_dispersion_epsilon) is
    used AS-IS for session_z and for persistent_z's "robust_mad" estimator.
    Nothing here recomputes a median/MAD independently.
  - schema.canonical_log_writer.MISSINGNESS_REASONS -- the ONE fixed
    missingness-reason vocabulary, extended (v2) with "no_prior_history"
    for persistent_z's own structural case (see that schema's own
    changelog note), not a second, independently-maintained list.

INPUT CONTRACT: sessions_in_order is a list of (session_id, samples) pairs,
IN CHRONOLOGICAL ORDER (a list, not a dict, so "which session came before
which" is never left to incidental dict-ordering behavior a reader would
have to trust). Each `samples` is a list of per-observation dicts:
    {"value": float | None, "missingness_reason": str | None}
An entry with value=None MUST carry a real missingness_reason (from the
UPSTREAM classification, e.g. features.signal_quality.classify_signal_missingness)
-- this module does not invent a reason for an already-missing raw value,
it only adds reasons for ITS OWN transform-specific missing cases
(zero_dispersion, insufficient_samples, no_prior_history).
"""

import numpy as np

from features.robust_baseline import mad_stats, mad_z_score
from simulation.config import PRE_REGISTERED_CONFIG
from schema.canonical_log_writer import MISSINGNESS_REASONS

BASELINE_ESTIMATORS = ("historical_sd", "robust_mad")
# "expanding" == "pooled within-person" in this task's parameter-naming list
# (1.1's own worked definition: "Expanding window over all prior sessions") --
# both names refer to the SAME rule; "expanding" is used as the canonical
# value because 1.1 gives its exact formula under that name.
BASELINE_WINDOW_RULES = ("expanding", "rolling", "preceding_session_only")

NO_PRIOR_HISTORY_REASON = "no_prior_history"
ZERO_DISPERSION_REASON = "zero_dispersion"
INSUFFICIENT_SAMPLES_REASON = "insufficient_samples"

for _reason in (NO_PRIOR_HISTORY_REASON, ZERO_DISPERSION_REASON, INSUFFICIENT_SAMPLES_REASON):
    assert _reason in MISSINGNESS_REASONS, (
        f"analysis/baselines.py emits reason {_reason!r} not in "
        f"schema.canonical_log_writer.MISSINGNESS_REASONS -- schema/canonical_log_v1.json "
        "must be updated first (see its own changelog note)."
    )


def _validate_sample(entry):
    if entry["value"] is None and entry.get("missingness_reason") is None:
        raise ValueError(
            "sample has value=None but no missingness_reason -- the upstream caller "
            "(e.g. features.signal_quality.classify_signal_missingness) must classify "
            "why a value is missing before it reaches analysis/baselines.py; this "
            "module does not invent a reason for an already-missing raw value."
        )


# ============================================================
# ESTIMATORS -- both consumed identically by persistent_z below, selected
# by BaselineParams.estimator. "robust_mad" REUSES features.robust_baseline
# directly; "historical_sd" is new (mean/std has no prior home in this
# codebase) but follows the exact same zero_dispersion-epsilon convention.
# ============================================================

def _historical_sd_stats(values):
    """values: iterable of raw floats/None. Returns the SAME shape
    mad_stats() returns ({"center","scale","n","zero_dispersion",
    "zero_dispersion_reason"}) but with mean/std instead of median/MAD --
    same zero-dispersion floor (PRE_REGISTERED_CONFIG.zero_dispersion_epsilon)
    as every other zero_dispersion check in this codebase, not a
    independently-invented threshold."""
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    n = len(arr)
    if n < 2:
        return {"center": None, "scale": None, "n": n, "zero_dispersion": None, "zero_dispersion_reason": INSUFFICIENT_SAMPLES_REASON}
    center = float(arr.mean())
    scale = float(arr.std())
    is_zero = scale < PRE_REGISTERED_CONFIG.zero_dispersion_epsilon
    return {
        "center": center, "scale": scale, "n": n,
        "zero_dispersion": is_zero,
        "zero_dispersion_reason": ZERO_DISPERSION_REASON if is_zero else None,
    }


def _robust_mad_stats(values):
    """REUSES features.robust_baseline.mad_stats() -- not reimplemented.
    Reshaped to the same {"center","scale",...} shape _historical_sd_stats
    uses, so persistent_z's z-computation is estimator-agnostic."""
    stats = mad_stats(values)
    return {
        "center": stats["median"], "scale": stats["mad_scaled"], "n": stats["n"],
        "zero_dispersion": stats["zero_dispersion"], "zero_dispersion_reason": stats["zero_dispersion_reason"],
    }


_ESTIMATOR_FNS = {"historical_sd": _historical_sd_stats, "robust_mad": _robust_mad_stats}


def _z_from_stats(value, stats):
    """(x - center) / scale, or None whenever value/center/scale is
    missing or scale is zero_dispersion -- NEVER divides by zero, NEVER
    adds a silent epsilon. Same contract as
    features.robust_baseline.mad_z_score, generalised to accept either
    estimator's stats shape (that function itself is reused directly for
    the MAD estimator's own z, via mad_z_score, where the stats came from
    mad_stats(); this helper additionally covers the historical_sd
    estimator, which mad_z_score's own signature does not)."""
    if value is None or stats.get("center") is None or stats.get("scale") is None:
        return None
    if stats.get("zero_dispersion"):
        return None
    return (value - stats["center"]) / stats["scale"]


# ============================================================
# 1 -- raw
# ============================================================

def compute_raw(sessions_in_order):
    """Pass-through: value stays value, missingness_reason stays whatever
    the caller supplied. n_session_pairs is 0 for every row -- raw never
    looks outside its own sample."""
    out = []
    for session_id, samples in sessions_in_order:
        for i, entry in enumerate(samples):
            _validate_sample(entry)
            out.append({
                "representation": "raw",
                "session_id": session_id,
                "sample_idx": i,
                "value": entry["value"],
                "missingness_flag": entry["value"] is None,
                "missingness_reason": entry.get("missingness_reason"),
                "n_session_pairs": 0,
            })
    return {"records": out, "n_session_pairs_total": 0, "representation": "raw"}


# ============================================================
# 2 -- session_z (within-session, reuses features.robust_baseline directly)
# ============================================================

def compute_session_z(sessions_in_order):
    """z computed WITHIN each session independently, via
    features.robust_baseline.mad_stats/mad_z_score (reused, not
    reimplemented). n_session_pairs is 0 for every row: this representation
    never uses any OTHER session's data."""
    out = []
    for session_id, samples in sessions_in_order:
        values = [entry["value"] for entry in samples]
        stats = mad_stats(values)
        for i, entry in enumerate(samples):
            _validate_sample(entry)
            if entry["value"] is None:
                missingness_reason = entry.get("missingness_reason")
            elif stats["zero_dispersion"]:
                missingness_reason = ZERO_DISPERSION_REASON
            elif stats["median"] is None:
                missingness_reason = stats["zero_dispersion_reason"] or INSUFFICIENT_SAMPLES_REASON
            else:
                missingness_reason = None
            z = mad_z_score(entry["value"], stats) if entry["value"] is not None else None
            out.append({
                "representation": "session_z",
                "session_id": session_id,
                "sample_idx": i,
                "value": z,
                "missingness_flag": z is None,
                "missingness_reason": missingness_reason,
                "n_session_pairs": 0,
                "session_median": stats["median"],
                "session_mad_scaled": stats["mad_scaled"],
                "session_n": stats["n"],
            })
    return {"records": out, "n_session_pairs_total": 0, "representation": "session_z"}


# ============================================================
# 3 -- persistent_z (cross-session, the temporal rule IS the point -- see
# analysis/baselines.py's module docstring and 1.2's invariant)
# ============================================================

def _select_prior_pool(sessions_in_order, t_idx, window_rule, rolling_window_sessions):
    """Returns (pooled_values, n_prior_sessions_used) for evaluating
    sessions_in_order[t_idx]. NEVER includes sessions_in_order[t_idx]
    itself -- this is the ONE place the temporal invariant (1.2) is
    enforced: prior_sessions is a slice STRICTLY BEFORE t_idx."""
    prior_sessions = sessions_in_order[:t_idx]  # STRICTLY before t -- the invariant, enforced here
    if window_rule == "expanding":
        chosen = prior_sessions
    elif window_rule == "rolling":
        if rolling_window_sessions < 1:
            raise ValueError(f"rolling_window_sessions must be >= 1, got {rolling_window_sessions}")
        chosen = prior_sessions[-rolling_window_sessions:]
    elif window_rule == "preceding_session_only":
        chosen = prior_sessions[-1:]
    else:
        raise ValueError(f"window_rule must be one of {BASELINE_WINDOW_RULES}, got {window_rule!r}")

    pooled = []
    for _sid, samples in chosen:
        pooled.extend(entry["value"] for entry in samples)
    return pooled, len(chosen)


def compute_persistent_z(sessions_in_order, estimator="robust_mad", window_rule="expanding", rolling_window_sessions=3):
    """estimator/window_rule/rolling_window_sessions default to
    PreRegisteredConfig's own defaults (robust_mad / expanding) but are
    plain parameters here, not read from the config directly -- see
    compute_all_baselines() for the config-driven entry point; this
    function stays testable with arbitrary parameter combinations without
    needing to construct a PreRegisteredConfig for every test case.

    1.2's invariant, restated as code: B_person,t and S_person,t are
    computed EXCLUSIVELY from _select_prior_pool(sessions_in_order, t_idx,
    ...), which slices STRICTLY before t_idx. Session t's own samples are
    never read by _select_prior_pool for evaluating session t -- see
    tests/test_baselines.py's leakage test, which is the actual evidence
    for this claim, not this docstring.

    1.4: session_in_order[0] (the first session, no matter what session_id
    it carries) has NO prior sessions by construction --
    _select_prior_pool returns an empty prior_sessions slice for t_idx=0
    under every window_rule, so persistent_z is emitted as missing with
    reason no_prior_history for every sample in that session. There is NO
    fallback to within-session values anywhere in this function."""
    if estimator not in BASELINE_ESTIMATORS:
        raise ValueError(f"estimator must be one of {BASELINE_ESTIMATORS}, got {estimator!r}")
    if window_rule not in BASELINE_WINDOW_RULES:
        raise ValueError(f"window_rule must be one of {BASELINE_WINDOW_RULES}, got {window_rule!r}")
    estimator_fn = _ESTIMATOR_FNS[estimator]

    out = []
    n_session_pairs_total = 0

    for t_idx, (session_id, samples) in enumerate(sessions_in_order):
        for entry in samples:
            _validate_sample(entry)

        if t_idx == 0:
            # 1.4 -- NO fallback to within-session values. Every sample in
            # the first session emits missing with reason no_prior_history.
            for i, entry in enumerate(samples):
                out.append({
                    "representation": "persistent_z",
                    "session_id": session_id,
                    "sample_idx": i,
                    "value": None,
                    "missingness_flag": True,
                    "missingness_reason": NO_PRIOR_HISTORY_REASON,
                    "n_session_pairs": 0,
                    "baseline_center": None,
                    "baseline_scale": None,
                    "n_prior_sessions_used": 0,
                    "estimator": estimator,
                    "window_rule": window_rule,
                })
            continue

        pooled_prior_values, n_prior_sessions_used = _select_prior_pool(
            sessions_in_order, t_idx, window_rule, rolling_window_sessions
        )
        stats = estimator_fn(pooled_prior_values)
        # 1.6 -- session-pair count: one (evaluated_session, prior_session)
        # pair per prior session actually pooled into THIS session's
        # baseline. Summed across all evaluated sessions below.
        n_session_pairs_total += n_prior_sessions_used

        for i, entry in enumerate(samples):
            if entry["value"] is None:
                missingness_reason = entry.get("missingness_reason")
            elif stats["center"] is None:
                missingness_reason = stats["zero_dispersion_reason"] or INSUFFICIENT_SAMPLES_REASON
            elif stats["zero_dispersion"]:
                missingness_reason = ZERO_DISPERSION_REASON
            else:
                missingness_reason = None
            z = _z_from_stats(entry["value"], stats)
            out.append({
                "representation": "persistent_z",
                "session_id": session_id,
                "sample_idx": i,
                "value": z,
                "missingness_flag": z is None,
                "missingness_reason": missingness_reason,
                "n_session_pairs": n_prior_sessions_used,
                "baseline_center": stats["center"],
                "baseline_scale": stats["scale"],
                "n_prior_sessions_used": n_prior_sessions_used,
                "estimator": estimator,
                "window_rule": window_rule,
            })

    return {
        "records": out,
        "n_session_pairs_total": n_session_pairs_total,
        "representation": "persistent_z",
        "estimator": estimator,
        "window_rule": window_rule,
        "rolling_window_sessions": rolling_window_sessions if window_rule == "rolling" else None,
    }


# ============================================================
# Entry point -- all three, config-driven for persistent_z's parameters.
# ============================================================

def compute_all_baselines(sessions_in_order, config=None):
    """config: a PreRegisteredConfig (defaults to
    simulation.config.PRE_REGISTERED_CONFIG) -- its baseline_estimator/
    baseline_window_rule/baseline_rolling_window_sessions fields drive
    persistent_z, so the choice is recorded and covered by config_hash()
    (1.1's explicit requirement), not a bare parameter a caller could vary
    without it being pre-registered anywhere.

    1.6, restated at the top level: raw and session_z carry
    n_session_pairs_total=0 (both are single-session-only representations
    by construction); persistent_z carries its real total. A caller
    printing all three side by side sees this difference directly -- they
    cannot be presented as like-for-like without visibly discarding a
    field every record already carries."""
    if config is None:
        config = PRE_REGISTERED_CONFIG

    raw = compute_raw(sessions_in_order)
    session_z = compute_session_z(sessions_in_order)
    persistent_z = compute_persistent_z(
        sessions_in_order,
        estimator=config.baseline_estimator,
        window_rule=config.baseline_window_rule,
        rolling_window_sessions=config.baseline_rolling_window_sessions,
    )

    return {
        "raw": raw,
        "session_z": session_z,
        "persistent_z": persistent_z,
        "config_hash": config.config_hash(),
    }
