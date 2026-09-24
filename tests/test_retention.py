"""
D0PA1 privacy/retention validation (runnable directly, no pytest). Every check here
operates on a throwaway temp directory created and destroyed by this test -- NONE of
these checks ever point RetentionConfig.storage_location at this repository's real
logs/ directory. That would risk actually deleting real historical session data from a
test run, which is exactly the hazard the dry-run default exists to prevent; a test
file is not an exception to that.
"""

import json
import os
import shutil
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from privacy.retention import RetentionConfig, scan_expired_files, run_retention, NEVER_DELETE_BASENAMES, RAW_MEDIA_RETENTION_DAYS


def _make_scratch_dir():
    d = tempfile.mkdtemp(prefix="d0pa1_retention_test_")
    return d


def _touch(path, age_days_ago):
    with open(path, "w", encoding="utf-8") as f:
        f.write("synthetic test content, not real session data\n")
    old_time = time.time() - age_days_ago * 86400.0
    os.utime(path, (old_time, old_time))


def check_dry_run_is_the_default():
    ok = RetentionConfig().dry_run is True
    return ok, RetentionConfig().dry_run


def check_scan_classifies_expired_correctly():
    scratch = _make_scratch_dir()
    try:
        _touch(os.path.join(scratch, "old_session.jsonl"), age_days_ago=400)
        _touch(os.path.join(scratch, "recent_session.jsonl"), age_days_ago=10)
        cfg = RetentionConfig(retention_days=365.0, storage_location=scratch)
        rows = scan_expired_files(cfg)
        by_name = {r["basename"]: r for r in rows}
        ok = (
            len(rows) == 2
            and by_name["old_session.jsonl"]["expired"] is True
            and by_name["recent_session.jsonl"]["expired"] is False
        )
        return ok, {k: v["expired"] for k, v in by_name.items()}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def check_never_delete_basenames_excluded_from_scan():
    scratch = _make_scratch_dir()
    try:
        for name in NEVER_DELETE_BASENAMES:
            _touch(os.path.join(scratch, name), age_days_ago=1000)  # deliberately ancient
        cfg = RetentionConfig(retention_days=1.0, storage_location=scratch)
        rows = scan_expired_files(cfg)
        return len(rows) == 0, [r["basename"] for r in rows]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def check_dry_run_deletes_nothing_and_writes_no_log():
    scratch = _make_scratch_dir()
    try:
        target = os.path.join(scratch, "old_session.jsonl")
        _touch(target, age_days_ago=400)
        deletion_log = os.path.join(scratch, "deletion_log.jsonl")
        cfg = RetentionConfig(retention_days=365.0, storage_location=scratch, dry_run=True)
        report = run_retention(cfg, deletion_log_path=deletion_log)
        ok = (
            os.path.exists(target)  # file still there
            and not os.path.exists(deletion_log)  # dry run wrote no log at all
            and report["record_type"] == "retention_dry_run"
            and report["n_expired"] == 1
            and "would_delete" in report
            and "deleted" not in report
        )
        return ok, report
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def check_real_run_deletes_expired_keeps_fresh_and_logs_both_correctly():
    scratch = _make_scratch_dir()
    try:
        expired_path = os.path.join(scratch, "old_session.jsonl")
        fresh_path = os.path.join(scratch, "recent_session.jsonl")
        _touch(expired_path, age_days_ago=400)
        _touch(fresh_path, age_days_ago=10)
        deletion_log = os.path.join(scratch, "deletion_log.jsonl")

        cfg = RetentionConfig(retention_days=365.0, storage_location=scratch, dry_run=False)
        report = run_retention(cfg, deletion_log_path=deletion_log)

        expired_gone = not os.path.exists(expired_path)
        fresh_kept = os.path.exists(fresh_path)

        with open(deletion_log, "r", encoding="utf-8") as f:
            log_lines = [json.loads(line) for line in f if line.strip()]
        log_ok = (
            len(log_lines) == 1
            and log_lines[0]["basename"] == "old_session.jsonl"
            and log_lines[0]["record_type"] == "deletion"
            and "sha256" in log_lines[0] and len(log_lines[0]["sha256"]) == 64
            and "deleted_at_utc" in log_lines[0]
        )
        report_ok = report["n_expired"] == 1 and "deleted" in report and "path" in report["deleted"][0]

        ok = expired_gone and fresh_kept and log_ok and report_ok
        return ok, {"expired_gone": expired_gone, "fresh_kept": fresh_kept, "log_lines": len(log_lines)}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def check_missing_storage_location_returns_empty_not_error():
    cfg = RetentionConfig(storage_location=os.path.join(tempfile.gettempdir(), "d0pa1_does_not_exist_" + str(time.time())))
    rows = scan_expired_files(cfg)
    return rows == [], rows


