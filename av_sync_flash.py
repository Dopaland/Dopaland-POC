"""
av_sync_flash.py -- D0PA1 closure work, Task 3: measures the offset, spread
and drift between the audio stream and the video stream, using a global
luminance flash + audio click as the physical event.

WHY THE STIMULUS CHANGED, NOT THE DETECTOR: five prior attempts (see
docs/AUDIO_ACQUISITION.md Sec 4 / Sec 7) used a hand clap plus frame-to-frame
grayscale motion detection on the video side, and failed every time --
loosened, the motion heuristic false-matched on ordinary movement; tightened,
it found 0-3 events across a whole session. A clap's video signature (a hand
moving against a mostly-static face-and-background scene) is small, local,
and easily confused with everything else that moves. A full-screen luminance
step is none of those things: it is global, large, and -- in an otherwise
static scene -- has no competing cause. This script keeps the SAME kind of
causal, rolling-median-baseline detector on both sides (the mechanism does
not need to be more clever); only the stimulus changed.

CRITICAL, stated once so it cannot be missed: the video onset detector reads
mean luminance from the RAW GRAYSCALE frame, computed BEFORE CLAHE.
apply_clahe() runs at stage1_step4_vectors.py:425 (re-checked against the
live file at the time this script was written, not assumed from an older
line number) on every frame of the validated capture pipeline; CLAHE
normalises LOCAL contrast and would actively suppress a GLOBAL luminance
step, which is exactly why this script never calls it. This script does not
import or reuse anything from the validated path (G5) -- it opens its own,
independent cv2.VideoCapture and does its own grayscale conversion.

NOT A STROBE: the flash is a single one-shot pulse (config.flash_duration_ms
of held white, then reverts) inside one emission event, never a repeating
on/off pattern -- so it has no "rate" in the photosensitive-epilepsy sense
at all. Events themselves are spaced config.event_interval_seconds apart
(default 30s = 0.033 Hz), far below the 3-60 Hz band the task's own
instruction names. Both are true by construction, not by a runtime check.

ATTEMPT 8 -- STIMULUS LENGTHENED, OFFSET REFERENCE CHANGED: the diagnostic
run (session 0e6b2a1a) found the flash's prior ~3-rendered-frames duration
was short enough, against a ~33ms camera exposure period, that whether the
flash landed inside a captured exposure was close to a coin flip -- the
most plausible mechanical explanation for that run's bimodal video
response (8/19 emissions ~0 excess over baseline, 9/19 at 8-24x). The flash
is now HELD WHITE for config.flash_duration_ms (~500ms default) instead of
a fixed frame count -- this only guarantees the crossing happens; it does
not add ambiguity to WHEN, since the onset detector still fires on the
FIRST sample crossing threshold, same as ever. The click is similarly
lengthened (config.click_duration_s) with a short, FIXED-length attack/
decay (config.click_ramp_ms, independent of total duration -- a longer
click must not mean a slower onset). Pairing and the reported offset now
use the CONFIRMED emission timestamps (flash_render_completed_ts,
audio_first_callback_ts) as each channel's own reference, not the single
scheduled timestamp -- this cancels the emitter's own render/play jitter
(69-159ms video, 61-91ms audio, per the diagnostic run) out of the
reported offset, which up to this attempt had jitter of that size sitting
inside every number below the 33ms floor it was supposed to resolve. See
compute_run_summary()'s docstring for the exact arithmetic. Every record
from this attempt (attempt 8) was stamped "offset_reference": "confirmed"
so it is never mistaken for the same quantity sessions 04d5cb0f and
0e6b2a1a reported (those used "offset_reference": "scheduled", stamped
retroactively true of their method, not present in their actual logs).

ATTEMPT 9 -- TWO DEFECTS FOUND BY READING CODE, BOTH FIXED: (1) attempt 8's
video reference, flash_render_completed_ts, was assigned AFTER the hold
loop exited -- it marked the flash's END, while audio_first_callback_ts
marks the click's START. Opposite edges of their stimuli biased every
attempt-8 offset by approximately -flash_duration_ms (predicted -500ms,
observed -502.5ms in session a6ce084e). Fixed: the emitter now records
flash_first_frame_ts (the true start edge, taken right after the FIRST
white frame is presented) as a SEPARATE field from flash_hold_ended_ts
(the old end-of-hold moment, kept because it is genuinely useful for
confirming the hold lasted its configured duration); pairing now uses
flash_first_frame_ts. (2) compute_diagnostic_window's max_value_in_window
spanned the WHOLE +/-1s window, including time before the stimulus, so a
pre-stimulus ambient noise event could be reported as though it were the
stimulus's own response -- confirmed for two emissions in session
a6ce084e whose "peaks" landed 0.75-0.98s BEFORE their own reference.
Fixed: max_value_in_window is now computed over the post-reference portion
only; the pre-reference portion's own max is reported separately as
pre_reference_max_value, specifically so this failure mode is visible
rather than silently repeated. Every record from this attempt is stamped
"offset_reference": "confirmed_v2" -- DELIBERATELY DIFFERENT from attempt
8's "confirmed", because attempt 8's video reference was defective and the
two are not the same quantity, not even approximately.

G1 -- NO PASS/FAIL, NO THRESHOLD-AS-VERDICT, NO "ACCEPTABLE SYNC" ANYWHERE
IN THIS FILE. K_v and K_a (the two onset-detection sensitivity multipliers)
live in AVSyncConfig, hashed into every record this script writes -- the
same treatment CLAUDE.md's delta_Gate3/delta_attention/delta_audio/delta_latent
get. This script computes and stores: onset timestamps, the offsets between
them, their spread, and a drift slope. It does not decide whether any of
that is "good sync" -- a human applies a pre-registered rule to these
numbers afterward, exactly like every other control in this repository.

G4 -- NO RAW AUDIO OR VIDEO CONTENT IS EVER WRITTEN TO DISK, and none is
even held in memory beyond the single current frame/audio block needed to
compute one scalar (luminance or energy) before being discarded. Only
onset timestamps, scalar magnitudes (for the rolling baseline), timestamps,
and counts are ever logged.

REUSED PATTERNS, NOT REINVENTED: the *Config + config_hash() dataclass
pattern (controls/null_input.py's NullInputConfig, audio_acquisition.py's
AudioCaptureConfig), the 1.4826*MAD robust-scale convention
(features/robust_baseline.py), sounddevice's callback-based InputStream for
audio (audio_acquisition.py's AudioAcquisitionThread), and "missingness is a
row with a reason, never an absent row" (D0PA1 hard constraint #8) via this
module's own small, honestly-separate missingness vocabulary -- the same
reasoning audio_acquisition.py's own AUDIO_MISSINGNESS_REASONS docstring
gives for not forcing a video-specific reason onto a non-video gap.
"""

