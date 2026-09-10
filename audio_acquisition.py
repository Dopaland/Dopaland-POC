"""
D0PA1 audio acquisition (U_t block) -- MINIMAL INSTRUMENT, Task 3.

Root-level module, same placement pattern as orientation_capture.py (a
capture/orchestration tool that lives alongside the D1 feature blocks, not
inside features/audio.py itself -- features/audio.py remains the U_t
FEATURE stub, still intentionally empty; see that module's own docstring
and CLAUDE.md's scope line). This file captures and measures; it computes
NO feature, NO score, NO psychological reading (Task 3.3 / the master
prompt's SCOPE LINE) -- level and timing only.

WHAT THIS IS: the smallest microphone capture path that can produce
evidence -- an instrument, not a feature. AudioAcquisitionThread opens the
default input device via sounddevice's callback-based InputStream (PortAudio
invokes the callback on its own thread; nothing here shares a lock, a
buffer, or any mutable state with T1/T2's video capture/processing threads
-- see the class docstring for why this makes "does not block/slow/touch
the existing architecture" a structural property, not just an intention,
and tests/test_audio_acquisition.py / the task's own final report for the
measured FPS-before/after proof).

NO CONTENT ANALYSIS (Task 3.3): every per-chunk record below is level and
timing only (peak/RMS amplitude, clipping flag, sample rate, channel count,
buffer size, dropout/overrun counts, two independently-sourced timestamps).
Nothing here transcribes, detects speech, extracts spectral features, or
characterises what was said -- there is no code path in this file that
could. If raw audio samples are ever written to disk at all (only
Task 4's clap-sync measurement does this, via write_raw_capture() below),
they are written OUTSIDE this repository (raises if the target path
resolves inside REPO_ROOT) and are the caller's responsibility to delete
immediately after measurement -- this module never deletes anything itself,
so the deletion is auditable in whatever script calls it, not hidden here.

MISSINGNESS (Task 3.2): a gap in the audio stream is a row with a reason,
never an absent row -- AUDIO_MISSINGNESS_REASONS below is this module's OWN
small, fixed vocabulary (device_unavailable / device_disconnected_mid_session
/ stream_error / buffer_overrun_data_lost), deliberately NOT reused from
schema/canonical_log_v1.json's missingness_reason enum: that enum's existing
values (no_face, low_landmark_confidence, out_of_frame, occlusion,
tracking_lost, ...) are video/face-tracking-specific and none of them
honestly describe an audio-stream gap -- inventing a forced-fit mapping
would be worse than a small, honestly-separate vocabulary (G3).

D1 / U_t: this module MAY be imported by orchestrators that also touch
video (same permitted relationship stage1_step4_vectors.py has with
features.attention today), but MUST NEVER be imported by features/x_core.py
or features/episodes.py, and must never import them either -- see
tests/test_feature_separation.py Task 5 additions for the machine-checked
proof.
"""

import hashlib
import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import numpy as np

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(REPO_ROOT, "logs")
CHUNK_LOG_PATH = os.path.join(LOG_DIR, "audio_chunk_integrity.jsonl")

SCHEMA_VERSION = "1.0"
RECORD_TYPE = "audio_chunk_integrity"

# Own, small, fixed vocabulary -- see module docstring for why this is not
# schema/canonical_log_v1.json's missingness_reason enum.
AUDIO_MISSINGNESS_REASONS = {
    "device_unavailable",       # stream could never be opened
    "device_disconnected_mid_session",  # was open, then vanished
    "stream_error",              # PortAudio/driver-level error mid-stream
    "buffer_overrun_data_lost",  # audio layer reports input overflow -- samples genuinely lost, not just a slow callback
}

# Clipping is a HARDWARE/SIGNAL fact (samples at or past full-scale), the
# same kind of quality flag as this codebase's existing detect_rate<0.5 /
# yaw_variance>ceiling gates -- not a G1 verdict about the subject. Not
# tuned against any real recording (none existed before this task, G2);
# derived from the float32 full-scale bound itself, the only
# first-principles reference point available.
CLIP_FRACTION_OF_FULL_SCALE = 0.999


