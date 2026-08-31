"""
D0PA1 Gate 0, A1 -- RUN PROVENANCE.

Every run of this pipeline (a real session, a control, a simulation sweep)
should be able to answer "what code, exactly, produced this data": a unique
human-readable experiment_id, the git commit hash of the code that ran, and
whether the working tree was clean at the time. A dirty tree is reported as
dirty -- NEVER silently presented as clean, and a tree whose cleanliness
could not even be checked is treated as dirty too (the failure-safe
direction), not defaulted to a false "clean".

Deliberately separate from simulation/config.py's PreRegisteredConfig:
PROVENANCE answers "which code and when" (captured fresh, once, per run);
CONFIG answers "which pre-registered parameter values" (fixed once, reused
across many runs). Conflating the two would make it impossible to tell "the
code changed between these two runs" apart from "the same code was
re-parameterized" just by diffing a single object.

GATE 0 B2 -- CONFIG-HASH COVERAGE GAP: PreRegisteredConfig.config_hash()
covers exactly the 3 parameters Gate 0 A2 moved into it. The other 39
constants Gate 0 A2's audit found and deliberately left in place (G5:
load-bearing inside the validated path) are covered by NEITHER
config_hash() nor anything else -- a reader could otherwise reasonably
assume "the config hash" means every behavior-affecting value is pinned,
which was false. validated_path_source_sha256 below closes that: a
whole-file SHA256 over every file Gate 0 A2's audit classified "left in
place, validated path" (see docs/GATE0_PROVENANCE.md section A2's table
and section B2). It answers a DIFFERENT question than config_hash() --
"did the validated-path SOURCE change" vs. "which pre-registered VALUES
are in force" -- and is recorded as a separate field, never merged into
config_hash(), so the two claims stay distinguishable.

USAGE:
    from simulation.provenance import capture_run_provenance
    provenance = capture_run_provenance(label="null_input")
    # stamp provenance.experiment_id / .git_commit_hash / .git_dirty /
    # .validated_path_source_sha256 onto every record this run produces.
"""

import hashlib
import json
import os
import platform
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every file Gate 0 A2's constant audit (docs/GATE0_PROVENANCE.md) classified
# "left in place, validated path" -- i.e. every file this task deliberately
# did NOT move a constant out of, because doing so would touch G5-protected
# code. Whole-file hashing, not constants-only extraction (see
# _hash_validated_path_sources' own docstring for why, and the honest
# consequence that follows from that choice).
VALIDATED_PATH_SOURCE_FILES = (
    "features/x_core.py",
    "features/geometry.py",
    "features/episodes.py",
    "features/attention.py",
    "stage1_step4_vectors.py",
)


def _hash_validated_path_sources():
    """Returns (aggregate_sha256, per_file_sha256_dict).

    Whole-file hashing, deliberately, not a surgical "extract just the
    constant assignments" parse: the task asks this to catch "a behavioural
    change" broadly, and a whole-file hash catches ANY edit to a file that
    HOLDS validated-path constants, not only a change to a constant's own
    literal. The honest consequence, stated once here rather than left for
    a reader to discover: an unrelated edit to one of these files (e.g. a
    comment, a docstring, a print statement) also moves this hash, even
    though no constant's VALUE changed. That is over-inclusive by design --
    for an integrity check, a false "something changed" that a reader can
    dismiss after a two-second diff is a far cheaper failure mode than a
    false "nothing changed" that hides a real constant edit inside noise.

    per_file_sha256_dict lets a reader who sees the aggregate move
    immediately identify WHICH of the 5 files changed, without re-deriving
    it themselves."""
    per_file = {}
    for rel_path in VALIDATED_PATH_SOURCE_FILES:
        full_path = os.path.join(REPO_ROOT, *rel_path.split("/"))
        try:
            with open(full_path, "rb") as f:
                per_file[rel_path] = hashlib.sha256(f.read()).hexdigest()
        except OSError as e:
            # A listed file that can't be read is itself a provenance-
            # relevant fact (moved/deleted/renamed) -- recorded as a string
            # explaining why, not silently skipped out of the aggregate.
            per_file[rel_path] = f"UNREADABLE: {e}"

    # Aggregate is a hash of the sorted "path:hash" pairs -- file iteration
    # order never matters, and an unreadable file still participates (its
    # error string is part of what gets hashed), so it can't be silently
    # dropped from the aggregate either.
    combined = "\n".join(f"{path}:{per_file[path]}" for path in sorted(per_file))
    aggregate = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    return aggregate, per_file


