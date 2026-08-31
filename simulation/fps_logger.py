"""
D0PA1 Part C, C3 -- continuous FPS logging as a metric.

docs/AUDIT_A_COLUMN.md Q1 finding: FPS was measured and printed to the
console every run, but only written to a FILE as a continuous time series
in --soak mode (opt-in, exercised exactly once in this repository's
history -- logs/soak_log.jsonl). This closes that gap: FPSLogger writes a
time-series JSONL record every interval, in EVERY run, not just soak runs
-- stamped with an experiment_id, and recording frames captured/processed/
dropped plus WHY frames were dropped, not just an FPS number.

Deliberately has no cv2/mediapipe/threading import and takes raw counters
as plain method calls -- this module can be fully unit-tested with
synthetic timestamps and no live camera, the same "pure computation, the
camera loop itself is untested" split docs/CONTROLS.md already documents
for controls/null_input.py's compute_dispersion().

THREAD SAFETY: one FPSLogger instance is meant to be owned by ONE thread
only (e.g. capture_thread gets its own instance, processing_thread gets
its own, each writing to its own file) -- there is no internal lock,
because the intended usage never has two threads calling the same
instance's methods. Do not share one instance across threads; construct
one per thread instead (see stage1_step4_vectors.py's wiring for the
pattern).
"""

import json
import os
import time
from datetime import datetime, timezone


class FPSLogger:
    def __init__(self, log_path, experiment_id, interval_seconds=3.0):
        self.log_path = log_path
        self.experiment_id = experiment_id
        self.interval_seconds = interval_seconds
        self._window_start = None
        self._frames_captured = 0
        self._frames_processed = 0
        self._frames_dropped = 0
        self._drop_reasons = {}
        directory = os.path.dirname(os.path.abspath(log_path))
        if directory:
            os.makedirs(directory, exist_ok=True)

    def record_captured(self, n=1):
        self._frames_captured += n

    def record_processed(self, n=1):
        self._frames_processed += n

    def record_dropped(self, reason, n=1):
        """reason: free-text (this is an operational/diagnostic log, not
        governed by the missingness_reason fixed vocabulary -- a dropped
        FRAME is a capture-pipeline event, not a per-signal missing
        VALUE; the two are related but distinct concepts and are not
        forced into one shared enum)."""
        self._frames_dropped += n
        self._drop_reasons[reason] = self._drop_reasons.get(reason, 0) + n

    def maybe_flush(self, now=None):
        """Call every cycle. Writes and returns ONE record once
        interval_seconds has elapsed since the last flush (or since
        construction, for the very first call, which only starts the
        clock and never flushes on its own -- there is nothing to report
        yet). Returns None on every call that doesn't flush."""
        now = now if now is not None else time.perf_counter()
        if self._window_start is None:
            self._window_start = now
            return None
        elapsed = now - self._window_start
        if elapsed < self.interval_seconds:
            return None

        record = {
            "record_type": "fps_metric",
            "experiment_id": self.experiment_id,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "window_seconds": elapsed,
            "frames_captured": self._frames_captured,
            "frames_processed": self._frames_processed,
            "frames_dropped": self._frames_dropped,
            "drop_reasons": dict(self._drop_reasons),
            "capture_fps": (self._frames_captured / elapsed) if elapsed > 0 else None,
            "processing_fps": (self._frames_processed / elapsed) if elapsed > 0 else None,
        }
        self._append(record)

        self._frames_captured = 0
        self._frames_processed = 0
        self._frames_dropped = 0
        self._drop_reasons = {}
        self._window_start = now
        return record

    def _append(self, record):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
