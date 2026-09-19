"""
D0PA1 privacy and retention (matrix row 30, client addendum §17).

Implements the mechanism §17 asks for: retention period and storage location as
CONFIG parameters (not literals), a deletion routine that removes data past retention
and writes a deletion LOG recording what was deleted and when (so the claim is
verifiable, not merely asserted), and a dry-run mode that is the DEFAULT.

G3, stated plainly, per this task's own instruction: the ACTUAL retention period and
the ACTUAL storage location are policy/business decisions this module does not make.
`RetentionConfig`'s defaults below are ENGINEERING PLACEHOLDERS -- values the code
needs to run and be tested, not a proposed or approved policy. See
docs/PRIVACY_AND_RETENTION.md for what is and is not decided, and PROVENANCE.md's own
open item on where derived-feature logs physically live.

DRY-RUN IS THE DEFAULT, twice over. `RetentionConfig.dry_run` defaults to True, and
`run_retention()` never deletes a single file unless the caller explicitly passes a
config with `dry_run=False`. The CLI entry point at the bottom requires an explicit
`--execute` flag on top of that -- a deletion tool whose default is to delete is a
hazard (this task's own words), so this one requires two separate, deliberate opt-ins
before it deletes anything.

G4: this module only ever deletes/reports on files under `storage_location` -- it
never touches git or git history. The deletion log itself records path, size, mtime and
a SHA256 of each deleted file's content -- never the file's CONTENTS -- so the log
cannot smuggle raw data into version control if it is later committed, the same
discipline `manifest/generate_data_manifest.py` already applies to the (also
git-ignored) files it describes.

G1: this module deletes files that have crossed an age threshold and reports what it
did. It does not decide anything about what a file's presence or absence MEANS for any
scientific result -- retention age is the one, explicit criterion.
"""

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# PLACEHOLDER -- the current, actual, on-disk location of derived-feature logs in this
# checkout. NOT a claim that this is where retained data SHOULD live -- see module
# docstring and docs/PRIVACY_AND_RETENTION.md's "storage location: open decision"
# section. Task 4.2's explicit instruction: implement the location as a parameter with
# the current path as its default, and do not move logs/ as part of this task.
DEFAULT_STORAGE_LOCATION = os.path.join(REPO_ROOT, "logs")
DEFAULT_DELETION_LOG_PATH = os.path.join(REPO_ROOT, "logs", "deletion_log.jsonl")

# Files the retention scan must never consider for deletion. Retention governs raw/
# derived SESSION DATA under storage_location, not this repository's own provenance
# records that happen to share the same directory (logs/variant_log.jsonl is the one
# other file in logs/ that is committed, per Gate 0 A5 / .gitignore's own exception;
# deletion_log.jsonl is this module's own audit trail -- deleting it while auditing
# deletions would defeat the point of keeping one).
NEVER_DELETE_BASENAMES = {"deletion_log.jsonl", "variant_log.jsonl"}

# ACCEPTED by the client, D0PA1_Client_SignOff_001.md sec5.1 (2026-09-18): the
# retention period for RAW MEDIA specifically -- video, and audio if any is
# ever recorded. NOT a decision about derived-feature logs' own retention,
# which remains unaddressed (see module docstring / docs/PRIVACY_AND_RETENTION.md
# -- "no change" per that same record's sec5.2). This is deliberately a
# separate, explicitly-named constant rather than a change to
# RetentionConfig's own class-level default: that default's storage_location
# (logs/, the derived-feature directory) is a DIFFERENT bucket than raw
# media, and silently applying 90 days to it would misrepresent an
# undecided retention as a decided one. A caller retaining raw media should
# construct RetentionConfig(retention_days=RAW_MEDIA_RETENTION_DAYS,
# storage_location=<resolved from privacy.video_storage_config /
# privacy.audio_storage_config>) explicitly.
RAW_MEDIA_RETENTION_DAYS = 90.0


@dataclass(frozen=True)
class RetentionConfig:
    """Every field here is a PARAMETER with a stated placeholder default -- neither
    value is a policy decision (see module docstring)."""

    # PLACEHOLDER. No retention period has been proposed or agreed with the client.
    # This value exists so the mechanism is testable end-to-end, not as a proposed
    # policy number -- do not read 365 as a recommendation.
    retention_days: float = 365.0

    # PLACEHOLDER. The current physical location of logs/ in this checkout. Using it
    # as a default is NOT a decision that raw/derived data should live here -- see
    # PROVENANCE.md's own open item (logs/ sits inside the repository directory,
    # untracked but present; genuinely relocating it outside the repository is a
    # separate, not-yet-made decision this module does not resolve).
    storage_location: str = DEFAULT_STORAGE_LOCATION

    # Hazard-safe default -- see module docstring.
    dry_run: bool = True

    def config_hash(self):
        """Same short-stable-hash pattern as every other *Config class in this
        codebase (NullInputConfig, PreRegisteredConfig, LeakageConfig, ...)."""
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


