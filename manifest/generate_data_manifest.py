"""
D0PA1 Gate 0, A4 -- DATA MANIFEST GENERATOR.

Generates manifest/data_manifest.csv by walking logs/ and, for every file
found there, recording: path, SHA256, size, subject/session/trial/experiment
identifiers WHERE DETERMINABLE, an acquisition timestamp, and a processing
version. The manifest itself is committed; the data it describes is not
(logs/ stays git-ignored per .gitignore -- see CLAUDE.md guardrail G4).

HONESTY RULE, applied throughout (no guessing): every file in logs/ today
predates this manifest and most predate the canonical log schema (schema/
canonical_log_v1.json, Part B of this task) entirely -- they were written by
a dozen different ad-hoc scripts with different field names, several of them
before "subject_id"/"experiment_id" existed as a concept in this codebase at
all. Rather than reverse-engineer a value for every field on every file (which
would silently manufacture identifiers that were never actually recorded),
this script extracts a field ONLY when a real value is present under one of a
small set of known historical field-name variants, and otherwise leaves the
manifest cell empty and records WHY in the `notes` column. A blank cell with
a stated reason is the honest output here (G3) -- not a guess dressed up as
data.

Re-run this script any time logs/ changes; it is idempotent and reads only,
never writes to logs/ itself.

USAGE:
    python manifest/generate_data_manifest.py
"""

import csv
import hashlib
import json
import os
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_manifest.csv")

# Files that are themselves manifests/pointers, not raw log output, and files
# this manifest generator itself would otherwise try (harmlessly, but
# pointlessly) to describe. None currently excluded -- every file in logs/ is
# a real logged artefact -- but the hook is here so a future non-data file
# dropped in logs/ (e.g. a README) doesn't silently get a garbage row.
SKIP_BASENAMES = set()