import argparse
import dataclasses
import hashlib
import json
import os
import platform
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

import numpy as np

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(REPO_ROOT, "logs")
SCHEMA_VERSION = "1.0"

WINDOW_TITLE = "av_sync_flash"

# This module's OWN small, fixed missingness vocabulary -- deliberately NOT
# forced into schema/canonical_log_v1.json's missingness_reason enum, which
# is video/face-tracking-specific (no_face, tracking_lost, ...) and does not
# honestly describe "no onset found within the pairing window on this
# channel" -- same reasoning audio_acquisition.py already applies to its own
# AUDIO_MISSINGNESS_REASONS.
MISSINGNESS_REASONS = (
    "no_video_onset_within_window",
    "no_audio_onset_within_window",
    "no_audio_confirmation_timestamp",  # attempt 8: the audio output callback never fired for
                                         # this emission, so there is no reference to pair against
                                         # at all -- distinct from "the click played but no onset
                                         # was found," which is no_audio_onset_within_window.
)


@dataclasses.dataclass
class AVSyncConfig:
    """Same *Config + config_hash() pattern as every other config class in
    this codebase (NullInputConfig, AudioCaptureConfig, PreRegisteredConfig).
    k_v/k_a are the ONLY detection-sensitivity parameters in this file and
    live here, never as a literal inside a detection function -- G1's "the
    same treatment the delta parameters get"."""

    duration_minutes: float = 10.0
    event_interval_seconds: float = 30.0
    min_events: int = 20
    # Attempt 8: HELD DURATION, not a frame count -- a fixed frame count's
    # real-world duration depends on how fast imshow()/waitKey(1) actually
    # run, which is why 3 frames turned out to be a near-coin-flip against
    # a 33ms camera exposure period (session 0e6b2a1a's bimodal video
    # response). ~500ms guarantees many exposures land inside it.
    flash_duration_ms: float = 500.0
    pairing_window_ms: float = 500.0  # UNCHANGED this attempt -- see module docstring's "ON THE
                                       # PAIRING WINDOW" reasoning: the prior 512ms IQR came from
                                       # only 3 matched events and is not evidence of anything.

    k_v: float = 6.0  # video (luminance) onset sensitivity, in robust-MAD multiples
    k_a: float = 6.0  # audio (energy) onset sensitivity, in robust-MAD multiples
    video_baseline_window_frames: int = 90
    audio_baseline_window_hops: int = 400
    refractory_seconds: float = 1.0

    audio_sample_rate_hz: int = 48000
    audio_hop_ms: float = 5.0
    audio_channels: int = 1

    camera_index: int = 0
    # Attempt 8: lengthened from 10ms so many 5ms audio hops sit fully
    # inside the click instead of straddling its boundary (the same
    # "coin flip vs frame period" mechanism as the flash, applied to hops
    # instead of camera frames) -- misses in 0e6b2a1a tracked a raised
    # ambient baseline/MAD, and more full-strength hops gives the RMS
    # detector more chances to see the click clearly above that baseline.
    click_duration_s: float = 0.15
    click_freq_hz: float = 2000.0
    # Already at full digital scale (a unit-amplitude sine cannot go
    # higher without clipping) -- made an explicit, versioned parameter
    # rather than an implicit hardcoded 1.0, per this attempt's instruction
    # to raise it. The real lever for audio registration is the duration
    # increase above, not amplitude, which had no headroom left; reported
    # honestly rather than claimed as a bigger lever than it is.
    click_amplitude: float = 1.0
    # FIXED length regardless of click_duration_s -- a longer click must
    # not mean a slower attack, since the onset detector fires on the
    # first sample to cross threshold and a gradual ramp would delay
    # exactly that instant.
    click_ramp_ms: float = 2.0

    subject_id: str = "UNSET_OPERATOR_MUST_PROVIDE"
    context_id: str = "av_sync_flash"
    device_id: str = dataclasses.field(default_factory=platform.node)

    def config_hash(self):
        payload = json.dumps(dataclasses.asdict(self), sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


# ============================================================
# PURE, TESTABLE LOGIC -- no camera, no audio device, no I/O.
# ============================================================

def robust_baseline_stats(values):
    """median + 1.4826*MAD over an iterable of floats. Reuses the exact
    scaling constant features/robust_baseline.py already uses for the same
    reason (a consistent estimator of the population std under normality,
    robust to the outlier the onset itself would otherwise be). Returns
    (None, None) on empty input, matching this codebase's established
    insufficient_samples convention elsewhere rather than raising."""
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return None, None
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    return median, 1.4826 * mad


def find_onsets(samples, timestamps, k, baseline_window, refractory_seconds, min_baseline_n=None):
    """CAUSAL onset detector -- the same mechanism for BOTH the video
    (luminance) and audio (energy) channel, per this task's own framing:
    the stimulus is what changes, not the detector's rigour. Scans
    `samples`/`timestamps` (matched, time-ordered) and returns a list of
    onset timestamps: the first sample of each excursion where
    sample > rolling_median + k*rolling_MAD, using ONLY samples already
    seen (never a future sample, so this could run live). A refractory
    period after each onset prevents one sustained excursion (the flash/
    click's own decay) from being counted as multiple events.

    k, baseline_window, and refractory_seconds are all CALLER-SUPPLIED
    (AVSyncConfig fields) -- nothing here is a hardcoded threshold (G1)."""
    if min_baseline_n is None:
        min_baseline_n = max(10, baseline_window // 4)
    onsets = []
    baseline = deque(maxlen=baseline_window)
    last_onset_t = None
    for s, t in zip(samples, timestamps):
        if len(baseline) >= min_baseline_n:
            median, mad_scaled = robust_baseline_stats(baseline)
            above = mad_scaled is not None and mad_scaled > 1e-12 and s > median + k * mad_scaled
            in_refractory = last_onset_t is not None and (t - last_onset_t) < refractory_seconds
            if above and not in_refractory:
                onsets.append(t)
                last_onset_t = t
        baseline.append(s)
    return onsets


def pair_emissions(scheduled_timestamps, video_reference_timestamps, audio_reference_timestamps,
                    video_onsets, audio_onsets, pairing_window_seconds):
    """For each emission, the NEAREST video onset to that emission's OWN
    confirmed video reference (flash_first_frame_ts -- the flash's START
    edge, ATTEMPT 9: was flash_render_completed_ts, its END edge, until
    Check 1 found that biased every offset by -flash_duration_ms), and the
    NEAREST audio onset to its OWN confirmed audio reference
    (audio_first_callback_ts) -- found independently, so one channel
    missing never disqualifies the other. Every emission produces exactly
    one record; an unmatched channel is missingness-with-a-reason, never a
    dropped row (D0PA1 hard constraint #8).

    ATTEMPT 8 CHANGE: prior to this, both channels were paired against the
    single SCHEDULED emission timestamp. Pairing against each channel's
    own CONFIRMED reference instead is what lets compute_run_summary()
    cancel the emitter's own render/play jitter out of the reported offset
    -- see that function's docstring for the arithmetic this enables.
    scheduled_timestamps is carried through only for bookkeeping (elapsed-
    time-since-start, human-readable logs); it plays no role in matching.

    A None audio_reference_timestamps entry (the output callback never
    fired for that emission -- see _play_click_with_confirmation) makes
    that emission's audio side immediately missing with its own reason,
    no search attempted, never a crash."""

    def nearest_within(onsets, reference_t):
        if reference_t is None:
            return None
        candidates = [o for o in onsets if abs(o - reference_t) <= pairing_window_seconds]
        if not candidates:
            return None
        return min(candidates, key=lambda o: abs(o - reference_t))

    records = []
    for e, vref, aref in zip(scheduled_timestamps, video_reference_timestamps, audio_reference_timestamps):
        v = nearest_within(video_onsets, vref)
        a = nearest_within(audio_onsets, aref)
        if aref is None:
            a_reason = "no_audio_confirmation_timestamp"
        else:
            a_reason = None if a is not None else "no_audio_onset_within_window"
        records.append({
            "emission_scheduled_ts": e,
            "video_reference_ts": vref,
            "audio_reference_ts": aref,
            "video_onset_ts": v,
            "video_missingness_flag": v is None,
            "video_missingness_reason": None if v is not None else "no_video_onset_within_window",
            "audio_onset_ts": a,
            "audio_missingness_flag": a is None,
            "audio_missingness_reason": a_reason,
        })
    return records


def compute_run_summary(records, stream_start_ts, camera_fps):
    """Numbers only -- no pass/fail, no "acceptable sync" (G1). Computed
    only over PAIRED events (both channels present); how many that is, out
    of how many emissions, is reported explicitly so the denominator is
    never hidden.

    ATTEMPT 8 CHANGE -- offset is no longer video_onset - audio_onset.
    Each record now carries its own video_reference_ts
    (flash_first_frame_ts as of ATTEMPT 9 -- was flash_render_completed_ts
    in attempt 8, found defective, see pair_emissions()'s docstring) and
    audio_reference_ts (audio_first_callback_ts), so:

        video_latency = video_onset_ts - video_reference_ts
        audio_latency = audio_onset_ts - audio_reference_ts
        offset        = video_latency - audio_latency

    Expanding that: offset = (video_onset_ts - audio_onset_ts) -
    (video_reference_ts - audio_reference_ts). The first term is the old
    formula; the second is exactly the emitter's own render/play jitter
    (69-159ms video, 61-91ms audio in session 0e6b2a1a) -- this
    subtraction is what removes it, leaving only the difference in each
    channel's OWN capture+detection latency, which is the quantity this
    measurement is actually for. When video_reference_ts equals
    audio_reference_ts (zero emitter jitter), this is numerically
    identical to the old formula -- it is a generalisation, not a
    different measurement in the zero-jitter case.

    Theil-Sen (scipy.stats.theilslopes) is used for the drift slope because
    it is robust to the occasional bad pairing a nearest-neighbour match can
    produce, unlike ordinary least squares. frame_period_floor_ms is
    reported ALONGSIDE every spread figure, per this task's own instruction
    -- a spread below that floor is not resolvable by this method."""
    n_emissions = len(records)
    paired = [r for r in records if not r["video_missingness_flag"] and not r["audio_missingness_flag"]]
    n_paired = len(paired)
    frame_period_floor_ms = (1000.0 / camera_fps) if camera_fps else None

    summary = {
        "n_emissions": n_emissions,
        "n_paired": n_paired,
        "n_video_missing": sum(1 for r in records if r["video_missingness_flag"]),
        "n_audio_missing": sum(1 for r in records if r["audio_missingness_flag"]),
        "frame_period_floor_ms": frame_period_floor_ms,
        "offset_reference": "confirmed_v2",  # ATTEMPT 9 -- must match run()'s own av_sync_run_start
                                              # stamp exactly (this dict is spread into
                                              # av_sync_summary via **summary): "confirmed" alone
                                              # is attempt 8's defective-video-reference quantity,
                                              # see module docstring's "ATTEMPT 9" note
        "offset_median_ms": None,
        "offset_iqr_ms": None,
        "offset_mad_scaled_ms": None,
        "drift_slope_ms_per_s": None,
        "drift_slope_ci_low_ms_per_s": None,
        "drift_slope_ci_high_ms_per_s": None,
    }
    if n_paired < 2:
        summary["note"] = "insufficient_samples -- fewer than 2 paired events, no spread or drift figure computed"
        return summary

    offsets_ms = np.array([
        ((r["video_onset_ts"] - r["video_reference_ts"]) - (r["audio_onset_ts"] - r["audio_reference_ts"])) * 1000.0
        for r in paired
    ])
    elapsed_s = np.array([r["emission_scheduled_ts"] - stream_start_ts for r in paired])

    median, mad_scaled = robust_baseline_stats(offsets_ms)
    q75, q25 = np.percentile(offsets_ms, [75, 25])

    summary["offset_median_ms"] = median
    summary["offset_iqr_ms"] = float(q75 - q25)
    summary["offset_mad_scaled_ms"] = mad_scaled

    if n_paired >= 3:
        from scipy.stats import theilslopes
        slope, intercept, low, high = theilslopes(offsets_ms, elapsed_s)
        summary["drift_slope_ms_per_s"] = float(slope)
        summary["drift_slope_ci_low_ms_per_s"] = float(low)
        summary["drift_slope_ci_high_ms_per_s"] = float(high)
    else:
        summary["note"] = "insufficient_samples -- fewer than 3 paired events, no drift slope computed"

    return summary


def compute_diagnostic_window(samples, timestamps, onsets, k, baseline_window, emission_ts,
                               window_seconds=1.0, min_baseline_n=None):
    """DIAGNOSTIC-ONLY, read-only inspection of the SAME rolling-baseline
    state find_onsets() computes for one channel around one emission. This
    function decides nothing and fires nothing -- `onsets` must be the
    unmodified output of a real find_onsets() call; this only reports
    whether one of those already-decided onsets happened to land in the
    window (G1: no new threshold, no verdict; G2: k is read, never chosen
    or fitted here).

    baseline_median_pre / baseline_mad_scaled_pre are the rolling baseline
    as of the last sample STRICTLY BEFORE the window opens
    (emission_ts - window_seconds) -- the pre-stimulus baseline, not
    contaminated by the flash/click itself, which is what the live
    detector actually compares in-window samples against (find_onsets
    computes its threshold from samples strictly preceding the one being
    tested, never the current or a future sample).

    threshold_absolute = baseline_median_pre + k*baseline_mad_scaled_pre,
    i.e. the exact value a sample would have had to exceed to fire, in the
    channel's own raw units. max_to_threshold_ratio near 1 means the peak
    came close to firing (a tuning question); near 0 means no real step
    exists in this window at all (a physics question) -- these are
    reported as numbers only, the distinction is for a human to draw.

    ATTEMPT 9 FIX (Check 2 found this defective): max_value_in_window is
    now computed ONLY over samples at or after emission_ts -- the
    stimulus's own response, not whatever happened anywhere in the ±1s
    window. Previously it spanned the whole window including time BEFORE
    the stimulus, so a pre-stimulus ambient noise event could dominate the
    max and be reported as though it were the stimulus's response (this is
    exactly what happened for two emissions in session a6ce084e: their
    "peaks" landed 0.75-0.98s BEFORE their own reference timestamp). The
    pre-reference portion of the window is UNCHANGED in its other role --
    it still feeds nothing into max_value_in_window, but its own max is
    now reported separately as pre_reference_max_value, specifically so a
    pre-stimulus event bigger than the real response is visible rather
    than silently inflating anything (the exact failure mode this fix
    closes).

    Returns insufficient_baseline=True (never a fabricated number) if the
    rolling baseline had not warmed up (fewer than min_baseline_n samples)
    before the window opened."""
    if min_baseline_n is None:
        min_baseline_n = max(10, baseline_window // 4)

    window_lo = emission_ts - window_seconds
    window_hi = emission_ts + window_seconds

    baseline = deque(maxlen=baseline_window)
    baseline_median_pre = None
    baseline_mad_scaled_pre = None
    window_values = []
    window_timestamps = []
    pre_reference_values = []   # window_lo <= t < emission_ts -- NOT the response
    post_reference_values = []  # emission_ts <= t <= window_hi -- the actual response

    for s, t in zip(samples, timestamps):
        if t < window_lo:
            baseline.append(s)
            continue
        if t > window_hi:
            break  # samples are time-ordered -- nothing further is in-window
        if baseline_median_pre is None and len(baseline) >= min_baseline_n:
            baseline_median_pre, baseline_mad_scaled_pre = robust_baseline_stats(baseline)
        window_values.append(s)
        window_timestamps.append(t)
        if t < emission_ts:
            pre_reference_values.append(s)
        else:
            post_reference_values.append(s)

    # Fallback for a window with NO in-window samples at all (e.g. it falls
    # entirely after capture stopped) -- the loop above only computes the
    # baseline snapshot when it reaches an in-window sample, so without
    # this it would report insufficient_baseline=True even when the
    # pre-window baseline was, in fact, fully warmed.
    if baseline_median_pre is None and len(baseline) >= min_baseline_n:
        baseline_median_pre, baseline_mad_scaled_pre = robust_baseline_stats(baseline)

    max_value = max(post_reference_values) if post_reference_values else None
    pre_reference_max_value = max(pre_reference_values) if pre_reference_values else None
    threshold_absolute = (
        baseline_median_pre + k * baseline_mad_scaled_pre
        if baseline_median_pre is not None and baseline_mad_scaled_pre is not None
        else None
    )
    ratio = (
        max_value / threshold_absolute
        if max_value is not None and threshold_absolute not in (None, 0)
        else None
    )
    onset_fired_in_window = any(window_lo <= o <= window_hi for o in onsets)

    return {
        "window_seconds": window_seconds,
        "n_samples_in_window": len(window_values),
        "timestamps": window_timestamps,
        "values": window_values,
        "baseline_median_pre": baseline_median_pre,
        "baseline_mad_scaled_pre": baseline_mad_scaled_pre,
        "threshold_absolute": threshold_absolute,
        "max_value_in_window": max_value,  # ATTEMPT 9: post-reference only, see docstring
        "pre_reference_max_value": pre_reference_max_value,  # NEW -- visible, never silently folded in
        "max_to_threshold_ratio": ratio,
        "onset_fired_in_window": onset_fired_in_window,
        "insufficient_baseline": baseline_median_pre is None,
    }


def synthesize_click(sample_rate_hz, duration_s, freq_hz, amplitude=1.0, ramp_ms=2.0):
    """A sine-burst click with a linear fade in/out envelope (avoids a hard
    edge, which would itself be a broadband click confusable with what we
    are trying to measure the timing of). Deterministic, no data-dependent
    tuning (G2 does not apply to a stimulus generator -- there is no
    "result" here to tune toward).

    ATTEMPT 8: ramp_ms is a FIXED duration in milliseconds, not a fraction
    of the total click length as it was before -- a longer click (now
    config.click_duration_s=0.15 by default, up from 0.01) must keep a
    SHARP onset, since the onset detector fires on the first sample to
    cross threshold and a ramp that grows with total duration would delay
    exactly that instant. amplitude scales the sine before the envelope is
    applied; the caller is responsible for keeping it within [-1, 1] to
    avoid clipping (AVSyncConfig.click_amplitude defaults to 1.0, already
    the maximum a normalised signal can carry)."""
    n = max(1, int(sample_rate_hz * duration_s))
    t = np.arange(n) / sample_rate_hz
    tone = amplitude * np.sin(2 * np.pi * freq_hz * t)
    ramp = max(1, int(sample_rate_hz * ramp_ms / 1000.0)) if n >= 2 else 0
    ramp = min(ramp, n // 2)
    envelope = np.ones(n)
    if ramp > 0:
        envelope[:ramp] = np.linspace(0.0, 1.0, ramp)
        envelope[-ramp:] = np.linspace(1.0, 0.0, ramp)
    return (tone * envelope).astype(np.float32)


# ============================================================
# LIVE CAPTURE -- camera + microphone. Not exercised by the unit tests
# above; see tests/test_av_sync_flash.py for what IS covered, and this
# task's own report for what "built but not run live this task" means here.
# ============================================================

class VideoLuminanceCapture:
    """Own thread: opens its own cv2.VideoCapture (never the validated
    pipeline's T1/T2), reads frames as fast as delivered, converts to
    grayscale, and appends (timestamp, mean_luminance) to a thread-safe
    deque. NEVER calls apply_clahe (see module docstring) and NEVER retains
    a frame after its scalar luminance is computed -- no raw video is ever
    held beyond one frame's lifetime, let alone written to disk (G4)."""

    def __init__(self, camera_index, max_samples=200000):
        self.camera_index = camera_index
        self.samples = deque(maxlen=max_samples)
        self.timestamps = deque(maxlen=max_samples)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self.frame_count = 0
        self.actual_fps = None

    def _run(self):
        import cv2
        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        start = time.perf_counter()
        n = 0
        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    continue
                now = time.perf_counter()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # RAW grayscale, pre-CLAHE, by construction (no apply_clahe import here)
                luminance = float(np.mean(gray))
                with self._lock:
                    self.samples.append(luminance)
                    self.timestamps.append(now)
                n += 1
        finally:
            cap.release()
            elapsed = time.perf_counter() - start
            self.actual_fps = (n / elapsed) if elapsed > 0 else None
            self.frame_count = n

    def start(self):
        self._thread = threading.Thread(target=self._run, name="VideoLuminanceCapture", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def snapshot(self):
        with self._lock:
            return list(self.samples), list(self.timestamps)


class AudioEnergyCapture:
    """sounddevice callback-based InputStream (same pattern as
    audio_acquisition.py's AudioAcquisitionThread), blocksize set to
    exactly one config.audio_hop_ms hop so each callback invocation IS one
    energy sample. Computes RMS per hop and discards the raw block
    immediately -- no raw audio is ever retained past that computation,
    let alone written to disk (G4)."""

    def __init__(self, sample_rate_hz, channels, hop_ms, max_samples=200000):
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.hop_frames = max(1, int(sample_rate_hz * hop_ms / 1000.0))
        self.samples = deque(maxlen=max_samples)
        self.timestamps = deque(maxlen=max_samples)
        self._lock = threading.Lock()
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        now = time.perf_counter()
        block = indata[:, 0] if indata.ndim > 1 else indata
        rms = float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
        with self._lock:
            self.samples.append(rms)
            self.timestamps.append(now)

    def start(self):
        import sounddevice as sd
        self._stream = sd.InputStream(
            samplerate=self.sample_rate_hz,
            channels=self.channels,
            dtype="float32",
            blocksize=self.hop_frames,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def snapshot(self):
        with self._lock:
            return list(self.samples), list(self.timestamps)


def _play_click_with_confirmation(click, sample_rate_hz):
    """Plays the click through its OWN short-lived sd.OutputStream with a
    callback, instead of a fire-and-forget sd.play(), so we get a real
    answer to "did the output callback consume the buffer, and when"
    rather than assuming it silently worked. Returns the perf_counter
    timestamp of the FIRST callback invocation (when the audio subsystem
    actually started pulling data), or None if no callback fired within a
    short deadline (itself a diagnostic fact, not an error to hide).

    ATTEMPT 8: promoted from --diagnose-only to the path EVERY run uses --
    this confirmed timestamp is now the pairing reference for the audio
    channel (see pair_emissions()/compute_run_summary()), not only a
    --diagnose trace field.

    Does not block the emission loop for the click's full duration: it
    waits only long enough for the first callback (typically sub-
    millisecond), then lets a short-lived background thread close the
    stream once the click has had time to finish playing."""
    import sounddevice as sd

    state = {"first_callback_ts": None, "pos": 0}

    def _callback(outdata, frames, time_info, status):
        if state["first_callback_ts"] is None:
            state["first_callback_ts"] = time.perf_counter()
        pos = state["pos"]
        end = pos + frames
        chunk = click[pos:end]
        if len(chunk) < frames:
            outdata[:len(chunk), 0] = chunk
            outdata[len(chunk):, 0] = 0.0
        else:
            outdata[:, 0] = chunk
        state["pos"] = end

    try:
        stream = sd.OutputStream(samplerate=sample_rate_hz, channels=1, dtype="float32", callback=_callback)
        stream.start()
    except Exception:
        return None  # missingness, not a crash -- Part C will see audio_first_callback_ts: null

    deadline = time.perf_counter() + 0.1
    while state["first_callback_ts"] is None and time.perf_counter() < deadline:
        time.sleep(0.001)

    def _close_after(stream_ref, delay_s):
        time.sleep(delay_s)
        try:
            stream_ref.stop()
            stream_ref.close()
        except Exception:
            pass

    threading.Thread(target=_close_after, args=(stream, len(click) / sample_rate_hz + 0.05), daemon=True).start()
    return state["first_callback_ts"]


def _emit_flash_and_click(config):
    """The ONE emitter, used identically whether or not --diagnose is set
    (attempt 8 merges what used to be a plain emitter and a
    --diagnose-only one: confirmation evidence is no longer a diagnostic
    extra, it is the pairing reference every run needs -- see
    pair_emissions()). Plays the click through its own confirmed-callback
    stream (_play_click_with_confirmation) and holds a full-screen white
    flash for config.flash_duration_ms (a HELD DURATION, not a frame
    count -- see AVSyncConfig.flash_duration_ms and the module docstring's
    "ATTEMPT 8" note for why).

    window_visible_flag reads cv2.getWindowProperty(..., WND_PROP_VISIBLE)
    for the log only -- it is NEVER used to decide anything (no branch
    reads it), unlike the getWindowProperty-based SHUTDOWN logic elsewhere
    in this repo that is known to false-trigger under a backgrounded
    launch context (see the soak runsheet). A read-only log field carries
    none of that risk; nothing here controls process lifetime.

    ATTEMPT 9 FIX (Check 1 found this defective): what used to be a single
    "flash_render_completed_ts", assigned AFTER the hold loop exited, has
    been split into two honestly-named fields --
    flash_first_frame_ts (assigned right after the FIRST white frame is
    presented, the actual start edge the video onset detector responds
    to) and flash_hold_ended_ts (assigned after the hold loop exits, kept
    because it is genuinely useful for confirming the hold lasted its
    configured duration -- just no longer used as the pairing reference).
    Using the end-of-hold timestamp as the video reference biased every
    attempt-8 offset by approximately -flash_duration_ms, because the
    audio reference (audio_first_callback_ts, below) marks the START of
    the click, not its end -- the two references were marking opposite
    edges of their stimuli. run() now pairs video against
    flash_first_frame_ts.

    Returns a dict of the scheduled timestamp, the two flash timestamps,
    and the CONFIRMED audio timestamp -- "an emission was scheduled" alone
    cannot establish that it actually happened, which is why these are
    measured rather than assumed."""
    import cv2

    click = synthesize_click(
        config.audio_sample_rate_hz, config.click_duration_s, config.click_freq_hz,
        amplitude=config.click_amplitude, ramp_ms=config.click_ramp_ms,
    )
    white = np.full((600, 800, 3), 255, dtype=np.uint8)
    black = np.zeros((600, 800, 3), dtype=np.uint8)

    emission_scheduled_ts = time.perf_counter()
    audio_first_callback_ts = _play_click_with_confirmation(click, config.audio_sample_rate_hz)

    flash_end = time.perf_counter() + config.flash_duration_ms / 1000.0
    flash_first_frame_ts = None
    while time.perf_counter() < flash_end:
        cv2.imshow(WINDOW_TITLE, white)
        cv2.waitKey(1)
        if flash_first_frame_ts is None:
            flash_first_frame_ts = time.perf_counter()  # the start edge -- ATTEMPT 9's pairing reference
    flash_hold_ended_ts = time.perf_counter()  # end-of-hold, kept for hold-duration confirmation only
    try:
        window_visible_flag = float(cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE))
    except Exception:
        window_visible_flag = None
    cv2.imshow(WINDOW_TITLE, black)
    cv2.waitKey(1)

    return {
        "emission_scheduled_ts": emission_scheduled_ts,
        "flash_first_frame_ts": flash_first_frame_ts,
        "flash_hold_ended_ts": flash_hold_ended_ts,
        "window_visible_flag": window_visible_flag,
        "audio_first_callback_ts": audio_first_callback_ts,
    }


def run(config, diagnose=False):
    """Orchestrates one full session: starts the two independent capture
    threads, emits config.min_events flashes/clicks on
    config.event_interval_seconds spacing (for at least
    config.duration_minutes), stops capture, computes onsets/pairing/
    summary from the in-memory scalar streams ONLY, writes per-event and
    summary records to logs/, and returns the summary dict. No raw audio
    or video sample is ever written to disk at any point (G4) -- confirmed
    structurally: neither capture class above has a disk-write path at
    all, unlike audio_acquisition.py's optional write_raw_capture, which
    this script deliberately does not use or import."""
    import cv2

    session_id = str(uuid.uuid4())
    video = VideoLuminanceCapture(config.camera_index)
    audio = AudioEnergyCapture(config.audio_sample_rate_hz, config.audio_channels, config.audio_hop_ms)

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    video.start()
    audio.start()
    time.sleep(1.0)  # let both streams accumulate a real rolling baseline before the first emission

    stream_start = time.perf_counter()
    n_events = max(config.min_events, int((config.duration_minutes * 60.0) / config.event_interval_seconds))
    emission_diagnostics = []  # ALWAYS populated now -- confirmation is no longer diagnose-only
    print(f"[av_sync_flash] emitting {n_events} events, one every {config.event_interval_seconds:.0f}s "
          f"({n_events * config.event_interval_seconds / 60.0:.1f} min total)"
          + (" [DIAGNOSE MODE -- extra per-emission traces logged]" if diagnose else ""))
    for i in range(n_events):
        emission_diagnostics.append(_emit_flash_and_click(config))
        print(f"[av_sync_flash] event {i + 1}/{n_events} emitted")
        if i < n_events - 1:
            time.sleep(config.event_interval_seconds)

    video.stop()
    audio.stop()
    cv2.destroyWindow(WINDOW_TITLE)

    video_samples, video_ts = video.snapshot()
    audio_samples, audio_ts = audio.snapshot()

    video_onsets = find_onsets(video_samples, video_ts, config.k_v, config.video_baseline_window_frames, config.refractory_seconds)
    audio_onsets = find_onsets(audio_samples, audio_ts, config.k_a, config.audio_baseline_window_hops, config.refractory_seconds)

    scheduled_timestamps = [d["emission_scheduled_ts"] for d in emission_diagnostics]
    video_reference_timestamps = [d["flash_first_frame_ts"] for d in emission_diagnostics]  # ATTEMPT 9 fix: start edge, not end-of-hold
    audio_reference_timestamps = [d["audio_first_callback_ts"] for d in emission_diagnostics]

    records = pair_emissions(
        scheduled_timestamps, video_reference_timestamps, audio_reference_timestamps,
        video_onsets, audio_onsets, config.pairing_window_ms / 1000.0,
    )
    summary = compute_run_summary(records, stream_start, video.actual_fps)

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"av_sync_flash_{session_id}.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "record_type": "av_sync_run_start",
            "session_id": session_id,
            "subject_id": config.subject_id,
            "context_id": config.context_id,
            "device_id": config.device_id,
            "diagnose": diagnose,
            "offset_reference": "confirmed_v2",  # attempt 9 -- see module docstring's "ATTEMPT 9" note.
                                                  # MUST differ from attempt 8's "confirmed": that
                                                  # label's video reference (flash_render_completed_ts,
                                                  # end-of-hold) was found defective by Check 1 and is
                                                  # NOT the same quantity as v2's flash_first_frame_ts.
            "config": dataclasses.asdict(config),
            "config_hash": config.config_hash(),
            "ts_utc": datetime.now(timezone.utc).isoformat(),
        }) + "\n")
        for i, r in enumerate(records):
            f.write(json.dumps({
                "schema_version": SCHEMA_VERSION,
                "record_type": "av_sync_event",
                "session_id": session_id,
                "event_index": i,
                **r,
            }) + "\n")
        if diagnose:
            for i, diag in enumerate(emission_diagnostics):
                # Diagnostic traces are centred on each channel's OWN
                # confirmed reference (same one pairing uses) -- ATTEMPT 9:
                # video now centres on flash_first_frame_ts (the start
                # edge), not the old end-of-hold timestamp. This changes
                # WHICH samples fall in the pre-/post-reference split
                # inside compute_diagnostic_window (itself also fixed this
                # attempt -- see that function's docstring for Check 2).
                video_window = compute_diagnostic_window(
                    video_samples, video_ts, video_onsets, config.k_v,
                    config.video_baseline_window_frames, diag["flash_first_frame_ts"],
                )
                audio_window = compute_diagnostic_window(
                    audio_samples, audio_ts, audio_onsets, config.k_a,
                    config.audio_baseline_window_hops, diag["audio_first_callback_ts"],
                ) if diag["audio_first_callback_ts"] is not None else None
                f.write(json.dumps({
                    "schema_version": SCHEMA_VERSION,
                    "record_type": "av_sync_diagnostic_emission",
                    "session_id": session_id,
                    "event_index": i,
                    "emission_scheduled_ts": diag["emission_scheduled_ts"],
                    "flash_first_frame_ts": diag["flash_first_frame_ts"],
                    "flash_hold_ended_ts": diag["flash_hold_ended_ts"],
                    "window_visible_flag": diag["window_visible_flag"],
                    "audio_first_callback_ts": diag["audio_first_callback_ts"],
                    "video_trace": video_window,
                    "audio_trace": audio_window,
                }) + "\n")
        f.write(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "record_type": "av_sync_summary",
            "session_id": session_id,
            "camera_actual_fps": video.actual_fps,
            "camera_frame_count": video.frame_count,
            **summary,
        }) + "\n")

    print(f"[av_sync_flash] wrote {log_path}")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="D0PA1 audio/video sync measurement via a global luminance flash + audio click.")
    parser.add_argument("--subject-id", type=str, required=True, help="Anonymous subject/participant code, e.g. P01 -- required, never a name")
    parser.add_argument("--duration-minutes", type=float, default=10.0)
    parser.add_argument("--event-interval-seconds", type=float, default=30.0)
    parser.add_argument("--min-events", type=int, default=20)
    parser.add_argument("--k-v", type=float, default=6.0)
    parser.add_argument("--k-a", type=float, default=6.0)
    parser.add_argument("--diagnose", action="store_true",
                         help="Diagnostic mode: log emission-confirmation and threshold-context "
                              "traces per event (av_sync_diagnostic_emission records). Adds "
                              "logging only -- does not change detection logic, k_v/k_a, or any "
                              "default. Without this flag, behaviour is unchanged.")
    args = parser.parse_args()

    cfg = AVSyncConfig(
        duration_minutes=args.duration_minutes,
        event_interval_seconds=args.event_interval_seconds,
        min_events=args.min_events,
        k_v=args.k_v,
        k_a=args.k_a,
        subject_id=args.subject_id,
    )
    run(cfg, diagnose=args.diagnose)