def _sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_expired_files(config: RetentionConfig, now=None):
    """Returns a list of {path, basename, size_bytes, mtime_utc, age_days, expired}
    for every FILE directly under config.storage_location (non-recursive -- logs/ is a
    flat directory as of this task; extend if that ever changes), excluding
    NEVER_DELETE_BASENAMES. Computes and reports; the only decision made is the single,
    stated rule age_days >= retention_days (G1) -- nothing here judges a file's
    content or importance.

    A storage_location that does not exist yet (a clean checkout with no local logs/)
    returns an empty list rather than raising -- there is nothing to scan, not an
    error."""
    now = now if now is not None else time.time()
    if not os.path.isdir(config.storage_location):
        return []

    rows = []
    for basename in sorted(os.listdir(config.storage_location)):
        if basename in NEVER_DELETE_BASENAMES:
            continue
        full_path = os.path.join(config.storage_location, basename)
        if not os.path.isfile(full_path):
            continue
        mtime = os.path.getmtime(full_path)
        age_days = (now - mtime) / 86400.0
        rows.append({
            "path": full_path,
            "basename": basename,
            "size_bytes": os.path.getsize(full_path),
            "mtime_utc": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            "age_days": age_days,
            "expired": age_days >= config.retention_days,
        })
    return rows


def run_retention(config: RetentionConfig, deletion_log_path=None, now=None):
    """The one entry point.

    config.dry_run=True (the dataclass default): reports what WOULD be deleted.
    Deletes nothing. Writes nothing to the deletion log -- a dry run must leave no
    trace indistinguishable from a real one.

    config.dry_run=False: actually deletes each expired file and appends ONE record
    per deleted file to the deletion log (never a summary line only -- so a reader can
    verify exactly what was deleted, not take a count on faith). Returns the same
    report shape either way, keyed by which action was actually taken."""
    deletion_log_path = deletion_log_path or DEFAULT_DELETION_LOG_PATH
    rows = scan_expired_files(config, now=now)
    expired = [r for r in rows if r["expired"]]

    report_field_name = "would_delete" if config.dry_run else "deleted"
    report = {
        "record_type": "retention_dry_run" if config.dry_run else "retention_run",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config),
        "config_hash": config.config_hash(),
        "n_scanned": len(rows),
        "n_expired": len(expired),
        report_field_name: [
            {
                "path": r["path"], "basename": r["basename"], "size_bytes": r["size_bytes"],
                "mtime_utc": r["mtime_utc"], "age_days": r["age_days"],
            }
            for r in expired
        ],
    }

    if not config.dry_run:
        directory = os.path.dirname(os.path.abspath(deletion_log_path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(deletion_log_path, "a", encoding="utf-8") as log_file:
            for r in expired:
                # Hashed BEFORE removal -- a file that vanished between the scan and
                # here (e.g. removed by something else concurrently) would raise on
                # os.remove() below rather than silently logging a deletion that
                # didn't happen; never guessed or skipped quietly.
                sha256 = _sha256_of(r["path"])
                os.remove(r["path"])
                deletion_record = {
                    "record_type": "deletion",
                    "deleted_at_utc": datetime.now(timezone.utc).isoformat(),
                    "path": r["path"],
                    "basename": r["basename"],
                    "size_bytes": r["size_bytes"],
                    "sha256": sha256,
                    "mtime_utc": r["mtime_utc"],
                    "age_days_at_deletion": r["age_days"],
                    "retention_days": config.retention_days,
                    "config_hash": config.config_hash(),
                }
                log_file.write(json.dumps(deletion_record) + "\n")

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "D0PA1 retention/deletion routine. DRY-RUN BY DEFAULT -- reports what "
            "would be deleted without deleting anything. Pass --execute to actually "
            "delete expired files and write the deletion log."
        )
    )
    parser.add_argument("--retention-days", type=float, default=RetentionConfig().retention_days)
    parser.add_argument("--storage-location", type=str, default=RetentionConfig().storage_location)
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually delete expired files and append to the deletion log. Without this flag, always dry-run.",
    )
    args = parser.parse_args()

    cfg = RetentionConfig(
        retention_days=args.retention_days,
        storage_location=args.storage_location,
        dry_run=not args.execute,
    )
    result = run_retention(cfg)
    print(json.dumps(result, indent=2))
    if cfg.dry_run:
        print(f"\n[retention] DRY RUN -- {result['n_expired']} file(s) would be deleted, 0 deleted. Pass --execute to actually delete.")
    else:
        print(f"\n[retention] EXECUTED -- {result['n_expired']} file(s) deleted. See {DEFAULT_DELETION_LOG_PATH}")
