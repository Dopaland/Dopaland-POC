# Project State

The document to open first. CLAUDE.md carries the stable package map and discipline;
this file carries what's true right now, and changes often.

## If you are picking this up cold

Read in this order: **1)** CLAUDE.md in full, including the "D0PA1 BUILD STATE"
section — the package map and the five guardrails (G1–G5) that govern every task here.
**2)** `docs/MATRIX_ROW_MAP.md` — the 30-row §19 sign-off matrix, reconciled against
what this repository actually contains, row by row, with disagreements stated
explicitly rather than absorbed. **3)** `docs/RESPONSE_VERIFICATION.md` — the detailed
per-claim check of every implementation-status assertion in the committed sign-off
response, including two verification passes (the original and a dated addendum after
a corrected version was supplied) and the one residual gap still open. Those three
documents, read in that order, answer nearly everything a fresh session will ask.

---

## 1. Current commit and where this phase stands

**HEAD at time of writing:** `1881ac0` — "docs: add A/V sync attempt 8/9
prompt records and this task's own prompts" (the "one heading fix, then
commit" task: fixed CC-001-A's own appendix heading, which still read
"the outstanding sync measurement" after a prior task replaced its body
wholesale with a closure record — that prior task's own instruction to
leave the heading untouched was itself wrong once the body no longer
matched it. Swept both client-facing `.docx` files and
`docs/MATRIX_ROW_MAP.md` for any other stale heading/label/caption
describing the sync measurement as outstanding or pending — found none,
at the XML level including table-nested paragraphs, not just via
`python-docx`'s own paragraph enumeration. Then committed everything that
had accumulated uncommitted across the last several sync-related tasks,
in four logical commits rather than one batch — see below.)
Prior: `569ca1c` — "docs: record A/V sync as a documented omission in
CC-001" (CC-001 §6(a) replaced with the closure record; CC-001-A's body
replaced with a closure record; §7's row-23 basis text updated to say
closed-as-omission rather than outstanding; `docs/MATRIX_ROW_MAP.md` row
23's stale "five attempts across two sessions" corrected to the real
count. Proposed status/counts in both documents left untouched — that
reclassification is still the client's to confirm. CC-001 §8/§9
untouched.)
Prior: `efa5201` — "docs: record soak closure and A/V sync disposition"
(this file's own "Soak and sync outcomes" section below, and
`docs/CLIENT_FIGURES.md`'s corresponding §6/§10/§12 updates — written
before the commits below existed, hence originally labelled "not yet
committed"; that label is now closed, see below.)
Prior: `e38ddc7` — "feat: A/V sync attempts 8-9 -- diagnostic mode,
reference-edge fix, corrected diagnostic max" (the `av_sync_flash.py`/
`tests/test_av_sync_flash.py` code itself — see this section's own
detailed account below for what attempts 8 and 9 each found and fixed).
Prior: `80beea0` — "docs: update PROJECT_STATE.md HEAD pointer to this
task's own commits" (closed the "not yet committed" gap the
preregistration-corrections subsection below carried, advancing HEAD from
`95d2367` to `45b5f57`).
Prior: `45b5f57` — "docs: add A/V sync operator
runsheet and this task's own prompt records" (the "D0PA1 — Next Two Tasks,
Part 1" commit task: closed the "not yet committed" gap this section used
to carry — see below — and swept up everything that had accumulated
uncommitted across several tasks. G4 check, golden snapshot, feature
separation and the full test suite all re-verified passing before and
after. Five commits, grouped by logical change rather than one batch,
though two of them (`e724167`, `87d7002`) predate this task and are coarser
than this task's own would have been — not re-split, since rewriting
already-landed history to look tidier is not something this task does.
Prior: `92352e3` — "docs: remove superseded SOAK_OPERATOR_RUNSHEET.md" (the
in-repo procedure-only copy, superseded once the merged procedure+frozen-
rule runsheet was established as living outside the repo).
Prior: `d9f00d6` — "chore: ignore Claude outputs/ to backstop frozen-rule
repo-hygiene rule" (a folder holding the frozen soak acceptance rule itself
had appeared twice, untracked, inside the repo tree — ignored as a
backstop against an accidental `git add -A`).
Prior: `87d7002` — "docs: add held audio-terminal-read prompt and CC002
change-control draft".
Prior: `e724167` — "chore: D0PA1 closure batch -- soak_checkpoint record,
pitch-claim retraction, av-sync flash tool" (this is the commit that
resolved the "not yet committed" gap below: both client-facing `.docx`
files' pitch-claim retraction and internal-contradiction fixes, the
`soak_checkpoint` record type, and the `av_sync_flash.py` instrument all
landed here as one batch).
Prior: `95d2367` — "feat: run the genuine empty-scene
control; row 16 EVIDENCED; figures pack closed out" (the "THE LAST GAP
BEFORE THE DOCUMENTS GO" task: ran `controls/null_input.py` for real,
camera on, no subject, 10 real minutes — the empty-scene control this
engagement had never actually run. Result: zero false-signal events,
exhaustively checked across all 17,888 real per-sample records — no face,
no pose, no composite/covariate value, no yaw reading, ever.
`calibration_completed: false`, correctly — the first real-world
confirmation of the prior task's `NeutralCalibrator` fix behaving correctly
on genuinely degenerate live data. No raw video was ever written (this
control processes every frame in-memory by design). Fixed the sign-off
response's stale §4.11 "clean object store" bullet to the durable wording
§4.27 already uses, and updated row 16 (null-input control) — in both
`docs/MATRIX_ROW_MAP.md` and the response document's own §4/§6 — to
`EVIDENCED`, naming the quiet-sitting baseline and the empty-scene control
separately for the first time, since the row's own original text
conflated them (matrix counts now 12/6/9/3, up from 11/7/9/3). Closed out
`docs/CLIENT_FIGURES.md`'s empty-scene section with the real result;
confirmed exactly two NOT TRACEABLE gaps remain (the audio sync figure,
real reliability figures) — no third. Also recorded the golden-hash
supersession durably in `docs/GATE0_PROVENANCE.md` (new dated note),
`CLAUDE.md`, and this file's own §1, per that task's own Step 0.
Prior: `b9ea218` — "docs: add client figures pack --
traced figures, corrections record, audio scope-change record, outstanding
items" (the "FIGURES PACK FOR THE CLIENT DOCUMENTS" task, documentation
only: assembled `docs/CLIENT_FIGURES.md` from artefacts already in this
repository, marking anything untraceable rather than filling it in —
notably the empty-scene control, which was never run, and the audio sync
measurement, which has never succeeded across 3 real attempts. Checked
eleven candidate claims from the user's own strategy notes against live
re-runs and direct `.docx` text extraction: ten confirmed, one found wrong
(a "27 of 27 verified to the stated figures" overclaim — the headline
27-of-27 VERIFIED count is accurate, but not every claim matched its exact
stated figure on first check). Compiled the corrections record for the
first time in one place: ten real corrections, none ever sent to the
client — verified by reading both client-facing `.docx` files' raw text
directly rather than trusting either document's own status labels; the
user's own prompt listed ten items while stating "eight," reported as a
direct count mismatch.
Prior: `44c02be` (fix) / `e4aa779` (docs) — the "AFTER THE PHYSICAL RUN"
task, Tasks 1–3 only (Tasks 4–6 — the empty-scene control, a sync
remeasurement, and the final retraction/report — were never run; that
session was interrupted before reaching them, and this repository's
working tree held the completed portion uncommitted until the next task
committed it). Task 1: found and fixed, with explicit permission, the
`NeutralCalibrator` bug reported by the prior task
(`is_calibrated()` returning `True` for a reference with zero real
samples) — `is_calibrated()` now checks an explicit `missingness_flag`
stamped on the reference rather than only "reference is not None";
should_complete()'s one-shot timing itself is unchanged. Blast-radius
check: scanned every real `calibration_complete` record in `logs/` (11
total) and found exactly 1 affected (the quiet-sitting baseline), its
dispersion table independently unaffected, and its one affected figure
(`excursion_count=0`) already reported as compromised at the time, never
sent to the client. Task 2: re-derived the vertical ROI verdict from real
graded pitch data rather than re-arguing the prior framing — magnitude is
solved at maximal commanded effort but not at ordinary intensity;
detection rate (8–27% even at the best maximal attempt) is now the
dominant blocker; practical verdict unchanged, reason moved a second
time. Task 3 (partial): renamed the quiet-sitting baseline away from
"null-input control" and explained its detection-rate pattern from the
real per-frame log.
Prior: `044ebca` — "docs: record PHYSICAL RUN SESSION
findings — null-input, pitch, sync, soak" (the "D0PA1 — PHYSICAL RUN SESSION"
task: the first session in this engagement to perform real camera/microphone
captures rather than investigate, build, or audit. Task 0 mic gate passed
(real signal, not the OS-policy silence artefact from the prior session,
which is now recorded in the corrections record below). Task 2 null-input
control run for real, 10 minutes, with a human subject present — see the
challenge/acceptance record and the full dispersion table below — and found
a real bug in the G5-protected `NeutralCalibrator`: a zero-real-sample
calibration window silently produces a null reference, which silently
disables `ExcursionDetector` for the rest of the run. Task 3 graded-intensity
pitch capture (new `graded_pitch_capture.py`, reusing `orientation_capture.py`'s
never-before-run schema-1.1 path) found real pitch up to -43.1 deg on maximal
attempts, scaling with commanded intensity — directly contradicting the
previously documented "~0.1 deg, structural, not fixable" claim, which is
retracted in `CLAUDE.md` and `docs/ROI_FEASIBILITY.md` this task; the
underlying mechanism (M1/M2/M3) is reported as still undifferentiated, not
rounded toward a tidy answer. Task 4 sync measurement: 5 video-motion-
threshold iterations across 5 real recordings never produced a trustworthy
audio/video match; no offset/spread/drift figure is reported, per the task's
own instruction not to present a noisy match as real data. Task 5 (blink
clips) explicitly skipped, session ran long. Task 6: the stability soak was
attempted twice for real and both times self-terminated after ~80-90s — a
real, diagnosed, environment-specific limitation (not a code defect), stated
honestly rather than claimed as a running soak — see the corrected item
below. Every raw recording made this session was deleted and confirmed;
only derived, non-identifying JSONL logs were kept.
Prior: `0fc829e` — "docs: correct stale physical-run
claims, record the sync-measurement attempt" (the "ENVIRONMENT AUDIT, SYNC
MEASUREMENT, G5 RIPPLE CHECK" task: tested — not re-read — every prior
session's "this coding environment cannot provide a live webcam" claim and
found it stale; a real camera and a real default microphone both open,
stream, and hold open simultaneously without failure or measurable
degradation, though only one physical camera exists (checked specifically,
per this task's own caution not to conflate that with a second camera).
Attempted the clap-based sync measurement live with the user's real-time
cooperation, entirely in-memory, and hit a genuinely new, non-hardware
blocker: no real acoustic content reached this process across two
microphones and two host APIs, consistent with an OS-level
microphone-privacy restriction — corrected the prior task's "genuine ...
room level" reading as very likely this same access-blocked silence
artifact, not real ambient sound. Verified the G5 ripple from the prior
task's consent-signature change directly (identical one-line diffs, dead
unused variable, additive-only record fields) and confirmed the line was
drawn correctly. Named the raw-media storage-location gap (neither video
nor audio has ever had one decided) as one item and proposed, without
deciding, a unified env-var-rooted pattern for both — see
`docs/AUDIO_ACQUISITION.md` §7 and `docs/PRIVACY_AND_RETENTION.md`'s named
open item.
Prior: `b5f440a` — "docs: audio moves from BLOCKED to RETAINED AND IN
ACQUISITION" (the "AUDIO PART A" task: the client's keep-or-formally-remove
decision on `Δ_audio` has been made — RETAINED. Built: the privacy guard
extended to every audio container; an audio acquisition instrument
(`audio_acquisition.py`, own thread, per-chunk level/timing integrity
logging, no content analysis); audio consent as a separate, independent,
architecturally-unreachable-when-declined question; raw audio's storage
location as env-var config, never a committed literal; the separation guard
extended to cover `audio_acquisition.py` itself as direct U_t content (a
real gap found by audit, the same way the `context`→`attention`/`audio` gap
was found the prior task). The FPS-impact proof used a synthetic
video-timing harness against the real microphone (camera use was declined
for that session); the audio/video sync measurement — Part A's actual
point — was **not performed** that session, stated plainly per that task's
own instruction, since it needs a physical event visible to
both sensors and only audio was exercised. See `docs/AUDIO_ACQUISITION.md`
for the full record, including the change-control note: this decision
reverses the sign-off response's own recommendation and is a scope change
against frozen `Scope v0.5.1`, not yet processed through the client's §18
change control.
Prior: `720af64` — "docs: record check-2 context gap and pitch-mechanism
correction in state docs" (the "PITCH: SEPARATE THE FINDING FROM ITS
EXPLANATION" task).)

