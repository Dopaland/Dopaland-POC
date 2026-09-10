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

**HEAD at time of writing:** `0fc829e` — "docs: correct stale physical-run
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
- The golden regression test (`tests/test_refactor_snapshot.py`) has matched its
  committed SHA256 (`4f9c0f1786c18e8dbe5e3048b8b6b6e280cf6c434b9c53b119344746fc31bcff`)
  through every commit in this phase — the validated path (G5) has not moved.

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

### Needs a physical run — THREE items actually run this phase ("PHYSICAL RUN SESSION")

**Task 0 gate result, stated first because it governs everything below:**
the microphone-content-access block found last phase (exact 16-bit
quantization floor / exact digital zero regardless of real noise) is
**gone this session** — a 2-second gate recording showed real, varying
signal (min=-0.084, max=0.057, std=0.00247, 1362 distinct values). Not
explained; not investigated further, per the task's own scope — recorded
as a fact: it was blocked one phase, it is not blocked this phase, on the
same machine.

**1. Null-input control — RUN, 10 real minutes, subject present** (Task
2). The user's own reading of "null input" (empty chair, no person) was
directly challenged and not adopted — `controls/null_input.py`'s own
docstring and instructions specify a present, resting human, because
`compute_v_pd` needs real pose landmarks to produce any dispersion figure
at all; an empty chair would yield `insufficient_samples`, not a
measurement. Real result, `logs/null_input_06e8d2be-f603-4c18-a654-98fb375fbd13.jsonl`
(12,234 records, kept — contains no image, only derived numbers):

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

**A real bug in the G5-protected validated path was found and is NOT
fixed here** (G5 — this document records it; a future task with explicit
permission would fix it): `features/x_core.py`'s `NeutralCalibrator`
completes calibration purely on WALL-CLOCK elapsed time
(`should_complete()`), independent of whether any real (non-`None`)
samples were collected. This session's 25-second calibration window fell
entirely inside the near-zero-detection opening minutes — **zero real
samples for every signal** — and `complete()` silently produced a
reference of `{mean: null, std: null, n: 0}` for all three composite
signals and all three covariates. `classify_calibration_quality` did
**not** flag this (`possibly_not_neutral: false, reasons: []`) — a
completed-but-empty calibration is currently invisible to the one check
meant to catch calibration problems. Consequence, confirmed directly: the
excursion detector's `z` stayed `None` for the entire session (a `None`
reference makes every subsequent z-score computation skip), so
**`excursion_count = 0` for all four signals is NOT evidence of a clean
null result — it is an artefact of the detector never running at all**
this session. The dispersion table above is unaffected (`compute_dispersion`
reads `raw_values`, collected independently of calibration, whenever
`face_detected` was true) — only the excursion/false-event-rate half of
Task 2's ask is compromised, and it is reported as compromised, not
smoothed into a false "0/min, clean" claim.

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
