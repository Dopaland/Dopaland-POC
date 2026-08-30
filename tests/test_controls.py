"""
D0PA1 controls validation (runnable directly, no pytest). Covers the pure-
computation pieces of controls/null_input.py and controls/negative_control.py
that do NOT require a camera -- compute_dispersion, ExcursionDetector,
config hashing, and the negative-control generator/wiring. The camera-loop
orchestration itself cannot be exercised without a real webcam and a human
operator (see controls/null_input.py's run() and docs/CONTROLS.md) and is
therefore NOT covered here -- stated explicitly, not silently skipped.
"""

import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from controls.null_input import compute_dispersion, ExcursionDetector, NullInputConfig, ZERO_DISPERSION_EPSILON
from controls.negative_control import generate_negative_control, NegativeControlConfig


def check_dispersion_normal():
    rng = np.random.default_rng(0)
    values = rng.normal(loc=0.0, scale=0.02, size=500).tolist()
    d = compute_dispersion(values)
    ok = d["std"] is not None and abs(d["std"] - 0.02) < 0.005 and not d["zero_dispersion"]
    return ok, d


def check_dispersion_zero():
    # A near-constant signal (V_pd-style: real dispersion ~0.0001, well
    # under the numerical-safety epsilon here for a clean test) -- must be
    # flagged, never divided into.
    values = ([1e-10] * 500)
    d = compute_dispersion(values)
    ok = d["zero_dispersion"] is True and d["zero_dispersion_reason"] == "zero_dispersion"
    return ok, d


def check_dispersion_insufficient():
    d = compute_dispersion([0.5])
    ok = d["std"] is None and d["zero_dispersion_reason"] == "insufficient_samples"
    return ok, d


def check_excursion_sustained_confirmed():
    det = ExcursionDetector("test", z_threshold=2.0, min_duration_seconds=1.0)
    # z=3.0 (above threshold) held from t=0 to t=1.5s, sampled every 0.1s
    t = 0.0
    while t <= 1.5:
        det.update(3.0, t)
        t += 0.1
    return det.confirmed_count == 1, det.confirmed_count


def check_excursion_brief_spike_not_confirmed():
    det = ExcursionDetector("test", z_threshold=2.0, min_duration_seconds=1.0)
    # z=3.0 held for only 0.3s -- below the 1.0s sustain requirement
    t = 0.0
    while t <= 0.3:
        det.update(3.0, t)
        t += 0.1
    det.update(0.1, 0.4)  # drops back below threshold
    return det.confirmed_count == 0, det.confirmed_count


def check_excursion_gap_breaks_timer():
    det = ExcursionDetector("test", z_threshold=2.0, min_duration_seconds=1.0)
    t = 0.0
    while t <= 0.6:
        det.update(3.0, t)
        t += 0.1
    det.update(None, 0.7)  # a tracking-loss gap -- must end the in-progress timer (documented design choice)
    t = 0.8
    while t <= 1.3:  # only ~0.5s more above threshold after the gap -- should NOT reach 1.0s sustained
        det.update(3.0, t)
        t += 0.1
    return det.confirmed_count == 0, det.confirmed_count


def check_excursion_not_double_counted():
    det = ExcursionDetector("test", z_threshold=2.0, min_duration_seconds=1.0)
    t = 0.0
    while t <= 3.0:  # sustained for 3s -- one long excursion, not three
        det.update(3.0, t)
        t += 0.1
    return det.confirmed_count == 1, det.confirmed_count


def check_config_hash_reproducible_and_sensitive():
    c1 = NullInputConfig(subject_id="P01")
    c2 = NullInputConfig(subject_id="P01")
    c3 = NullInputConfig(subject_id="P01", excursion_z_threshold=2.5)
    same = c1.config_hash() == c2.config_hash()
    different = c1.config_hash() != c3.config_hash()
    return same and different, (c1.config_hash(), c2.config_hash(), c3.config_hash())


def check_negative_control_reproducible():
    cfg = NegativeControlConfig(seed=5, n_samples=500, sampling_rate_hz=25.0, ar1_phi=0.5)
    r1 = generate_negative_control(cfg)
    r2 = generate_negative_control(cfg)
    return np.array_equal(r1, r2), len(r1)


def check_negative_control_carries_no_information():
    """The negative control must not predict a synthetic 'outcome' better
    than chance -- generated independently of any task/class label by
    construction. Checked via correlation with an UNRELATED random label
    sequence: should be indistinguishable from zero."""
    cfg = NegativeControlConfig(seed=11, n_samples=5000, sampling_rate_hz=25.0, ar1_phi=0.6)
    signal = generate_negative_control(cfg)
    rng = np.random.default_rng(999)
    unrelated_outcome = rng.normal(size=len(signal))
    corr = float(np.corrcoef(signal, unrelated_outcome)[0, 1])
    return abs(corr) < 0.05, corr


if __name__ == "__main__":
    failures = []
    checks = [
        ("dispersion: normal signal", check_dispersion_normal),
        ("dispersion: zero_dispersion flag fires", check_dispersion_zero),
        ("dispersion: insufficient samples", check_dispersion_insufficient),
        ("excursion: sustained -> confirmed", check_excursion_sustained_confirmed),
        ("excursion: brief spike -> not confirmed", check_excursion_brief_spike_not_confirmed),
        ("excursion: gap breaks timer (documented choice)", check_excursion_gap_breaks_timer),
        ("excursion: long excursion counted once", check_excursion_not_double_counted),
        ("config_hash: reproducible + sensitive to change", check_config_hash_reproducible_and_sensitive),
        ("negative control: reproducible", check_negative_control_reproducible),
        ("negative control: carries no information", check_negative_control_carries_no_information),
    ]
    for i, (name, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {name} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(name)

    print()
    if failures:
        print(f"CONTROLS VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("CONTROLS VALIDATION: PASS")
    print("\nNOTE: this covers the pure-computation pieces only. The camera-loop")
    print("orchestration in controls/null_input.py's run() requires a real webcam")
    print("and human operator and is NOT exercised by this test -- see docs/CONTROLS.md.")
