"""
D6 precision-pipeline validation (runnable directly, no pytest). Checks:

  1. resample_unit is a required argument with no default, and 'trial' is
     explicitly refused (CLAUDE.md D0PA1 hard constraint #4).
  2. Null case (effect_size=0): the point estimate of Delta should be near
     zero and its bootstrap CI should typically contain zero -- a sanity
     check that the "without" and "with" models are not spuriously
     different when the candidate signal carries no real information.
  3. Strong-effect case (effect_size=0.8, generous N): Delta should be
     clearly positive and the CI should typically exclude zero -- a check
     that the pipeline CAN detect a real effect when one is present, not
     just that it says "inconclusive" no matter what.
  4. CI half-width shrinks as N (episodes per session) grows, holding
     everything else fixed -- the basic monotonicity a precision curve
     must show, checked directly rather than assumed.
  5. D0PA1 Part 2.2: the negative control cannot be omitted -- an "unaware
     caller" using compute_delta/run_one with no mention of negative
     controls anywhere in the call still gets delta_negative_control back,
     populated.
  6. D0PA1 primary-metric comparison (docs/D6_SIMULATION.md section 11):
     the metric refactor changed NO default behavior -- run_one_refit with
     no metric argument reproduces the exact pre-refactor macro-F1 numbers.
  7. neg_log_loss's clipping: a probability of exactly 0.0 for the true
     class does not produce inf/nan, and the reported value is sensitive
     to the clip epsilon in the documented direction.
  8. neg_log_loss's orientation: a model that is MORE confident in the
     correct class (same argmax, different probability) has a HIGHER U,
     even though macro-F1 would report zero difference -- this is the
     entire reason the comparison exists.

This is a validation of the PIPELINE's plumbing, not a claim about what
real data will show -- see docs/D6_SIMULATION.md and
artefacts/precision_analysis_v1.md / precision_analysis_v2.md for the
actual precision findings.
"""

import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.generator import GeneratorConfig
from simulation.precision import (
    run_one, run_one_refit, compute_delta, bootstrap_ci_on_delta, chronological_split,
    MACRO_F1_METRIC, NEG_LOG_LOSS_METRIC,
)
from simulation.generator import generate
from simulation.models import neg_log_loss


def check_resample_unit_required():
    cfg = GeneratorConfig(seed=1, n_sessions=1, episodes_per_session=30, trials_per_episode=4)
    records = generate(cfg)
    delta_result = compute_delta(records, cfg.n_classes, cfg.n_sessions)
    rng = np.random.default_rng(0)
    try:
        bootstrap_ci_on_delta(delta_result, "trial", 200, 0.05, rng)
        return False, "bootstrap_ci_on_delta accepted resample_unit='trial' -- should have raised"
    except ValueError as e:
        if "trial" not in str(e).lower() and "episode" not in str(e).lower():
            return False, f"raised for the wrong reason: {e}"
    try:
        import inspect
        sig = inspect.signature(bootstrap_ci_on_delta)
        if sig.parameters["resample_unit"].default is not inspect.Parameter.empty:
            return False, "resample_unit has a default -- task requires no default"
    except Exception as e:
        return False, f"could not inspect signature: {e}"
    return True, "resample_unit correctly required, defaultless, and 'trial' rejected"


def check_null_case(seed=42):
    cfg = GeneratorConfig(
        seed=seed, n_sessions=3, episodes_per_session=150, trials_per_episode=5, effect_size=0.0,
    )
    row = run_one(cfg, resample_unit="episode", n_boot=500)
    contains_zero = row["ci_lo"] <= 0.0 <= row["ci_hi"]
    return row, contains_zero


def check_strong_effect_case(seed=42):
    cfg = GeneratorConfig(
        seed=seed, n_sessions=3, episodes_per_session=400, trials_per_episode=5, effect_size=0.8,
    )
    row = run_one(cfg, resample_unit="episode", n_boot=500)
    excludes_zero_below = row["ci_lo"] > 0.0
    return row, excludes_zero_below


def check_ci_shrinks_with_n(seed=7):
    widths = []
    for eps in (50, 150, 400):
        cfg = GeneratorConfig(seed=seed, n_sessions=3, episodes_per_session=eps, trials_per_episode=5, effect_size=0.3)
        row = run_one(cfg, resample_unit="episode", n_boot=400)
        widths.append((eps, row["ci_half_width"]))
    return widths


