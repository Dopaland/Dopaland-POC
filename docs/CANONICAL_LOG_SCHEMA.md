# Canonical Log Schema — Part B

**Files:** [`schema/canonical_log_v1.json`](../schema/canonical_log_v1.json) (the
schema document) · [`schema/canonical_log_writer.py`](../schema/canonical_log_writer.py)
(the single writer/validator) · [`tests/test_canonical_log.py`](../tests/test_canonical_log.py)

## What this is

ONE versioned schema, defining two record types:

- `canonical_session_header` — written **exactly once** per session, by
  `CanonicalLogWriter.open_session()`. This is where "the wall-clock offset
  recorded once per session" (this task's explicit requirement) actually
  lives: it captures `wall_clock_utc` (`datetime.now`) and
  `monotonic_reference` (`time.perf_counter()`) at the same instant, so
  every later monotonic timestamp in the session is interpretable as real
  time. Calling `open_session()` twice for the same `session_id` raises.
- `canonical_observation` — one row per signal reading, carrying the full
  field list the task specified: `subject_id · session_id · trial_id ·
  experiment_id · context_id · device_id`, `commit`/`config_version` +
  `model_version`, `stimulus_id · stimulus_onset · roi_or_condition`,
  `prediction_timestamp · action_timestamp · action_class`, `signal ·
  value · confidence`, `modality_availability · modality_quality ·
  missingness_flag · missingness_reason`, `prediction_output ·
  prediction_confidence · ground_truth_outcome`.

All fields are declared on every record — a field that has nothing to
report is `null`, not absent. Every field the writer doesn't yet have a
real value for (`stimulus_*`, `roi_or_condition`, `action_*`,
`prediction_output`, `model_version`, `ground_truth_outcome`) is
consistently `null` today, because nothing in this repository populates
them — see "What this deliberately does NOT do" below.

## Invariants enforced in code, not by convention

- **`subject_id` required on every record, from the first observation** —
  `validate_record()` rejects any record missing it; there is no code path
  that can write an observation without one, even in a single-subject
  study (D0PA1 hard constraint #7).
- **`context_id` and `device_id` required, never dropped** — same
  enforcement, plus `write_observation()` checks a session's identity
  (`subject_id`/`context_id`/`device_id`) stays fixed for the whole
  session; a caller passing a different value mid-session raises rather
  than silently accepting drift.
- **Missingness is logged, never dropped, from a fixed vocabulary** —
  `missingness_flag` is not a caller input; it is derived from
  `value is None` and cross-checked against `missingness_reason` in both
  directions: missing-without-a-reason raises, present-with-a-reason
  raises, and a reason outside the fixed `missingness_reason` enum
  (`no_face`, `low_landmark_confidence`, `out_of_frame`, `occlusion`,
  `tracking_lost`, `zero_dispersion`, `quality_gate_rejected`,
  `insufficient_samples`, `not_yet_calibrated`, `not_applicable`,
  `harness_not_available`) raises. A missing signal is always a row with
  a reason, never an absent row.
- **Timestamps monotonic within a session** — `stimulus_onset`,
  `prediction_timestamp`, and `action_timestamp` are each tracked
  independently per session; a value smaller than the last one seen for
  that same field in that same session raises.

All four are exercised directly in `tests/test_canonical_log.py` (7
checks, including proving the validator itself — not just the writer's
higher-level checks — rejects a wrong-typed field, a missing required
field, and an out-of-vocabulary enum value). All pass.

## Validator scope, stated honestly

The `jsonschema` package is not installed in this environment and this
task did not warrant adding a new dependency for it. `canonical_log_writer.py`
instead reads `canonical_log_v1.json` directly and hand-validates the
subset of JSON Schema this one document actually uses — `required`,
`type`, `const`, `enum`, `oneOf`-of-enum-or-null, `minLength` — so the
schema document and the validator cannot silently drift apart on those
checks (there is no second, hand-copied definition anywhere). It does
**not** implement the full JSON Schema spec.

## What this deliberately does NOT do

- **Does not migrate any existing log.** Every file in `logs/` predates
  this schema and stays in its own original format — described instead by
  `manifest/data_manifest.csv` (Gate 0 A4). This is a new, forward-looking
  capability.
- **Is not wired into the live capture pipeline.** Nothing in
  `stage1_step4_vectors.py`, `controls/null_input.py`, or any other real
  entry point calls `CanonicalLogWriter` yet. It exists and is tested;
  integrating it into a real capture loop is follow-on work, not part of
  this task.
- **Does not populate or fix the stimulus/ROI/action-class fields.** Per
  the task's explicit instruction, this writer accepts them as
  caller-supplied (currently always `None`, since the client's task
  harness that would populate them is under separate acceptance review)
  and does not attempt to compute or infer them. `action_class` is
  deliberately an **open string**, not a fixed enum — the action-class
  vocabulary itself is BLOCKED pending the client's D2 decision
  (CLAUDE.md's "BLOCKED" section). The schema's own `$comment` states
  this, and its `action_class` description records the constraint that,
  once the harness exists, `ABANDON` and `NO_ACTION` must be logged as
  real string values here — never an absent row or a bare `null`.
