"""
Audio acquisition module validation (Task 3), pure-computation pieces only
-- same discipline as controls/null_input.py: the device-loop orchestration
itself needs real hardware and a real session (covered separately, by hand,
in this task's own report, not by this automated suite); everything that
does NOT need a live device is unit-tested here against synthetic/injected
input, never a real recording.
"""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np

from audio_acquisition import (
    AUDIO_MISSINGNESS_REASONS, AudioAcquisitionThread, AudioCaptureConfig,
    AudioChunkLogger, compute_level_stats,
)


def check_level_silence():
    samples = np.zeros(4800, dtype=np.float32)
    stats = compute_level_stats(samples)
    ok = stats["peak_abs"] == 0.0 and stats["rms"] == 0.0 and stats["clipping_detected"] is False
    return ok, stats


def check_level_moderate_signal():
    rng = np.random.default_rng(0)
    samples = (rng.standard_normal(4800).astype(np.float32) * 0.1).clip(-1.0, 1.0)
    stats = compute_level_stats(samples)
    ok = 0.0 < stats["rms"] < 0.5 and stats["clipping_detected"] is False
    return ok, stats


def check_level_clipping():
    samples = np.full(4800, 0.9999, dtype=np.float32)
    stats = compute_level_stats(samples)
    ok = stats["clipping_detected"] is True and stats["peak_abs"] >= 0.999
    return ok, stats


def check_level_empty_chunk():
    stats = compute_level_stats(np.array([], dtype=np.float32))
    ok = stats == {"peak_abs": None, "rms": None, "clipping_detected": None}
    return ok, stats


def check_config_hash_stable_and_sensitive():
    a = AudioCaptureConfig(sample_rate_hz=48000, channels=1)
    b = AudioCaptureConfig(sample_rate_hz=48000, channels=1)
    c = AudioCaptureConfig(sample_rate_hz=16000, channels=1)
    ok = a.config_hash() == b.config_hash() and a.config_hash() != c.config_hash()
    return ok, {"a": a.config_hash(), "b": b.config_hash(), "c": c.config_hash()}


def check_logger_requires_ids():
    config = AudioCaptureConfig()
    for kwargs in [
        dict(subject_id="", context_id="ctx", device_id="dev"),
        dict(subject_id="sub", context_id="", device_id="dev"),
        dict(subject_id="sub", context_id="ctx", device_id=""),
    ]:
        try:
            AudioChunkLogger(session_id="s1", config=config, **kwargs)
            return False, f"did not raise for {kwargs}"
        except ValueError:
            pass
    return True, "raised for every missing id field"


def check_logger_writes_complete_chunk_record():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "chunks.jsonl")
        config = AudioCaptureConfig()
        logger = AudioChunkLogger(
            subject_id="SUBJ01", context_id="CTX01", device_id="mic-default",
            session_id="sess-1", config=config, log_path=log_path,
        )
        samples = np.full(48000, 0.1, dtype=np.float32)
        record = logger.log_chunk(
            samples=samples, buffer_size_frames=48000,
            dropout_count=0, overrun_count=0, portaudio_adc_time=123.456,
        )
        with open(log_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        required = {"schema_version", "record_type", "session_id", "subject_id", "context_id",
                    "device_id", "seq", "ts_utc", "chunk_ts_perf_counter", "chunk_ts_portaudio_adc",
                    "clock_sources", "config_hash", "sample_rate_hz", "channels", "bit_depth",
                    "buffer_size_frames", "dropout_count", "overrun_count", "level",
                    "missingness_flag", "missingness_reason"}
        ok = (
            len(lines) == 1
            and required.issubset(lines[0].keys())
            and lines[0]["subject_id"] == "SUBJ01"
            and lines[0]["context_id"] == "CTX01"
            and lines[0]["device_id"] == "mic-default"
            and lines[0]["missingness_flag"] is False
            and lines[0]["missingness_reason"] is None
            and lines[0]["chunk_ts_portaudio_adc"] == 123.456
        )
        return ok, {"record": lines[0] if lines else None}


def check_logger_missing_record_never_absent():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "chunks.jsonl")
        config = AudioCaptureConfig()
        logger = AudioChunkLogger(
            subject_id="SUBJ01", context_id="CTX01", device_id="mic-default",
            session_id="sess-1", config=config, log_path=log_path,
        )
        logger.log_missing("device_disconnected_mid_session")
        with open(log_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        ok = (
            len(lines) == 1
            and lines[0]["missingness_flag"] is True
            and lines[0]["missingness_reason"] == "device_disconnected_mid_session"
            and lines[0]["level"] == {"peak_abs": None, "rms": None, "clipping_detected": None}
        )
        return ok, {"record": lines[0] if lines else None}


def check_missing_reason_must_be_known():
    with tempfile.TemporaryDirectory() as tmp:
        config = AudioCaptureConfig()
        logger = AudioChunkLogger(
            subject_id="S", context_id="C", device_id="D", session_id="s1", config=config,
            log_path=os.path.join(tmp, "x.jsonl"),
        )
        try:
            logger.log_missing("made_up_reason_not_in_vocabulary")
            return False, "did not raise for an unknown reason"
        except ValueError:
            return True, f"raised correctly; known reasons are {sorted(AUDIO_MISSINGNESS_REASONS)}"


def check_seq_increments_across_mixed_calls():
    with tempfile.TemporaryDirectory() as tmp:
        config = AudioCaptureConfig()
        logger = AudioChunkLogger(
            subject_id="S", context_id="C", device_id="D", session_id="s1", config=config,
            log_path=os.path.join(tmp, "x.jsonl"),
        )
        r1 = logger.log_chunk(np.zeros(10, dtype=np.float32), 10, 0, 0, 1.0)
        r2 = logger.log_missing("stream_error")
        r3 = logger.log_chunk(np.zeros(10, dtype=np.float32), 10, 0, 0, 2.0)
        ok = [r1["seq"], r2["seq"], r3["seq"]] == [0, 1, 2]
        return ok, {"seqs": [r1["seq"], r2["seq"], r3["seq"]]}


def check_write_raw_path_inside_repo_rejected():
    config = AudioCaptureConfig()
    logger = AudioChunkLogger(
        subject_id="S", context_id="C", device_id="D", session_id="s1", config=config,
        log_path=os.path.join(tempfile.gettempdir(), "unused.jsonl"),
    )
    inside_repo_path = os.path.join(REPO_ROOT, "should_never_be_created.raw")
    try:
        AudioAcquisitionThread(config=config, logger=logger, write_raw_path=inside_repo_path)
        return False, "did not raise for a raw-output path inside the repository"
    except ValueError as e:
        return True, f"raised correctly: {e}"


def check_intentional_stop_does_not_log_missingness():
    """Regression test for a real bug found by testing against the actual
    device (Task 3): _on_finished() fires on ANY stream stop, including a
    deliberate one -- an earlier version logged
    'device_disconnected_mid_session' unconditionally there, mislabeling
    every normal stop() as an unexpected disconnection. Exercises the
    callback directly (no real device needed) by simulating the sequence
    stop() actually drives: set _intentional_stop, then invoke
    _on_finished(), exactly as sounddevice would after stream.stop()."""
    config = AudioCaptureConfig()
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "chunks.jsonl")
        logger = AudioChunkLogger(
            subject_id="S", context_id="C", device_id="D", session_id="s1",
            config=config, log_path=log_path,
        )
        thread = AudioAcquisitionThread(config=config, logger=logger, write_raw_path=None)
        thread._intentional_stop.set()  # what stop() does before touching the stream
        thread._on_finished()           # what sounddevice invokes when the stream actually stops
        n_records = sum(1 for _ in open(log_path)) if os.path.exists(log_path) else 0
        return n_records == 0, {"n_records_logged": n_records}


