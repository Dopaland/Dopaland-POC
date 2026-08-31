"""
D0PA1 canonical log writer (Part B, Gate 0).

ONE versioned schema (schema/canonical_log_v1.json) and the ONE writer this
repository routes canonical-format logging through. Every record is
validated against the schema document itself (read from disk, not a
hand-copied second definition that could drift out of sync with it) AT
WRITE TIME -- a record that doesn't conform raises before it ever reaches
disk, not after some downstream consumer trips over it.

VALIDATOR SCOPE, stated honestly: the `jsonschema` package is not installed
in this environment (checked; not present, and this task does not warrant
adding a new dependency for it). What follows is a small, hand-rolled
validator that understands exactly the subset of JSON Schema this one
document actually uses -- required/type/const/enum/oneOf-of-enum-or-null,
minLength -- read directly from canonical_log_v1.json's own parsed JSON, so
schema and validator cannot silently drift apart on THOSE checks. It does
NOT implement the full JSON Schema spec (if/then, pattern, format,
additionalProperties, etc.). If this schema grows features this validator
doesn't understand, extend the validator alongside the schema change, not
after.

INVARIANTS ENFORCED IN CODE, per this task's explicit requirement (not just
documented as a convention the caller is trusted to follow):
  - subject_id/context_id/device_id required on every record, and held
    fixed for a given session_id once opened (a caller cannot silently
    change a session's identity mid-stream).
  - missingness_flag/missingness_reason are DERIVED and CROSS-CHECKED by
    the writer, never taken as independent caller inputs that could
    disagree with `value`'s actual presence.
  - timestamps monotonic within a session: stimulus_onset,
    prediction_timestamp, and action_timestamp are each checked
    independently against the last value THIS session logged for that
    same field; a caller supplying a smaller value than before raises.
  - the wall-clock <-> monotonic-clock offset is recorded exactly once per
    session, via open_session()'s canonical_session_header record --
    calling it twice for the same session_id raises rather than silently
    creating two different time references for the same data.

NOT DONE BY THIS MODULE, stated per this task's explicit instruction: it
does not migrate any existing log (session_*.jsonl, null_input logs, etc.)
into this schema, and it does not attempt to populate the stimulus/ROI/
action-class fields from anything -- those stay caller-supplied (typically
None today, since the client's task harness that would populate them is
under separate acceptance review). Nothing in this repository's existing
capture pipeline calls this writer yet.
"""

import json
import os
import time
from datetime import datetime, timezone

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "canonical_log_v1.json")

with open(SCHEMA_PATH, "r", encoding="utf-8") as _f:
    SCHEMA_DOC = json.load(_f)

SCHEMA_VERSION = SCHEMA_DOC["schema_version"]
MISSINGNESS_REASONS = tuple(SCHEMA_DOC["$defs"]["missingness_reason"]["enum"])
_MISSINGNESS_REASON_SET = set(MISSINGNESS_REASONS)
_SESSION_HEADER_DEF = SCHEMA_DOC["$defs"]["canonical_session_header"]
_OBSERVATION_DEF = SCHEMA_DOC["$defs"]["canonical_observation"]

_MONOTONIC_TS_FIELDS = ("stimulus_onset", "prediction_timestamp", "action_timestamp")

