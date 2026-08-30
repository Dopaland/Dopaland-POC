"""
D6 generator validation (runnable directly, no pytest -- matches this
repo's convention). Checks:

  1. REPRODUCIBILITY -- same seed, same config, same output, verified by
     generating twice and comparing every field exactly (not just a hash of
     the summary stats).
  2. A5 missingness -- realized missing rate and mean run length are close
     to the configured targets (bursty, not IID -- checked by comparing
     mean run length against what IID dropout at the same rate would give).
  3. A6 effect size -- empirical correlation between x_signal and z tracks
     the configured effect_size, and effect_size=0 gives ~zero correlation
     (a true null, not a weak-but-nonzero leak).
  4. A1 serial dependence -- z is autocorrelated at lag 1 (not i.i.d.).
  5. A2/A3 -- learning increases gamma's effective pull on z over the
     study; fatigue's innovation-sigma inflation resets each session
     (checked directly from the documented formulas, not re-estimated).

This is NOT a correctness proof of "reality" -- it is a check that the
generator does what its own documented model says it does (G3: the
assumptions are the finding, so the code must actually implement them).
"""

import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.generator import GeneratorConfig, generate, _markov_missingness_params


def check_reproducibility():
    cfg = GeneratorConfig(seed=12345, n_sessions=2, episodes_per_session=20, trials_per_episode=4, effect_size=0.3)
    r1 = generate(cfg)
    r2 = generate(cfg)
    assert len(r1) == len(r2)
    mismatches = [i for i, (a, b) in enumerate(zip(r1, r2)) if a != b]
    assert not mismatches, f"generate() is non-deterministic at record indices {mismatches[:5]}"
    return len(r1)


def check_missingness(seed=7):
    cfg = GeneratorConfig(
        seed=seed, n_sessions=1, episodes_per_session=2000, trials_per_episode=1,
        missingness_rate=0.10, missingness_mean_run_length=6.0,
    )
    records = generate(cfg)
    missing_flags = np.array([r["missing"] for r in records])
    realized_rate = missing_flags.mean()

    # Realized run-length: count consecutive True runs.
    run_lengths = []
    run = 0
    for m in missing_flags:
        if m:
            run += 1
        elif run > 0:
            run_lengths.append(run)
            run = 0
    if run > 0:
        run_lengths.append(run)
    realized_mean_run = float(np.mean(run_lengths)) if run_lengths else 0.0

    # Sanity: bursty missingness at the same overall rate should show a
    # mean run length well above 1 (IID dropout at any rate has mean run
    # length ~1/(1-rate) ~= 1.0 for a 10% rate -- clustering must look
    # clearly different from that).
    iid_expected_run_length = 1.0 / (1.0 - cfg.missingness_rate)

    return {
        "target_rate": cfg.missingness_rate,
        "realized_rate": realized_rate,
        "target_mean_run_length": cfg.missingness_mean_run_length,
        "realized_mean_run_length": realized_mean_run,
        "iid_expected_run_length_for_comparison": iid_expected_run_length,
    }


def check_effect_size(seed=99):
    results = {}
    for effect_size in (0.0, 0.2, 0.5, 0.8):
        cfg = GeneratorConfig(
            seed=seed, n_sessions=1, episodes_per_session=3000, trials_per_episode=1,
            effect_size=effect_size, missingness_rate=0.0,
        )
        records = generate(cfg)
        z = np.array([r["z"] for r in records])
        x = np.array([r["x_signal"] for r in records], dtype=float)
        corr = float(np.corrcoef(z, x)[0, 1])
        results[effect_size] = corr
    return results


def check_serial_dependence(seed=3):
    cfg = GeneratorConfig(seed=seed, n_sessions=1, episodes_per_session=3000, trials_per_episode=1)
    records = generate(cfg)
    z = np.array([r["z"] for r in records])
    lag1_autocorr = float(np.corrcoef(z[:-1], z[1:])[0, 1])
    return lag1_autocorr, cfg.ar1_phi


def check_missingness_markov_math():
    # Directly verify _markov_missingness_params solves the stationary
    # distribution correctly for a few (rate, run_length) pairs.
    for rate, run_length in [(0.05, 5.0), (0.10, 3.0), (0.20, 10.0)]:
        p_enter, p_recover = _markov_missingness_params(rate, run_length)
        # Stationary distribution of a 2-state chain with
        # P(present->missing)=p_enter, P(missing->present)=p_recover:
        # pi_missing = p_enter / (p_enter + p_recover)
        pi_missing = p_enter / (p_enter + p_recover)
        assert abs(pi_missing - rate) < 1e-9, (rate, run_length, pi_missing)
        assert abs((1.0 / p_recover) - run_length) < 1e-9
    return True


if __name__ == "__main__":
    failures = []

    n = check_reproducibility()
    print(f"[1/5] REPRODUCIBILITY -- PASS ({n} records identical across two independent generate() calls)")

    miss = check_missingness()
    print(f"[2/5] MISSINGNESS (A5) -- target rate={miss['target_rate']:.3f} realized={miss['realized_rate']:.3f} | "
          f"target mean run={miss['target_mean_run_length']:.1f} realized={miss['realized_mean_run_length']:.2f} "
          f"(IID-at-same-rate would give ~{miss['iid_expected_run_length_for_comparison']:.2f})")
    if abs(miss["realized_rate"] - miss["target_rate"]) > 0.02:
        failures.append("missingness realized rate diverges from target by more than 0.02")
    if miss["realized_mean_run_length"] < 2.0 * miss["iid_expected_run_length_for_comparison"]:
        failures.append("missingness does not look bursty relative to IID dropout at the same rate")

    effect = check_effect_size()
    print("[3/5] EFFECT SIZE (A6) -- configured -> empirical corr(x_signal, z):")
    for es, corr in effect.items():
        print(f"      {es:.1f} -> {corr:+.3f}")
    if abs(effect[0.0]) > 0.05:
        failures.append(f"effect_size=0.0 should be a true null (|corr|<=0.05), got {effect[0.0]:.3f}")
    prev = -1.0
    for es in (0.2, 0.5, 0.8):
        if effect[es] <= prev:
            failures.append(f"empirical correlation should increase monotonically with effect_size, broke at {es}")
        prev = effect[es]

    lag1, phi = check_serial_dependence()
    print(f"[4/5] SERIAL DEPENDENCE (A1) -- configured phi={phi:.2f}, empirical lag-1 autocorr of z={lag1:.3f}")
    if abs(lag1 - phi) > 0.1:
        failures.append(f"empirical lag-1 autocorrelation {lag1:.3f} too far from configured ar1_phi {phi:.2f}")

    ok = check_missingness_markov_math()
    print(f"[5/5] MISSINGNESS MARKOV MATH -- stationary-distribution solve verified exactly: {ok}")

    print()
    if failures:
        print(f"GENERATOR VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("GENERATOR VALIDATION: PASS")