def check_config_hash_reproducible_and_sensitive():
    a = RetentionConfig(retention_days=365.0)
    b = RetentionConfig(retention_days=365.0)
    c = RetentionConfig(retention_days=90.0)
    return (a.config_hash() == b.config_hash() and a.config_hash() != c.config_hash()), (a.config_hash(), c.config_hash())


def check_raw_media_retention_days_matches_signoff_and_does_not_leak_into_default():
    """D0PA1_Client_SignOff_001.md sec5.1 (2026-09-19): RAW_MEDIA_RETENTION_DAYS
    must equal the accepted 90-day figure, must be config_hash-sensitive when
    actually used, and -- the important negative check -- RetentionConfig's
    own bare, zero-argument default must be UNCHANGED by this constant's
    existence, since that default governs the derived-logs bucket whose own
    retention the sign-off record explicitly leaves undecided ("no change")."""
    ok = RAW_MEDIA_RETENTION_DAYS == 90.0
    bare_default = RetentionConfig()
    ok = ok and bare_default.retention_days == 365.0  # unchanged -- still the generic placeholder
    raw_media_cfg = RetentionConfig(retention_days=RAW_MEDIA_RETENTION_DAYS, storage_location="X:\\somewhere_outside_the_repo")
    ok = ok and raw_media_cfg.config_hash() != bare_default.config_hash()
    return ok, {
        "RAW_MEDIA_RETENTION_DAYS": RAW_MEDIA_RETENTION_DAYS,
        "bare_default_retention_days": bare_default.retention_days,
        "hashes_differ": raw_media_cfg.config_hash() != bare_default.config_hash(),
    }


def check_cli_requires_explicit_execute_flag():
    """Structural check, not a subprocess run: confirms argparse's --execute is
    store_true (absent by default => dry_run stays True) by reading the module
    source rather than invoking the CLI, so this test needs no real files at all."""
    import inspect
    import privacy.retention as mod
    source = inspect.getsource(mod)
    ok = '"--execute"' in source and "store_true" in source and "dry_run=not args.execute" in source
    return ok, "checked source for --execute/store_true/dry_run=not args.execute"


if __name__ == "__main__":
    failures = []
    checks = [
        ("dry_run is the RetentionConfig default", check_dry_run_is_the_default),
        ("scan classifies expired vs fresh correctly", check_scan_classifies_expired_correctly),
        ("never-delete basenames excluded from scan", check_never_delete_basenames_excluded_from_scan),
        ("dry run deletes nothing, writes no log", check_dry_run_deletes_nothing_and_writes_no_log),
        ("real run deletes expired, keeps fresh, logs correctly", check_real_run_deletes_expired_keeps_fresh_and_logs_both_correctly),
        ("missing storage_location -> empty scan, not an error", check_missing_storage_location_returns_empty_not_error),
        ("config_hash reproducible + sensitive to change", check_config_hash_reproducible_and_sensitive),
        ("RAW_MEDIA_RETENTION_DAYS matches sign-off, doesn't leak into the bare default", check_raw_media_retention_days_matches_signoff_and_does_not_leak_into_default),
        ("CLI requires explicit --execute to disable dry-run", check_cli_requires_explicit_execute_flag),
    ]
    for i, (name, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {name} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(name)

    print()
    if failures:
        print(f"RETENTION VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("RETENTION VALIDATION: PASS")
    print("\nNOTE: every check above ran against a throwaway temp directory. This repository's")
    print("real logs/ directory was never scanned or touched by this test.")
