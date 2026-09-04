"""
D0PA1 D3 -- absolute reliability measures.

CONTEXT (restated from the task, because it determines what this module
must NOT build): this study has ONE subject. A summary value per session
across three sessions is three observations of a SINGLE unit -- no
between-unit variance, so an ICC computed on that structure would be
uninterpretable, not merely imprecise. Absolute reliability measures
(SEM, RC, Bland-Altman, within-unit CV) do not require between-unit
variance and are what this module implements for real use; compute_icc()
below exists too, but REFUSES to run on an invalid (single-unit) design --
see its own docstring.

G1: every function here computes and stores a number. None of them decide
pass/fail, label a signal reliable/unreliable, or compare a result to a
threshold -- that reading is left entirely to a human.

REUSE, not reimplementation (this task's explicit instruction):
  - simulation.precision.precompute_unit_row_groups / resample_rows_once
    -- the exact unit-level bootstrap resampling primitive extracted from
    bootstrap_ci_on_delta -- power every confidence interval in this file.
    No second rng.choice(..., replace=True) resampling loop exists here.
  - simulation.config.PRE_REGISTERED_CONFIG.zero_dispersion_epsilon --
    the same pre-registered near-zero threshold used everywhere else in
    this codebase, applied here to within_unit_cv's grand-mean check.

INPUT CONTRACT: every measure below operates on a (n_units, n_sessions)
numpy array, NaN for a missing cell -- "units = scripted episodes or
trials, measurements = sessions" (this task's own framing, 2.2).
build_unit_session_matrix() is a convenience adapter from a flat list of
{"unit_id", "session_id", "value"} rows; callers with their own matrix
may skip it entirely.
"""

import numpy as np

from simulation.config import PRE_REGISTERED_CONFIG
from simulation.precision import precompute_unit_row_groups, resample_rows_once


def build_unit_session_matrix(rows):
    """rows: list of {"unit_id", "session_id", "value"} (value may be
    None for missing). Returns (matrix, unit_ids, session_ids) -- matrix
    shape (n_units, n_sessions), unit_ids/session_ids sorted and giving
    each matrix row/column's identity."""
    unit_ids = sorted({r["unit_id"] for r in rows})
    session_ids = sorted({r["session_id"] for r in rows})
    unit_idx = {u: i for i, u in enumerate(unit_ids)}
    session_idx = {s: i for i, s in enumerate(session_ids)}
    matrix = np.full((len(unit_ids), len(session_ids)), np.nan)
    for r in rows:
        v = r["value"]
        matrix[unit_idx[r["unit_id"]], session_idx[r["session_id"]]] = np.nan if v is None else v
    return matrix, unit_ids, session_ids


# ============================================================
# 2.1a -- SEM (standard error of measurement)
# ============================================================

def compute_sem(matrix):
    """SEM = sqrt(mean over units of that unit's own sample variance
    across sessions) -- the standard generalization, to >2 sessions, of
    SD(session_i - session_j)/sqrt(2) (the classic 2-session formula).
    Units with fewer than 2 non-missing session measurements cannot
    contribute a within-unit variance and are excluded from the pool --
    counted (n_units_used vs n_units_total), never silently dropped from
    the report."""
    n_units_total = matrix.shape[0]
    within_unit_vars = []
    for row in matrix:
        vals = row[~np.isnan(row)]
        if len(vals) >= 2:
            within_unit_vars.append(float(np.var(vals, ddof=1)))
    n_units_used = len(within_unit_vars)
    if n_units_used == 0:
        return {"sem": None, "n_units_used": 0, "n_units_total": n_units_total, "missingness_reason": "insufficient_samples"}
    sem = float(np.sqrt(np.mean(within_unit_vars)))
    return {"sem": sem, "n_units_used": n_units_used, "n_units_total": n_units_total, "missingness_reason": None}


# ============================================================
# 2.1b -- RC (repeatability coefficient)
# ============================================================

def compute_rc(sem):
    """RC = 1.96 * sqrt(2) * SEM. `sem` is a plain float (or None)."""
    if sem is None:
        return None
    return float(1.96 * np.sqrt(2) * sem)


# ============================================================
# 2.1c -- Bland-Altman limits of agreement, between SESSION PAIRS
# ============================================================

