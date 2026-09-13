# Gate 0 Provenance — A1–A5, B2

**Purpose:** CLAUDE.md's "WHAT D0PA1 ADDS" lists Gate 0 provenance as
authorised, in-scope infrastructure work: experiment ID + run provenance,
config + hash, pinned dependencies, a data manifest, a variant log. This
document records what was built for each, checkable directly against the
repository rather than taken on faith.

**G5 discipline applied throughout:** every change described below is
additive or orchestration-only. Nothing on the validated path (the affect
vector formulas, `NeutralCalibrator`, the rolling window, the V/A mapping,
the two-thread architecture) was touched. `tests/test_refactor_snapshot.py`
was re-run after every step in this document and reported an exact match
against the committed golden file each time — see the commit history for
the literal pass/fail output at each point, not just this document's word
for it.

**⚠️ Golden hash supersession, recorded here durably — this is the one
exception to "nothing on the validated path was touched" above, and it was
authorised, not incidental.** The "AFTER THE PHYSICAL RUN" task's Task 1.3
found and fixed a real bug in `features/x_core.py`'s `NeutralCalibrator`:
`is_calibrated()` returned `True` for a completed calibration reference
that had collected zero real (non-`None`) samples for every composite
vector — a calibration window that fell entirely inside a no-face-detected
stretch — silently disabling every downstream consumer (excursion
detection, the V/A mapping, `stage1_step4_vectors.py`'s own
`calibration_status` field) for the rest of that session, with nothing
in the log distinguishing this from a genuine, usable calibration. That
task's own prompt granted explicit, one-time permission to fix this one
G5-path item. The fix: `is_calibrated()` now checks an explicit
`missingness_flag`/`missingness_reason` (`"not_yet_calibrated"`, the
pipeline's existing fixed missingness vocabulary) stamped onto the
reference by `complete()`, rather than only `reference is not None`. The
one-shot completion TIMING itself (`should_complete()`'s wall-clock
trigger) is unchanged — a separate internal flag preserves the original
freeze-once behaviour so the fix cannot cause repeated re-completion or
unbounded sample growth (verified by a dedicated test,
`tests/test_neutral_calibrator.py`).

Because this changes the calibration reference's own output shape (two new
fields on every reference, present or degenerate), the golden snapshot
necessarily changed too — this was confirmed by diffing the freshly
generated snapshot against the previous committed golden file BEFORE
regenerating it: **the only difference was the two new fields on a normal
(non-degenerate) reference; nothing else in the validated path's output
moved.**

- **Superseded hash:** `4f9c0f1786c18e8dbe5e3048b8b6b6e280cf6c434b9c53b119344746fc31bcff`
  (valid through commit `13e3dd4`)
- **Current hash:** `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`
  (from commit `44c02be` onward)
- Commit: `44c02be` — "fix: NeutralCalibrator no longer reports a degenerate
  window as calibrated"
- Also recorded in `CLAUDE.md`'s "STANDING VERIFICATION HABITS" section and
  `docs/PROJECT_STATE.md` §1, so a session or a client reading any one of
  the three finds the same explanation rather than a bare, unexplained
  hash change.

---

## A1 — Experiment ID and run provenance

**File:** [`simulation/provenance.py`](../simulation/provenance.py)

`capture_run_provenance(label=None)` returns a frozen `RunProvenance` with:

- `experiment_id` — `<label_>YYYYMMDDTHHMMSSZ_<8 hex>`, human-readable and
  collision-safe (a timestamp alone can collide across two runs starting
  in the same second; the random suffix cannot).
- `git_commit_hash` — `git rev-parse HEAD` against the repo, or `None` if
  it could not be determined.
- `git_dirty` / `git_dirty_reason` — from `git status --porcelain`. **A
  dirty tree is reported dirty. A tree whose cleanliness could not even be
  checked (git absent, timeout, any error) is ALSO reported dirty**, with
  `git_check_error` carrying why — this was a deliberate design choice per
  the task's explicit requirement ("never silently presented as clean"),
  not an oversight: `capture_run_provenance` never defaults to `False`
  when it cannot verify the truth.
- `hostname`, `captured_at_utc`.
- `provenance_hash()` — same short-SHA256-prefix pattern as
  `PreRegisteredConfig.config_hash()` / `NullInputConfig.config_hash()`.

