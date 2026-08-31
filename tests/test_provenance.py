"""
D0PA1 Gate 0, A1 -- run provenance validation (runnable directly, no
pytest). Covers: experiment_id uniqueness/human-readability, real-repo git
commit hash + dirty-flag detection, the "never silently clean" failure mode
when git cannot be queried, and provenance_hash's reproducibility/
sensitivity contract (same pattern as tests/test_config.py's config_hash
checks).
"""

import os
import subprocess
import sys
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.provenance import capture_run_provenance, RunProvenance, _run_git


def check_experiment_id_unique_and_readable():
    p1 = capture_run_provenance(label="test_run")
    p2 = capture_run_provenance(label="test_run")
    unique = p1.experiment_id != p2.experiment_id
    readable = p1.experiment_id.startswith("test_run_") and "T" in p1.experiment_id and "Z" in p1.experiment_id
    return unique and readable, {"id1": p1.experiment_id, "id2": p2.experiment_id}


def check_real_repo_reports_commit_and_clean_or_dirty():
    """This repo IS a real git repository -- capture_run_provenance should
    find a real commit hash, and git_dirty should exactly match what `git
    status --porcelain` itself reports right now (checked independently,
    not assumed)."""
    p = capture_run_provenance()
    ok_ok, status_out = _run_git(["status", "--porcelain"])
    expected_dirty = bool(status_out.strip()) if ok_ok else True
    commit_present = p.git_commit_hash is not None and len(p.git_commit_hash) == 40
    dirty_matches = p.git_dirty == expected_dirty
    return commit_present and dirty_matches, {
        "git_commit_hash": p.git_commit_hash,
        "git_dirty": p.git_dirty,
        "expected_dirty": expected_dirty,
        "git_dirty_reason": p.git_dirty_reason,
    }


def check_git_failure_reports_dirty_never_clean():
    """If git cannot be queried at all (simulated here), the requirement is
    explicit: never silently present the tree as clean. Both the commit
    hash AND status queries are mocked to fail."""
    with mock.patch("simulation.provenance._run_git", return_value=(False, "simulated: git not found")):
        p = capture_run_provenance()
    ok = p.git_dirty is True and p.git_commit_hash is None and p.git_check_error is not None
    return ok, {
        "git_dirty": p.git_dirty,
        "git_commit_hash": p.git_commit_hash,
        "git_check_error": p.git_check_error,
    }


def check_provenance_hash_reproducible_and_sensitive():
    p1 = RunProvenance(
        experiment_id="fixed_id", git_commit_hash="abc123", git_dirty=False,
        git_dirty_reason=None, git_check_error=None, hostname="host-a",
        captured_at_utc="2026-01-01T00:00:00+00:00",
    )
    p2 = RunProvenance(
        experiment_id="fixed_id", git_commit_hash="abc123", git_dirty=False,
        git_dirty_reason=None, git_check_error=None, hostname="host-a",
        captured_at_utc="2026-01-01T00:00:00+00:00",
    )
    p3 = RunProvenance(
        experiment_id="fixed_id", git_commit_hash="def456", git_dirty=False,
        git_dirty_reason=None, git_check_error=None, hostname="host-a",
        captured_at_utc="2026-01-01T00:00:00+00:00",
    )
    same = p1.provenance_hash() == p2.provenance_hash()
    different = p1.provenance_hash() != p3.provenance_hash()
    return same and different, (p1.provenance_hash(), p2.provenance_hash(), p3.provenance_hash())


if __name__ == "__main__":
    failures = []

    ok, detail = check_experiment_id_unique_and_readable()
    print(f"[1/4] EXPERIMENT_ID UNIQUE + HUMAN-READABLE -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"experiment_id check failed: {detail}")

    ok, detail = check_real_repo_reports_commit_and_clean_or_dirty()
    print(f"[2/4] REAL REPO: COMMIT HASH PRESENT, DIRTY FLAG MATCHES `git status` -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"real-repo provenance check failed: {detail}")

    ok, detail = check_git_failure_reports_dirty_never_clean()
    print(f"[3/4] GIT-UNAVAILABLE -> REPORTED DIRTY, NEVER SILENTLY CLEAN -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"git-failure fallback did not report dirty: {detail}")

    ok, detail = check_provenance_hash_reproducible_and_sensitive()
    print(f"[4/4] PROVENANCE_HASH REPRODUCIBLE + SENSITIVE TO CHANGE -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"provenance_hash did not behave as expected: {detail}")

    print()
    if failures:
        print(f"PROVENANCE VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("PROVENANCE VALIDATION: PASS")