@dataclass(frozen=True)
class AudioCaptureConfig:
    """Same *Config + config_hash() pattern as every other config class in
    this codebase. No storage-location field here -- that lives in
    privacy/audio_storage_config.py, resolved separately, only when a raw
    write is actually requested (Task 1.4's module)."""

    sample_rate_hz: int = 48000
    channels: int = 1
    chunk_seconds: float = 1.0
    device: object = None  # None = system default input device (sd.default.device[0])

    def config_hash(self):
        payload = json.dumps(asdict(self), sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


def compute_level_stats(samples):
    """Pure amplitude measurement -- peak absolute value, RMS, and a
    clipping flag. `samples` is a float32 array in [-1.0, 1.0] (sounddevice's
    default dtype). NO frequency-domain transform, no windowing beyond what
    is needed for RMS, nothing that could be described as characterising
    CONTENT (Task 3.3) -- this tells silence (near-zero) apart from signal
    (moderate) apart from clipping (samples pinned near full-scale), nothing
    more."""
    if samples.size == 0:
        return {"peak_abs": None, "rms": None, "clipping_detected": None}
    arr = np.abs(samples.astype(np.float64))
    peak = float(arr.max())
    rms = float(np.sqrt(np.mean(arr ** 2)))
    clipping = bool(peak >= CLIP_FRACTION_OF_FULL_SCALE)
    return {"peak_abs": peak, "rms": rms, "clipping_detected": clipping}


def _missing_record(reason, *, subject_id, context_id, device_id, session_id, config, seq):
    if reason not in AUDIO_MISSINGNESS_REASONS:
        raise ValueError(f"unknown missingness reason {reason!r}, must be one of {sorted(AUDIO_MISSINGNESS_REASONS)}")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "session_id": session_id,
        "subject_id": subject_id,
        "context_id": context_id,
        "device_id": device_id,
        "seq": seq,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "chunk_ts_perf_counter": time.perf_counter(),
        "chunk_ts_portaudio_adc": None,
        "clock_sources": {
            "chunk_ts_perf_counter": "time.perf_counter() -- same monotonic clock convention as the rest of this repository",
            "chunk_ts_portaudio_adc": "PortAudio inputBufferAdcTime via sounddevice's callback `time` argument -- hardware/driver-timestamped ADC time, not available for a missing chunk",
        },
        "config_hash": config.config_hash(),
        "sample_rate_hz": config.sample_rate_hz,
        "channels": config.channels,
        "bit_depth": 32,
        "buffer_size_frames": None,
        "dropout_count": None,
        "overrun_count": None,
        "level": {"peak_abs": None, "rms": None, "clipping_detected": None},
        "missingness_flag": True,
        "missingness_reason": reason,
    }


