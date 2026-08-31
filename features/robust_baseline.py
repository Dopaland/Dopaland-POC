"""
D0PA1 Part C, C1 -- MAD-based robust baseline.

Computed ALONGSIDE features.x_core.NeutralCalibrator's existing mean/std
calibration -- NOT a replacement. Both representations are computed and
logged; neither supersedes the other (this task's explicit instruction).

    z = (x_t - median_s) / (1.4826 * MAD_s)

1.4826 is the normal-consistency constant (makes MAD comparable to std
under a normal distribution) -- used EXACTLY, never rounded or re-derived.

WHY THIS IS A SEPARATE MODULE, NOT A NEW NeutralCalibrator METHOD:
NeutralCalibrator is validated-path (G5) and its complete()/`.reference`
output is captured byte-for-byte by tests/test_refactor_snapshot.py's
golden file. Adding a field to that return shape would be a real,
observable change to the validated path -- exactly what G5 forbids without
an explicit ask, and this task's Part C asked for "alongside", not
"inside". This module instead consumes NeutralCalibrator.samples (already
a public attribute: list[{"composite": {...}, "covariate": {...},
"yaw_deg": ...}]) as a READ-ONLY input. NeutralCalibrator itself is never
imported, subclassed, or modified -- confirmed by this file having no
`from features.x_core import NeutralCalibrator` anywhere in it.

MAD == 0 (or near enough to be meaningless), handled EXPLICITLY per
CLAUDE.md D0PA1 hard constraint #5 and this task's own instruction: "emit
missing with reason zero_dispersion. Do not divide by zero, do not add a
silent epsilon." Concretely:
  - mad_stats() NEVER silently adds an epsilon to mad_scaled before using
    it as a denominator -- there is no "+ epsilon" anywhere in this file.
  - The exact-zero case (mad_scaled == 0.0, e.g. more than half of a
    signal's samples share the identical value) is handled the same way
    as the near-zero case: both are classified zero_dispersion=True and
    mad_z_score() returns None (missing), never a computed number.
  - "Near enough to be meaningless" is judged against
    simulation.config.PRE_REGISTERED_CONFIG.zero_dispersion_epsilon --
    the SAME pre-registered, hashed threshold controls/null_input.py's own
    compute_dispersion() already uses for exactly this purpose (Gate 0 A2
    centralized it there specifically so this decision has one source of
    truth). Reusing it here is NOT "adding a silent epsilon to smooth
    division" -- it is a THRESHOLD deciding whether z should be computed
    AT ALL; when the threshold is crossed, z is reported missing, never a
    finite-but-fabricated number. V_pd's real neutral MAD is expected to
    sit at or near this exact boundary (CLAUDE.md's own STATUS section) --
    an exact-zero-only check would fail to catch that case, which is
    precisely the failure mode this whole task exists to prevent (the std
    version of the same problem is documented at length in CLAUDE.md).
"""

import numpy as np

from simulation.config import PRE_REGISTERED_CONFIG

ZERO_DISPERSION_REASON = "zero_dispersion"
INSUFFICIENT_SAMPLES_REASON = "insufficient_samples"
MAD_NORMAL_CONSTANT = 1.4826

MIN_SAMPLES_FOR_MAD = 2  # below this, median/MAD are not meaningfully defined


def mad_stats(values):
    """values: iterable of raw floats/None (None/non-finite entries are
    excluded here, same convention NeutralCalibrator._stats uses -- the
    caller does not need to pre-filter). Returns:
        {median, mad, mad_scaled, n, zero_dispersion, zero_dispersion_reason}
    NEVER divides by zero, NEVER adds a silent epsilon -- see module
    docstring."""
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    n = len(arr)
    if n < MIN_SAMPLES_FOR_MAD:
        return {
            "median": None, "mad": None, "mad_scaled": None, "n": n,
            "zero_dispersion": None, "zero_dispersion_reason": INSUFFICIENT_SAMPLES_REASON,
        }

    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    mad_scaled = MAD_NORMAL_CONSTANT * mad

    is_zero = mad_scaled < PRE_REGISTERED_CONFIG.zero_dispersion_epsilon
    return {
        "median": median,
        "mad": mad,
        "mad_scaled": mad_scaled,
        "n": n,
        "zero_dispersion": is_zero,
        "zero_dispersion_reason": ZERO_DISPERSION_REASON if is_zero else None,
    }


def mad_z_score(raw_value, stats):
    """z = (raw_value - stats['median']) / stats['mad_scaled'], or None
    (missing) whenever raw_value is missing, stats itself has no median/
    mad_scaled (insufficient_samples), or stats['zero_dispersion'] is True
    -- the last case is the one that matters most: NEVER divides by a
    zero-or-near-zero mad_scaled, no matter how the caller got here."""
    if raw_value is None:
        return None
    if stats is None or stats.get("median") is None or stats.get("mad_scaled") is None:
        return None
    if stats.get("zero_dispersion"):
        return None
    return (raw_value - stats["median"]) / stats["mad_scaled"]


def robust_calibration_reference(samples, composite_keys, covariate_keys):
    """Mirrors NeutralCalibrator.complete()'s {"composite": {...},
    "covariates": {...}} structure -- same samples input
    (NeutralCalibrator.samples, a list of {"composite": {...}, "covariate":
    {...}, "yaw_deg": ...} dicts, already collected by the real
    calibration pass) -- but reports median/MAD instead of mean/std.
    Purely read-only over `samples`; never touches NeutralCalibrator or
    its state. Meant to be computed ONCE, at the same moment
    NeutralCalibrator.complete() is called, and logged alongside its
    output -- "both computed, both logged", per this task's instruction."""
    def _values(bucket, key):
        return [s[bucket].get(key) for s in samples]

    return {
        "composite": {k: mad_stats(_values("composite", k)) for k in composite_keys},
        "covariates": {k: mad_stats(_values("covariate", k)) for k in covariate_keys},
    }


def robust_deviation(raw_value, key, robust_reference, bucket="composite"):
    """Per-sample robust z-score for `key`, against a frozen
    robust_calibration_reference() result -- the MAD-based analogue of
    NeutralCalibrator.deviation()/x_core._z_score() for a single sample."""
    if robust_reference is None:
        return None
    stats = robust_reference.get(bucket, {}).get(key)
    return mad_z_score(raw_value, stats)