_JSON_TYPE_TO_PY = {
    "string": str,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


class CanonicalLogValidationError(ValueError):
    """Raised when a record fails schema validation or one of this
    writer's cross-field invariants (missingness consistency, session
    identity, timestamp monotonicity). Deliberately a plain ValueError
    subclass, not swallowed anywhere in this module -- a caller must
    handle or fix the input, never have a bad record silently dropped."""


def _resolve_ref(ref):
    if not ref.startswith("#/$defs/"):
        raise CanonicalLogValidationError(f"unsupported $ref (validator only understands '#/$defs/...'): {ref}")
    return SCHEMA_DOC["$defs"][ref.split("/")[-1]]


def _value_matches_type(value, type_spec):
    types = type_spec if isinstance(type_spec, list) else [type_spec]
    for t in types:
        py_types = _JSON_TYPE_TO_PY[t]
        if t == "number" and isinstance(value, bool):
            continue  # bool is a subclass of int in Python; JSON boolean must not pass as JSON number
        if isinstance(value, py_types):
            return True
    return False


def _validate_property(value, prop_schema, field_name):
    if "const" in prop_schema:
        if value != prop_schema["const"]:
            raise CanonicalLogValidationError(f"{field_name}: expected const {prop_schema['const']!r}, got {value!r}")
        return
    if "enum" in prop_schema:
        if value not in prop_schema["enum"]:
            raise CanonicalLogValidationError(f"{field_name}: {value!r} not in enum {prop_schema['enum']}")
        return
    if "oneOf" in prop_schema:
        for branch in prop_schema["oneOf"]:
            if "$ref" in branch:
                sub = _resolve_ref(branch["$ref"])
                if "enum" in sub and value in sub["enum"]:
                    return
            elif branch.get("type") == "null" and value is None:
                return
        raise CanonicalLogValidationError(f"{field_name}: {value!r} did not match any oneOf branch")
    if "type" in prop_schema:
        if not _value_matches_type(value, prop_schema["type"]):
            raise CanonicalLogValidationError(f"{field_name}: {value!r} does not match type {prop_schema['type']}")
        if "minLength" in prop_schema and isinstance(value, str) and len(value) < prop_schema["minLength"]:
            raise CanonicalLogValidationError(f"{field_name}: string shorter than minLength {prop_schema['minLength']}")


def validate_record(record, definition):
    """Checks `record` against a $defs entry (canonical_session_header or
    canonical_observation): every required field present, and every field
    that IS present matches its declared type/const/enum. Fields in the
    schema but absent from `record` are allowed only when not required
    (this writer always supplies every declared field explicitly as None
    where unknown, so in practice nothing is ever actually absent -- see
    CanonicalLogWriter -- but validate_record itself does not assume that)."""
    required = definition.get("required", [])
    missing = [f for f in required if f not in record]
    if missing:
        raise CanonicalLogValidationError(f"missing required field(s): {missing}")
    for field_name, prop_schema in definition["properties"].items():
        if field_name in record:
            _validate_property(record[field_name], prop_schema, field_name)


class CanonicalLogWriter:
    """One instance per log file. Holds the per-session state (has this
    session's header been written yet, last-seen value per monotonic
    timestamp field) needed to enforce invariants ACROSS calls, not just
    within one record in isolation."""

    def __init__(self, log_path):
        self.log_path = log_path
        self._sessions = {}
        directory = os.path.dirname(os.path.abspath(log_path))
        if directory:
            os.makedirs(directory, exist_ok=True)

    def open_session(self, session_id, subject_id, context_id, device_id,
                      experiment_id=None, commit=None, config_version=None):
        """Writes the ONE canonical_session_header record for session_id,
        capturing the wall-clock <-> monotonic-clock offset at this exact
        instant. Must be called before write_observation() for this
        session_id, and must be called at most once per session_id."""
        if session_id in self._sessions:
            raise CanonicalLogValidationError(
                f"session {session_id!r} already opened -- the wall-clock offset is recorded "
                "EXACTLY ONCE per session (this task's explicit timing invariant); calling "
                "open_session twice for the same session_id would silently create two different "
                "time references for the same data."
            )
        header = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "canonical_session_header",
            "session_id": session_id,
            "subject_id": subject_id,
            "context_id": context_id,
            "device_id": device_id,
            "experiment_id": experiment_id,
            "commit": commit,
            "config_version": config_version,
            "wall_clock_utc": datetime.now(timezone.utc).isoformat(),
            "monotonic_reference": time.perf_counter(),
        }
        validate_record(header, _SESSION_HEADER_DEF)
        self._append(header)
        self._sessions[session_id] = {
            "identity": {"subject_id": subject_id, "context_id": context_id, "device_id": device_id},
            "last_ts": {},
        }
        return header

    def write_observation(self, *, session_id, subject_id, context_id, device_id,
                           signal, value, confidence=None,
                           trial_id=None, experiment_id=None, commit=None, config_version=None,
                           model_version=None,
                           stimulus_id=None, stimulus_onset=None, roi_or_condition=None,
                           prediction_timestamp=None, action_timestamp=None, action_class=None,
                           modality_availability=None, modality_quality=None,
                           missingness_reason=None,
                           prediction_output=None, prediction_confidence=None, ground_truth_outcome=None):
        """Writes one canonical_observation record. `missingness_flag` is
        NOT a parameter -- it is derived from `value is None` and
        cross-checked against `missingness_reason` here, so the two can
        never be logged in disagreement with each other."""
        if session_id not in self._sessions:
            raise CanonicalLogValidationError(
                f"session {session_id!r} was never opened -- call open_session() first so the "
                "wall-clock offset this session's timestamps are relative to actually exists."
            )
        session = self._sessions[session_id]
        identity = session["identity"]
        for field_name, expected in (("subject_id", subject_id), ("context_id", context_id), ("device_id", device_id)):
            if expected != identity[field_name]:
                raise CanonicalLogValidationError(
                    f"{field_name} changed mid-session ({identity[field_name]!r} -> {expected!r}) for "
                    f"session {session_id!r} -- one session_id must carry ONE identity throughout."
                )

        missingness_flag = value is None
        if missingness_flag and missingness_reason is None:
            raise CanonicalLogValidationError(
                f"signal {signal!r}: value is missing but no missingness_reason was given -- "
                "missingness is logged, never dropped, and must carry a reason from the fixed "
                f"enumerated vocabulary {MISSINGNESS_REASONS}."
            )
        if not missingness_flag and missingness_reason is not None:
            raise CanonicalLogValidationError(
                f"signal {signal!r}: value is present ({value!r}) but missingness_reason "
                f"({missingness_reason!r}) was also given -- these must never both be set."
            )
        if missingness_flag and missingness_reason not in _MISSINGNESS_REASON_SET:
            raise CanonicalLogValidationError(
                f"signal {signal!r}: missingness_reason {missingness_reason!r} is not in the fixed "
                f"enumerated vocabulary {MISSINGNESS_REASONS}."
            )

        provided_ts = {
            "stimulus_onset": stimulus_onset,
            "prediction_timestamp": prediction_timestamp,
            "action_timestamp": action_timestamp,
        }
        for field_name, ts in provided_ts.items():
            if ts is None:
                continue
            last = session["last_ts"].get(field_name)
            if last is not None and ts < last:
                raise CanonicalLogValidationError(
                    f"{field_name} went backward within session {session_id!r}: {ts} < {last} "
                    "(timestamps must be monotonic within a session -- this task's explicit invariant)."
                )
            session["last_ts"][field_name] = ts

        record = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "canonical_observation",
            "subject_id": subject_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "experiment_id": experiment_id,
            "context_id": context_id,
            "device_id": device_id,
            "commit": commit,
            "config_version": config_version,
            "model_version": model_version,
            "stimulus_id": stimulus_id,
            "stimulus_onset": stimulus_onset,
            "roi_or_condition": roi_or_condition,
            "prediction_timestamp": prediction_timestamp,
            "action_timestamp": action_timestamp,
            "action_class": action_class,
            "signal": signal,
            "value": value,
            "confidence": confidence,
            "modality_availability": modality_availability,
            "modality_quality": modality_quality,
            "missingness_flag": missingness_flag,
            "missingness_reason": missingness_reason,
            "prediction_output": prediction_output,
            "prediction_confidence": prediction_confidence,
            "ground_truth_outcome": ground_truth_outcome,
        }
        validate_record(record, _OBSERVATION_DEF)
        self._append(record)
        return record

    def _append(self, record):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
