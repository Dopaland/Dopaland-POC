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

**HEAD at time of writing:** `720af64` — "docs: record check-2 context gap and
pitch-mechanism correction in state docs" (the "PITCH: SEPARATE THE FINDING
FROM ITS EXPLANATION" task: retracted the pitch magnitude-ceiling claim
explicitly, separated the established directed-look-down FAILURE from its
not-yet-separated MECHANISM (M1 behavioural / M2 estimator / M3 threshold
artifact — disagreed with the prompt's own suggested "leans toward M2"
reading), and specified — not built — the capture protocol that would settle
which mechanism is responsible. See `docs/ROI_FEASIBILITY.md` §2.4a and §6.
Prior: `7473742` — "docs: symmetric resolution table, separation-guard fix,
ROI status split" (closed the yaw/pitch resolution-comparison asymmetry,
closed the `context`→`attention`/`audio` separation-guard gap, and built the
ROI dwell/switching/persistence/coverage aggregation layer against a
synthetic supplier).)

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

### Needs a physical run (a live camera and/or a human operator this environment cannot provide)

- **The null-input control's own 10-minute camera session** — its pure-computation
  pieces (dispersion, excursion detection, config hashing) are unit-tested; the
  camera loop itself has never executed, synthetic or real.
- **10 real one-minute blink clips + manual frame-by-frame counts** — the positive
  blink control's harness is built and validated against synthetic aperture streams
  through the real detector; zero real clips exist.
- **An extended stability soak** — the only soak on record is the POC-era 41-minute
  run (`logs/soak_log.jsonl`); a longer or repeated soak is scheduled, not existing.
- **The directed-capture protocol that would separate M1/M2/M3 behind the pitch
  finding** — specified, not built, in `docs/ROI_FEASIBILITY.md` §6. Resolves
  whether pitch's directed-look-down failure (§2.2/§2.4a of that document) is a
  property of subject behaviour (permanent), this specific estimator, or its
  threshold logic (either potentially addressable by different sensing later) —
  needs raw per-frame yaw/pitch logging, an independent ground-truth judgement of
  actual head movement from the frames themselves (not from the estimator being
  tested), and repeated directed attempts at graded intensity. ~15–20 min per
  subject; any video used for the independent judgement stays outside this
  repository per G4, only the derived judgement labels are logged.
- **The audio/video sync measurement (Δ_audio's actual point)** — a repeated
  hand-clap timestamp-alignment measurement, built and ready
  (`audio_acquisition.py`'s raw-capture path, `docs/AUDIO_ACQUISITION.md` §4) but
  **not run**: it needs a single physical event visible to BOTH the camera and
  microphone simultaneously, and this phase's real-hardware session explicitly
  declined camera use (audio-only was exercised instead — see
  `docs/AUDIO_ACQUISITION.md` §3's FPS-impact proof, which used a synthetic video
  timing harness for exactly this reason). Resolves whether audio events can be
  placed on the video timeline to better than the resolution the study needs — if
  the achievable alignment is worse than needed, `Δ_audio` measures alignment
  error, not information, regardless of what else is built. No offset, spread, or
  drift figure exists yet; none should be assumed or estimated.

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