**Verified, not just written:** `tests/test_provenance.py` checks (1)
`experiment_id` uniqueness and readable format, (2) that a real call
against this actual repository returns a real 40-character commit hash and
a `git_dirty` value matching an independently-run `git status --porcelain`
check in the same test, (3) that a mocked total git failure produces
`git_dirty=True`, never `False` — the specific failure-safe behavior the
task called out, exercised directly rather than assumed, and (4)
`provenance_hash()` reproducibility/sensitivity. All four pass — see the
commit history for the pasted run.

**Kept deliberately separate from `PreRegisteredConfig` (A2 below):**
provenance answers "which code, exactly, ran" (captured fresh every run);
config answers "which pre-registered parameter values are in force" (fixed
once, reused across many runs). Not yet wired into every entry point in
this repository — `capture_run_provenance()` exists and is tested, but no
existing script (the real session pipeline, the controls, the simulation
sweeps) calls it yet. **Stated as a gap, not smoothed over**: wiring it
into every run is follow-on work, not part of this task.

---

## A2 — Config and hash

**File:** [`simulation/config.py`](../simulation/config.py)

`PreRegisteredConfig` (previously home to exactly one field,
`log_loss_clip_eps`) gained three fields, each moved from a bare local
literal to this single hashed, versioned home:

| Field | Value | Moved from |
|---|---|---|
| `zero_dispersion_epsilon` | `1e-9` | `controls/null_input.py`'s local `ZERO_DISPERSION_EPSILON` |
| `camera_index` | `0` | `stage1_step4_vectors.py`'s local `CAMERA_INDEX` |
| `fps_report_interval_seconds` | `3.0` | `stage1_step4_vectors.py`'s local `FPS_REPORT_INTERVAL_SECONDS` |

Each site now reads `PRE_REGISTERED_CONFIG.<field>` instead of defining its
own literal — **same numeric value, single source of truth, not a
behavior change.** `tests/test_config.py`'s third check asserts each moved
site's value equals the config's value directly (would fail if either
drifted independently), and `tests/test_refactor_snapshot.py` was re-run
after this change and matched the golden file exactly (these two constants
are orchestration-only and were never part of the golden-tested surface,
but the check was run anyway, not assumed).

### Full constant audit: moved vs. left in place, with reasons

The task asked for the earlier hardcoded-constant audit
(`docs/AUDIT_A_COLUMN.md` Q6, 42 constants: 28 thresholds + 14 landmark
indices, found in `stage1_step4_vectors.py` before the D1 refactor moved
most of them into `features/*.py`) to be re-run and each constant's
disposition reported. Current locations, re-confirmed by direct search,
not assumed from the old document:

**Moved into `PreRegisteredConfig` (3):** `camera_index`,
`fps_report_interval_seconds` (both were in `stage1_step4_vectors.py`, an
orchestrator file, not inside a G5-protected formula/calibration/window
function) and `zero_dispersion_epsilon` (was in `controls/null_input.py`,
not a G5 file at all). All three are pure I/O or reporting knobs, or a
numerical-safety floor — none of them are inputs to an affect-vector
formula.

**Left in place — load-bearing inside the validated path (G5), reported
per the task's explicit escape hatch ("if a constant is load-bearing there,
report it as 'left in place, validated path' rather than touching it"):**

| Constant | Current location | Reason left in place |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | `stage1_step4_vectors.py:188` | Feeds MediaPipe detector options (`min_face_presence_confidence`/`min_tracking_confidence`); changes what "detected" means for every downstream computation |
| `WINDOW_SECONDS` | `features/geometry.py:133` | Shared by `WindowAccumulator` (E_t) and `AttentionWindowAccumulator` (A_t); captured in the golden snapshot's `window_summary` output |
| `YAW_VARIANCE_CEILING_DEG2` | `features/geometry.py:147` | Shared by `classify_window_confidence` and `classify_calibration_quality`; captured in the golden snapshot |
| `CALIBRATION_SECONDS` | `features/x_core.py:33` | `NeutralCalibrator`'s duration; captured in the golden snapshot's `calibrator_reference` |
| `CALIBRATION_DRIFT_EFFECT_SIZE` | `features/x_core.py:34` | `classify_calibration_quality`'s contamination-flag threshold; captured in the golden snapshot |
| `PD_BUFFER_SECONDS` | `features/x_core.py:36` | `compute_v_pd`'s rolling buffer length; captured in the golden snapshot's `compute_v_pd_sequence` |
| `DETECT_RATE_FLOOR` | `features/episodes.py:65` | `classify_window_confidence`'s gate; captured in the golden snapshot |
| 14 landmark-index constants (`IRIS_LEFT_CENTER` … `POSE_SHOULDER_R`) | `features/geometry.py:100–122` | MediaPipe topology IDs, not tunable parameters — moving them into a "pre-registered config" would misrepresent fixed anatomical indices as a decision that was made |