def compute_bland_altman_pair(matrix, session_i_idx, session_j_idx):
    """One session pair. bias = mean(session_i - session_j) across units
    with BOTH sessions present; limits of agreement = bias +/- 1.96*SD(diff)."""
    col_i = matrix[:, session_i_idx]
    col_j = matrix[:, session_j_idx]
    valid = ~np.isnan(col_i) & ~np.isnan(col_j)
    n = int(valid.sum())
    if n < 2:
        return {
            "n_units": n, "bias": None, "sd_diff": None, "loa_lower": None, "loa_upper": None,
            "diffs": np.array([]), "means": np.array([]), "missingness_reason": "insufficient_samples",
        }
    diffs = col_i[valid] - col_j[valid]
    means = (col_i[valid] + col_j[valid]) / 2.0
    bias = float(np.mean(diffs))
    sd_diff = float(np.std(diffs, ddof=1))
    return {
        "n_units": n, "bias": bias, "sd_diff": sd_diff,
        "loa_lower": bias - 1.96 * sd_diff, "loa_upper": bias + 1.96 * sd_diff,
        "diffs": diffs, "means": means, "missingness_reason": None,
    }


def compute_bland_altman_all_pairs(matrix, session_ids):
    """Every session PAIR, never one blended number across pairs (2.1's
    explicit requirement -- 'between session PAIRS')."""
    n_sessions = matrix.shape[1]
    results = {}
    for i in range(n_sessions):
        for j in range(i + 1, n_sessions):
            results[(session_ids[i], session_ids[j])] = compute_bland_altman_pair(matrix, i, j)
    return results


def plot_bland_altman_svg(ba_result, out_path, title="Bland-Altman"):
    """Writes an SVG (G4: never PNG). Same matplotlib.use('Agg') +
    fig.savefig(<path ending .svg>) pattern already used by
    simulation/run_precision_sweep.py's plots.

    DETERMINISM (D0PA1 D4, found while verifying reproduce.py's byte-diff
    -- see docs/D4_REPRODUCIBILITY.md): matplotlib's SVG backend embeds
    two non-deterministic things by default, neither of which reflects
    the plotted DATA -- (1) a creation-timestamp in the SVG's Dublin Core
    metadata block, and (2) per-element `id`/`clip-path` attributes
    derived from a random hash salt regenerated every process run (the
    coordinate DATA those elements carry is identical across runs; only
    the arbitrary label matplotlib gives each element differs). Both are
    suppressed below -- `svg.hashsalt` fixed to a constant so element ids
    are a deterministic function of the figure's own content, and
    `metadata={"Date": None}` so no timestamp is embedded. Confirmed by
    the actual fix: two runs of the same plot are now byte-identical
    (tests/test_reliability.py's `check_bland_altman_svg_written` still
    only checks structural validity, not byte-identity across runs --
    that end-to-end proof lives in the D4 reproduction check instead)."""
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "d0pa1-reproducible-svg"
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 5))
    if len(ba_result["means"]) > 0:
        ax.scatter(ba_result["means"], ba_result["diffs"], alpha=0.6, s=15, color="tab:blue")
    if ba_result["bias"] is not None:
        ax.axhline(ba_result["bias"], color="black", linestyle="-", label=f"bias={ba_result['bias']:.4g}")
        ax.axhline(ba_result["loa_upper"], color="tab:red", linestyle="--", label=f"+1.96 SD={ba_result['loa_upper']:.4g}")
        ax.axhline(ba_result["loa_lower"], color="tab:red", linestyle="--", label=f"-1.96 SD={ba_result['loa_lower']:.4g}")
    ax.set_xlabel("Mean of session pair")
    ax.set_ylabel("Difference (session i - session j)")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, metadata={"Date": None})
    plt.close(fig)
    return out_path


# ============================================================
# 2.1d -- within-unit coefficient of variation
# ============================================================

