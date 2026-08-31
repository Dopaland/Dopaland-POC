"""
D0PA1 Gate 0, A1 + B2 -- run provenance validation (runnable directly, no
pytest). Covers: experiment_id uniqueness/human-readability, real-repo git
commit hash + dirty-flag detection, the "never silently clean" failure mode
when git cannot be queried, provenance_hash's reproducibility/sensitivity
contract, and (B2) validated_path_source_sha256's presence against the real
repo plus its change-on-edit/revert-on-revert behavior against a synthetic
file tree (never the real repository files -- see
check_source_hash_changes_on_edit_and_reverts' own docstring for why).
"""

import os
import subprocess
import sys
import tempfile
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import simulation.provenance as provenance_module
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


def check_real_repo_source_hash_present_and_distinct_from_config_hash():
    """B2.1: against THIS real repository, validated_path_source_sha256
    must be populated, cover exactly the 5 declared files with real-looking
    64-hex-char SHA256 strings, and be a genuinely separate value from
    PreRegisteredConfig.config_hash() -- the whole point of B2 is that
    these answer different questions and must never collapse into the same
    number by construction."""
    from simulation.config import PRE_REGISTERED_CONFIG

    p = capture_run_provenance()
    aggregate_looks_like_sha256 = isinstance(p.validated_path_source_sha256, str) and len(p.validated_path_source_sha256) == 64
    all_files_present = set(p.validated_path_source_files.keys()) == set(provenance_module.VALIDATED_PATH_SOURCE_FILES)
    all_hashes_look_real = all(
        isinstance(h, str) and len(h) == 64 for h in p.validated_path_source_files.values()
    )
    distinct_from_config_hash = p.validated_path_source_sha256 != PRE_REGISTERED_CONFIG.config_hash()

    ok = aggregate_looks_like_sha256 and all_files_present and all_hashes_look_real and distinct_from_config_hash
    return ok, {
        "validated_path_source_sha256": p.validated_path_source_sha256,
        "files_covered": sorted(p.validated_path_source_files.keys()),
        "all_hashes_look_real": all_hashes_look_real,
        "config_hash": PRE_REGISTERED_CONFIG.config_hash(),
        "distinct_from_config_hash": distinct_from_config_hash,
    }


def check_source_hash_changes_on_edit_and_reverts():
    """B2.2, automated: proves _hash_validated_path_sources() actually
    reacts to a file edit and returns to the original value on revert --
    against a SYNTHETIC file tree built in a temp dir (REPO_ROOT and
    VALIDATED_PATH_SOURCE_FILES monkeypatched for the duration), never the
    real repository files. The real-file version of this same proof (real
    x_core.py, real hash values, pasted in the task's report) was run
    manually once as the primary evidence; this test exists so the
    mechanism keeps being checked automatically on every future run,
    without an automated test ever having to mutate real source files."""
    original_repo_root = provenance_module.REPO_ROOT
    original_files = provenance_module.VALIDATED_PATH_SOURCE_FILES
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            rel_paths = ("fake_a.py", "fake_b.py")
            for rp in rel_paths:
                with open(os.path.join(tmpdir, rp), "w", encoding="utf-8") as f:
                    f.write("X = 1\n")

            provenance_module.REPO_ROOT = tmpdir
            provenance_module.VALIDATED_PATH_SOURCE_FILES = rel_paths

            agg_before, per_before = provenance_module._hash_validated_path_sources()

            with open(os.path.join(tmpdir, "fake_a.py"), "w", encoding="utf-8") as f:
                f.write("X = 2\n")
            agg_changed, per_changed = provenance_module._hash_validated_path_sources()

            with open(os.path.join(tmpdir, "fake_a.py"), "w", encoding="utf-8") as f:
                f.write("X = 1\n")
            agg_reverted, per_reverted = provenance_module._hash_validated_path_sources()

        aggregate_moved = agg_before != agg_changed
        edited_file_hash_moved = per_before["fake_a.py"] != per_changed["fake_a.py"]
        untouched_file_hash_stable = per_before["fake_b.py"] == per_changed["fake_b.py"]
        aggregate_reverted = agg_reverted == agg_before
        per_file_reverted = per_reverted["fake_a.py"] == per_before["fake_a.py"]

        ok = aggregate_moved and edited_file_hash_moved and untouched_file_hash_stable and aggregate_reverted and per_file_reverted
        return ok, {
            "agg_before": agg_before, "agg_changed": agg_changed, "agg_reverted": agg_reverted,
            "aggregate_moved": aggregate_moved, "untouched_file_hash_stable": untouched_file_hash_stable,
            "aggregate_reverted": aggregate_reverted,
        }
    finally:
        provenance_module.REPO_ROOT = original_repo_root
        provenance_module.VALIDATED_PATH_SOURCE_FILES = original_files


if __name__ == "__main__":
    failures = []

    ok, detail = check_experiment_id_unique_and_readable()
    print(f"[1/6] EXPERIMENT_ID UNIQUE + HUMAN-READABLE -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"experiment_id check failed: {detail}")

    ok, detail = check_real_repo_reports_commit_and_clean_or_dirty()
    print(f"[2/6] REAL REPO: COMMIT HASH PRESENT, DIRTY FLAG MATCHES `git status` -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"real-repo provenance check failed: {detail}")

    ok, detail = check_git_failure_reports_dirty_never_clean()
    print(f"[3/6] GIT-UNAVAILABLE -> REPORTED DIRTY, NEVER SILENTLY CLEAN -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"git-failure fallback did not report dirty: {detail}")

    ok, detail = check_provenance_hash_reproducible_and_sensitive()
    print(f"[4/6] PROVENANCE_HASH REPRODUCIBLE + SENSITIVE TO CHANGE -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"provenance_hash did not behave as expected: {detail}")

    ok, detail = check_real_repo_source_hash_present_and_distinct_from_config_hash()
    print(f"[5/6] B2: VALIDATED_PATH_SOURCE_SHA256 PRESENT (5 FILES) + DISTINCT FROM CONFIG_HASH -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"validated_path_source_sha256 check failed: {detail}")

    ok, detail = check_source_hash_changes_on_edit_and_reverts()
    print(f"[6/6] B2: SOURCE HASH CHANGES ON EDIT, RETURNS TO ORIGINAL ON REVERT -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"source-hash change/revert behavior failed: {detail}")

    print()
    if failures:
        print(f"PROVENANCE VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("PROVENANCE VALIDATION: PASS")