### Soak and sync outcomes — committed in `e38ddc7`/`efa5201`/`569ca1c`/`1881ac0`

This subsection recorded session work (three interactive soak runs, nine
A/V sync attempts, several code fixes to
`av_sync_flash.py`/`tests/test_av_sync_flash.py`) that existed only in
this conversation and the uncommitted working tree at the time it was
first written. **That gap is now closed** — the same "not yet committed"
pattern this file's own HEAD-pointer chain above already records once —
via four commits: `e38ddc7` (the `av_sync_flash.py`/test code itself),
`efa5201` (this section and `docs/CLIENT_FIGURES.md`'s corresponding
updates), `569ca1c` (CC-001's documented-omission record and
`docs/MATRIX_ROW_MAP.md` row 23), and `1881ac0` (the process-prompt
records for the sync work). Folded into the HEAD-pointer chain above.

**The extended stability soak is closed.** Three interactive runs, against
a frozen acceptance rule kept OUTSIDE this repository (same convention as
`GATE2_SCORING_RULE.md`/`ORIENTATION_SCORING_RULE.md` — not copied in
here; three revisions, v1–v3, exist there):

- **2026-09-14, 73.2 min**, stopped by operator, `clean_exit: true`.
  Verdict **INCONCLUSIVE** under the then-current rule (no scene-validity
  precondition existed yet). `detect_rate` ≈0 for 71 of 73 minutes — the
  printed photo used as the scene had slipped from frame.
- **2026-09-16, 140.2 min**, stopped by operator, `clean_exit: true`.
  Verdict **VOID** under the scene-validity precondition added after the
  first run: mean `detect_rate_60s` 0.493 against a required ≥0.90 — the
  "scene" was a person present intermittently, not an unattended screen.
  The five criteria were still computed and are recorded here, but capped
  by VOID, never counted as passes: FPS drift ratio 1.015, FPS floor
  19.7/24.76 fps, memory Δ +2.1MB over 130 min, no leak signature across 4
  windows, liveness clean.
- **Closed under the rule's own pre-declared stopping condition** — no
  fourth run without a new reason (a capture-path code change, a client
  request, or a specific stability concern that actually arises).

**Two statements stand, and must be kept apart, per the frozen rule's own
B.5/B.4 wording:**

1. **The only validated stability claim:** *"stability demonstrated over a
   41-minute continuous soak"* (POC era, passed against POC criteria).
