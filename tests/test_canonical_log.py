"""
D0PA1 Part B -- canonical log schema/writer validation (runnable directly,
no pytest). Writes to throwaway temp files only -- never touches any real
log. Covers: session header written once with wall-clock/monotonic offset,
double-open rejected, subject_id/context_id/device_id required and held
fixed within a session, missingness_flag/reason derived and cross-checked
(all four disagreement shapes rejected), fixed-enum reason enforcement,
timestamp monotonicity per field, and that every written line round-trips
as valid JSON conforming to the schema's required fields.
"""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from schema.canonical_log_writer import (
    CanonicalLogWriter, CanonicalLogValidationError, MISSINGNESS_REASONS,
    validate_record, SCHEMA_DOC, SCHEMA_VERSION,
)


def _new_writer(tmpdir):
    return CanonicalLogWriter(os.path.join(tmpdir, "canonical.jsonl"))


def check_session_header_once_with_offset():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _new_writer(tmpdir)
        header = w.open_session("sess1", subject_id="S01", context_id="ctx", device_id="dev1")
        has_offset = "wall_clock_utc" in header and "monotonic_reference" in header
        header_type_ok = header["record_type"] == "canonical_session_header"

        double_open_raised = False
        try:
            w.open_session("sess1", subject_id="S01", context_id="ctx", device_id="dev1")
        except CanonicalLogValidationError:
            double_open_raised = True

        with open(w.log_path, encoding="utf-8") as f:
            n_lines = len(f.readlines())

        ok = has_offset and header_type_ok and double_open_raised and n_lines == 1
        return ok, {"has_offset": has_offset, "header_type_ok": header_type_ok, "double_open_raised": double_open_raised, "n_lines": n_lines}


def check_write_before_open_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _new_writer(tmpdir)
        raised = False
        try:
            w.write_observation(session_id="never_opened", subject_id="S01", context_id="ctx", device_id="dev1",
                                 signal="v_es", value=0.5, confidence=0.9)
        except CanonicalLogValidationError:
            raised = True
        return raised, {"raised": raised}


def check_identity_locked_within_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _new_writer(tmpdir)
        w.open_session("sess1", subject_id="S01", context_id="ctx", device_id="dev1")
        raised = False
        try:
            w.write_observation(session_id="sess1", subject_id="S02", context_id="ctx", device_id="dev1",
                                 signal="v_es", value=0.5, confidence=0.9)
        except CanonicalLogValidationError:
            raised = True
        return raised, {"subject_id_mismatch_raised": raised}


def check_missingness_all_four_shapes():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _new_writer(tmpdir)
        w.open_session("sess1", subject_id="S01", context_id="ctx", device_id="dev1")

        # (1) present value, no reason -- OK
        r1 = w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                                  signal="v_es", value=0.42, confidence=0.9)
        shape1_ok = r1["missingness_flag"] is False and r1["missingness_reason"] is None

        # (2) missing value, valid reason -- OK
        r2 = w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                                  signal="v_es", value=None, missingness_reason="no_face")
        shape2_ok = r2["missingness_flag"] is True and r2["missingness_reason"] == "no_face"

        # (3) missing value, NO reason -- must raise
        shape3_raised = False
        try:
            w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                                 signal="v_es", value=None)
        except CanonicalLogValidationError:
            shape3_raised = True

        # (4) present value, reason ALSO given -- must raise
        shape4_raised = False
        try:
            w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                                 signal="v_es", value=0.1, missingness_reason="no_face")
        except CanonicalLogValidationError:
            shape4_raised = True

        # (5) missing value, reason NOT in fixed vocabulary -- must raise
        shape5_raised = False
        try:
            w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                                 signal="v_es", value=None, missingness_reason="the_camera_fell_over")
        except CanonicalLogValidationError:
            shape5_raised = True

        ok = shape1_ok and shape2_ok and shape3_raised and shape4_raised and shape5_raised
        return ok, {
            "shape1_present_no_reason_ok": shape1_ok,
            "shape2_missing_valid_reason_ok": shape2_ok,
            "shape3_missing_no_reason_raised": shape3_raised,
            "shape4_present_with_reason_raised": shape4_raised,
            "shape5_invalid_reason_raised": shape5_raised,
        }


def check_timestamp_monotonicity():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _new_writer(tmpdir)
        w.open_session("sess1", subject_id="S01", context_id="ctx", device_id="dev1")
        w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                             signal="v_es", value=0.1, prediction_timestamp=10.0)
        w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                             signal="v_es", value=0.2, prediction_timestamp=10.5)  # forward -- OK

        went_backward_raised = False
        try:
            w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                                 signal="v_es", value=0.3, prediction_timestamp=9.0)  # backward -- must raise
        except CanonicalLogValidationError:
            went_backward_raised = True

        # a DIFFERENT timestamp field's own sequence is tracked independently
        independent_field_ok = True
        try:
            w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                                 signal="v_es", value=0.4, action_timestamp=1.0)
        except CanonicalLogValidationError:
            independent_field_ok = False

        ok = went_backward_raised and independent_field_ok
        return ok, {"went_backward_raised": went_backward_raised, "independent_field_ok": independent_field_ok}