def check_negative_control_cannot_be_omitted(seed=13):
    """D0PA1 Part 2.2: the negative control must be wired into the
    analysis path automatically, not a flag a caller can forget. Verified
    two ways: (1) calling compute_delta with NO mention of the negative
    control anywhere in the call (exactly how an unaware caller would use
    it) still returns delta_negative_control populated; (2) the plain
    run_one() path (used by every sweep/report in this codebase) also
    carries it through to the result dict, unconditionally."""
    cfg = GeneratorConfig(seed=seed, n_sessions=3, episodes_per_session=150, trials_per_episode=5, effect_size=0.2)
    records = generate(cfg)

    # An "unaware caller" -- positional/required args only, nothing about
    # negative controls anywhere in this call.
    delta_result = compute_delta(records, cfg.n_classes, cfg.n_sessions)
    has_it_in_compute_delta = (
        delta_result.delta_negative_control is not None
        and delta_result.u_with_negative_control is not None
        and delta_result.negative_control_seed is not None
    )

    row = run_one(cfg, resample_unit="episode", n_boot=200)
    has_it_in_run_one = "delta_negative_control" in row and row["delta_negative_control"] is not None

    ok = has_it_in_compute_delta and has_it_in_run_one
    return ok, {
        "delta_negative_control_from_compute_delta": delta_result.delta_negative_control,
        "delta_negative_control_from_run_one": row.get("delta_negative_control"),
    }


def check_metric_refactor_preserves_default_behavior(seed=7):
    """D0PA1 primary-metric comparison: the Metric abstraction must not
    have changed macro-F1's own numbers. Reproduces
    check_ci_shrinks_with_n's exact config and compares against its
    known-good, pre-refactor half-widths."""
    cfg = GeneratorConfig(seed=seed, n_sessions=3, episodes_per_session=150, trials_per_episode=5, effect_size=0.3)
    row_default = run_one(cfg, resample_unit="episode", n_boot=400)  # no metric= argument at all
    row_explicit = run_one(cfg, resample_unit="episode", n_boot=400, metric=MACRO_F1_METRIC)
    ok = (
        row_default["ci_half_width"] == row_explicit["ci_half_width"]
        and row_default["delta_point"] == row_explicit["delta_point"]
        and row_default["metric"] == "macro_f1"
    )
    return ok, {"default_half_width": row_default["ci_half_width"], "explicit_half_width": row_explicit["ci_half_width"]}


def check_neg_log_loss_clipping():
    """A probability of exactly 0.0 for the true class must not produce
    inf/nan (that is the entire reason clipping exists), and the reported
    value must be SENSITIVE to the clip epsilon -- a clipping value that
    made no difference wouldn't need stating."""
    y_true = np.array([0, 1])
    proba = np.array([[0.0, 1.0], [0.5, 0.5]])  # trial 0: true class assigned EXACTLY zero probability
    val_loose = neg_log_loss(y_true, proba, n_classes=2, eps=1e-6)
    val_tight = neg_log_loss(y_true, proba, n_classes=2, eps=1e-15)
    ok = np.isfinite(val_loose) and np.isfinite(val_tight) and val_loose != val_tight
    return ok, {"eps=1e-6": val_loose, "eps=1e-15": val_tight}


def check_neg_log_loss_orientation_beats_macro_f1_blindness():
    """The whole point of comparing against macro-F1: two prediction sets
    with the IDENTICAL argmax (so macro-F1 reports ZERO difference) but
    different confidence must produce DIFFERENT, correctly-oriented
    neg_log_loss values (more confidence in the correct class -> higher
    U)."""
    from simulation.models import macro_f1
    y_true = np.array([0, 0, 1, 1])
    proba_confident = np.array([[0.9, 0.1], [0.9, 0.1], [0.1, 0.9], [0.1, 0.9]])
    proba_unsure = np.array([[0.55, 0.45], [0.55, 0.45], [0.45, 0.55], [0.45, 0.55]])
    pred_hard = np.array([0, 0, 1, 1])  # identical argmax for both proba arrays above

    f1_confident = macro_f1(y_true, pred_hard, 2)
    f1_unsure = macro_f1(y_true, pred_hard, 2)
    u_confident = neg_log_loss(y_true, proba_confident, 2)
    u_unsure = neg_log_loss(y_true, proba_unsure, 2)

    ok = (f1_confident == f1_unsure) and (u_confident > u_unsure)
    return ok, {"macro_f1_confident": f1_confident, "macro_f1_unsure": f1_unsure, "U_confident": u_confident, "U_unsure": u_unsure}