2. **Raw observation, not a pre-registered result:** two interactive runs
   of 73.2 and 140.2 minutes, both clean exits, no FPS drift, no floor
   breach, no memory growth, no stalls — under intermittent or near-zero
   detection load, neither satisfying the scene-validity precondition.
   True and useful; never to be written as a stability result.

**Also recorded, closing two open questions:** the ~90-second
self-termination seen in earlier attempts is established as
launch-context dependent, not a code defect — both interactive runs above
reached 73 and 140 minutes with clean exits, and `stage3_demo_ui.py`'s
`cv2.getWindowProperty`-based shutdown logic was never modified (G5). FPS
under genuine detection load is ~29 (28.9–29.8 fps at `detect_rate ≈
1.0`), matching the POC baseline — the 2026-09-14 run's low 20.66 floor
was a startup-ramp artefact, not a regression.

---

**A/V synchronisation is now a documented omission, not an open
attempt.** Nine attempts across five sessions:

- Stimulus changed twice: hand-clap with frame-difference motion
  detection → a brief global luminance flash → a 500ms held flash with a
  lengthened, full-amplitude click.
- **Two defects found by code review and corrected before the final
  attempt.** (1) The video reference timestamp
  (`flash_render_completed_ts`, now `flash_first_frame_ts`) was assigned
  after the flash's hold ended, while the audio reference
  (`audio_first_callback_ts`) marks the click's start — opposite edges of
  their stimuli, biasing every offset by ≈−`flash_duration_ms` (predicted
  −500ms, observed −502.5ms in the attempt this was found in). (2) The
  diagnostic's `max_value_in_window` spanned the whole ±1s window
  including time before the stimulus, so a pre-stimulus ambient-noise
  event could be reported as though it were the stimulus's own response —
  confirmed for two specific emissions whose "peaks" landed 0.75–0.98s
  before their own reference. Both fixed; `av_sync_flash.py` now also
  reports `pre_reference_max_value` per emission so this failure mode is
  visible rather than silently repeated.
- **Video-side registration was diagnosed and fixed — a real, durable
  result.** 19/19 emissions register cleanly at 19×–72× the detection
  threshold in the final attempt. The mechanism was the flash's real-world
  duration: a ~3-frame flash against a ~33ms camera exposure period made
  whether it landed inside a captured frame close to a coin flip; holding
  it for ~500ms resolved this completely.
- **Emitter confirmed working** in every attempt from the diagnostic
  session onward — flash-render and audio-callback timestamps recorded
  directly (own confirmed-callback audio stream, `cv2.getWindowProperty`
  read only into a log field, never used for control flow), never
  assumed.
- **Audio-side registration fails, and the cause is NOT characterised.**
  An earlier attribution to ambient noise rested on the diagnostic
  statistic later found to measure pre-stimulus noise rather than the
  stimulus's response, and does not stand. It is **not** replaced with a
  new cause. "We do not know why" is the supportable statement.
  - **Checked this task, directly from the code, per this task's own
    instruction to verify rather than assume:** whether the audio onset
    detector is the same across the hand-clap era (attempts 1–5) and the
    speaker-click era (attempts 6–9). **It is not.** The clap-era attempts
    used a percentile-based threshold (`docs/AUDIO_ACQUISITION.md` §4
    describes the working version; §7 records it being "moved to a
    percentile-based threshold with an absolute floor" after an earlier
    thresholding bug). `av_sync_flash.py`'s `find_onsets` is a different
    algorithm: a causal rolling-median + k×MAD detector with refractory
    gating. No script from the clap era survives in this repository to
    compare directly — only the described mechanism does, and it is
    described differently. Because the two detectors differ, a clap being
    reliably detected by the old one does not establish anything about
    whether the same detector would or would not detect a click. **The
    narrower claim — "the detector registers real acoustic transients,
    only the click reaching the microphone at a detectable level is what
    fails" — is not supportable from this evidence and is not made.** The
    broader "audio-side registration fails, cause not characterised"
    statement is the one that stands.
- **Consequence:** Δ_audio cannot be computed. §10.9's condition is
  **not** lifted by the acquisition build alone — a working acquisition
  pipeline is not the same as a working synchronisation measurement.
- **Closed under a pre-declared, final stopping condition.** No further
  attempts proposed, no further diagnostics proposed.

This closes both items that were previously the entire contents of
`docs/CLIENT_FIGURES.md` §12's "Needs nothing but machine time" bucket —
see that document's own updated §12 for the disposition, and its §6/§10
for the fuller audio record.

### Preregistration document corrections — three closure tasks, committed in `e724167`