def compute_within_unit_cv(matrix):
    """CV% = SEM / |grand_mean| * 100 -- the standard clinical
    'within-subject CV%' formula. Undefined when the grand mean sits too
    close to zero for a RATIO to be meaningful -- judged against
    PRE_REGISTERED_CONFIG.zero_dispersion_epsilon (this codebase's single
    pre-registered near-zero threshold), applied here to the MEAN, not
    the spread -- a structurally different judgment from zero_dispersion
    (which is about the spread being ~0), so this reports
    missingness_reason="not_applicable", not "zero_dispersion"."""
    sem_result = compute_sem(matrix)
    if sem_result["sem"] is None:
        return {**sem_result, "cv_percent": None, "grand_mean": None}
    all_vals = matrix[~np.isnan(matrix)]
    grand_mean = float(np.mean(all_vals))
    if abs(grand_mean) < PRE_REGISTERED_CONFIG.zero_dispersion_epsilon:
        return {**sem_result, "cv_percent": None, "grand_mean": grand_mean, "missingness_reason": "not_applicable"}
    cv_percent = float((sem_result["sem"] / abs(grand_mean)) * 100.0)
    return {**sem_result, "cv_percent": cv_percent, "grand_mean": grand_mean}


# ============================================================
# Bootstrap CI, REUSED unit-level resampling machinery (2.1's "each with a
# confidence interval from the episode-level resampling machinery you
# reused from simulation/precision.py").
# ============================================================

def bootstrap_ci_for_measure(matrix, measure_fn, n_boot, alpha, rng):
    """measure_fn: callable(matrix_subset) -> float | None. Resamples
    UNITS (matrix rows) with replacement via
    simulation.precision.precompute_unit_row_groups/resample_rows_once
    -- the SAME extracted primitive bootstrap_ci_on_delta itself uses,
    not a second implementation. A replicate whose measure_fn returns
    None/non-finite (e.g. too few complete units in that particular
    resample) is excluded from the percentile computation and counted,
    never silently treated as zero."""
    n_units = matrix.shape[0]
    unique_units, unit_to_rows = precompute_unit_row_groups(np.arange(n_units))  # raises if n_units < 2

    point = measure_fn(matrix)
    values = []
    n_invalid = 0
    for _ in range(n_boot):
        rows = resample_rows_once(unique_units, unit_to_rows, rng)
        v = measure_fn(matrix[rows])
        if v is None or not np.isfinite(v):
            n_invalid += 1
            continue
        values.append(v)

    if len(values) < 2:
        return {
            "point": point, "ci_lo": None, "ci_hi": None, "ci_half_width": None,
            "n_boot": n_boot, "n_valid_replicates": len(values), "n_invalid_replicates": n_invalid,
            "alpha": alpha, "resample_unit": "unit",
        }
    values = np.asarray(values)
    lo = float(np.percentile(values, 100 * (alpha / 2)))
    hi = float(np.percentile(values, 100 * (1 - alpha / 2)))
    return {
        "point": point, "ci_lo": lo, "ci_hi": hi, "ci_half_width": (hi - lo) / 2.0,
        "n_boot": n_boot, "n_valid_replicates": len(values), "n_invalid_replicates": n_invalid,
        "alpha": alpha, "resample_unit": "unit",
    }


def compute_all_reliability_measures(matrix, session_ids, n_boot=1000, alpha=0.05, rng=None):
    """2.1, all four measures + CIs, on ONE (n_units, n_sessions) matrix.
    Never blends across signals -- call once per signal's own matrix."""
    if rng is None:
        rng = np.random.default_rng(0)

    sem_point = compute_sem(matrix)
    sem_ci = bootstrap_ci_for_measure(matrix, lambda m: compute_sem(m)["sem"], n_boot, alpha, rng)
    rc_ci = bootstrap_ci_for_measure(matrix, lambda m: compute_rc(compute_sem(m)["sem"]), n_boot, alpha, rng)
    cv_point = compute_within_unit_cv(matrix)
    cv_ci = bootstrap_ci_for_measure(matrix, lambda m: compute_within_unit_cv(m)["cv_percent"], n_boot, alpha, rng)

    ba_pairs = compute_bland_altman_all_pairs(matrix, session_ids)
    ba_with_ci = {}
    for (si, sj), ba in ba_pairs.items():
        i, j = session_ids.index(si), session_ids.index(sj)
        bias_ci = bootstrap_ci_for_measure(matrix, lambda m, i=i, j=j: compute_bland_altman_pair(m, i, j)["bias"], n_boot, alpha, rng)
        ba_with_ci[(si, sj)] = {**ba, "bias_ci": bias_ci}

    return {
        "sem": {**sem_point, "ci": sem_ci},
        "rc": {"rc": compute_rc(sem_point["sem"]), "ci": rc_ci},
        "cv": {**cv_point, "ci": cv_ci},
        "bland_altman": ba_with_ci,
        "n_units_total": matrix.shape[0],
        "n_sessions": matrix.shape[1],
    }


