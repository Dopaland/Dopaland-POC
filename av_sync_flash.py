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

NOT A STROBE: the flash is a single one-shot pulse (config.flash_frames
consecutive rendered white frames, then reverts) inside one emission event,
never a repeating on/off pattern -- so it has no "rate" in the photosensitive-
epilepsy sense at all. Events themselves are spaced config.event_interval_seconds
apart (default 30s = 0.033 Hz), far below the 3-60 Hz band the task's own
instruction names. Both are true by construction, not by a runtime check.

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
    flash_frames: int = 3
    pairing_window_ms: float = 500.0

    k_v: float = 6.0  # video (luminance) onset sensitivity, in robust-MAD multiples
    k_a: float = 6.0  # audio (energy) onset sensitivity, in robust-MAD multiples
    video_baseline_window_frames: int = 90
    audio_baseline_window_hops: int = 400
    refractory_seconds: float = 1.0

    audio_sample_rate_hz: int = 48000
    audio_hop_ms: float = 5.0
    audio_channels: int = 1

    camera_index: int = 0
    click_duration_s: float = 0.01
    click_freq_hz: float = 2000.0

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


def pair_emissions(emission_timestamps, video_onsets, audio_onsets, pairing_window_seconds):
    """For each emission, the NEAREST video onset and the NEAREST audio
    onset within +/- pairing_window_seconds, independently -- a video
    match and an audio match are found separately, so one channel missing
    never disqualifies the other. Every emission produces exactly one
    record; an unmatched channel is missingness-with-a-reason, never a
    dropped row (D0PA1 hard constraint #8)."""

    def nearest_within(onsets, emission_t):
        candidates = [o for o in onsets if abs(o - emission_t) <= pairing_window_seconds]
        if not candidates:
            return None
        return min(candidates, key=lambda o: abs(o - emission_t))

    records = []
    for e in emission_timestamps:
        v = nearest_within(video_onsets, e)
        a = nearest_within(audio_onsets, e)
        records.append({
            "emission_ts": e,
            "video_onset_ts": v,
            "video_missingness_flag": v is None,
            "video_missingness_reason": None if v is not None else "no_video_onset_within_window",
            "audio_onset_ts": a,
            "audio_missingness_flag": a is None,
            "audio_missingness_reason": None if a is not None else "no_audio_onset_within_window",
        })
    return records


def compute_run_summary(records, stream_start_ts, camera_fps):
    """Numbers only -- no pass/fail, no "acceptable sync" (G1). Computed
    only over PAIRED events (both channels present); how many that is, out
    of how many emissions, is reported explicitly so the denominator is
    never hidden. offset = video_onset - audio_onset, in milliseconds.
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

    offsets_ms = np.array([(r["video_onset_ts"] - r["audio_onset_ts"]) * 1000.0 for r in paired])
    elapsed_s = np.array([r["emission_ts"] - stream_start_ts for r in paired])

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


def synthesize_click(sample_rate_hz, duration_s, freq_hz):
    """A short sine-burst click with a linear fade in/out envelope (avoids
    a hard edge, which would itself be a broadband click confusable with
    what we are trying to measure the timing of). Deterministic, no data-
    dependent tuning (G2 does not apply to a stimulus generator -- there is
    no "result" here to tune toward)."""
    n = max(1, int(sample_rate_hz * duration_s))
    t = np.arange(n) / sample_rate_hz
    tone = np.sin(2 * np.pi * freq_hz * t)
    ramp = min(n // 4, 1) if n < 4 else n // 4
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


def _emit_flash_and_click(config):
    """Simultaneously: play a short click through the default output
    device, and render a full-screen white flash for config.flash_frames
    frames via a plain cv2 window (no video capture in this function --
    that is VideoLuminanceCapture's own, independent camera handle).
    Returns the software emission timestamp (perf_counter, recorded as
    close to both triggers as a single Python call sequence allows)."""
    import cv2
    import sounddevice as sd

    click = synthesize_click(config.audio_sample_rate_hz, config.click_duration_s, config.click_freq_hz)
    white = np.full((600, 800, 3), 255, dtype=np.uint8)
    black = np.zeros((600, 800, 3), dtype=np.uint8)

    emission_ts = time.perf_counter()
    sd.play(click, samplerate=config.audio_sample_rate_hz, blocking=False)
    for _ in range(config.flash_frames):
        cv2.imshow(WINDOW_TITLE, white)
        cv2.waitKey(1)
    cv2.imshow(WINDOW_TITLE, black)
    cv2.waitKey(1)
    return emission_ts


def run(config):
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
    emission_timestamps = []
    print(f"[av_sync_flash] emitting {n_events} events, one every {config.event_interval_seconds:.0f}s "
          f"({n_events * config.event_interval_seconds / 60.0:.1f} min total)")
    for i in range(n_events):
        emission_timestamps.append(_emit_flash_and_click(config))
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

    records = pair_emissions(emission_timestamps, video_onsets, audio_onsets, config.pairing_window_ms / 1000.0)
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
    args = parser.parse_args()

    cfg = AVSyncConfig(
        duration_minutes=args.duration_minutes,
        event_interval_seconds=args.event_interval_seconds,
        min_events=args.min_events,
        k_v=args.k_v,
        k_a=args.k_a,
        subject_id=args.subject_id,
    )
    run(cfg)