# Known historical field-name variants for each identifier, in preference
# order, gathered by inspecting a representative sample of every log file
# family present today (session_*, gate2_trials*, consent_log, agent_log,
# orientation_trials, soak_log, variant_log, video_analysis_*, calib_repeat_*,
# validation_*, browdiag/browonly/maxelicit/yawhold). Extend this list if a
# future file family uses yet another name -- do not invent a mapping for a
# field that genuinely isn't there.
SUBJECT_ID_FIELDS = ["person_label", "subject_id", "participant_code"]
SESSION_ID_FIELDS = ["session_id"]
TRIAL_ID_FIELDS = ["trial_id"]
EXPERIMENT_ID_FIELDS = ["experiment_id"]
TIMESTAMP_FIELDS = ["ts_utc", "generated_at_utc"]
PROCESSING_VERSION_FIELDS = ["schema_version"]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _first_record(path):
    """Returns (record_or_None, parse_status). Handles both JSONL (first
    non-empty line) and a single JSON document (object or array; first
    element of an array). Never raises -- a file that can't be parsed at all
    gets parse_status describing why, and every identifier field for that
    row is reported missing with that same reason."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read file: {e}"

    stripped = text.lstrip()
    if not stripped:
        return None, "file is empty"

    if stripped[0] in "{[":
        # Could be one JSON document (object or array) OR JSONL where the
        # first line itself starts with { -- try whole-file parse first
        # (covers calib_repeat_*.json's top-level array and video_analysis_*
        # /validation_*_manifest.json's top-level object), fall back to
        # first-line JSONL parse if that fails.
        try:
            doc = json.loads(text)
            if isinstance(doc, list):
                if not doc:
                    return None, "JSON array is empty"
                return doc[0], "parsed: single JSON document (array)"
            return doc, "parsed: single JSON document (object)"
        except json.JSONDecodeError:
            pass

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line), "parsed: JSONL (first record)"
        except json.JSONDecodeError as e:
            return None, f"first non-empty line is not valid JSON: {e}"

    return None, "no non-empty lines found"


def _extract(record, field_candidates):
    """Returns (value_or_None, reason_if_missing_or_None). Only ever reads a
    value that is actually present and non-null under one of the known
    field names -- never derives, parses-out-of-a-string, or guesses one."""
    if record is None:
        return None, "file could not be parsed (see parse_status)"
    for field in field_candidates:
        if field in record and record[field] is not None:
            return record[field], None
    return None, f"none of {field_candidates} present in this file's records"


def build_row(basename):
    path = os.path.join(LOGS_DIR, basename)
    rel_path = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    size_bytes = os.path.getsize(path)
    digest = sha256_of(path)

    record, parse_status = _first_record(path)
    record_type = record.get("record_type") if isinstance(record, dict) else None

    subject_id, subject_reason = _extract(record, SUBJECT_ID_FIELDS)
    session_id, session_reason = _extract(record, SESSION_ID_FIELDS)
    trial_id, trial_reason = _extract(record, TRIAL_ID_FIELDS)
    experiment_id, experiment_reason = _extract(record, EXPERIMENT_ID_FIELDS)
    processing_version, version_reason = _extract(record, PROCESSING_VERSION_FIELDS)

    acquisition_ts, ts_reason = _extract(record, TIMESTAMP_FIELDS)
    if acquisition_ts is not None:
        acquisition_source = "record field (ts_utc/generated_at_utc of first record)"
    else:
        # Fallback: file mtime. Same convention docs/AUDIT_A_COLUMN.md and
        # PROVENANCE.md already use elsewhere in this repo -- explicitly
        # labeled weak/non-evidentiary (trivially alterable by copy/checkout,
        # proves nothing about original acquisition time), never presented
        # as equivalent to a real logged timestamp.
        mtime = os.path.getmtime(path)
        acquisition_ts = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        acquisition_source = "file mtime (WEAK, non-evidentiary -- no ts_utc/generated_at_utc field in this file)"

    # experiment_id is deliberately expected to be missing for every file
    # generated before this task -- Gate 0 provenance (RunProvenance,
    # simulation/provenance.py) did not exist yet when any of these logs
    # were written. Stated once here so every per-row reason string doesn't
    # have to re-explain it, and echoed into the notes column per-row so the
    # CSV is self-contained without cross-referencing this comment.
    notes = []
    if subject_reason:
        notes.append(f"subject_id: {subject_reason}")
    if session_reason:
        notes.append(f"session_id: {session_reason}")
    if trial_reason:
        notes.append(f"trial_id: {trial_reason}")
    if experiment_reason:
        notes.append(f"experiment_id: {experiment_reason} (predates Gate 0 provenance, this task)")
    if version_reason:
        notes.append(f"processing_version: {version_reason}")
    notes.append(f"parse_status: {parse_status}")

    return {
        "path": rel_path,
        "sha256": digest,
        "size_bytes": size_bytes,
        "subject_id": subject_id if subject_id is not None else "",
        "session_id": session_id if session_id is not None else "",
        "trial_id": trial_id if trial_id is not None else "",
        "experiment_id": experiment_id if experiment_id is not None else "",
        "acquisition_timestamp": acquisition_ts if acquisition_ts is not None else "",
        "acquisition_timestamp_source": acquisition_source,
        "processing_version": processing_version if processing_version is not None else "",
        "record_type_sample": record_type if record_type is not None else "",
        "notes": "; ".join(notes),
    }


def generate():
    basenames = sorted(
        f for f in os.listdir(LOGS_DIR)
        if os.path.isfile(os.path.join(LOGS_DIR, f)) and f not in SKIP_BASENAMES
    )
    rows = [build_row(b) for b in basenames]

    fieldnames = [
        "path", "sha256", "size_bytes", "subject_id", "session_id", "trial_id",
        "experiment_id", "acquisition_timestamp", "acquisition_timestamp_source",
        "processing_version", "record_type_sample", "notes",
    ]
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")
    return rows


if __name__ == "__main__":
    generate()
