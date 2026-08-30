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

This is a validation of the PIPELINE's plumbing, not a claim about what
real data will show -- see docs/D6_SIMULATION.md and
artefacts/precision_analysis_v1.md for the actual precision findings.
"""

import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.generator import GeneratorConfig
from simulation.precision import run_one, compute_delta, bootstrap_ci_on_delta, chronological_split
from simulation.generator import generate


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


if __name__ == "__main__":
    failures = []

    ok, msg = check_resample_unit_required()
    print(f"[1/4] RESAMPLE UNIT REQUIRED/NO-DEFAULT/REJECTS 'trial' -- {'PASS' if ok else 'FAIL'}: {msg}")
    if not ok:
        failures.append(msg)

    row, contains_zero = check_null_case()
    print(
        f"[2/4] NULL CASE (effect_size=0.0) -- Delta_point={row['delta_point']:+.4f}, "
        f"CI=[{row['ci_lo']:+.4f}, {row['ci_hi']:+.4f}], contains zero: {contains_zero}"
    )
    if not contains_zero:
        failures.append(f"null-case CI unexpectedly excludes zero: {row}")

    row, excludes_zero = check_strong_effect_case()
    print(
        f"[3/4] STRONG EFFECT (effect_size=0.8, generous N) -- Delta_point={row['delta_point']:+.4f}, "
        f"CI=[{row['ci_lo']:+.4f}, {row['ci_hi']:+.4f}], excludes zero below: {excludes_zero}"
    )
    if not excludes_zero:
        failures.append(f"strong-effect CI unexpectedly includes/goes below zero: {row}")

    widths = check_ci_shrinks_with_n()
    print("[4/4] CI HALF-WIDTH vs N (episodes/session, fixed effect_size=0.3):")
    for eps, w in widths:
        print(f"      episodes_per_session={eps:4d} -> ci_half_width={w:.4f}")
    if not (widths[0][1] > widths[1][1] > widths[2][1]):
        failures.append(f"CI half-width did not shrink monotonically with N: {widths}")

    print()
    if failures:
        print(f"PRECISION PIPELINE VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("PRECISION PIPELINE VALIDATION: PASS")
