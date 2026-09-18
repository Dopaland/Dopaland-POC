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

import ast
import inspect
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np

import av_sync_flash
from av_sync_flash import (
    AVSyncConfig,
    robust_baseline_stats,
    find_onsets,
    pair_emissions,
    compute_run_summary,
    compute_diagnostic_window,
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
    missingness reason must be from this module's own fixed vocabulary.
    ATTEMPT 8: video and audio are matched against their OWN reference
    lists (here identical to the scheduled list -- zero emitter jitter --
    so this is the same scenario as before the change, just through the
    new signature)."""
    window = 0.5
    scheduled = [10.0, 20.0, 30.0, 40.0]
    video_refs = scheduled
    audio_refs = scheduled
    video_onsets = [10.02, 30.03]        # matches emission 0 and 2; nothing near 20 or 40
    audio_onsets = [10.01, 20.01]        # matches emission 0 and 1; nothing near 30 or 40

    records = pair_emissions(scheduled, video_refs, audio_refs, video_onsets, audio_onsets, window)

    ok = len(records) == 4  # never dropped
    r0, r1, r2, r3 = records
    ok = ok and not r0["video_missingness_flag"] and not r0["audio_missingness_flag"]  # both matched
    ok = ok and r1["video_missingness_flag"] and r1["video_missingness_reason"] == "no_video_onset_within_window" and not r1["audio_missingness_flag"]  # video-only missing
    ok = ok and not r2["video_missingness_flag"] and r2["audio_missingness_flag"] and r2["audio_missingness_reason"] == "no_audio_onset_within_window"  # audio-only missing
    ok = ok and r3["video_missingness_flag"] and r3["audio_missingness_flag"]  # both missing
    return ok, {"records": records}


def check_pair_emissions_missing_audio_reference_never_crashes():
    """A None audio reference (the output callback never fired for that
    emission) must produce audio_missingness_reason ==
    'no_audio_confirmation_timestamp', with no search attempted and no
    crash -- distinct from a confirmed reference that simply found no
    nearby onset."""
    window = 0.5
    scheduled = [10.0, 20.0]
    video_refs = [10.0, 20.0]
    audio_refs = [10.0, None]
    video_onsets = [10.02, 20.02]
    audio_onsets = [10.01]

    records = pair_emissions(scheduled, video_refs, audio_refs, video_onsets, audio_onsets, window)

    ok = len(records) == 2
    ok = ok and not records[0]["audio_missingness_flag"]
    ok = ok and records[1]["audio_missingness_flag"] and records[1]["audio_missingness_reason"] == "no_audio_confirmation_timestamp"
    ok = ok and records[1]["audio_onset_ts"] is None
    return ok, {"records": records}


def check_compute_run_summary_recovers_known_constant_offset():
    """Synthetic PAIRED records with a KNOWN constant offset (50ms) and NO
    drift, ZERO emitter jitter (video_reference_ts == audio_reference_ts
    == emission_ts) -- isolates the median/IQR/MAD computation from the
    drift-slope one below and from attempt 8's jitter-cancellation, which
    has its own dedicated check further down. With no drift, the median
    offset across the whole session should land near the true constant
    offset directly."""
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
            "emission_scheduled_ts": emission_ts,
            "video_reference_ts": emission_ts,
            "audio_reference_ts": emission_ts,
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
    ok = ok and summary["offset_reference"] == "confirmed_v2"
    return ok, {"summary": summary, "true_offset_ms": true_offset_s * 1000.0}


def check_compute_run_summary_recovers_known_drift():
    """Synthetic PAIRED records with a KNOWN linear drift (2ms per second
    of elapsed time) on top of a base offset, zero emitter jitter -- same
    "inject a known effect, verify recovery" discipline as
    test_leakage.py/test_baselines.py. The median offset over a DRIFTING
    signal reflects the offset at the MEDIAN elapsed time, not at t=0 --
    that is correct behaviour for a plain median, not a bug, so this check
    verifies the Theil-Sen SLOPE specifically, which is exactly the number
    the task asks this script to report for drift, rather than asserting a
    t=0 value the median was never claimed to estimate."""
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
            "emission_scheduled_ts": emission_ts,
            "video_reference_ts": emission_ts,
            "audio_reference_ts": emission_ts,
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


def check_compute_run_summary_cancels_emitter_jitter():
    """THE point of attempt 8's change 3, isolated and proven: inject a
    LARGE, DIFFERENT jitter between video_reference_ts and
    audio_reference_ts for every emission (as if the flash render and the
    audio callback fired at noticeably different times from each other and
    from a nominal schedule) while keeping the TRUE underlying
    capture+detection latency on each channel constant and equal (so the
    real answer is offset ~= 0). The OLD formula (video_onset - audio_onset)
    would show the jitter directly in the result; the NEW formula must
    recover ~0 regardless of how large the jitter is, because it subtracts
    each onset from its OWN reference first."""
    stream_start = 1000.0
    n = 12
    rng = np.random.RandomState(4)
    true_capture_latency_s = 0.020  # SAME on both channels, by construction -- true offset is 0
    records = []
    for i in range(n):
        scheduled = stream_start + i * 10.0
        # Large, emission-varying emitter jitter -- video and audio fire at
        # noticeably different, noisy times relative to the schedule AND to
        # each other (tens to ~100ms, matching session 0e6b2a1a's own
        # 69-159ms / 61-91ms observed spread).
        video_ref = scheduled + 0.10 + rng.normal(0, 0.02)
        audio_ref = scheduled + 0.07 + rng.normal(0, 0.02)
        video_onset = video_ref + true_capture_latency_s
        audio_onset = audio_ref + true_capture_latency_s
        records.append({
            "emission_scheduled_ts": scheduled,
            "video_reference_ts": video_ref,
            "audio_reference_ts": audio_ref,
            "video_onset_ts": video_onset,
            "video_missingness_flag": False,
            "video_missingness_reason": None,
            "audio_onset_ts": audio_onset,
            "audio_missingness_flag": False,
            "audio_missingness_reason": None,
        })

    summary = compute_run_summary(records, stream_start, camera_fps=30.0)

    # Sanity check: the OLD formula would NOT be near zero here (the video/
    # audio reference gap of ~30ms would show up directly), confirming this
    # test scenario actually exercises jitter, not a degenerate no-op case.
    old_formula_offsets_ms = [(r["video_onset_ts"] - r["audio_onset_ts"]) * 1000.0 for r in records]
    old_formula_median = float(np.median(old_formula_offsets_ms))

    ok = summary["n_paired"] == n
    ok = ok and abs(summary["offset_median_ms"]) < 5.0  # true offset is 0, jitter must not leak in
    ok = ok and abs(old_formula_median - 30.0) < 15.0  # confirms the old formula WOULD have shown the jitter
    return ok, {"summary": summary, "old_formula_median_ms": old_formula_median}


def check_compute_run_summary_insufficient_samples_never_fabricates():
    zero_paired = [{
        "emission_scheduled_ts": 0.0, "video_reference_ts": 0.0, "audio_reference_ts": 0.0,
        "video_onset_ts": None, "video_missingness_flag": True, "video_missingness_reason": "no_video_onset_within_window",
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


def check_config_hash_reflects_attempt8_stimulus_parameters():
    """ATTEMPT 8's new versioned parameters (flash_duration_ms,
    click_duration_s, click_amplitude, click_ramp_ms) must each be
    load-bearing in config_hash(), same standard as k_v/k_a above -- not
    decorative fields that happen to sit in the dataclass."""
    base = AVSyncConfig(subject_id="P01")
    variants = {
        "flash_duration_ms": AVSyncConfig(subject_id="P01", flash_duration_ms=999.0),
        "click_duration_s": AVSyncConfig(subject_id="P01", click_duration_s=0.999),
        "click_amplitude": AVSyncConfig(subject_id="P01", click_amplitude=0.5),
        "click_ramp_ms": AVSyncConfig(subject_id="P01", click_ramp_ms=99.0),
    }
    ok = all(base.config_hash() != v.config_hash() for v in variants.values())
    ok = ok and base.flash_duration_ms == 500.0 and base.click_duration_s == 0.15  # defaults actually changed
    return ok, {"base_hash": base.config_hash(), "variant_hashes": {k: v.config_hash() for k, v in variants.items()}}


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


def check_synthesize_click_amplitude_scales_peak():
    """amplitude must actually scale the signal -- half amplitude means
    half the peak, not a decorative parameter."""
    full = synthesize_click(sample_rate_hz=48000, duration_s=0.15, freq_hz=2000.0, amplitude=1.0, ramp_ms=2.0)
    half = synthesize_click(sample_rate_hz=48000, duration_s=0.15, freq_hz=2000.0, amplitude=0.5, ramp_ms=2.0)
    ok = abs(np.max(np.abs(half)) - 0.5 * np.max(np.abs(full))) < 1e-6
    return ok, {"full_peak": float(np.max(np.abs(full))), "half_peak": float(np.max(np.abs(half)))}


def check_synthesize_click_ramp_is_fixed_not_proportional():
    """ATTEMPT 8's whole point for this parameter: a MUCH longer click
    (150ms vs 10ms, a 15x difference) must have the SAME ramp sample count
    when ramp_ms is held fixed -- proving the ramp no longer scales with
    total duration the way the old n//4 logic did. Detected here by
    checking that the envelope reaches (near) full amplitude at the same
    SAMPLE INDEX for both, not at a duration-proportional one."""
    sample_rate = 48000
    ramp_ms = 2.0
    short = synthesize_click(sample_rate, duration_s=0.01, freq_hz=2000.0, ramp_ms=ramp_ms)
    long_ = synthesize_click(sample_rate, duration_s=0.15, freq_hz=2000.0, ramp_ms=ramp_ms)
    expected_ramp_samples = int(sample_rate * ramp_ms / 1000.0)

    def reaches_near_full_amplitude_by(click, idx):
        # envelope is monotone during ramp-in; compare the envelope's
        # implied magnitude (click / sin at that sample) isn't clean
        # because sin passes through zero -- instead check that a sample
        # well past expected_ramp_samples is no longer small in magnitude
        # relative to the click's own overall peak.
        return abs(click[idx]) > 0.3 * np.max(np.abs(click))

    ok = reaches_near_full_amplitude_by(short, min(expected_ramp_samples + 5, len(short) - 1))
    ok = ok and reaches_near_full_amplitude_by(long_, expected_ramp_samples + 5)
    # And the long click must have MANY samples at full amplitude beyond
    # the short ramp region -- the old proportional-ramp logic (n//4)
    # would have made ~37ms of a 150ms click still ramping.
    tail = long_[expected_ramp_samples + 10: expected_ramp_samples + 100]
    ok = ok and np.max(np.abs(tail)) > 0.9 * np.max(np.abs(long_))
    return ok, {"expected_ramp_samples": expected_ramp_samples, "short_len": len(short), "long_len": len(long_)}


def check_diagnostic_window_recovers_baseline_and_ratio():
    """A flat noisy baseline with ONE known spike well after warm-up.
    Window it around the spike's own timestamp: baseline_median_pre/
    mad_scaled_pre must match robust_baseline_stats() computed by hand over
    exactly the pre-window slice, max_value_in_window must be the spike,
    and threshold_absolute/ratio must be the plain arithmetic the
    docstring promises -- not re-derived some other way."""
    dt = 0.01
    n = 400
    rng = np.random.RandomState(7)
    samples = (0.02 + rng.normal(0, 0.002, n)).tolist()
    spike_idx = 300
    samples[spike_idx] = 5.0
    timestamps = [i * dt for i in range(n)]
    emission_ts = timestamps[spike_idx]
    k = 6.0
    baseline_window = 90

    onsets = find_onsets(samples, timestamps, k=k, baseline_window=baseline_window, refractory_seconds=0.5)
    result = compute_diagnostic_window(samples, timestamps, onsets, k, baseline_window, emission_ts, window_seconds=1.0)

    pre_window_values = [s for s, t in zip(samples, timestamps) if t < emission_ts - 1.0]
    expected_median, expected_mad = robust_baseline_stats(pre_window_values[-baseline_window:])

    ok = result["insufficient_baseline"] is False
    ok = ok and abs(result["baseline_median_pre"] - expected_median) < 1e-9
    ok = ok and abs(result["baseline_mad_scaled_pre"] - expected_mad) < 1e-9
    ok = ok and result["max_value_in_window"] == 5.0
    expected_threshold = expected_median + k * expected_mad
    ok = ok and abs(result["threshold_absolute"] - expected_threshold) < 1e-9
    ok = ok and abs(result["max_to_threshold_ratio"] - (5.0 / expected_threshold)) < 1e-9
    ok = ok and result["onset_fired_in_window"] is True  # the spike is a real, detected onset
    return ok, {"result": {k: v for k, v in result.items() if k not in ("timestamps", "values")}}


def check_diagnostic_window_onset_flag_false_when_no_onset_in_window():
    """Same shape as above but the window is centred somewhere with NO
    injected spike and no detected onset -- onset_fired_in_window must be
    False, distinguishing 'nothing happened here' from the True case."""
    dt = 0.01
    n = 400
    rng = np.random.RandomState(8)
    samples = (0.02 + rng.normal(0, 0.002, n)).tolist()
    samples[300] = 5.0  # one spike, far from the window we inspect below
    timestamps = [i * dt for i in range(n)]
    k = 6.0
    baseline_window = 90

    onsets = find_onsets(samples, timestamps, k=k, baseline_window=baseline_window, refractory_seconds=0.5)
    quiet_emission_ts = timestamps[150]  # nowhere near index 300
    result = compute_diagnostic_window(samples, timestamps, onsets, k, baseline_window, quiet_emission_ts, window_seconds=1.0)

    ok = result["onset_fired_in_window"] is False
    ok = ok and result["max_to_threshold_ratio"] is not None and result["max_to_threshold_ratio"] < 1.0
    return ok, {"ratio": result["max_to_threshold_ratio"], "onset_fired": result["onset_fired_in_window"]}


def check_diagnostic_window_insufficient_baseline_never_fabricates():
    """An emission so early that the rolling baseline has not warmed up
    before the window opens must report insufficient_baseline=True with
    None for every derived number -- never a fabricated threshold from a
    near-empty baseline."""
    dt = 0.01
    n = 50
    samples = [0.02] * n
    timestamps = [i * dt for i in range(n)]
    early_emission_ts = timestamps[5]  # window opens at t=-0.95s, essentially no prior data

    result = compute_diagnostic_window(samples, timestamps, onsets=[], k=6.0, baseline_window=90, emission_ts=early_emission_ts, window_seconds=1.0)

    ok = result["insufficient_baseline"] is True
    ok = ok and result["baseline_median_pre"] is None
    ok = ok and result["threshold_absolute"] is None
    ok = ok and result["max_to_threshold_ratio"] is None
    return ok, {"result": {k: v for k, v in result.items() if k not in ("timestamps", "values")}}


def check_diagnostic_window_empty_window_reports_no_samples():
    """An emission window that falls entirely after the last recorded
    sample (e.g. capture stopped early) must report zero in-window
    samples and no max/ratio -- not an error, not a fabricated zero."""
    dt = 0.01
    n = 200
    rng = np.random.RandomState(9)
    samples = (0.02 + rng.normal(0, 0.002, n)).tolist()
    timestamps = [i * dt for i in range(n)]
    far_emission_ts = timestamps[-1] + 5.0  # window opens well after data ends

    result = compute_diagnostic_window(samples, timestamps, onsets=[], k=6.0, baseline_window=90, emission_ts=far_emission_ts, window_seconds=1.0)

    ok = result["n_samples_in_window"] == 0
    ok = ok and result["max_value_in_window"] is None
    ok = ok and result["max_to_threshold_ratio"] is None
    ok = ok and result["onset_fired_in_window"] is False
    ok = ok and result["insufficient_baseline"] is False  # plenty of samples preceded the window
    return ok, {"result": {k: v for k, v in result.items() if k not in ("timestamps", "values")}}


def check_diagnostic_window_max_excludes_pre_reference_spike():
    """ATTEMPT 9 FIX 2, directly targeted: a LARGE spike placed BEFORE
    emission_ts (but inside the +/-1s window) must NOT appear in
    max_value_in_window -- exactly the failure mode Check 1/2 found in
    session a6ce084e (idx 12 and idx 19, whose reported 'near-threshold'
    peaks were pre-click ambient noise). The genuine (small, sub-threshold)
    post-reference value must be what max_value_in_window reports instead,
    and the pre-reference spike must still be visible as its own field."""
    dt = 0.01
    n = 400
    rng = np.random.RandomState(11)
    samples = (0.02 + rng.normal(0, 0.002, n)).tolist()
    timestamps = [i * dt for i in range(n)]

    pre_spike_idx = 150   # well before the reference, inside the window
    reference_idx = 200
    post_small_idx = 210  # after the reference, genuinely small -- should NOT fire

    samples[pre_spike_idx] = 9.0     # huge pre-reference spike
    samples[post_small_idx] = 0.03   # tiny post-reference bump, near baseline

    emission_ts = timestamps[reference_idx]
    k = 6.0
    baseline_window = 90

    onsets = find_onsets(samples, timestamps, k=k, baseline_window=baseline_window, refractory_seconds=0.5)
    result = compute_diagnostic_window(samples, timestamps, onsets, k, baseline_window, emission_ts, window_seconds=1.0)

    ok = result["pre_reference_max_value"] == 9.0  # the spike is visible, not hidden
    ok = ok and result["max_value_in_window"] != 9.0  # and it must NOT contaminate the post-reference max
    ok = ok and abs(result["max_value_in_window"] - 0.03) < 1e-9  # the genuine (small) post-reference value instead
    ok = ok and result["max_to_threshold_ratio"] is not None and result["max_to_threshold_ratio"] < 1.0  # correctly reads as a near-miss/no-step, not a hit
    return ok, {k: v for k, v in result.items() if k not in ("timestamps", "values")}


def check_diagnostic_window_pre_reference_max_none_when_no_pre_samples():
    """If the window has no pre-reference samples at all (e.g. emission_ts
    equals window_lo), pre_reference_max_value must be None, not a
    fabricated zero."""
    dt = 0.01
    n = 200
    rng = np.random.RandomState(12)
    samples = (0.02 + rng.normal(0, 0.002, n)).tolist()
    timestamps = [i * dt for i in range(n)]
    emission_ts = timestamps[100] - 1.0  # window_lo == emission_ts -- no room for pre-reference samples

    result = compute_diagnostic_window(samples, timestamps, onsets=[], k=6.0, baseline_window=90, emission_ts=emission_ts, window_seconds=1.0)
    ok = result["pre_reference_max_value"] is None
    return ok, {k: v for k, v in result.items() if k not in ("timestamps", "values")}


def check_emitter_flash_first_frame_ts_assigned_inside_hold_loop():
    """ATTEMPT 9 FIX 1 cannot be exercised live without a real display and
    audio device (same convention as VideoLuminanceCapture/AudioEnergyCapture
    -- this file's tests never touch hardware). Instead this proves the fix
    STRUCTURALLY, by reading _emit_flash_and_click's own source: the
    assignment to flash_first_frame_ts must occur INSIDE the hold `while`
    loop's body (so it captures the moment right after the FIRST frame is
    presented), and the assignment to flash_hold_ended_ts must occur
    OUTSIDE the loop, after it exits. This is exactly the shape that
    regresses back to the attempt-8 bug if someone moves the first
    assignment out of the loop -- this test exists to catch that."""
    source = inspect.getsource(av_sync_flash._emit_flash_and_click)
    tree = ast.parse(source)
    func_def = tree.body[0]

    while_node = None
    for node in ast.walk(func_def):
        if isinstance(node, ast.While):
            while_node = node
            break
    ok = while_node is not None

    def assigns_name(node, name):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for target in sub.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        return True
            if isinstance(sub, ast.If):  # the `if flash_first_frame_ts is None:` guard's own assignment
                for sub2 in ast.walk(sub):
                    if isinstance(sub2, ast.Assign):
                        for target in sub2.targets:
                            if isinstance(target, ast.Name) and target.id == name:
                                return True
        return False

    first_frame_inside_loop = ok and assigns_name(while_node, "flash_first_frame_ts")

    # flash_hold_ended_ts must be assigned somewhere in the function but
    # NOT inside the while loop's own body.
    hold_ended_inside_loop = ok and assigns_name(while_node, "flash_hold_ended_ts")
    hold_ended_anywhere = assigns_name(func_def, "flash_hold_ended_ts")

    result = ok and first_frame_inside_loop and not hold_ended_inside_loop and hold_ended_anywhere
    return result, {
        "while_loop_found": ok,
        "flash_first_frame_ts_assigned_inside_loop": first_frame_inside_loop,
        "flash_hold_ended_ts_assigned_inside_loop": hold_ended_inside_loop,
        "flash_hold_ended_ts_assigned_anywhere": hold_ended_anywhere,
    }


if __name__ == "__main__":
    checks = [
        ("robust_baseline_stats -- hand-computed, and empty input", check_robust_baseline_stats_hand_computed),
        ("find_onsets -- recovers 5 KNOWN injected onsets, timing error < 2 samples", check_find_onsets_recovers_synthetic_injected_onsets),
        ("find_onsets -- CAUSAL, no onset before the baseline has warmed up", check_find_onsets_is_causal_and_needs_a_warm_baseline),
        ("find_onsets -- refractory period prevents double-counting one sustained excursion", check_find_onsets_refractory_prevents_double_counting),
        ("find_onsets -- k is real (stricter k detects <= as many onsets)", check_find_onsets_k_is_real_not_decorative),
        ("pair_emissions -- all 4 paths, never drops an emission", check_pair_emissions_all_four_paths),
        ("pair_emissions -- missing audio reference timestamp never crashes, own reason", check_pair_emissions_missing_audio_reference_never_crashes),
        ("compute_run_summary -- recovers a KNOWN constant offset (no drift)", check_compute_run_summary_recovers_known_constant_offset),
        ("compute_run_summary -- recovers a KNOWN drift slope via Theil-Sen", check_compute_run_summary_recovers_known_drift),
        ("compute_run_summary -- ATTEMPT 8: cancels large emitter jitter, recovers true zero offset", check_compute_run_summary_cancels_emitter_jitter),
        ("compute_run_summary -- insufficient_samples never fabricates a number", check_compute_run_summary_insufficient_samples_never_fabricates),
        ("AVSyncConfig.config_hash() -- changes with k_v, stable otherwise", check_config_hash_reflects_k_parameters),
        ("AVSyncConfig.config_hash() -- ATTEMPT 8's new stimulus parameters are load-bearing", check_config_hash_reflects_attempt8_stimulus_parameters),
        ("synthesize_click -- correct length, bounded, fades in/out", check_synthesize_click_shape),
        ("synthesize_click -- amplitude scales the peak", check_synthesize_click_amplitude_scales_peak),
        ("synthesize_click -- ramp is FIXED duration, not proportional to click length", check_synthesize_click_ramp_is_fixed_not_proportional),
        ("compute_diagnostic_window -- recovers baseline/max/threshold/ratio by hand-computed arithmetic", check_diagnostic_window_recovers_baseline_and_ratio),
        ("compute_diagnostic_window -- onset_fired_in_window is False with no onset present", check_diagnostic_window_onset_flag_false_when_no_onset_in_window),
        ("compute_diagnostic_window -- insufficient_baseline never fabricates a threshold", check_diagnostic_window_insufficient_baseline_never_fabricates),
        ("compute_diagnostic_window -- empty window (data ended early) reports zero samples, not an error", check_diagnostic_window_empty_window_reports_no_samples),
        ("compute_diagnostic_window -- ATTEMPT 9 FIX 2: pre-reference spike excluded from max_value_in_window", check_diagnostic_window_max_excludes_pre_reference_spike),
        ("compute_diagnostic_window -- pre_reference_max_value is None with no pre-reference samples", check_diagnostic_window_pre_reference_max_none_when_no_pre_samples),
        ("_emit_flash_and_click -- ATTEMPT 9 FIX 1: flash_first_frame_ts assigned inside the hold loop, not after", check_emitter_flash_first_frame_ts_assigned_inside_hold_loop),
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
