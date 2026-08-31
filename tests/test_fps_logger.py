"""
D0PA1 Part C, C3 -- FPS logger validation (runnable directly, no pytest;
no camera required -- synthetic timestamps throughout). Covers: no record
on the first call (only starts the clock), a flush happens once
interval_seconds elapses and counters reset afterward, captured/processed/
dropped counts and drop reasons are recorded accurately, computed FPS
matches hand arithmetic, and the experiment_id is stamped on every record.
"""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.fps_logger import FPSLogger


def check_first_call_starts_clock_no_flush():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = FPSLogger(os.path.join(tmpdir, "fps.jsonl"), experiment_id="exp1", interval_seconds=3.0)
        result = logger.maybe_flush(now=100.0)
        file_exists_but_empty = not os.path.exists(logger.log_path) or os.path.getsize(logger.log_path) == 0
        ok = result is None and file_exists_but_empty
        return ok, {"result": result, "file_exists_but_empty": file_exists_but_empty}


def check_flush_after_interval_with_correct_counts_and_fps():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = FPSLogger(os.path.join(tmpdir, "fps.jsonl"), experiment_id="exp1", interval_seconds=3.0)
        logger.maybe_flush(now=100.0)  # starts clock, no flush

        logger.record_captured(30)
        logger.record_processed(28)
        logger.record_dropped("capture_read_failed", 2)

        no_flush_yet = logger.maybe_flush(now=101.5)  # elapsed=1.5s < 3.0s
        record = logger.maybe_flush(now=103.2)  # elapsed=3.2s >= 3.0s -> flush

        expected_capture_fps = 30 / 3.2
        expected_processing_fps = 28 / 3.2

        ok = (
            no_flush_yet is None
            and record is not None
            and record["frames_captured"] == 30
            and record["frames_processed"] == 28
            and record["frames_dropped"] == 2
            and record["drop_reasons"] == {"capture_read_failed": 2}
            and abs(record["capture_fps"] - expected_capture_fps) < 1e-9
            and abs(record["processing_fps"] - expected_processing_fps) < 1e-9
            and record["experiment_id"] == "exp1"
        )
        return ok, {"record": record}


def check_counters_reset_after_flush():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = FPSLogger(os.path.join(tmpdir, "fps.jsonl"), experiment_id="exp1", interval_seconds=2.0)
        logger.maybe_flush(now=0.0)
        logger.record_captured(10)
        first = logger.maybe_flush(now=2.0)

        # second window: NO new frames recorded -- must report 0, not carry over the 10 from before.
        second = logger.maybe_flush(now=4.0)

        ok = first["frames_captured"] == 10 and second["frames_captured"] == 0 and second["drop_reasons"] == {}
        return ok, {"first": first, "second": second}


def check_multiple_drop_reasons_tallied_independently():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = FPSLogger(os.path.join(tmpdir, "fps.jsonl"), experiment_id="exp1", interval_seconds=1.0)
        logger.maybe_flush(now=0.0)
        logger.record_dropped("capture_read_failed", 3)
        logger.record_dropped("buffer_overwrite", 5)
        logger.record_dropped("capture_read_failed", 1)  # accumulates into the same reason
        record = logger.maybe_flush(now=1.5)

        ok = record["frames_dropped"] == 9 and record["drop_reasons"] == {"capture_read_failed": 4, "buffer_overwrite": 5}
        return ok, {"record": record}


def check_records_appended_to_real_file_as_valid_jsonl():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "fps.jsonl")
        logger = FPSLogger(log_path, experiment_id="exp_real_file", interval_seconds=1.0)
        logger.maybe_flush(now=0.0)
        logger.record_captured(5)
        logger.maybe_flush(now=1.2)
        logger.record_captured(6)
        logger.maybe_flush(now=2.5)

        with open(log_path, encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        ok = len(lines) == 2 and all(l["record_type"] == "fps_metric" and l["experiment_id"] == "exp_real_file" for l in lines)
        return ok, {"n_lines": len(lines), "lines": lines}


if __name__ == "__main__":
    checks = [
        ("FIRST CALL STARTS CLOCK, NO FLUSH, NO FILE WRITE YET", check_first_call_starts_clock_no_flush),
        ("FLUSH AFTER INTERVAL: COUNTS + FPS MATCH HAND ARITHMETIC", check_flush_after_interval_with_correct_counts_and_fps),
        ("COUNTERS RESET AFTER EACH FLUSH (NO CARRY-OVER)", check_counters_reset_after_flush),
        ("MULTIPLE DROP REASONS TALLIED INDEPENDENTLY, NOT BLENDED", check_multiple_drop_reasons_tallied_independently),
        ("RECORDS APPENDED TO REAL FILE AS VALID JSONL", check_records_appended_to_real_file_as_valid_jsonl),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"FPS LOGGER VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("FPS LOGGER VALIDATION: PASS")
