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

USAGE:
    from simulation.provenance import capture_run_provenance
    provenance = capture_run_provenance(label="null_input")
    # stamp provenance.experiment_id / .git_commit_hash / .git_dirty onto
    # every record this run produces.
"""

import hashlib
import json
import os
import platform
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

    return RunProvenance(
        experiment_id=experiment_id,
        git_commit_hash=git_commit_hash,
        git_dirty=git_dirty,
        git_dirty_reason=git_dirty_reason,
        git_check_error=git_check_error,
        hostname=platform.node(),
        captured_at_utc=datetime.now(timezone.utc).isoformat(),
    )
