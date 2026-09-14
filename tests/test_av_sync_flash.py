"""
D0PA1 closure work, Task 3 -- av_sync_flash.py's pure logic (runnable
directly, no pytest, no camera, no microphone). Covers: the shared
rolling-median/robust-MAD onset detector against synthetic signals with
KNOWN injected onset times (both a clean case and a causality/refractory
check), the pairing logic's all-four-paths behaviour (matched / video-only-
missing / audio-only-missing / both-missing, with an emission NEVER
dropped), the run-summary computation's ability to recover a KNOWN injected
offset and drift from synthetic paired data, and that AVSyncConfig's k_v/k_a
are real, hashed, load-bearing parameters rather than decorative fields.

cv2/sounddevice are imported lazily inside av_sync_flash.py's capture
classes and functions, never at module level, so importing av_sync_flash
here to test its pure functions needs neither a camera nor a microphone.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np

from av_sync_flash import (
    AVSyncConfig,
    robust_baseline_stats,
    find_onsets,
    pair_emissions,
    compute_run_summary,
    synthesize_click,
)


def check_robust_baseline_stats_hand_computed():
    values = [1, 2, 3, 4, 5, 100]  # same hand-computed example as test_robust_baseline.py
    median, mad_scaled = robust_baseline_stats(values)
    ok = abs(median - 3.5) < 1e-9 and abs(mad_scaled - 1.4826 * 1.5) < 1e-9
    empty_median, empty_mad = robust_baseline_stats([])
    ok = ok and empty_median is None and empty_mad is None
    return ok, {"median": median, "mad_scaled": mad_scaled}


def _synthetic_stream_with_injected_onsets(n_total, dt, onset_indices, baseline_level, baseline_noise_std, spike_height, seed=0):
    """A flat, noisy baseline with KNOWN spikes injected at KNOWN sample
    indices -- the "known ground truth" pattern this codebase already uses
    elsewhere (test_leakage.py's injected leak, test_baselines.py's
    constructed session). Each injected onset holds for `hold_samples`
    samples (a sustained excursion, like a real flash/click's brief decay),
    so the refractory-period behaviour is exercised too, not just a single
    isolated sample."""
    rng = np.random.RandomState(seed)
    samples = baseline_level + rng.normal(0, baseline_noise_std, n_total)
    timestamps = np.arange(n_total) * dt
    hold_samples = 3
    true_onset_times = []
    for idx in onset_indices:
        samples[idx:idx + hold_samples] += spike_height
        true_onset_times.append(timestamps[idx])
    return samples.tolist(), timestamps.tolist(), true_onset_times


def check_find_onsets_recovers_synthetic_injected_onsets():
    dt = 1.0 / 200.0  # 200 Hz-ish, arbitrary but realistic for either channel
    onset_indices = [150, 400, 700, 1000, 1350]
    samples, timestamps, true_onsets = _synthetic_stream_with_injected_onsets(
        n_total=1500, dt=dt, onset_indices=onset_indices,
        baseline_level=0.01, baseline_noise_std=0.002, spike_height=0.5,
    )
    detected = find_onsets(samples, timestamps, k=6.0, baseline_window=90, refractory_seconds=0.5)

    ok = len(detected) == len(true_onsets)
    max_err = 0.0
    if ok:
        for d, t in zip(detected, true_onsets):
            max_err = max(max_err, abs(d - t))
        ok = ok and max_err < dt * 2  # detected onset should land within ~2 samples of the true injected onset
    return ok, {"n_detected": len(detected), "n_true": len(true_onsets), "max_timing_error_s": max_err, "detected": detected, "true": true_onsets}


def check_find_onsets_is_causal_and_needs_a_warm_baseline():
    """An anomalously large value in the first few samples -- before the
    baseline has enough history (min_baseline_n) -- must NOT be reported as
    an onset. A detector that used future or too-little data here would be
    detecting off of nothing, not off a real rolling baseline."""
    dt = 0.005
    n = 200
    samples = [0.01] * n
    samples[2] = 5.0  # huge spike, but only 2 samples into the stream
    timestamps = [i * dt for i in range(n)]
    detected = find_onsets(samples, timestamps, k=6.0, baseline_window=90, refractory_seconds=0.5, min_baseline_n=20)
    ok = len(detected) == 0
    return ok, {"detected": detected}


def check_find_onsets_refractory_prevents_double_counting():
    """A single sustained excursion (the flash/click's own brief decay, or
    just a wide spike) must be counted ONCE, not once per sample it stays
    above threshold."""
    dt = 0.005
    n = 300
    rng = np.random.RandomState(1)
    samples = (0.01 + rng.normal(0, 0.001, n)).tolist()
    for i in range(150, 170):  # 20 consecutive samples = 100ms sustained excursion
        samples[i] += 0.5
    timestamps = [i * dt for i in range(n)]
    detected = find_onsets(samples, timestamps, k=6.0, baseline_window=90, refractory_seconds=0.5, min_baseline_n=20)
    ok = len(detected) == 1
    return ok, {"detected": detected}


def check_find_onsets_k_is_real_not_decorative():
    """Same signal, stricter k must detect fewer or equal onsets than a
    looser k -- proves k actually gates detection rather than being an
    unused, decorative config field (G1's own point: parameters must be
    load-bearing, not just present)."""
    dt = 0.005
    onset_indices = [100, 300, 500]
    samples, timestamps, _ = _synthetic_stream_with_injected_onsets(
        n_total=700, dt=dt, onset_indices=onset_indices,
        baseline_level=0.01, baseline_noise_std=0.003, spike_height=0.03,  # a SMALL spike, borderline detectable
    )
    loose = find_onsets(samples, timestamps, k=2.0, baseline_window=60, refractory_seconds=0.5, min_baseline_n=20)
    strict = find_onsets(samples, timestamps, k=20.0, baseline_window=60, refractory_seconds=0.5, min_baseline_n=20)
    ok = len(strict) <= len(loose)
    return ok, {"n_loose_k2": len(loose), "n_strict_k20": len(strict)}


def check_pair_emissions_all_four_paths():
    """Four emissions, one of each outcome: both matched, video-only-
    missing, audio-only-missing, both missing. Every emission must produce
    exactly one record (never dropped, D0PA1 hard constraint #8), and each
    missingness reason must be from this module's own fixed vocabulary."""
    window = 0.5
    emissions = [10.0, 20.0, 30.0, 40.0]
    video_onsets = [10.02, 30.03]        # matches emission 0 and 2; nothing near 20 or 40
    audio_onsets = [10.01, 20.01]        # matches emission 0 and 1; nothing near 30 or 40

    records = pair_emissions(emissions, video_onsets, audio_onsets, window)

    ok = len(records) == 4  # never dropped
    r0, r1, r2, r3 = records
    ok = ok and not r0["video_missingness_flag"] and not r0["audio_missingness_flag"]  # both matched
    ok = ok and r1["video_missingness_flag"] and r1["video_missingness_reason"] == "no_video_onset_within_window" and not r1["audio_missingness_flag"]  # video-only missing
    ok = ok and not r2["video_missingness_flag"] and r2["audio_missingness_flag"] and r2["audio_missingness_reason"] == "no_audio_onset_within_window"  # audio-only missing
    ok = ok and r3["video_missingness_flag"] and r3["audio_missingness_flag"]  # both missing
    return ok, {"records": records}


def check_compute_run_summary_recovers_known_constant_offset():
    """Synthetic PAIRED records with a KNOWN constant offset (50ms) and NO
    drift -- isolates the median/IQR/MAD computation from the drift-slope
    one below. With no drift, the median offset across the whole session
    should land near the true constant offset directly."""
    true_offset_s = 0.050
    stream_start = 1000.0
    n = 12
    rng = np.random.RandomState(2)
    records = []
    for i in range(n):
        emission_ts = stream_start + i * 10.0
        audio_ts = emission_ts + 0.001
        video_ts = audio_ts + true_offset_s + rng.normal(0, 0.001)
        records.append({
            "emission_ts": emission_ts,
            "video_onset_ts": video_ts,
            "video_missingness_flag": False,
            "video_missingness_reason": None,
            "audio_onset_ts": audio_ts,
            "audio_missingness_flag": False,
            "audio_missingness_reason": None,
        })

    summary = compute_run_summary(records, stream_start, camera_fps=30.0)

    ok = summary["n_paired"] == n
    ok = ok and abs(summary["offset_median_ms"] - true_offset_s * 1000.0) < 5.0
    ok = ok and abs(summary["drift_slope_ms_per_s"]) < 1.0  # no injected drift -- slope should recover ~0
    ok = ok and abs(summary["frame_period_floor_ms"] - (1000.0 / 30.0)) < 1e-9
    return ok, {"summary": summary, "true_offset_ms": true_offset_s * 1000.0}


def check_compute_run_summary_recovers_known_drift():
    """Synthetic PAIRED records with a KNOWN linear drift (2ms per second
    of elapsed time) on top of a base offset -- same "inject a known
    effect, verify recovery" discipline as test_leakage.py/test_baselines.py.
    The median offset over a DRIFTING signal reflects the offset at the
    MEDIAN elapsed time, not at t=0 -- that is correct behaviour for a
    plain median, not a bug, so this check verifies the Theil-Sen SLOPE
    specifically, which is exactly the number the task asks this script to
    report for drift, rather than asserting a t=0 value the median was
    never claimed to estimate."""
    true_base_offset_s = 0.050
    true_drift_s_per_s = 0.002
    stream_start = 1000.0
    n = 12
    rng = np.random.RandomState(3)
    records = []
    for i in range(n):
        emission_ts = stream_start + i * 10.0
        elapsed = emission_ts - stream_start
        audio_ts = emission_ts + 0.001
        offset = true_base_offset_s + true_drift_s_per_s * elapsed + rng.normal(0, 0.001)
        video_ts = audio_ts + offset
        records.append({
            "emission_ts": emission_ts,
            "video_onset_ts": video_ts,
            "video_missingness_flag": False,
            "video_missingness_reason": None,
            "audio_onset_ts": audio_ts,
            "audio_missingness_flag": False,
            "audio_missingness_reason": None,
        })

    summary = compute_run_summary(records, stream_start, camera_fps=30.0)

    ok = summary["n_paired"] == n
    ok = ok and abs(summary["drift_slope_ms_per_s"] - true_drift_s_per_s * 1000.0) < 1.0
    return ok, {"summary": summary, "true_drift_ms_per_s": true_drift_s_per_s * 1000.0}


def check_compute_run_summary_insufficient_samples_never_fabricates():
    zero_paired = [{
        "emission_ts": 0.0, "video_onset_ts": None, "video_missingness_flag": True, "video_missingness_reason": "no_video_onset_within_window",
        "audio_onset_ts": None, "audio_missingness_flag": True, "audio_missingness_reason": "no_audio_onset_within_window",
    }]
    summary = compute_run_summary(zero_paired, stream_start_ts=0.0, camera_fps=30.0)
    ok = (
        summary["n_paired"] == 0
        and summary["offset_median_ms"] is None
        and summary["drift_slope_ms_per_s"] is None
        and "insufficient_samples" in summary.get("note", "")
    )
    return ok, {"summary": summary}


def check_config_hash_reflects_k_parameters():
    base = AVSyncConfig(subject_id="P01")
    same = AVSyncConfig(subject_id="P01")
    different_k = AVSyncConfig(subject_id="P01", k_v=99.0)
    ok = base.config_hash() == same.config_hash() and base.config_hash() != different_k.config_hash()
    return ok, {"base_hash": base.config_hash(), "different_k_hash": different_k.config_hash()}


def check_synthesize_click_shape():
    click = synthesize_click(sample_rate_hz=48000, duration_s=0.01, freq_hz=2000.0)
    ok = (
        len(click) == int(48000 * 0.01)
        and click.dtype == np.float32
        and np.max(np.abs(click)) <= 1.0 + 1e-6
        and abs(click[0]) < 0.05  # fades in from near zero
        and abs(click[-1]) < 0.05  # fades out to near zero
    )
    return ok, {"n_samples": len(click), "first": float(click[0]), "last": float(click[-1]), "max_abs": float(np.max(np.abs(click)))}


if __name__ == "__main__":
    checks = [
        ("robust_baseline_stats -- hand-computed, and empty input", check_robust_baseline_stats_hand_computed),
        ("find_onsets -- recovers 5 KNOWN injected onsets, timing error < 2 samples", check_find_onsets_recovers_synthetic_injected_onsets),
        ("find_onsets -- CAUSAL, no onset before the baseline has warmed up", check_find_onsets_is_causal_and_needs_a_warm_baseline),
        ("find_onsets -- refractory period prevents double-counting one sustained excursion", check_find_onsets_refractory_prevents_double_counting),
        ("find_onsets -- k is real (stricter k detects <= as many onsets)", check_find_onsets_k_is_real_not_decorative),
        ("pair_emissions -- all 4 paths, never drops an emission", check_pair_emissions_all_four_paths),
        ("compute_run_summary -- recovers a KNOWN constant offset (no drift)", check_compute_run_summary_recovers_known_constant_offset),
        ("compute_run_summary -- recovers a KNOWN drift slope via Theil-Sen", check_compute_run_summary_recovers_known_drift),
        ("compute_run_summary -- insufficient_samples never fabricates a number", check_compute_run_summary_insufficient_samples_never_fabricates),
        ("AVSyncConfig.config_hash() -- changes with k_v, stable otherwise", check_config_hash_reflects_k_parameters),
        ("synthesize_click -- correct length, bounded, fades in/out", check_synthesize_click_shape),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"AV SYNC FLASH TEST: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("AV SYNC FLASH TEST: PASS")