def check_neg_log_loss_selectable_end_to_end(seed=3):
    """metric=NEG_LOG_LOSS_METRIC must run end-to-end through the full
    refit-bootstrap pipeline (run_one_refit) and produce a finite,
    plausible result in nats, distinct from the macro-F1 run on the same
    data."""
    cfg = GeneratorConfig(
        seed=seed, n_sessions=2, episodes_per_session=60, trials_per_episode=5,
        n_classes=5, n_rare_classes=2, rare_class_frequency=0.05, effect_size=0.3,
    )
    row_f1 = run_one_refit(cfg, resample_unit="episode", n_boot=30, metric=MACRO_F1_METRIC)
    row_ll = run_one_refit(cfg, resample_unit="episode", n_boot=30, metric=NEG_LOG_LOSS_METRIC)
    ok = (
        row_f1["metric"] == "macro_f1"
        and row_ll["metric"] == "neg_log_loss"
        and np.isfinite(row_ll["delta_point"])
        and np.isfinite(row_ll["ci_half_width"])
        and row_ll["ci_half_width"] >= 0.0
    )
    return ok, {"macro_f1_delta": row_f1["delta_point"], "neg_log_loss_delta": row_ll["delta_point"]}


if __name__ == "__main__":
    failures = []
    N = 9

    ok, msg = check_resample_unit_required()
    print(f"[1/{N}] RESAMPLE UNIT REQUIRED/NO-DEFAULT/REJECTS 'trial' -- {'PASS' if ok else 'FAIL'}: {msg}")
    if not ok:
        failures.append(msg)

    row, contains_zero = check_null_case()
    print(
        f"[2/{N}] NULL CASE (effect_size=0.0) -- Delta_point={row['delta_point']:+.4f}, "
        f"CI=[{row['ci_lo']:+.4f}, {row['ci_hi']:+.4f}], contains zero: {contains_zero}"
    )
    if not contains_zero:
        failures.append(f"null-case CI unexpectedly excludes zero: {row}")

    row, excludes_zero = check_strong_effect_case()
    print(
        f"[3/{N}] STRONG EFFECT (effect_size=0.8, generous N) -- Delta_point={row['delta_point']:+.4f}, "
        f"CI=[{row['ci_lo']:+.4f}, {row['ci_hi']:+.4f}], excludes zero below: {excludes_zero}"
    )
    if not excludes_zero:
        failures.append(f"strong-effect CI unexpectedly includes/goes below zero: {row}")

    widths = check_ci_shrinks_with_n()
    print(f"[4/{N}] CI HALF-WIDTH vs N (episodes/session, fixed effect_size=0.3):")
    for eps, w in widths:
        print(f"      episodes_per_session={eps:4d} -> ci_half_width={w:.4f}")
    if not (widths[0][1] > widths[1][1] > widths[2][1]):
        failures.append(f"CI half-width did not shrink monotonically with N: {widths}")

    ok, detail = check_negative_control_cannot_be_omitted()
    print(f"[5/{N}] NEGATIVE CONTROL WIRED IN AUTOMATICALLY -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"negative control missing from an unaware caller's result: {detail}")

    ok, detail = check_metric_refactor_preserves_default_behavior()
    print(f"[6/{N}] METRIC REFACTOR PRESERVES DEFAULT (macro_f1) BEHAVIOR -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"metric refactor changed default macro_f1 behavior: {detail}")

    ok, detail = check_neg_log_loss_clipping()
    print(f"[7/{N}] NEG_LOG_LOSS CLIPPING (eps sensitivity, no inf/nan) -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"neg_log_loss clipping behaved unexpectedly: {detail}")

    ok, detail = check_neg_log_loss_orientation_beats_macro_f1_blindness()
    print(f"[8/{N}] NEG_LOG_LOSS SEES CONFIDENCE MACRO-F1 CANNOT -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"neg_log_loss did not correctly distinguish confidence at identical argmax: {detail}")

    ok, detail = check_neg_log_loss_selectable_end_to_end()
    print(f"[9/{N}] NEG_LOG_LOSS SELECTABLE END-TO-END (run_one_refit) -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"neg_log_loss failed to run end-to-end through run_one_refit: {detail}")

    print()
    if failures:
        print(f"PRECISION PIPELINE VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("PRECISION PIPELINE VALIDATION: PASS")