**Left in place — `features/attention.py`'s own thresholds (11:
`ATTENTION_YAW_THRESHOLD_DEG`, `ATTENTION_PITCH_THRESHOLD_DEG`,
`ATTENTION_POSE_WEIGHT`, `ATTENTION_ORIENTED_SCORE_THRESHOLD`,
`GAZE_PLAUSIBLE_SLACK`, `GAZE_DIRECTION_DEVIATION_THRESHOLD`,
`GAZE_LABEL_SIGN`, and the 7 `BLINK_*` constants):** `attention.py`'s own
docstring holds this module to G5 discipline ("no formula, threshold, or
state-machine logic changed") even though CLAUDE.md's G5 bullet does not
name it explicitly — these constants are also PILOT / UNVALIDATED signals
(V_so, gaze, blink), explicitly out of POC/D0PA1 scope for new signal work.
Moving them would touch a file under the same "don't modify without an
explicit ask" discipline for a signal this task's guardrails already treat
as lower priority than the validated V_bf/V_es/V_pd/V_jc path. Left in
place.

**Net result:** 3 of 42 constants moved (the 3 that were genuinely outside
any G5-protected file and met the "materially affects what a run/record
reports" bar without being a formula input); 39 left in place, each with a
stated reason above rather than a blanket "didn't touch anything."

---

## B2 — Closing the config-hash coverage gap

**The gap, stated plainly:** `PreRegisteredConfig.config_hash()` covers
exactly **3** declared parameters. It does not cover the other **39**
constants A2's audit above found and deliberately left in place, load-bearing
inside the validated path (G5). A reader seeing "config hash" could
reasonably — and wrongly — assume every behavior-affecting value was
pinned by it. It was not: two runs sharing an identical `config_hash()`
could still behave differently if any of those 39 changed between them.

**Fix, without moving anything out of the validated path:**
[`simulation/provenance.py`](../simulation/provenance.py)'s `RunProvenance`
gained a second, **separate** field, `validated_path_source_sha256`
(plus `validated_path_source_files`, a per-file breakdown), computed by
`_hash_validated_path_sources()`. It is a whole-file SHA256 over every file
this task's constant audit named "left in place, validated path":
`features/x_core.py`, `features/geometry.py`, `features/episodes.py`,
`features/attention.py`, `stage1_step4_vectors.py`. The aggregate is a
hash of the sorted `path:hash` pairs, so file order never matters and a
missing/unreadable file still participates (as an error string) rather
than being silently skipped.

**Deliberately not merged with `config_hash()`.** They answer different
questions — `config_hash()`: *which pre-registered values are in force*;
`validated_path_source_sha256`: *did the validated-path source change at
all* — and collapsing them into one number would make it impossible to
tell which kind of change moved it. `tests/test_provenance.py` check 5
asserts the two are computed independently and are, on this real repo,
different values, as expected.

**Whole-file, not surgical — an honest tradeoff, not an oversight.** This
hashes entire files, not just the constant assignments inside them. An
unrelated edit to one of these 5 files (a comment, a docstring, a print
statement) also moves this hash, even when no constant's value changed.
That is over-inclusive **by design**: for an integrity signal, a false
"something changed" a reader can dismiss after a two-second `git diff` is
a far cheaper failure than a false "nothing changed" that hides a real
constant edit inside noise from an unrelated change to the same file.

### B2.2 — Verified to actually move, and to actually revert

Ran against the **real** `features/x_core.py`, not a synthetic stand-in
(the automated regression test, `tests/test_provenance.py` check 6, uses a
synthetic file tree instead — see its own docstring for why an automated
test should never mutate real source files — but this manual run is the
primary evidence, on the real file the client will actually inspect):

| Step | `PD_BUFFER_SECONDS` | `validated_path_source_sha256` (aggregate) | `features/x_core.py` hash |
|---|---|---|---|
| Before | `1.5` | `4d31e0df357aef90624bf71444716610ca31b7fc6d6d34ed482a02dd47572fa7` | `118ea07b137d5f3b58fad9ba5eadeb38f959ff0d5c71e68b5b91b181b85640d9` |
| Changed to `1.6` | `1.6` | `b7a84e9e57fc4e294a5843072d9be25259441510d61890c397a284e96fca7c78` | `b55772d8e7302235bccd9f591104522109df230720b59b190dbe523e5d70e9ee` |
| Reverted to `1.5` | `1.5` | `4d31e0df357aef90624bf71444716610ca31b7fc6d6d34ed482a02dd47572fa7` | `118ea07b137d5f3b58fad9ba5eadeb38f959ff0d5c71e68b5b91b181b85640d9` |

Both the aggregate and the specific per-file hash moved on the edit and
returned to their **exact original values** on revert — confirmed
`git diff --stat features/x_core.py` showed no residual diff after
reverting, and `tests/test_refactor_snapshot.py` matched the golden file
throughout (the edit was made, measured, and reverted before any golden
comparison was run against the changed state — this was a hash-mechanism
proof, not a real constant change, and never touched the committed file).

### B2.3 — What is and isn't covered now, stated honestly

**Together, `config_hash()` (3 parameters) and `validated_path_source_sha256`
(5 files covering the other 39 constants) mean a behavioral change to any
of the 42 audited constants cannot occur without at least one of the two
values moving.** A reader comparing two runs' provenance records can tell,
without reading a line of code, whether either surface changed.

**Residual gap, stated rather than smoothed over:** neither hash catches a
change in an **installed dependency's own behavior** — e.g. a MediaPipe or
NumPy point release that alters a computation's output without any file in
this repository changing at all. That risk is caught by neither hash;
`requirements.txt`'s pinned versions (A3 above) are the only defense
against it, and pinning prevents silent drift but does not itself detect a
behavior change *within* a pinned version (a package publishing a patch
release under the same pin, or a transitively-pinned sub-dependency
resolving differently on a clean install, would not be caught by either
hash or by the pin itself). Also unaddressed: a change to a file that
computes a validated-path VALUE but lives outside the 5 hashed files (none
are currently known to exist — the 39 constants were confirmed by direct
search to live only in those 5 files — but this hash would not catch a
future constant added somewhere else without also being added to
`VALIDATED_PATH_SOURCE_FILES`).

---

## A3 — Pinned dependencies

**File:** [`requirements.txt`](../requirements.txt)

Re-verified this session: `python -m pip freeze` against the actual
installed environment, diffed against `requirements.txt` (ignoring only
line-ending noise — this repo's `requirements.txt` has CRLF line endings,
`pip freeze`'s output does not). **Zero package differences.** The file's
own header claim (Python 3.12.10, `Windows-11-10.0.26200-SP0`) was checked
against `platform.platform()`/`platform.python_version()` run live this
session and matches exactly.

**Model bundle versions/checksums:** already linked by reference —
`models/MODEL_MANIFEST.md` records SHA256 + size for both `.task` bundles
and states which pinned `mediapipe` version each pairs with
(`mediapipe==0.10.35`, matching `requirements.txt`). No new linkage needed;
confirmed the existing one is still accurate (the manifest's own stated
limitation — no live download-and-compare against the source URLs was
performed — stands unchanged, and is not something this task re-verified).

---

## A4 — Data manifest

**Generator:** [`manifest/generate_data_manifest.py`](../manifest/generate_data_manifest.py)
**Output (committed):** [`manifest/data_manifest.csv`](../manifest/data_manifest.csv)

One row per file in `logs/` (50 files, matching `logs/`'s current
contents exactly — re-run the generator to regenerate if `logs/` changes;
it is read-only and idempotent). Columns: `path`, `sha256`, `size_bytes`,
`subject_id`, `session_id`, `trial_id`, `experiment_id`,
`acquisition_timestamp` (+ `acquisition_timestamp_source`),
`processing_version`, `record_type_sample`, `notes`.

**The manifest is committed; the data it describes is not** — `logs/`
stays git-ignored (G4), the CSV is the only artefact that enters version
control.

**Honesty rule applied, not smoothed over:** every file in `logs/` predates
this manifest, and most predate any concept of `subject_id`/`experiment_id`
in this codebase at all — they were written by a dozen different ad-hoc
scripts with different field names. The generator extracts an identifier
ONLY when a real value is present under one of a small set of known
historical field-name variants (`person_label`/`subject_id`/
`participant_code` for subject; `session_id`; `trial_id`; `experiment_id`;
`ts_utc`/`generated_at_utc` for acquisition time; `schema_version` for
processing version). When none of those is present, the cell is left
empty and the `notes` column states why — it never guesses or derives a
value from, e.g., parsing a filename.

**Real counts from this run:** of 50 files, 36 have no recoverable
`subject_id` (mostly diagnostic/calibration/validation captures that never
carried a person label — `browdiag_*`, `browonly_*`, `maxelicit_*`,
`yawhold_*`, `soak_log.jsonl`'s later samples, etc. — not every file in
this repo is a real participant session); **all 50 have no
`experiment_id`**, because Gate 0 provenance (A1, this same task) did not
exist when any of them were written — expected, not a bug; 14 files have
no `ts_utc`/`generated_at_utc` field at all and fall back to file mtime,
explicitly labeled `"WEAK, non-evidentiary"` in the
`acquisition_timestamp_source` column (same convention `PROVENANCE.md`
and `docs/AUDIT_A_COLUMN.md` already use for exactly this situation —
mtime is trivially alterable by any copy/checkout and proves nothing about
original acquisition time).

### Known limitation of the historical data (stated once, here, as a property of the data — not a defect a reader should have to discover)

**36 of 50 files (72%) carry no recoverable `subject_id`, and 14 of 50
(28%) have no real acquisition timestamp** (falling back to the weak file-
mtime proxy instead). This is expected, not a gap in the manifest
generator: every file in `logs/` was written before Gate 0 existed, by
scripts that in several cases predate the very concept of a `subject_id`
field in this codebase. **It is a property of the pre-Gate-0 data, not
something this manifest failed to extract.** Any log written from this
point forward, through `schema/canonical_log_writer.py` (Part B) or any
future caller of `simulation/provenance.py`, carries `subject_id` on every
record by construction (enforced in code — see `docs/CANONICAL_LOG_SCHEMA.md`)
and a real `experiment_id`/timestamp via `RunProvenance`. The historical
gap does not recur going forward; it is a closed, dated fact about data
collected before this infrastructure existed, not an open risk.

---

## A5 — Variant log

**Writer:** [`simulation/variant_log.py`](../simulation/variant_log.py)
**Log:** [`logs/variant_log.jsonl`](../logs/variant_log.jsonl) (tracked —
the sole exception to `logs/*` in `.gitignore`)

**Append-only, demonstrated not asserted:** `append_variant_log_entry` is
the only function in this repository that writes to
`logs/variant_log.jsonl` (confirmed by search), and it opens the target
file in `"a"` mode exclusively — there is no truncate/rewrite code path
anywhere. `tests/test_variant_log.py` calls it twice against a throwaway
temp file and checks the file only grows and the first line is byte-
identical before and after the second call — passed.

**Schema, confirmed flexible enough for the task's requirement**
("timestamp, description, what was tried, and why"): every entry carries
`ts_utc` (when the entry was actually written), `description`,
`what_was_tried`, `why`, plus `retrospective` (bool) and `event_ts_utc`
(the real time the described work happened, when known, for a
retrospective entry) — kept distinct from `ts_utc` so a reader can never
mistake "when this was written down" for "when it happened." `extra`
fields (e.g. `commit_range`) may be attached per entry without a schema
migration, since the format is a flat JSON object, not a fixed-column
table.

**8 retrospective entries added**, covering every substantive block of
work in this repository's commit history since the variant log's own
start commit (`06af054`, 2026-08-24) up through the start of this task
(`a15e05a`, 2026-08-31) — the repository audit, the D1 feature-block
refactor, the D6 precision-simulation build-out (three separate rounds:
initial sweep, rare-classes + controls + Pass 2, and the finalisation
pass), the primary-metric comparison work, the clip-epsilon
pre-registration, and the feature-separation shim-guard + log-evidence
work immediately preceding this task. Each entry carries its real commit
range (`extra.commit_range`) and `retrospective: true` — **never
presented as if written contemporaneously**, exactly the same honest-
framing discipline `PROVENANCE.md` already applies to this repository's
git history itself. The original entry (`version_control_established`,
written 2026-08-24) is unmodified — confirmed byte-identical before and
after the backfill.