def check_records_round_trip_and_conform():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _new_writer(tmpdir)
        w.open_session("sess1", subject_id="S01", context_id="ctx", device_id="dev1", experiment_id="exp1")
        w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                             signal="v_pd", value=0.0004, confidence=0.7,
                             modality_availability=True, modality_quality=0.95)
        w.write_observation(session_id="sess1", subject_id="S01", context_id="ctx", device_id="dev1",
                             signal="v_pd", value=None, missingness_reason="zero_dispersion")

        with open(w.log_path, encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        required_observation_fields = [
            "subject_id", "session_id", "context_id", "device_id",
            "signal", "value", "confidence", "modality_availability", "modality_quality",
            "missingness_flag", "missingness_reason",
        ]
        obs_lines = [l for l in lines if l["record_type"] == "canonical_observation"]
        all_fields_present = all(all(k in l for k in required_observation_fields) for k in obs_lines for l in [k])
        n_total = len(lines)
        n_obs = len(obs_lines)

        ok = n_total == 3 and n_obs == 2 and all_fields_present
        return ok, {"n_total": n_total, "n_obs": n_obs, "all_fields_present": all_fields_present}


def check_validator_actually_rejects_bad_shapes():
    """Proves validate_record() itself (not just the writer's higher-level
    cross-field checks above) catches a real schema violation -- a guard
    that has never been observed to fail is not a guard (same standard
    tests/test_feature_separation.py's shim check was held to)."""
    obs_def = SCHEMA_DOC["$defs"]["canonical_observation"]

    base = {
        "schema_version": SCHEMA_VERSION, "record_type": "canonical_observation",
        "subject_id": "S01", "session_id": "sess1", "trial_id": None,
        "experiment_id": None, "context_id": "ctx", "device_id": "dev1",
        "commit": None, "config_version": None, "model_version": None,
        "stimulus_id": None, "stimulus_onset": None, "roi_or_condition": None,
        "prediction_timestamp": None, "action_timestamp": None, "action_class": None,
        "signal": "v_es", "value": 0.5, "confidence": 0.9,
        "modality_availability": True, "modality_quality": 0.9,
        "missingness_flag": False, "missingness_reason": None,
        "prediction_output": None, "prediction_confidence": None, "ground_truth_outcome": None,
    }
    valid_passes = True
    try:
        validate_record(base, obs_def)
    except CanonicalLogValidationError:
        valid_passes = False

    wrong_type = dict(base, session_id=12345)  # int instead of required string
    wrong_type_rejected = False
    try:
        validate_record(wrong_type, obs_def)
    except CanonicalLogValidationError:
        wrong_type_rejected = True

    missing_required = dict(base)
    del missing_required["device_id"]
    missing_field_rejected = False
    try:
        validate_record(missing_required, obs_def)
    except CanonicalLogValidationError:
        missing_field_rejected = True

    bad_enum = dict(base, missingness_reason="not_a_real_reason")
    bad_enum_rejected = False
    try:
        validate_record(bad_enum, obs_def)
    except CanonicalLogValidationError:
        bad_enum_rejected = True

    ok = valid_passes and wrong_type_rejected and missing_field_rejected and bad_enum_rejected
    return ok, {
        "valid_record_passes": valid_passes,
        "wrong_type_session_id_rejected": wrong_type_rejected,
        "missing_required_field_rejected": missing_field_rejected,
        "bad_enum_value_rejected": bad_enum_rejected,
    }


if __name__ == "__main__":
    checks = [
        ("SESSION HEADER WRITTEN ONCE, CARRIES WALL-CLOCK/MONOTONIC OFFSET, DOUBLE-OPEN REJECTED", check_session_header_once_with_offset),
        ("WRITE BEFORE OPEN_SESSION REJECTED", check_write_before_open_rejected),
        ("SUBJECT/CONTEXT/DEVICE IDENTITY LOCKED WITHIN A SESSION", check_identity_locked_within_session),
        ("MISSINGNESS_FLAG/REASON: ALL FOUR AGREEMENT/DISAGREEMENT SHAPES", check_missingness_all_four_shapes),
        ("TIMESTAMPS MONOTONIC PER-FIELD WITHIN A SESSION", check_timestamp_monotonicity),
        ("WRITTEN RECORDS ROUND-TRIP AS VALID JSON, REQUIRED FIELDS PRESENT", check_records_round_trip_and_conform),
        ("VALIDATOR ITSELF REJECTS WRONG-TYPE / MISSING-FIELD / BAD-ENUM RECORDS", check_validator_actually_rejects_bad_shapes),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"CANONICAL LOG VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("CANONICAL LOG VALIDATION: PASS")