def _run_git(args):
    """Runs a git command against REPO_ROOT. Returns (ok, output_or_error).
    Never raises -- git being absent, timing out, or erroring is a real,
    reportable condition (see capture_run_provenance's dirty-by-default
    handling), not something this helper should crash on."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"git invocation failed: {e}"
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        return False, err or f"git exited with code {result.returncode}"
    return True, result.stdout.strip()


def _generate_experiment_id(label=None):
    """<label_>[UTC timestamp]_[8 hex chars]. Timestamp alone is not
    collision-safe -- two runs can start within the same second -- the
    random suffix is, at negligible cost to readability. label is purely
    cosmetic (a human-chosen tag like "null_input" or "gate3_analysis"),
    never parsed back out of the id programmatically."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:8]
    prefix = f"{label}_" if label else ""
    return f"{prefix}{ts}_{suffix}"


@dataclass(frozen=True)
class RunProvenance:
    """Captured ONCE at the start of a run and meant to be stamped onto
    every record/log/summary that run produces."""

    experiment_id: str
    git_commit_hash: Optional[str]
    git_dirty: bool
    git_dirty_reason: Optional[str]
    git_check_error: Optional[str]
    hostname: str
    captured_at_utc: str
    # Gate 0 B2: answers "did the validated-path SOURCE change", a
    # different question from PreRegisteredConfig.config_hash()'s "which
    # pre-registered VALUES are in force" -- see module docstring's B2
    # section. Deliberately a SEPARATE field, never merged into
    # config_hash() or provenance_hash() as a single blended number.
    validated_path_source_sha256: str = ""
    validated_path_source_files: Dict[str, str] = field(default_factory=dict)

    def provenance_hash(self):
        """Same short-stable-hash pattern as PreRegisteredConfig.config_hash
        / NullInputConfig.config_hash -- lets a downstream record cite one
        short token instead of repeating every field."""
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


def capture_run_provenance(label=None):
    """label: optional short human-readable tag folded into experiment_id
    (see _generate_experiment_id). Safe to call with no git repository
    present (git_commit_hash becomes None, git_dirty becomes True with a
    stated reason) -- this must never raise merely because provenance
    could not be fully determined; an incomplete provenance record, clearly
    marked as such, is the honest output (G3), not an exception that takes
    down the run it was meant to describe."""
    experiment_id = _generate_experiment_id(label)

    commit_ok, commit_out = _run_git(["rev-parse", "HEAD"])
    git_commit_hash = commit_out if commit_ok else None

    status_ok, status_out = _run_git(["status", "--porcelain"])
    if status_ok:
        n_dirty_paths = len([line for line in status_out.splitlines() if line.strip()])
        git_dirty = n_dirty_paths > 0
        git_dirty_reason = f"{n_dirty_paths} modified/untracked path(s)" if git_dirty else None
        git_check_error = None
    else:
        # Cannot verify cleanliness at all -- per the requirement, this must
        # NEVER be presented as clean by default. Marked dirty, with the
        # underlying git error recorded so a reader can tell "actually
        # dirty" apart from "couldn't check" without losing the distinction.
        git_dirty = True
        git_dirty_reason = "git status could not be determined -- see git_check_error"
        git_check_error = status_out

    source_aggregate, source_per_file = _hash_validated_path_sources()

    return RunProvenance(
        experiment_id=experiment_id,
        git_commit_hash=git_commit_hash,
        git_dirty=git_dirty,
        git_dirty_reason=git_dirty_reason,
        git_check_error=git_check_error,
        hostname=platform.node(),
        captured_at_utc=datetime.now(timezone.utc).isoformat(),
        validated_path_source_sha256=source_aggregate,
        validated_path_source_files=source_per_file,
    )