# ============================================================
# 2.2 -- ICC that REFUSES to run on an invalid (single-unit) structure.
# ============================================================

def compute_icc(matrix, unit_ids, session_ids):
    """ICC(2,1) -- two-way random effects, absolute agreement, single
    measurement (Shrout & Fleiss 1979). Takes an EXPLICIT repeated-unit
    argument (unit_ids: units = scripted episodes or trials;
    session_ids: measurements = sessions) -- both required, never
    inferred or defaulted.

    RAISES ValueError if fewer than 2 distinct units are given. This is
    not a conservative default that could be argued around: with ONE
    subject, a single summary value per session across sessions is THREE
    OBSERVATIONS OF ONE UNIT, not multiple units x k measurements -- there
    is no between-unit variance for an ICC to be a ratio OF, and any
    number this function returned on that structure would be
    UNINTERPRETABLE, not merely imprecise (CLAUDE.md D0PA1 hard
    constraint #1). This function exists so it is CORRECT once a valid
    multi-unit design is agreed with the client, and FAILS LOUDLY,
    every time, until then -- it must never silently return a number from
    an invalid design."""
    unique_units = sorted(set(unit_ids))
    if len(unique_units) < 2:
        raise ValueError(
            f"ICC requires at least 2 distinct repeated-measurement units; got {len(unique_units)} "
            f"({unique_units!r}). With a single unit -- e.g. one subject's one summary value per "
            "session, repeated across sessions -- there is no between-unit variance for an ICC to "
            "be a ratio of; the result would be UNINTERPRETABLE, not merely imprecise. Use the "
            "absolute reliability measures instead (compute_sem/compute_rc/compute_bland_altman_*/"
            "compute_within_unit_cv in this module) -- see CLAUDE.md D0PA1 hard constraint #1 and "
            "docs/RELIABILITY.md."
        )
    if matrix.shape[0] != len(unique_units):
        raise ValueError(
            f"matrix has {matrix.shape[0]} rows but unit_ids names {len(unique_units)} distinct "
            "units -- these must correspond 1:1 (one row per unit)."
        )
    if matrix.shape[1] != len(session_ids):
        raise ValueError(f"matrix has {matrix.shape[1]} columns but {len(session_ids)} session_ids were given.")

    complete_mask = ~np.isnan(matrix).any(axis=1)
    complete_matrix = matrix[complete_mask]
    n = complete_matrix.shape[0]
    k = complete_matrix.shape[1]
    if n < 2:
        raise ValueError(
            f"only {n} unit(s) have complete data across all {k} sessions (out of {matrix.shape[0]} "
            "total units) -- ICC requires at least 2 units with a measurement in every session."
        )
    if k < 2:
        raise ValueError(f"ICC requires at least 2 sessions (measurements); got {k}.")

    grand_mean = complete_matrix.mean()
    unit_means = complete_matrix.mean(axis=1)
    session_means = complete_matrix.mean(axis=0)

    ss_total = float(((complete_matrix - grand_mean) ** 2).sum())
    ss_units = float(k * ((unit_means - grand_mean) ** 2).sum())
    ss_sessions = float(n * ((session_means - grand_mean) ** 2).sum())
    ss_error = ss_total - ss_units - ss_sessions

    ms_units = ss_units / (n - 1)
    ms_sessions = ss_sessions / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))

    denom = ms_units + (k - 1) * ms_error + k * (ms_sessions - ms_error) / n
    icc_value = (ms_units - ms_error) / denom if denom != 0 else float("nan")

    return {
        "icc": float(icc_value), "n_units": n, "n_units_total": matrix.shape[0], "k_sessions": k,
        "ms_units": float(ms_units), "ms_sessions": float(ms_sessions), "ms_error": float(ms_error),
        "formula": "ICC(2,1) two-way random, absolute agreement, single measurement (Shrout & Fleiss 1979)",
    }