Three sequential tasks (this engagement's "D0PA1 closure work," "Task 1c
redo," and "two `.docx` fixes" tasks) corrected both client-facing
preregistration documents. **Both `.docx` files were committed in
`e724167`**, folded into that batch commit rather than split out on their
own — see the HEAD-pointer chain above.

- **Both preregistration `.docx` files are now free of the retracted pitch
  claim.** `D0PA1_Section19_SignOff_Response.docx` §4.14: the two
  asserted-as-fact paragraphs were replaced with four retraction
  paragraphs; a redundant fifth paragraph left standing by the first pass
  (making the same point as the new closing paragraph) was subsequently
  removed entirely, not blanked. `D0PA1_Build_Status_Report.docx` §5.4:
  the section heading itself ("Attention pitch detection is structurally
  unreliable") and its two body paragraphs were replaced with a corrected
  heading and three retraction paragraphs. A final multi-term sweep of
  both documents (`0.1°`, `structurally unreliable`, `chin-to-chest`,
  `not fixable`, `oriented-rate stayed at 1.0`) found every surviving hit
  sitting inside retraction language, never asserted as current fact.
- **Two internal contradictions were also fixed in the sign-off response's
  closing section**: "Eight rows are implemented and tested but have
  never touched real data" corrected to "Six rows" — independently
  counted against `docs/MATRIX_ROW_MAP.md`'s response-status column before
  editing (rows 3, 4, 9, 15, 18, 30) rather than taken on request — and
  the stale clause "the null-input control has no camera run" removed,
  since it contradicted that same document's own §4.16 and §6 (both
  null-input runs — quiet-sitting baseline and empty-scene control — have
  in fact been performed against a real camera).
- **`docs/MATRIX_ROW_MAP.md` row 14's citation of §4.14 was checked directly
  and is correct** — it was briefly suspected of being wrong as a
  consequence of the same false-negative audit method (below), and was
  **not** changed.

**The repository-side work is complete for this phase.** "Complete" here has a
specific, narrow meaning, not a general one: **everything that can be built without
the client's task harness, real recordings, or a client decision has been built,
tested, and cross-checked against the pre-registration response that describes it.**
That is a real, bounded claim — checkable by reading `docs/MATRIX_ROW_MAP.md`'s 30-row
table — not an assertion that the study itself is finished. Nothing downstream of a
real collection session exists yet, by design; that is the next phase, not this one.

Concretely, as of this commit:
- All D0PA1 infrastructure describable in code (D1 separation, D3/D7/D6 machinery,
  all five controls, the canonical schema, Gate 0 provenance, D4 reproducibility,
  privacy/retention) is built and tested against synthetic input.
- The pre-registration sign-off response (`docs/preregistration/D0PA1_Section19_SignOff_Response.docx`)
  is committed, in its third and current revision, with every implementation-status
  claim in it independently verified against live re-runs of this repository's own
  tests — not recalled from documentation, not taken on the document's own word.
  27 of 27 checkable claims verified; the handful of findings raised were either
  corrected in the current revision (four of five) or explicitly flagged as still
  open (one residual textual gap; two judgment-call boundary questions).
- `git fsck --full --strict` returns clean (verified this session, after
  `git reflog expire --expire=now --all` + `git gc --prune=now`).
- The golden regression test (`tests/test_refactor_snapshot.py`) matched its
  committed SHA256 (`4f9c0f1786c18e8dbe5e3048b8b6b6e280cf6c434b9c53b119344746fc31bcff`)
  through every commit up to `13e3dd4`. **That hash is now superseded** —
  the "AFTER THE PHYSICAL RUN" task's Task 1.3 fixed a real
  `NeutralCalibrator` bug (explicit, one-time G5 permission) and
  regenerated the golden file; the diff was confirmed to be exactly the two
  new `missingness_flag`/`missingness_reason` fields, nothing else on the
  validated path moved. **Current golden SHA256, matched at every commit
  since `44c02be`:** `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`.
  See `docs/GATE0_PROVENANCE.md`'s dated supersession note for the full record.

Last several commits, most recent first (see `git log` for the full history):

1. `6e5bef7` / `0a7bc98` — the corrected sign-off response committed (third revision),
   all five prior findings re-checked against the actual new text (four fully
   corrected, one partially — see `docs/RESPONSE_VERIFICATION.md` §5), and the row
   map reconciled against it.
2. `f60ff88` / `1235101` — the original verification pass: every implementation-status
   claim in the second response revision checked against live test re-runs.
3. `5fac8e2` / `5b2749b` — the response document's history: an agent-authored
   substitute (found improper and removed), then two real vendor-authored revisions.
4. Earlier: Gate 0 provenance, the canonical schema, signal completions, D7/D3, all
   five controls, D6's three sweep passes, the D4 reproduction command, and the
   privacy/retention mechanism — the full D0PA1 infrastructure build, documented in
   CLAUDE.md's own "D0PA1 BUILD STATE" section.

---

## 2. Outstanding items, in three groups

Nothing below is a code gap. Everything in this repository that can be built without
one of these three things has been built. These are listed because a future session
must not attempt to close any of them by writing code — each needs something this
repository cannot supply on its own.

### Needs the client's task harness (the controlled software environment producing ROIs and logged on-screen actions)

- **D2** (prediction target: real action classes, horizon, tie/rapid-succession
  handling) — everything downstream waits on this.
- **Real `A_t`/ROI attention features** beyond the existing pilot V_so/gaze/blink
  code — with one distinction now load-bearing, established by
  `docs/ROI_FEASIBILITY.md` §5 and repeated here so it cannot be lost: the
  **aggregation math** (dwell/switching/persistence/coverage over a *supplied*
  `(timestamp, roi_id)` stream, `features.attention.ROIWindowAccumulator`) is
  **built and tested** against a synthetic supplier — this specific piece is
  blocked ONLY on the harness delivering the stream, i.e. integration work, not
  construction. **Gaze-to-ROI attribution from this system's own sensor** is a
  separate, independent limit — constrained by real angular-resolution
  measurement (`docs/ROI_FEASIBILITY.md` §2), not by the harness at all: coarse
  horizontal (left/right) attribution is defensible; vertical attribution is not,
  at any tested granularity, including the coarsest possible split. A future
  session must not present these two as one blocked item — the harness arriving
  resolves the first and does nothing for the second.
- **The leakage and time-shuffle controls run on real trial data** — both harnesses
  are built and exercised on synthetic data only; `leakage.py`'s `post_action` variant
  specifically cannot even establish its expected *direction* on synthetic data (see
  `docs/CONTROLS.md` §3).
- **D3/D7's reliability and baseline machinery run on real sessions** — three real
  sessions on three separate days, fixed protocol, matched repeatable units. Not
  collected; nothing here can be pointed at real data until the harness (and the
  reliability-episode design that depends on it) exists.
- **`CanonicalLogWriter` wired into a real capture loop** — the schema and writer are
  built and tested in isolation; no real session writes through them today.
- **The D4 confirmatory reproduction** — `reproduce.py` regenerates the analysis
  machinery from synthetic/self-contained inputs today; the confirmatory archived
  inputs (real stored video + a real logged feature stream) don't exist yet.
- **The harness acceptance check itself** (§4.2 of the response: the vendor's own
  check of the delivered harness against §6.4/§6.5/§6.8) — per the response's own
  corrected wording, this has not started; the harness package has not yet been
  opened by a session.

### "AFTER THE PHYSICAL RUN" task, Task 1 — calibrator bug blast-radius check

Before fixing the `NeutralCalibrator` bug found last phase (see below), this
task checked whether it had already affected any PREVIOUSLY REPORTED figure
— from the logged record, not from reasoning about the code.

**Every `calibration_complete`/`null_input_calibration_complete` record in
`logs/` was scanned this task** (11 total across 10 POC-era `session_*.jsonl`
files plus the one real `null_input_*.jsonl` file) and each composite
vector's real-sample count (`n`) checked for the degenerate
all-composites-zero pattern the bug produces:

| File | v_bf n | v_es n | v_pd n | Degenerate? |
|---|---|---|---|---|
| session_09a3bc97… | 549 | 549 | 633 | No |
| session_2be7a0e4… | 736 | 736 | 747 | No |
| session_35bd3488… | 716 | 716 | 715 | No |
| session_518d2fe5… | 620 | 620 | 619 | No |
| session_677e0e86… | 755 | 755 | 754 | No |
| session_91da6e39… | 614 | 614 | 613 | No |
| session_bc384003… | 614 | 614 | 613 | No |
| session_d7339aaa… | 641 | 641 | 645 | No |
| session_eb41ba71… | 588 | 588 | 654 | No |
| session_fd54305e… | 620 | 620 | 620 | No |
| null_input_06e8d2be… | 0 | 0 | 0 | **YES** |

**1 of 11 (9%) sessions with a completed calibration is affected — the
quiet-sitting baseline from last phase, and only that one.** Every POC-era
`session_*.jsonl` file has hundreds of real composite samples per vector;
none is degenerate.

**Which previously reported figures rest on the affected session, traced
specifically, per this task's own instruction:**

- **The dispersion table** (`v_bf`/`v_es`/`v_jc`/`v_pd` std/mad_scaled/
  `zero_dispersion`) from that same session — **NOT affected**.
  `compute_dispersion` (`controls/null_input.py`) reads `raw_values`,
  appended whenever `face_detected` was true, entirely independent of
  `calibrator`/`is_calibrated()` — re-verified directly from the code again
  this task, not just re-cited from last task's claim (G3: do not trust a
  prior session's status claim over a fresh check).
- **The `excursion_count = 0` figure, same session, same table** — **the
  ONE affected figure**, and it was already reported as compromised, in the
  same document, in the same task that produced it (last phase's own
  PROJECT_STATE.md text, and that task's own final report to the user, both
  stated the excursion detector never ran rather than presenting "0" as a
  clean pass). It was never presented anywhere, at any point, as an
  unqualified clean result.
- **`docs/MATRIX_ROW_MAP.md` row 16 ("Null-input control")** and
  **`docs/RESPONSE_VERIFICATION.md` §2's V_pd robust-scale figures
  (1.6e-4 / 2.6e-3 / ratio ≈16.75)** — checked specifically, since both
  reference real log data near this topic. Row 16's own text already says
  "BUILT, NOT YET RUN ON REAL DATA" (now itself stale post-physical-run, a
  separate, smaller correction — not a calibrator-bug consequence) and does
  not cite the excursion figure. The V_pd robust-scale figures trace to
  `session_eb41ba71-7b48-4126-ae6f-8162b79ca890.jsonl` (confirmed above:
  `v_pd n=654`, NOT degenerate) — **not affected**, a different, real
  session.
- **`docs/preregistration/` (the only documents in this repository ever
  intended for client delivery)** — searched specifically: no reference to
  the quiet-sitting/null-input session, the excursion figure, or this bug
  anywhere. **Nothing built on the affected figure has ever been sent to the
  client** — this stays in the "found and corrected before it left this
  repository" category, not the "already delivered, now needs a retraction
  to the client" category. See Task 6's corrections-record entry for the
  same distinction stated plainly for the record.

**Conclusion: the bug's blast radius is one session, one figure, that
figure was already caveated everywhere it appeared, and nothing built on it
reached the client.** This is a real, checked result — not an assumption
that "it probably didn't matter."

### Needs a physical run — THREE items actually run this phase ("PHYSICAL RUN SESSION")

**Task 0 gate result, stated first because it governs everything below:**
the microphone-content-access block found last phase (exact 16-bit
quantization floor / exact digital zero regardless of real noise) is
**gone this session** — a 2-second gate recording showed real, varying
signal (min=-0.084, max=0.057, std=0.00247, 1362 distinct values). Not
explained; not investigated further, per the task's own scope — recorded
as a fact: it was blocked one phase, it is not blocked this phase, on the
same machine.

**1. Quiet-sitting baseline (NOT the null-input/empty-scene control) — RUN,
10 real minutes, subject present.** **Renamed by the "AFTER THE PHYSICAL RUN"
task's Task 3** — this heading previously called the run below "the
null-input control," and that name was wrong, not just informal. The
technical argument for why a HUMAN was needed for what was actually run
(`compute_v_pd` needs real pose landmarks to produce any dispersion figure
at all) is still correct — an empty chair genuinely cannot produce THIS
particular measurement, a per-signal dispersion figure under the pipeline's
normal calibrated path. But that is a reason this run needed a person, not
a reason it deserves the name "null input" — a true null/empty-scene input
means literally no subject in frame, and what "null-input" conceptually
promises is the false-signal floor: what the pipeline reports when there is
nothing to measure at all. That is a DIFFERENT, still-outstanding question,
answered for real for the first time in this task's own Task 4 below, not
by the quiet-sitting run described here. Real result,
`logs/null_input_06e8d2be-f603-4c18-a654-98fb375fbd13.jsonl`
(12,234 records, kept — contains no image, only derived numbers; filename
unchanged from when it was logged, since renaming a committed log file
after the fact would break its own internal `session_id`-based traceability
for no real benefit — only the DESCRIPTION of what it is changes here):

| Signal | std | mad_scaled | zero_dispersion | excursions (0-min baseline) |
|---|---|---|---|---|
| v_bf | 0.0348 | 0.0270 | false | 0 |
| v_es | 0.0436 | 0.0407 | false | 0 |
| v_jc | 0.0173 | 0.0148 | false | 0 |
| v_pd | 0.00605 | 0.00180 | false | 0 |

Overall `detect_rate = 0.295` (3,612/12,231 frames) — but this hides a
real, structured pattern, not a stable rate: per-minute face-detect rate
went 0.003 → 0.000 → 0.000 → 0.222 → 0.933 → 0.997 → 0.990 → 0.681 → 0.000
→ 0.000 across the 10 minutes — near-zero at the start and end, ~99% only
in a roughly 3-minute middle stretch. Not interpreted here (G1); a real,
reportable instability in how reliably this setup holds detection over 10
minutes.

**The detection pattern, explained (Task 3.2) — real, checked against the
data, not just proposed:** a per-minute breakdown of `yaw_deg` alongside the
detect rate (computed fresh this task from the same real log) shows the
near-zero opening two minutes (0.3%, 0.0%, 0.0%) are followed by five
minutes of strong detection (22%→93%→99.7%→99.0%→68%) during which the
subject's face, when detected, sat at a consistently large, roughly
constant yaw offset (avg −18° to −30°, individual readings ranging as
extreme as −79.2° to +8.3°) — not centred on the camera — before dropping
back to exactly zero for the final two minutes (8, 9). **Ruled out directly,
by reading the code, not by elimination:** the calibrator bug above CANNOT
be the cause — `face_detected`/`pose_detected` in `controls/null_input.py`
are set purely from MediaPipe's own `detect_for_video` success/failure,
called and recorded before `calibrator.add_sample()`/`calibrator.complete()`
run at all; nothing about calibration state feeds back into detection.
**Also checked and ruled out: no D0PA1-added quality gate (the 35°-yaw
CLAUDE.md describes) is applied in this script at all** — only MediaPipe's
own `min_face_presence_confidence`/`min_tracking_confidence` thresholds are
in effect, so the extreme yaw readings during the "good" stretch are real
MediaPipe successes despite the large angle, not gated readings. **The most
data-consistent explanation, stated as an inference from telemetry rather
than a witnessed fact (no video was kept, per G4, so this cannot be
independently confirmed from a recording):** the subject was most likely
not yet settled into frame for the first ~2 minutes (there is no
interactive "ready?" gate in `controls/null_input.py` between printing
operator instructions and starting the 10-minute clock — the clock starts
almost immediately after the two MediaPipe models load), was present but
seated at a real, substantial, roughly constant angle to the camera — not
looking straight at the lens — for the ~5-minute middle stretch (consistent
with a camera/screen physically offset from where the subject was actually
oriented, a framing detail, not a lighting or warm-up effect), and most
likely left frame again before the full 10 minutes elapsed for the final
~2 minutes (a long, complete, zero-detection stretch is more consistent
with physical absence than with a merely bad angle, since a person present
but off-axis for 10 minutes straight would be expected to occasionally
re-center and produce at least some detections, as the middle stretch
itself shows). **A camera-hardware or lighting warm-up effect is considered
and rated less likely**, given the scale (minutes, not the sub-second-to-
low-second range typical of auto-exposure/auto-gain settling). **Until this
is independently confirmed by a monitored re-run, the DENOMINATOR question
this section's own Task 4 caution flags remains open**: this session's
5-minute "good" stretch is itself not a clean, centred, at-rest baseline —
it is a real person, present, but oriented well off-axis for its duration —
so even the dispersion figures above should be read as "dispersion during
whatever this particular 5-minute stretch actually was," not as "dispersion
during a canonical, centred, quiet-sitting baseline." This is a genuine,
reportable limitation of the ONE run collected, not evidence the pipeline
itself is unstable.

**A real bug in the G5-protected validated path was found last task and is
FIXED this task, with explicit Task-1.3 permission** (see Task 1's own
blast-radius check below for which sessions were and were not affected, and
`features/x_core.py`'s `NeutralCalibrator` for the fix itself):
`should_complete()` used to complete calibration purely on WALL-CLOCK
elapsed time, independent of whether any real (non-`None`) sample was ever
collected. This session's 25-second calibration window fell entirely inside
the near-zero-detection opening minutes — **zero real samples for every
signal** — and `complete()` silently produced a reference of
`{mean: null, std: null, n: 0}` for all three composite signals and all
three covariates, while `is_calibrated()` still reported `True` for it.
Consequence, confirmed directly at the time: the excursion detector's `z`
stayed `None` for the entire session, so **`excursion_count = 0` for all
four signals was NOT evidence of a clean null result — it was an artefact
of the detector never running at all** this session. The dispersion table
above is unaffected (`compute_dispersion` reads `raw_values`, collected
independently of calibration, whenever `face_detected` was true, re-verified
directly from the code again this task) — only the excursion/false-event-rate
half of the original ask was compromised, and it was reported as
compromised at the time, not smoothed into a false "0/min, clean" claim.
Post-fix, `is_calibrated()` now correctly reports `False` for this exact
degenerate case (`missingness_flag: true, missingness_reason:
"not_yet_calibrated"` stamped on the reference) — this record of what
happened is retained rather than rewritten, since the log file itself is
immutable and was produced under the pre-fix code.

**2. Directed pitch capture — RUN, graded intensity + yaw positive
control + real-time independent judgement** (Task 3), via a new script,
`graded_pitch_capture.py` (kept — reuses `orientation_capture.py`'s real
`record_segment`/`build_trial_record` unmodified; appends to the same
`logs/orientation_trials.jsonl`, same schema). Yaw positive control:
1/2 attempts detected any face at all (`look_right_control`: 0/709
frames, no judgement collected because there was nothing to judge;
`look_left_control_2`: yaw avg −34.9° range [−39.4°, −25.1°],
independently judged "held fully the whole time" — confirms the protocol
and setup CAN produce clean, real, judgement-matched yaw data, even
though this session's own yaw sample is incomplete).

**Graded pitch result — a genuine, materially significant reversal of
every prior session's finding, reported plainly rather than downplayed:**

| Phase | Judgement (collected in real time) | Detection rate | Raw pitch avg | Raw pitch range |
|---|---|---|---|---|
| small (slight glance) | held slight glance, full duration | 1/1282 (0.08%) | 5.66° (single sample) | n/a |
| medium #1 | held moderate tilt, full duration | 124/1129 (11%) | 2.24° | [−3.21°, 5.58°] |
| medium #2 | held moderate tilt, full duration | 224/1144 (20%) | 3.00° | [−11.1°, 11.6°] |
| maximal #1 | genuine maximal chin-to-chest, full duration | 182/663 (27%) | −31.6° | [−43.1°, −15.2°] |
| maximal #2 | "same effort as attempt 1, genuine maximal" | 94/749 (13%) | −15.2° | [−23.6°, −1.17°] |

**Unlike every session before this one, pitch DID register large,
real values during genuinely, independently-judged maximal attempts** —
up to −43.1° at the extreme, an order of magnitude beyond the ≤4.4°
figure `docs/ROI_FEASIBILITY.md` and `PITCH_DIAGNOSTIC.md` built the
"pitch is structurally unreliable" finding on, and starkly inconsistent
with CLAUDE.md's own "verified chin-to-chest... pitch stayed ~0.1°"
claim, which `docs/ROI_FEASIBILITY.md` §2.4a already flagged last phase
as undocumented and unverifiable. **Magnitude also scaled with commanded
intensity in the expected direction** (|5.66°| small → |2.24–3.00°|
medium → |15.2–31.6°| maximal) — the graded-series signature Task 3.2
asked for, and evidence against a simple "the estimator never responds to
real pitch effort" story.

**What is NOT resolved, stated as plainly as the reversal itself:**
(a) a sign inconsistency — medium readings were positive, maximal
readings were negative, unexplained, flagged rather than silently
normalised; (b) detection RATE during every pitch attempt stayed low
(0.08%–27%) even when pitch DID register — most of every window still
produced no reading at all, a real, separate limitation from the
magnitude question; (c) both maximal attempts were judged EQUALLY
genuine and maximal by the same real-time report, yet produced
substantially different magnitudes (−31.6° vs −15.2°, roughly 2×) —
real evidence of estimator INCONSISTENCY, not subject inconsistency,
bearing on M2 specifically; (d) n=1 subject, one session, 2 maximal reps
— this reverses a claim that itself rested on comparably thin evidence,
not a large validation. `docs/ROI_FEASIBILITY.md` needs a substantive
update reflecting all of this — flagged here, not yet written (see that
document's own note).

**3. The sync measurement — attempted 5 times, no reliable figure**
(Task 4). The microphone side worked cleanly and consistently across
every attempt (real, clap-correlated transient onsets detected via a
percentile-based threshold each time). The video side — simple
frame-to-frame grayscale-difference motion detection — did not: across 5
threshold/timing adjustments, it was either too sensitive (matching
general movement, not just claps: 19 video events for ~8 real claps,
producing a 9-pair match with an 828ms spread — almost certainly
contaminated by false matches, not real sync jitter) or too strict
(0–3 video events, no usable matches at all). **No offset, spread, or
drift figure is reported** — the noisy 40ms mean / 281ms std from the
one run that DID produce matches is explicitly NOT trusted or reported as
a result, because the match quality itself was not trustworthy (per
Task 4.4's own instruction: a method whose error may exceed the true
offset tells you nothing). This is a different outcome from either prior
session (no hardware, no content access) — hardware and content both
worked; the specific visual-event-detection METHOD chosen today was not
specific enough. A brighter, more visually distinctive event (e.g. a
light flash) rather than hand-clap motion against a mostly-static
background would likely resolve this; not attempted this session.

**4. Blink clips — explicitly skipped**, per the task's own instruction
("if the session is running long, skip this... Tasks 2, 3 and 4 matter
more"). This session ran long. Zero real clips exist, unchanged.

**5. Second-camera sensor swap — unchanged, genuinely still
hardware-blocked** (only one camera exists, confirmed again implicitly
by every capture this session using camera index 0 exclusively).

### Prior phase's environment-audit framing, retained below for its own record

**"This coding environment cannot provide a live camera" was stale, and had been
stale for at least one prior session before anyone tested it.** The "ENVIRONMENT
AUDIT, SYNC MEASUREMENT, G5 RIPPLE CHECK" task tested rather than read the claim
(`cv2.VideoCapture(0)` opens, reads real 640×480 frames, ~26–27 fps standalone in a
raw read loop, MSMF backend) and a real default microphone (`sounddevice` enumerates
"Microphone Array (Intel Smart Sound Technology)", 4-channel, MME/DirectSound/WASAPI
variants all listed) — **both can be held open simultaneously with neither failing nor
measurably degrading** (camera: 25.9–26.2 fps with the mic stream running vs.
26.0–26.6 fps alone, two repeats, well inside run-to-run noise; mic: ~47,800–48,000
samples/sec against a 48,000 target both ways, zero overrun flags either way). See
`docs/AUDIO_ACQUISITION.md` §7 for the full record, including a NEW finding this
audit surfaced (genuine microphone *content* access is separately blocked for this
process — a different problem from hardware availability, and NOT resolved by this
correction).

**Checked specifically, per this task's own caution: a camera existing is not a
second camera existing.** Indices 1–3 all fail to open (`cv2.VideoCapture` returns
`isOpened()==False`) — only one physical camera exists on this machine. The
simultaneous-two-camera sensor-swap requirement (D0PA1 hard constraint #6) is
**not** satisfied by this correction and remains genuinely hardware-blocked — see
the "needs a client decision" group below, unchanged.

**What this actually unblocks, stated precisely rather than declared wholesale
"runnable" — most of these items were never blocked on camera hardware ALONE; they
need a real human's TIME as a study subject, which this correction does not by
itself supply:**

- **An extended stability soak — attempted this session ("PHYSICAL RUN SESSION"),
  real finding, NOT currently sustaining a long run.** Two real launches of
  `python stage3_demo_ui.py --soak`, both clean exits (`clean_exit: true`,
  `any_thread_death: false`, `any_exception: false` both times — not crashes),
  but both self-terminated far short of an extended soak: 90.7s (3 samples,
  FPS 27.91–29.97, mem 310.5→309.0 MB) and 80.5s (2 samples, FPS 28.92–29.95,
  mem 311.8→305.1 MB). Root cause diagnosed by reading `stage3_demo_ui.py`'s
  own shutdown logic (not modified — G5): it treats
  `cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1` (or a raised
  `cv2.error`) as equivalent to the operator closing the window via the
  X-button, and this condition appears to self-trigger reliably when the
  script is launched through a backgrounded tool-invoked process rather than
  an interactive desktop session with a persistently composited window. This
  is an execution-context limitation, not a code defect and not a data
  finding about the pipeline itself — the two short runs' own FPS/memory
  numbers are consistent with the POC-era 41-minute soak's steady-state
  values, they just don't cover enough wall-clock time to say anything new
  about drift or leaks. **Not resolved this session** (would require either
  changing G5-protected shutdown logic without permission, or running from an
  execution context this session doesn't have). The only soak long enough to
  speak to genuine long-run stability remains the POC-era 41-minute run
  (`logs/soak_log.jsonl`) — a person running `python stage3_demo_ui.py --soak`
  themselves, in their own interactive terminal with a real visible window,
  would be expected not to hit this self-close condition, since it appears
  tied to the backgrounded-launch context specifically, not to the soak code.
- **The null-input control's own 10-minute camera session** — the camera-hardware
  half of "this environment cannot provide either" is stale. The human-operator
  half is not: this control needs a real human sitting still, as the study subject,
  for 10 minutes — a real, substantial time commitment this session did not attempt
  to arrange (a brief, one-off cooperation for the sync measurement below is not the
  same thing as a structured 10-minute session). Its pure-computation pieces remain
  unit-tested only; the camera loop itself has still never executed, synthetic or
  real.
- **10 real one-minute blink clips + manual frame-by-frame counts** — same
  correction and same caveat: camera hardware no longer blocks this; the repeated
  human time (10 separate one-minute sessions) plus manual counting labor was not
  attempted this session. Zero real clips exist.
- **The directed-capture protocol that would separate M1/M2/M3 behind the pitch
  finding** (`docs/ROI_FEASIBILITY.md` §6) — same correction, same caveat: camera
  hardware no longer blocks it; the ~15–20 minute structured human session (graded-
  intensity directed attempts, independent judgement) was not attempted this
  session.
- **The audio/video sync measurement (Δ_audio's actual point)** — **attempted this
  session, with full hardware access and a cooperating human subject, and still not
  completed — for a genuinely different reason than camera/mic unavailability.**
  See `docs/AUDIO_ACQUISITION.md` §7 for the full account: the microphone's own
  ACCESS API succeeds (opens, streams, correct timing) but no real acoustic content
  — including a user's own deliberate loud claps, tested twice, across two
  different physical microphones and two different host APIs (MME, WASAPI) — ever
  reached this process. This is consistent with an OS-level microphone-privacy
  restriction on this specific process, not a hardware absence. No offset, spread,
  or drift figure exists yet; none should be assumed or estimated from acquisition
  code existing, and none should be assumed resolved by the camera/mic
  correction above — this is a separate, newly-found blocker.

### Needs a client decision

**⚠️ Four of the six items below are now CLOSED, per
`docs/preregistration/D0PA1_Client_SignOff_001.md` (signed 2026-09-19) — kept
here un-rewritten, as this document's own established practice, with the
closure recorded here rather than blended into the historical bullets:**
the δ-threshold/blink-criterion sign-off (§2/§3 of that record — the
synthetic-recovery threshold and the eight stopping/exclusion rules were
NOT part of it and remain open), the retention-period/storage-location
decision (§5 — 90 days, split location; derived-logs retention itself is
unaddressed, "no change"), and the §19 row 19/23 reclassification (§4,
confirming what CC-001 §7 proposed — CC-001 ITSELF remains unsigned, a
separate instrument, see the bullet below). Full implementation detail:
`simulation/config.py`'s new frozen δ fields, `privacy/retention.py`'s new
`RAW_MEDIA_RETENTION_DAYS`, `privacy/video_storage_config.py` (new,
mirroring `privacy/audio_storage_config.py`), and
`docs/MATRIX_ROW_MAP.md`/the response `.docx`'s updated rows 19/23 and
counts (now 12/6/11/1). Also applied: §1 of that same record caught and
fixed a real nats/macro-F1 unit-conversion error in the response's own
§4.7 leakage-control threshold (was "0.10 macro-F1 points", corrected to
"0.10 nats" — `δ_Gate3` is defined in nats and the document itself forbids
converting it to macro-F1), duplicated in `docs/MATRIX_ROW_MAP.md` row 9
and fixed there too.

- **Second-camera sensor swap** — pending hardware procurement and an FPS feasibility
  test on the actual capture hardware (Decision B); must happen *during* real
  collection or the opportunity is permanently lost.
- **Session length and expected ABANDON/NO_ACTION frequency** (Decision C) — not a
  scope decision so much as two measurements only the client's harness can supply;
  they were the two largest levers in the D6 precision simulation (session length
  moved the CI half-width by ~60%, rare-class frequency by ~66%) and together select
  which cell of the computed grid this study can actually claim.
- **Actual sign-off on every proposed threshold** — `δ_Gate3`, `δ_attention`,
  `δ_audio`, `δ_latent` (all proposed at 0.05 nats, derived and justified in the
  response, never applied by any code here — G1), the blink positive control's pass
  criterion, the synthetic-recovery success threshold, and the eight stopping/
  exclusion rules (`docs/STOPPING_AND_EXCLUSION_RULES.md`) — all are proposals
  returned for sign-off, not yet confirmed.
- **The actual retention period and storage location** (`docs/PRIVACY_AND_RETENTION.md`)
  — the mechanism is built and defaults to dry-run; both values are engineering
  placeholders, not proposed policy.
- **CC-001 — the §18 change control for audio retention** (draft at
  `docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`), reversing
  the sign-off response's own recommendation to formally remove `Δ_audio`.
  Drafted; awaiting vendor review, a cost-and-schedule figure (§8, deliberately
  left blank pending the vendor), and a client-side signature by DOPALAND, the same
  party as the vendor; that limitation is disclosed in CC-001 §9.1. **Its consequence is
  blocking, stated plainly so it is not read as a formality**: even once signed,
  retention alone does not lift §10.9's disqualification — that needs the
  clock-synchronisation measurement between audio and video (CC-001-A, now
  closed as a documented omission — see CC-001 §6(a)), which does not exist.
  `Δ_audio` is not yet computable regardless of what has been built. The
  consequential §19 matrix reclassification (rows 19/23 off `DECISION REQUIRED`)
  was **confirmed in `D0PA1_Client_SignOff_001.md` §4 and applied to
  `docs/MATRIX_ROW_MAP.md` at `00d3a92`**; CC-001 §7 documents it, and signing
  CC-001 adds nothing to it (§9.1).

---

## 3. Known limitations, gathered in one place

- **V_pd's near-zero dispersion.** Neutral std ≈ 0.0001–0.0026 depending on session
  (see `docs/RESPONSE_VERIFICATION.md` §2 for a real, independently-reproduced
  figure: one real session's calibration-phase std ≈ 2.6e-3, MAD-based robust scale
  ≈ 1.6e-4, ratio ≈ 16.75). Any z-score built on this denominator is enormous for even
  tiny movement — this is *why* the null-input control and the `zero_dispersion`
  handling (hard constraint #5) exist. Never treat a large V_pd z as evidence of a
  large real effect without checking dispersion first.
- **CV% is uninformative for a near-zero-mean signal.** `compute_within_unit_cv` was
  confirmed, on a synthetic V_pd-shaped exploration, to swing from hundreds to tens of
  thousands of percent — a real property of dividing by a near-zero grand mean, not a
  bug (`docs/RELIABILITY.md`, "V_pd's known shape").
- **Precision (bootstrap CI half-width) varies by roughly a factor of three across
  synthetic subject realisations (seeds) at a fixed sample size** — re-verified this
  phase: the realistic-configuration cell (45 min, rare-class frequency 0.05) spans
  0.013 to 0.043 (mean 0.021) in macro-F1 units, and this spread did **not** shrink
  when bootstrap replicates were quadrupled — it is driven by which single subject
  realisation is drawn, not by estimation noise (`artefacts/precision_analysis_v2.md`).
  Adopting log loss reduced this spread to roughly a third of its size but did not
  eliminate it. Any single-seed precision number from this simulation is one draw
  from a wide distribution, not a stable estimate.
- **Pitch (head tilt up/down) fails under direction — established, but the MECHANISM
  is not yet separated from the finding.** Corrected this phase (`docs/ROI_FEASIBILITY.md`
  §2.4a): the earlier claim that this was "structurally unrecoverable," resting on a
  "verified" chin-to-chest observation, does not hold up under direct examination —
  no documented verification method for that specific claim exists anywhere in this
  repository, it is numerically inconsistent (~0.1° vs. the later, more carefully
  measured ≤4.4°) with the one figure that IS backed by a documented method
  (`PITCH_DIAGNOSTIC.md`'s frame-by-frame scan), and that later investigation's own
  author explicitly declines to rule out that the subject simply didn't move enough.
  **What IS established, from two independent real-data sources: the failure itself
  reproduces cleanly.** What is NOT yet established: whether it is a property of
  human behaviour (permanent), this specific estimator, or its threshold logic
  (either potentially addressable by different sensing later) — see
  `docs/ROI_FEASIBILITY.md` §2.4a for the three-mechanism breakdown and §6 for the
  capture protocol that would settle it. **A future session must state the failure
  and the mechanism as two separate claims with two separate confidence levels — do
  not restate "structurally unrecoverable" as if it were still this document's
  position.** This is still why the response pre-declares an elevated risk that the
  D8 attention-validity criterion fails (§4.14) — the practical risk assessment is
  unchanged; only the mechanism claimed for it is corrected.
- **The three capture/UI consumers have diverged.** `stage1_step4_vectors.py`'s own
  loop, `stage3_demo_ui.py`, and `analyze_video.py` all call the identical
  `features.x_core` functions (so the validated math cannot diverge) but differ in
  what they do around it: v_jc z-scoring (stage3 only), V_so usage (full vs.
  yaw-only), gaze/blink tracking (stage3 only), and `analyze_video.py`'s video-time
  rather than wall-clock calibration clock. See `docs/D1_DEPENDENCY_MAP.md` §7. None
  of this is a D0PA1 defect — it predates D0PA1 — but a future session must not
  assume the three consumers behave identically outside the shared core.
- **Much of the historical `logs/` data is weakly identified.** Per
  `manifest/data_manifest.csv` (Gate 0 A4): 36 of 50 files carry no recoverable
  `subject_id`, and 14 of 50 have no real acquisition timestamp (falling back to file
  mtime, explicitly marked weak/non-evidentiary). Expected for data predating Gate 0,
  not a defect in the manifest generator — but historical `logs/` files cannot be
  treated as reliably attributable without checking the manifest's `notes` column
  first.
- **The separation guard's check 2 (static call graph) is hardcoded to
  `("x_core", "episodes")` as sources** — it does not consider `context` even
  though check 1's `FORBIDDEN_EDGES` now does (`docs/D1_DEPENDENCY_MAP.md` §10).
  Not urgent while `features/context.py` stays empty (confirmed again this
  phase); becomes a real gap the day `context.py` gains content that
  references an `attention.py`/`audio.py`-defined symbol. Fix is adding
  `"context"` to check 2's `src` tuple — flagged here so a future session
  encounters it before writing the first line of real `context.py` content.
- **Audio (`U_t`) is RETAINED, acquisition built — a scope change against frozen
  `Scope v0.5.1`, not yet through change control.** This reverses the sign-off
  response's own recommendation to formally remove `Δ_audio` (Decision A,
  `docs/MATRIX_ROW_MAP.md` row 23/19). See `docs/AUDIO_ACQUISITION.md` §6 — this
  document records that the change exists and requires the client's own §18
  change-control process; it does not characterise the commercial position and
  does not assert the change has been processed. Audio FEATURE definitions
  remain unbuilt and are the client's to sign off, exactly as before this
  decision — only acquisition (capture, integrity logging, consent, storage
  config, separation guard) is now in scope and built.
- **The audio/video sync figure does not exist. Do not estimate, assume, or
  infer one from acquisition being built.** See the physical-run item above and
  `docs/AUDIO_ACQUISITION.md` §4 — the measurement was explicitly not performed
  this phase (camera use declined), stated plainly rather than simulated. A
  future session must not read "acquisition works" as implying anything about
  achievable alignment.
- **One residual documentation gap, found this phase and not yet fixed**: the
  response document's §4.11 still contains an unreworded "clean object store" bullet
  that its own §4.27 correctly softened elsewhere in the same document — see
  `docs/RESPONSE_VERIFICATION.md` §5. Does not affect the object store's actual state
  (verified clean this session); a wording inconsistency in a document not yet sent.

---

## 4. What a future session must NOT do

- **Do not tune anything against existing data** (G2) — not a formula, not a
  threshold, not a config default, regardless of how a result looks. V_bf's Gate-2
  failure is the standing proof of what tuning against n=1 costs.
- **Do not implement a verdict** (G1) — no `if metric > X: return PASS`, no
  RETAIN/DROP/INCONCLUSIVE branch, anywhere in this codebase's own logic. Every
  control and every analysis module computes and stores numbers; a human applies the
  pre-registered rule afterward. This includes the four thresholds now proposed in
  the sign-off response — proposed and justified is not the same as applied.
- **Do not modify the validated path** (G5) without an explicit ask —
  `features/x_core.py`, `features/episodes.py`, `features/geometry.py`, and
  `stage1_step4_vectors.py`'s capture/processing logic. Re-run
  `tests/test_refactor_snapshot.py` after any change anywhere near these and report
  the SHA256 match/mismatch explicitly.
- **Do not present a harness or control as validated when it has only been run on
  synthetic input.** `controls/leakage.py`, `controls/time_shuffle.py`,
  `controls/blink_positive.py`, `controls/null_input.py`, and `reproduce.py`'s
  confirmatory scope are all in this category — state the synthetic-only status every
  time one of these is discussed, not just the first time. This applies even to rows
  the response itself marks `EVIDENCED` (rows 6, 11, 13, 17, 21) — that status means
  the *machinery* is built and its own deliverable is complete, never that it has
  touched real data, which none of these have.
- **Do not attempt to close any of §2's three outstanding-item groups by writing
  code.** Each needs something external (a harness, a physical run, a client
  decision) that no amount of additional code in this repository can substitute for.
  If a task seems to ask for this, stop and say so, per CLAUDE.md's BLOCKED section.
- **Do not trust a prior session's status claim over a fresh check.** This phase's
  own history is the proof: two rounds of independent verification against live test
  re-runs found real, fixable discrepancies in a document that read as complete on
  its own terms. Re-verify against the repository, every time, the same way
  `docs/RESPONSE_VERIFICATION.md` did.
- **Never audit a `.docx` in this repository using `python-docx`'s
  `Document.paragraphs` alone.** It enumerates body-level paragraphs only and
  silently excludes every paragraph inside a table cell. Substantial parts of
  both preregistration documents live inside `w:tbl` elements. Any search,
  audit or verification of these documents must enumerate every `<w:p>` in
  `word/document.xml` regardless of ancestry — and a verification pass must
  not use the same method as the edit pass, or it inherits the same blind
  spot. A clean result from a method that cannot see half the document is
  not a clean result. This cost two rounds and produced a confident false
  negative about a client-facing document (the retracted pitch claim was
  reported as absent from the repository entirely, when it was present in
  two places, one of them a section heading). A substring search for an
  exact phrase is also insufficient on its own: `D0PA1_Build_Status_Report.docx`
  said "not fixable **with** a single webcam" where
  `D0PA1_Section19_SignOff_Response.docx` said "**within**" — only a
  multi-term search caught it.