def check_unexpected_finish_does_log_missingness():
    """The other half of the same fix: an UNREQUESTED finish (device
    genuinely disappeared, _intentional_stop never set) must still be
    logged as missingness -- the fix must not have overcorrected into
    silently swallowing real disconnection events."""
    config = AudioCaptureConfig()
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "chunks.jsonl")
        logger = AudioChunkLogger(
            subject_id="S", context_id="C", device_id="D", session_id="s1",
            config=config, log_path=log_path,
        )
        thread = AudioAcquisitionThread(config=config, logger=logger, write_raw_path=None)
        thread._on_finished()  # fires with NO prior stop() call -- an unrequested finish
        with open(log_path) as f:
            records = [json.loads(l) for l in f if l.strip()]
        ok = len(records) == 1 and records[0]["missingness_reason"] == "device_disconnected_mid_session"
        return ok, {"records": records}


def check_write_raw_path_outside_repo_accepted():
    config = AudioCaptureConfig()
    logger = AudioChunkLogger(
        subject_id="S", context_id="C", device_id="D", session_id="s1", config=config,
        log_path=os.path.join(tempfile.gettempdir(), "unused.jsonl"),
    )
    outside_path = os.path.join(tempfile.gettempdir(), "d0pa1_audio_sync_test_raw.f32")
    thread = AudioAcquisitionThread(config=config, logger=logger, write_raw_path=outside_path)
    return thread.write_raw_path == outside_path, {"path": thread.write_raw_path}


def run_all():
    checks = [
        ("LEVEL: SILENCE", check_level_silence),
        ("LEVEL: MODERATE SIGNAL", check_level_moderate_signal),
        ("LEVEL: CLIPPING DETECTED", check_level_clipping),
        ("LEVEL: EMPTY CHUNK RETURNS NONES", check_level_empty_chunk),
        ("CONFIG HASH STABLE + SENSITIVE TO CHANGE", check_config_hash_stable_and_sensitive),
        ("LOGGER REQUIRES SUBJECT/CONTEXT/DEVICE ID", check_logger_requires_ids),
        ("LOGGER WRITES A COMPLETE CHUNK RECORD", check_logger_writes_complete_chunk_record),
        ("MISSING RECORD IS A ROW, NEVER ABSENT", check_logger_missing_record_never_absent),
        ("MISSINGNESS REASON MUST BE FROM THE FIXED VOCABULARY", check_missing_reason_must_be_known),
        ("SEQ INCREMENTS ACROSS CHUNK + MISSING CALLS", check_seq_increments_across_mixed_calls),
        ("INTENTIONAL STOP DOES NOT LOG MISSINGNESS (regression)", check_intentional_stop_does_not_log_missingness),
        ("UNEXPECTED FINISH STILL LOGS MISSINGNESS", check_unexpected_finish_does_log_missingness),
        ("WRITE_RAW_PATH INSIDE REPO -- REJECTED", check_write_raw_path_inside_repo_rejected),
        ("WRITE_RAW_PATH OUTSIDE REPO -- ACCEPTED", check_write_raw_path_outside_repo_accepted),
    ]
    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"AUDIO ACQUISITION VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("AUDIO ACQUISITION VALIDATION: PASS")


if __name__ == "__main__":
    run_all()