class AudioChunkLogger:
    """Appends one JSON record per chunk (or per missingness event) to
    CHUNK_LOG_PATH -- its own file, its own record type, never mixed with
    video sample/window_summary records. subject_id/context_id/device_id
    are REQUIRED constructor arguments (D0PA1 hard constraint #7 -- present
    from the first record, never optional here)."""

    def __init__(self, subject_id, context_id, device_id, session_id, config, log_path=None):
        if not subject_id or not context_id or not device_id:
            raise ValueError("subject_id, context_id, and device_id are all required from the first record")
        self.subject_id = subject_id
        self.context_id = context_id
        self.device_id = device_id
        self.session_id = session_id
        self.config = config
        self.log_path = log_path or CHUNK_LOG_PATH
        self._seq = 0
        self._lock = threading.Lock()

    def _write(self, record):
        directory = os.path.dirname(os.path.abspath(self.log_path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

    def log_chunk(self, samples, buffer_size_frames, dropout_count, overrun_count, portaudio_adc_time):
        with self._lock:
            seq = self._seq
            self._seq += 1
        record = {
            "schema_version": SCHEMA_VERSION,
            "record_type": RECORD_TYPE,
            "session_id": self.session_id,
            "subject_id": self.subject_id,
            "context_id": self.context_id,
            "device_id": self.device_id,
            "seq": seq,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "chunk_ts_perf_counter": time.perf_counter(),
            "chunk_ts_portaudio_adc": portaudio_adc_time,
            "clock_sources": {
                "chunk_ts_perf_counter": "time.perf_counter() -- same monotonic clock convention as the rest of this repository",
                "chunk_ts_portaudio_adc": "PortAudio inputBufferAdcTime via sounddevice's callback `time` argument -- hardware/driver-timestamped ADC time",
            },
            "config_hash": self.config.config_hash(),
            "sample_rate_hz": self.config.sample_rate_hz,
            "channels": self.config.channels,
            "bit_depth": 32,
            "buffer_size_frames": buffer_size_frames,
            "dropout_count": dropout_count,
            "overrun_count": overrun_count,
            "level": compute_level_stats(samples),
            "missingness_flag": False,
            "missingness_reason": None,
        }
        self._write(record)
        return record

    def log_missing(self, reason):
        with self._lock:
            seq = self._seq
            self._seq += 1
        record = _missing_record(
            reason, subject_id=self.subject_id, context_id=self.context_id,
            device_id=self.device_id, session_id=self.session_id, config=self.config, seq=seq,
        )
        self._write(record)
        return record


class AudioAcquisitionThread:
    """Own thread, non-blocking with respect to T1/T2 (see module
    docstring). Uses sounddevice's callback-based InputStream: PortAudio
    delivers each chunk on its own internally-managed thread, so this class
    never polls, never blocks on a read() call, and shares no lock or
    buffer with the video capture/processing threads -- structurally
    decoupled the same way T1 and T2 are decoupled from each other
    (MANDATORY ARCHITECTURE #1), just a third, entirely independent stream.

    write_raw_capture: OFF by default (None). Only Task 4's sync
    measurement passes a real path, and that path must resolve OUTSIDE
    REPO_ROOT (checked in __init__, raises otherwise) -- see module
    docstring's NO CONTENT ANALYSIS section. When set, raw float32 samples
    are appended to that file for the duration of capture only; nothing in
    this class ever deletes it -- the caller (Task 4's own script) is
    responsible for deleting it immediately after measurement and confirms
    that deletion explicitly, per this task's own instruction.
    """

    def __init__(self, config, logger, write_raw_path=None, cumulative_dropout=True):
        self.config = config
        self.logger = logger
        self.write_raw_path = write_raw_path
        if write_raw_path is not None:
            resolved = os.path.abspath(write_raw_path)
            if resolved == REPO_ROOT or resolved.startswith(REPO_ROOT + os.sep):
                raise ValueError(
                    f"write_raw_path {write_raw_path!r} resolves inside this repository "
                    f"({REPO_ROOT}) -- raw audio must never be written inside the repo (G4)."
                )
        self._stream = None
        self._dropout_count = 0
        self._overrun_count = 0
        self._device_disappeared = threading.Event()
        self._intentional_stop = threading.Event()
        self._raw_file = None

    def _callback(self, indata, frames, time_info, status):
        # status is sounddevice's CallbackFlags -- input_overflow means
        # PortAudio genuinely lost samples (buffer_overrun), input_underflow
        # is the output-side equivalent (not applicable to input-only), and
        # any other truthy status bit is logged as an overrun too rather
        # than silently ignored, since this module has no way to
        # distinguish every possible driver-level flag more finely without
        # inventing an interpretation G2 would not license.
        if status:
            self._overrun_count += 1
            if getattr(status, "input_overflow", False):
                self._dropout_count += 1

        adc_time = getattr(time_info, "inputBufferAdcTime", None)
        samples = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()

        if self._raw_file is not None:
            samples.tofile(self._raw_file)

        self.logger.log_chunk(
            samples=samples,
            buffer_size_frames=frames,
            dropout_count=self._dropout_count,
            overrun_count=self._overrun_count,
            portaudio_adc_time=adc_time,
        )

    def start(self):
        import sounddevice as sd

        if self.write_raw_path is not None:
            directory = os.path.dirname(os.path.abspath(self.write_raw_path))
            if directory:
                os.makedirs(directory, exist_ok=True)
            self._raw_file = open(self.write_raw_path, "wb")

        chunk_frames = int(self.config.sample_rate_hz * self.config.chunk_seconds)
        try:
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate_hz,
                channels=self.config.channels,
                dtype="float32",
                blocksize=chunk_frames,
                device=self.config.device,
                callback=self._callback,
                finished_callback=self._on_finished,
            )
            self._stream.start()
        except Exception:
            self.logger.log_missing("device_unavailable")
            self._close_raw_file()
            raise

    def _on_finished(self):
        # sounddevice invokes this whenever the stream stops, for ANY
        # reason -- including our own, deliberate stop() below. Found by
        # testing against the real device (Task 3's own point): an earlier
        # version of this method logged "device_disconnected_mid_session"
        # unconditionally here, which meant every NORMAL stop() call was
        # mislogged as an unexpected disconnection. _intentional_stop is
        # set BEFORE stream.stop() is called in stop() below, specifically
        # so this callback can tell the two cases apart -- only an
        # unrequested stop (the device actually disappearing while this
        # class did not ask it to) is missingness; a deliberate stop is not
        # a gap in the stream, it is the stream ending on purpose.
        if self._intentional_stop.is_set():
            return
        if not self._device_disappeared.is_set():
            self._device_disappeared.set()
            self.logger.log_missing("device_disconnected_mid_session")

    def stop(self):
        self._intentional_stop.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._close_raw_file()

    def _close_raw_file(self):
        if self._raw_file is not None:
            self._raw_file.close()
            self._raw_file = None

    def is_running(self):
        return self._stream is not None and self._stream.active
