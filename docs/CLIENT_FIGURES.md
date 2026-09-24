# Client Figures Pack

Assembled by the "D0PA1 — FIGURES PACK FOR THE CLIENT DOCUMENTS" task.
**Documentation only — no code was changed to produce this file.** Every
figure below is traced to a specific artefact (a file, a record type, a
test, or a commit) and a production date where one is knowable. **Anything
that could not be traced to a real artefact is marked NOT TRACEABLE and
excluded from the number, not filled in with an estimate** — per this
task's own instruction, dropping a number is preferred to printing one that
cannot be defended.

This document also carries the corrections record (Task 3), the audio
scope-change record (Task 4), and the outstanding-items list (Task 5), so
that everything intended for eventual client use lives in one place.

**Nothing in this document has been sent to the client.** Same status as
every file in `docs/preregistration/` — see that directory's own `README.md`.

---

## 1. Precision and thresholds

| Figure | Value | Meaning | Artefact | Date |
|---|---|---|---|---|
| Worst-cell half-width | **0.0339** macro-F1 points (individual seeds up to 0.0444) | The widest bootstrap CI half-width found across the D6 sweep grid, at the most pessimistic real cell (25 min session, rare-class frequency 0.02) | `artefacts/precision_analysis_v2.md`, line 313 (re-checked this task) | D6 sweep, addendum pass — see file header |
| Realistic-cell spread | 0.013–0.043, mean 0.021 (45 min, rare=0.05) | How much the same CI half-width varies just from which synthetic subject is drawn, at a more typical configuration | Same file, line 318 | Same |
| Decidability ratio (log loss vs. macro-F1) | **~2.1×** average, no exceptions across cells/effect sizes tested; spread in bootstrap half-width reduced to **~1/3** | Adopting multiclass log loss as the primary metric materially improves how reliably a fixed effect size can be told apart from a CI half-width, versus macro-F1 | Same file, "Metric comparison" section, lines 411–418 | Same |
| Information figure thresholds derive from | **0.272 nats** (uniform-predictor baseline 1.609 nats − context-only M0b baseline 1.337 nats) | The context-only model (base rates, time-in-session, previous action) already captures this much structure over chance — the yardstick a core behavioural model must clear a meaningful fraction of to be worth anything | `docs/preregistration/D0PA1_Section19_SignOff_Response.docx` §4.7 (extracted and read directly this task) | Current committed response revision |
| Resulting δ (Gate 3 / attention / audio / latent) | **0.05 nats** (0.20 × 0.272 = 0.054, rounded down) | The proposed minimum-effect threshold for every "does the core model add meaningful information" decision this study makes | Same document | Same |
| δ=0.03 candidate — DROP reachability | At the pessimistic worst cell (25 min, rare=0.02): **DROP is not reachable for any non-negative true effect** (half-width 0.0339 alone exceeds δ=0.03) | A smaller candidate threshold than 0.05 nats was also evaluated and found impractical at the worst realistic cell | `artefacts/precision_analysis_v2.md`, lines 268–270, 366–370 | Same |

---

## 2. Reliability

**No real reliability result exists for this study.** `docs/RELIABILITY.md`
states this as its own first line: the required data (three sessions, three
separate days, fixed protocol, matched repeatable units) has not been
collected, and every number the reliability machinery has ever produced in
this repository is either a synthetic correctness check or a structural
smoke test that reports no magnitude at all.

| Figure | Value | Meaning | Artefact | Status |
|---|---|---|---|---|
| SEM (synthetic correctness check) | Computed 0.1896, target 1/√30 = 0.1826 (3.8% relative error) | Confirms `compute_sem()` recovers a KNOWN synthetic population value — a machinery-correctness check, **not a reliability finding about any real signal** | `tests/test_reliability.py`, check 14 (re-run live this task) | SYNTHETIC ONLY |
| RC (repeatability coefficient) | `1.96 × √2 × SEM` — formula only, no real magnitude ever computed | The formula is implemented and unit-tested; no real RC number exists for any signal in this study | `analysis/reliability.py` | NOT TRACEABLE to any real result — only a formula exists |
| CV% — reported vs. omitted | **Deliberately not to be trusted for V_pd-shaped signals**: a synthetic V_pd-shaped (heavy-tailed, near-zero-mean) exploration found CV% swinging from hundreds to tens of thousands of percent, confirmed to match its own formula exactly (not a bug) — a real property of dividing by a near-zero grand mean | `docs/RELIABILITY.md`, "V_pd's known shape" section | Reason for omission: near-zero-mean signals make percentage-of-mean measures uninformative by construction, not a data quality issue |

**Recommendation for the client pack: state plainly that D3's reliability
machinery is built, unit-tested, and ready, but that no SEM/RC/CV figure
exists yet for any real signal in this study** — the three-session
matched-protocol data this machinery requires has not been collected.

---

## 3. Quiet baseline (subject present, sitting still — NOT the null-input control)

Renamed this engagement's own prior task ("AFTER THE PHYSICAL RUN," Task 3) — this
run required a present human by the module's own design and is genuinely
a different thing from the empty-scene control below.

| Figure | Value | Artefact | Date |
|---|---|---|---|
| Per-signal std / robust scale (mad_scaled) | v_bf: 0.0348 / 0.0270 · v_es: 0.0436 / 0.0407 · v_jc: 0.0173 / 0.0148 · v_pd: 0.00605 / 0.00180 | `logs/null_input_06e8d2be-f603-4c18-a654-98fb375fbd13.jsonl`, `null_input_summary` record | This engagement's "PHYSICAL RUN SESSION" task |
| V_pd's ratio (std ÷ mad_scaled) | **≈3.36×** | Computed directly from the two figures above (0.00605 / 0.00180) | Same session |
| Detection-rate pattern | Per-minute: 0.003 → 0.000 → 0.000 → 0.222 → 0.933 → 0.997 → 0.990 → 0.681 → 0.000 → 0.000 (overall 0.295, 3,612/12,231 frames) | Same log file, per-sample records, re-aggregated this engagement's own "AFTER THE PHYSICAL RUN" task | Same |
| Explanation | Most consistent with: not-yet-settled-into-frame for the first ~2 minutes (no interactive "ready?" gate exists in `controls/null_input.py`), present but seated at a real, roughly constant off-axis angle (avg yaw −18° to −30°) for the ~5-minute middle stretch, and likely leaving frame again before the full 10 minutes for the final ~2 minutes. **Stated as an inference from telemetry, not a witnessed fact** — no video was kept (G4), and the calibrator bug was directly ruled out as a cause by reading the code (detection state is set before any calibration logic runs) | `docs/PROJECT_STATE.md`, "Quiet-sitting baseline" section | "AFTER THE PHYSICAL RUN" task |

**Caveat carried forward from that same section**: this one real run's own
5-minute "good" stretch was itself off-axis, not a canonical centred
baseline — the dispersion figures above describe "dispersion during
whatever this particular stretch actually was," not a clean reference
condition. A second run under monitored, centred conditions would be needed
before citing these numbers as a stable baseline.

**⚠️ The `1.6e-4` / `2.6e-3` / `≈16.75×` V_pd figures also in this
repository are a DIFFERENT measurement from the ≈3.36× above — see Task 2,
claim 1 below for the full reconciliation. Do not conflate the two.**

---

## 4. Empty-scene control (no subject) — **RUN, real result**

Run for the first time this task ("THE LAST GAP BEFORE THE DOCUMENTS GO"),
after the "AFTER THE PHYSICAL RUN" task's own Task 4 was interrupted before
reaching it. Camera on, nobody in frame (the user confirmed the frame clear
of anyone and any face-like content — posters, photos, screens — before
this started), ten real minutes, the normal `controls/null_input.py` path,
no special harness.

| Figure | Value | Artefact |
|---|---|---|
| **False-signal events (the single most important number this control produces)** | **Zero.** Exhaustively checked across all 17,888 real per-sample records: `face_detected` False every time, `pose_detected` False every time, every `composite` value (v_bf/v_es/v_pd) null every time, every `covariate` value null every time, `yaw_deg` null every time, `calibrated` False every time | `logs/null_input_a9820674-83db-442b-9523-8cf795bab4b8.jsonl`, full per-sample scan, this task |
| Missing-row-with-reason vs. value | **All 17,888 sample rows are missing, none carry a value.** At the sample level, missingness is represented by `face_detected`/`pose_detected` = `false` plus null fields (`controls/null_input.py`'s own sample schema does not carry a per-sample `missingness_reason` string field — that richer pattern lives in `features/signal_quality.py` and was not wired into this tool). At the AGGREGATE level, every one of the four dispersion figures and the calibration reference itself DOES carry an explicit, fixed-vocabulary reason | Same log, `null_input_summary` and `null_input_calibration_complete` records |
| Missingness reasons — documented or generic? | **Documented, not generic.** Every signal's dispersion: `zero_dispersion_reason: "insufficient_samples"`. The calibration reference: `missingness_flag: true, missingness_reason: "not_yet_calibrated"` — both drawn from `schema/canonical_log_v1.json`'s fixed enum, and `"not_yet_calibrated"` is the first time this specific reason has ever actually been emitted by this repository (previously declared in the schema, never triggered) | Same log |
| `detect_rate` | **0.0** (0/17,888) | Same log, `null_input_summary` |
| Calibration | **Correctly reports `calibration_completed: false`** — the first real-world confirmation of the "AFTER THE PHYSICAL RUN" task's calibrator fix behaving correctly on genuinely degenerate live data, not just a synthetic unit test | Same log |
| `excursion_count` / false-event rate | `0` for all four signals, but **not a meaningful "clean" result** — `monitoring_minutes: 0.0` and `false_event_rate_per_minute: null` for every signal, because calibration never completed and the excursion detector never had a baseline to compare against. Reported as structurally not-yet-computable, not as a rate of zero | Same log |

**How this differs from the quiet-sitting baseline, so the two are never
conflated again:**

| | Quiet-sitting baseline (§3) | Empty-scene control (this section) |
|---|---|---|
| Subject present? | Yes | No |
| `detect_rate` | 0.295 (3,612/12,231) | **0.0** (0/17,888) |
| Detection pattern | Erratic — 0% at start/end, up to 99.7% mid-session | **Flat zero, the entire 10 minutes** |
| Dispersion figures | Real (std/mad_scaled computed per signal) | **None — `insufficient_samples`, n=0, every signal** |
| Calibration | Degenerate by bad luck of timing (real subject present, but zero real samples fell in the 25s window) | Degenerate because no subject was ever present at all — a structurally different cause |
| What it answers | What the pipeline reports about a real, present, resting person | **The false-signal floor — what the pipeline reports with nothing there at all** |

Raw video: **none was ever written to disk** — `controls/null_input.py`
processes every frame in-memory and discards it immediately, by design, the
same as every prior run of this tool. Confirmed by a repository-wide scan
for `.mp4`/`.avi`/`.mov` files, before and after this run: zero, both times.
There is nothing to delete because nothing raw was ever written.

Repo status updated this task: `docs/MATRIX_ROW_MAP.md` row 16 and the
sign-off response's own item 16 now read `RETURNED · EVIDENCED` and
distinguish the two controls by name.

---

## 5. Pitch and ROI

| Commanded intensity | Real attempt(s) | Achieved pitch (avg / max magnitude) | Detection rate | Required (Quadrants/top-bottom, 8.84°) | Required (3×3, 5.88°) |
|---|---|---|---|---|---|
| Small (slight glance) | 1 attempt, n=1 sample | 5.66° | 0.08% (1/1282) | 1.56× — unfavourable | 1.04× — unfavourable |
| Medium (moderate tilt) | 2 attempts | 2.24° avg (att.1) / 3.00° avg (att.2) | 10.98% / 19.58% | 2.95–3.94× — unfavourable | 1.96–2.62× — unfavourable |
| Maximal (chin-to-chest) | 2 attempts, both independently judged "genuine maximal" | 31.6° avg / 15.2° avg (max 43.1°/23.6°) | 27.45% / 12.55% | 0.28–0.58× — favourable | 0.19–0.39× — favourable |

Artefact: `logs/orientation_trials.jsonl`, schema-1.1 records
(`look_down_small_1`, `look_down_medium_1`/`_2`, `look_down_maximal_1`/`_2`).
Required separations: `docs/ROI_FEASIBILITY.md` §2.1 (unchanged this task).
Full derivation and the detection-rate methodology caveat (the recording
loop's `n_samples` counts processing cycles, not unique camera frames — a
real limitation found this task by reading `orientation_capture.py`
directly): `docs/ROI_FEASIBILITY.md` §2.7.

**Yaw, for context**: clears its own required separations by **≈24×** its
resting noise floor (0.65° std, from `look_at_screen` segments across 3
real sessions) — `docs/ROI_FEASIBILITY.md` §2.1/§2.4.

**Verdict**: vertical ROI attribution is **not deliverable, at any tested
granularity including the coarsest (top/bottom) split** — unchanged from
every prior version of this finding. **What has moved is the reason, twice
now**: originally a magnitude ceiling (retracted), then a "directed
reliability" framing implying large values never show up under command
(now shown incomplete — they do, at maximal effort), and now: **magnitude
is solved only at maximal commanded effort and still fails at ordinary
intensity; availability (8–27% of processing cycles producing any reading,
even at the single best maximal attempt) is the dominant blocker; a
secondary, real consistency problem exists (two equally-judged-maximal
attempts differed ≈2× in magnitude)**. Full three-way breakdown:
`docs/ROI_FEASIBILITY.md` §2.7.4.

---

## 6. Audio

| Figure | Value | Artefact | Date |
|---|---|---|---|
| Sync offset, spread, drift | **NOT MEASURED (superseded below — SEE NEXT ROW for the current, final disposition).** Attempted 5 times ("PHYSICAL RUN SESSION," real hardware, real human clapping) with real clap-correlated audio detected every time, but no video-motion-detection threshold across 5 iterations produced a trustworthy match (either too sensitive — false matches from general motion — or too strict — 0–3 events, unusable). The one run that DID produce matched pairs (40ms mean / 281ms std) is explicitly NOT reported as a result, per this engagement's own instruction not to present a noisy match as real data. A genuine empty-scene-style re-attempt (Task 5 of "AFTER THE PHYSICAL RUN") was never run either | `docs/AUDIO_ACQUISITION.md` §4, §7 | Attempted across 3 sessions total as of this row; never succeeded |
| **Sync offset, spread, drift — FINAL DISPOSITION, documented omission** | Nine attempts total across five sessions (the five above, plus four more using a purpose-built `av_sync_flash.py` instrument, stimulus changed twice more: brief flash → 500ms held flash). **Video-side registration was diagnosed and fixed** — 19/19 emissions register cleanly at 19×–72× threshold in the final attempt; the mechanism was flash duration (a ~3-frame flash against a ~33ms exposure period made detection a near coin-flip). Two code defects were found by review and corrected before the final attempt: a video/audio reference-timestamp edge mismatch (biased every offset by ≈−500ms) and a diagnostic statistic that could report pre-stimulus noise as the stimulus's own response. **Audio-side registration still fails, and the cause is NOT characterised** — an earlier attribution to ambient noise rested on the now-corrected, previously-contaminated statistic and is withdrawn, not replaced with a new cause. **Checked directly from the code this task:** the clap-era audio detector (percentile-based threshold) and the click-era detector (`find_onsets`, causal rolling-median+MAD) are different algorithms — a clap being detected by the old one says nothing about whether the same detector would detect a click, so the narrower "detector works, only the click fails" claim is not supportable and is not made. **Δ_audio cannot be computed; §10.9's condition is not lifted by the acquisition build alone.** Closed under a pre-declared, final stopping condition — no further attempts proposed | `docs/AUDIO_ACQUISITION.md` §4, §7 (history); this session's own record, currently only in `docs/PROJECT_STATE.md`'s "Soak and sync outcomes" section and conversation — `av_sync_flash.py`/`tests/test_av_sync_flash.py` carry the code, uncommitted as of this writing | Nine attempts, five sessions; closed this task |
| Audio thread's effect on pipeline frame rate | T1 (capture-equivalent): 29.998→29.997 fps (Δ −0.001); T2 (processing-equivalent): 8.374→8.374 fps (Δ ≈0) | `docs/AUDIO_ACQUISITION.md` §3, "FPS-impact proof" table | "AUDIO PART A" task |
| **Caveat on what that FPS measurement actually exercised** | This used a **synthetic** two-thread harness reproducing the real architecture's TIMING SHAPE (T1 at a fixed 30fps target, T2 sleeping 120ms/frame — CLAUDE.md's own previously-measured Gate-1 figure, reused exactly) — NOT the real webcam or real MediaPipe FaceLandmarker/PoseLandmarker detection. The AUDIO side was real (real `AudioAcquisitionThread`, real default microphone). **This is evidence about thread contention under a timing-realistic synthetic load, not a measurement of the real webcam pipeline's real FPS with real detection alongside real audio capture** — that specific combination was never measured and should not be inferred from this table | Same document, same section | Same |

---

## 7. Separation and provenance

| Figure | Value | Artefact | Date checked |
|---|---|---|---|
| Number of separation checks | **4** — [1] static import graph, [2] static call graph, [3] runtime monkeypatch (attention/audio poisoned), [4] compatibility-shim isolation | `tests/test_feature_separation.py`, re-run live this task | Today |
| What each covers | [1]/[2]: whether `x_core.py`/`episodes.py` import or call anything defined in `attention.py`/`audio.py`, directly or transitively. [3]: whether real end-to-end computation still works with `attention`/`audio` poisoned to raise on any attribute access. [4]: whether a repo-root module either re-exports across blocks (a "shim") or, as of the audio task, IS direct U_t content itself (`DIRECT_UT_MODULES = {"audio_acquisition"}`) | Same file | Same |
| Forbidden edges (6 total) | `(x_core,attention)`, `(x_core,audio)`, `(episodes,attention)`, `(episodes,audio)`, `(context,attention)`, `(context,audio)` | `tests/test_feature_separation.py` lines 97–113 | Same |
| Which were demonstrated failing before being relied on | **All six**, plus the separate `DIRECT_UT_MODULES` check. The first four: `docs/D1_DEPENDENCY_MAP.md` §6 (a real, pasted failure from a deliberately introduced `ATTENTION_ORIENTED_SCORE_THRESHOLD` import). The two `context` edges: `docs/ROI_FEASIBILITY.md` §4.2 (a temporary `features.attention`/`features.audio` import into `context.py`, each independently made check 1 fail with the exact expected path message, then reverted). `audio_acquisition` as direct U_t content: `docs/AUDIO_ACQUISITION.md` §5.2 (a temporary `import audio_acquisition` into `x_core.py` failed check 4 with the exact expected message, reverted) | Cited documents | Various, see each |
| Golden regression hash | **`f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`** (current, matches the committed golden file — re-run live today) | `tests/test_refactor_snapshot.py` | Today. Supersedes `4f9c0f1786c18e8dbe5e3048b8b6b6e280cf6c434b9c53b119344746fc31bcff` — see the note below |
| Verification pass result | **27 of 27** checkable implementation-status claims in the sign-off response **VERIFIED** against live test re-runs | `docs/RESPONSE_VERIFICATION.md` §1 | 2026-09-04, re-checked in the addendum same date |

**Golden hash supersession — settled, and now recorded durably.** The
golden SHA256 changed once, from `4f9c0f1786c18e8dbe5e3048b8b6b6e280cf6c434b9c53b119344746fc31bcff`
to `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`, at
commit `44c02be` — the "AFTER THE PHYSICAL RUN" task's authorised,
one-time fix to `NeutralCalibrator`'s degenerate-reference bug, which added
two new fields to the calibration reference's output and was diffed to
confirm nothing else on the validated path moved. **This is no longer
carried only in a commit message or a prior session's own report**: it is
now recorded, in the same words, in `docs/GATE0_PROVENANCE.md` (a new,
dated supersession note), `CLAUDE.md`'s own "STANDING VERIFICATION HABITS"
section, and `docs/PROJECT_STATE.md` §1 — a client (or a future session)
finding a changed hash in any one of the three finds the same explanation,
not a bare number.

---

## 8. Matrix

**Status counts, re-derived directly from the response document's own §4
table this task** (not carried forward from any previous statement,
including this document's own earlier draft, superseded by this task's own
Task 2.2 change to row 16):

| Status | Count |
|---|---|
| `RETURNED · EVIDENCED` | **12** (was 11 before this task) |
| `RETURNED · BUILT, NOT YET RUN ON REAL DATA` | **6** (was 7) |
| Plain `RETURNED` | **9** (unchanged) |
| `DECISION REQUIRED` | **3** (unchanged) |
| **Total** | **30** |

**Row 16 (null-input control) moved from `BUILT, NOT YET RUN ON REAL DATA`
to `EVIDENCED` this task** — the empty-scene control (§4 above) was finally
run, with a real, clean, zero-false-signal result. Updated in both the
response document's own §4 table and its §4/§6 body text (both status
mentions for item 16, and the §6 summary sentence/tally), and in
`docs/MATRIX_ROW_MAP.md` row 16 and its own top-of-file count line — all
four locations checked to agree after the edit, not assumed to.

Artefact: `docs/MATRIX_ROW_MAP.md` line 21 and its row-16 entry;
`docs/preregistration/D0PA1_Section19_SignOff_Response.docx` §4/§6, edited
this task; both re-extracted and re-counted directly from the document's
raw text after editing, not assumed correct from the edit script's own
intent.

---

## 9. Task 2 — claims checked against artefacts

| # | Claim | Result | Artefact |
|---|---|---|---|
| 1 | V_pd's robust scale ≈16× smaller than its SD | **CONFIRMED — both figures are real, of different data.** ≈16.75× is from `session_eb41ba71…jsonl`'s CALIBRATION-PHASE-only v_pd samples (n=653, an expressive Gate-2-era session). ≈3.36× is from the quiet-sitting baseline's WHOLE-SESSION v_pd (10 min, a person trying to sit still). Both use the identical `1.4826×MAD` formula. **They are not interchangeable** — cite whichever matches the context (calibration-phase dispersion vs. whole-session quiet-sitting dispersion) and never the other's number | `docs/RESPONSE_VERIFICATION.md` §2; `docs/PROJECT_STATE.md`'s quiet-baseline table |
| 2 | δ=0.03 has no reachable DROP outcome | **CONFIRMED, at the pessimistic worst cell specifically** (25 min, rare=0.02, half-width 0.0339 > δ=0.03). **Not universally true** — a less pessimistic table in the same artefact shows δ=0.03 still has a DROP range [0, 0.0151] at a different (non-worst-case) configuration. State the qualifier, not a blanket claim | `artefacts/precision_analysis_v2.md`, lines 268–270 (worst-cell) vs. lines 123–128 (a different cell) |
| 3 | Metric change: ≈2.1× better decidability, spread to ≈1/3 | **CONFIRMED exactly** — "~2.1×... no exceptions" and "~3×" smaller spread, verbatim | `artefacts/precision_analysis_v2.md` lines 411–418 |
| 4 | δ = 0.20 × 0.272 ≈ 0.054, rounds to 0.05 | **CONFIRMED verbatim**, extracted directly from the sign-off response document's own text | `docs/preregistration/D0PA1_Section19_SignOff_Response.docx` |
| 5 | Longest soak on record ≈41 minutes | **CONFIRMED exactly** (2486.9s = 41.45 min) and confirmed to genuinely be the longest — the only other two soak_summary records on record are 90.7s and 80.5s, both from this engagement's own later, unsuccessful extended-soak attempts | `logs/soak_log.jsonl`, all `soak_summary` records, re-scanned live this task |
| 6 | 27 claims verified, 27 to the stated figures | **WRONG as stated, in its second half.** "27 of 27 checkable claims VERIFIED" is the document's own accurate headline (confirmed). But NOT all 27 matched their stated figures on first check — one was found UNDERSTATED (3 checks claimed, 4 actual) and needed a later revision to correct; the object-store "returns clean" claim was found NOT currently true (a dangling tree object existed) and needed a repository action before it held. "Verified" and "verified exactly as first stated, with nothing needing correction" are different claims — the first is true, the second is not | `docs/RESPONSE_VERIFICATION.md` §1 (row 4.1: "UNDERSTATED"), §3.2 (fsck), §5 (addendum) |
| 7 | 11 evidenced, 7 built-not-run, 9 definitions, 3 decisions | **CONFIRMED exactly at the time it was checked** — 11+7+9+3=30. **Now superseded by this task's own Task 2.2**: row 16 moved to EVIDENCED once the empty-scene control was run, making the current, correct count **12/6/9/3** — see §8 above | `docs/MATRIX_ROW_MAP.md` line 21 (as it read at check time); §8 above for the current count |
| 8 | ROI aggregation passes 9/9 against a synthetic supplier | **CONFIRMED** — re-ran live this task, 9/9 PASS | `tests/test_roi_aggregation.py`, re-run today |
| 9 | 1 of 11 sessions affected by the calibrator bug, already caveated, never sent | **CONFIRMED**, with an additional check this task didn't skip: searched both client-facing `.docx` files directly for the affected session, the bug, and the excursion figure — every hit found ("null-input," "excursion," "calibrator") is a GENERIC, pre-existing reference to the control's own design/row name, not to this session's actual run or its bug. Nothing built on the affected figure has ever appeared in a document intended for the client | `logs/*.jsonl` scan; `docs/preregistration/*.docx` direct text extraction, this task |
| 10 | Only one camera exists; simultaneous two-camera capture not possible | **CONFIRMED, re-verified live this task** (indices 1–3 all fail to open; only index 0 opens) | Live `cv2.VideoCapture` probe, this task |
| 11 | Vertical attribution not deliverable, now resting on availability not magnitude | **CONFIRMED, directionally, with an incompleteness the claim itself doesn't mention.** Availability is the dominant blocker, correctly. But magnitude is only solved at MAXIMAL commanded effort — it is still unfavourable at ordinary/moderate intensity (§5 above), and a secondary, real consistency problem also exists (≈2× magnitude difference between two equally-judged-maximal attempts). "Resting on availability rather than magnitude" is the right headline; it omits two real qualifiers this document's own §2.7.4 states explicitly | `docs/ROI_FEASIBILITY.md` §2.7 |

---

## 10. Task 3 — the corrections record, complete

**The prompt's own list names ten items while stating "I count eight" —
this is a direct arithmetic mismatch in the prompt's own text, reported
here rather than quietly resolved by picking a number.** Counting the
prompt's own bullets (separated by "·"): multi-hour stability claim /
version control implied to predate the work / separation test as three
checks / acceptance check as in progress / evidenced-row count of five /
object store "returns clean" / vertical ceiling of roughly twice / pitch
claim of ≈0.1° as structural / blocked-microphone level as a real room
measurement / quiet baseline as null-input control — that is **ten** items,
not eight. Every one of the ten is a real, independently traceable
correction (verified below). **No eleventh correction was found** beyond
what these ten already cover — the "directed reliability" framing that
later moved to "availability" (this task's own §5 above) is part of the
SAME evolving pitch/ROI finding chain as items 7 and 8, not a distinct
additional retraction.

| # | What was claimed | What is true | How found | Reached the client? |
|---|---|---|---|---|
| 1 | Stability was "multi-hour" | Longest logged soak is ~41 minutes | Self-disclosed inside the vendor's own Build Status Report, present in this exact self-corrected form in the FIRST version ever committed to this repository (`71b95eb`) — **the original, uncorrected claim predates this repository's own version-controlled history entirely; it cannot be independently inspected here, only referenced by the correction itself** | Never — no version of either vendor document has ever been sent (`docs/preregistration/README.md`, "What has been SENT to the client") |
| 2 | Version control was implied to predate the work / commit dates could be read as when code was written | "This repository was not under version control until this month... no commit has been backdated, no history has been reconstructed" | Same nature as #1 — self-disclosed from the first committed version, original claim not independently inspectable in this repo's history | Never |
| 3 | The separation test was "three checks" | It runs **four** | `docs/RESPONSE_VERIFICATION.md` §1 (row 4.1), corrected in the response's later revision, re-verified in §5's addendum | Never |
| 4 | The harness acceptance check was described as "in progress" (§2) while §4.2 separately said it "has not started" — an internal contradiction | It has not started, stated consistently now in both places | `docs/RESPONSE_VERIFICATION.md` §3.3, resolved in §5's addendum | Never |
| 5 | Five rows carry implementing code / inspectable artefacts (§6 summary) | Eleven do, by the document's own §4 table | `docs/RESPONSE_VERIFICATION.md` §3.1, corrected to eleven in §5's addendum, independently re-derived to match | Never |
| 6 | "The object store... returns clean" (unqualified) | Pruned after hook verification; a dangling object from ordinary commit activity is not evidence of anything | `docs/RESPONSE_VERIFICATION.md` §3.2, reworded in §4.27 of the corrected response — **but §4.11's own bullet list still reads the old unqualified phrase, a residual gap not fully corrected** (§5's addendum) | Never |
| 7 | The vertical (pitch) magnitude ceiling was ≈2× (required exceeds achievable) | Retracted within `docs/ROI_FEASIBILITY.md` itself — later real measurement found pitch reaching 31.2° incidentally, far above every requirement | `docs/ROI_FEASIBILITY.md`, "RETRACTION" section — corrected in the SAME repository state it was introduced, never left it | Never |
| 8 | Pitch "stayed ~0.1°" on a "verified" maximal chin-to-chest look-down — described as structural, unfixable | Real graded maximal attempts (this engagement, "PHYSICAL RUN SESSION" task) register pitch up to −43.1°; the "verified" claim had no documented verification method anywhere, was numerically inconsistent (~0.1° vs. a separately-measured ≤4.4°), and the investigation that produced the ≤4.4° figure explicitly declined to rule out the subject simply not moving enough. **See the detailed answer below** | Multi-session: first flagged as unverifiable (`docs/ROI_FEASIBILITY.md` §2.4a, "PITCH: SEPARATE THE FINDING FROM ITS EXPLANATION" task), then directly refuted by real data — **and its full reach was itself only found in a later pass, see below** | At the time this row was first written: never (`CLAUDE.md` and `docs/PROJECT_STATE.md` both carried it, neither client-facing). **That was incomplete** — it also lived in `D0PA1_Section19_SignOff_Response.docx` §4.14 and `D0PA1_Build_Status_Report.docx` §5.4, both client-facing and both unsent. Still never sent; the finding was that the correction's own reach was underestimated, not that the claim reached the client. |
| 9 | A logged audio level (`peak_abs ≈3.05e-5`) was "genuine captured evidence... real (very quiet) room level" | That exact value is the 16-bit PCM quantization floor an OS-blocked/silent stream returns — very likely the same artefact, not real ambient sound | Found by testing microphone content access directly the following session (two mics, two host APIs, all returning exact zero or the same floor) | `docs/AUDIO_ACQUISITION.md` §7.3 | Never |
| 10 | The quiet-sitting-subject-present run was called "the null-input control" | It required a present human by the module's own design; a true null/empty-scene input is a different, still-outstanding question (§4 above) | This engagement's own "AFTER THE PHYSICAL RUN" task, Task 3.1 | Never |
| 11 | `D0PA1_Client_SignOff_001.md`'s capacity note: "Proposer and signer are different parties, which is the structure the governing documents assume." | The record was signed `DOPALAND, by Debanjan Das`, and DOPALAND is the same solo operation as the vendor, so proposer and signer were the same party. **The document itself is not edited.** The correction is recorded here, and CC-001 §9.1 states the limitation explicitly rather than repeating the claim | Found 2026-09-25 while drafting CC-001 §9.1: a proposed §9.1 cited `SignOff_001` as precedent for disclosed same-party signing, and checking it against the source found that the source states the opposite | Not established. `SignOff_001` is itself the client-side record, and `docs/preregistration/README.md`'s "What has been SENT to the client" does not list it either way |
| 12 | `D0PA1_Client_SignOff_001.md` dates itself as 2026-09-18 in its header and status line | Its signature row is dated **2026-09-19**. The record carries two dates, and which is correct is for the signatory to state; not resolved when this entry was first written. **Resolved 2026-09-25: the correct date is 2026-09-19**, stated by the signatory in an erratum *appended* to the signed record ("Erratum — added 2026-09-25, after signature"), not by amending its header, status line or signature row, which still read as signed | Found 2026-09-25, in the same check as #11 | Not established, as #11 |

**Entries 11 and 12 were added 2026-09-25, after the section above was written.** The "ten" in
this section's opening paragraph and in "The count above stays at ten" below refer to the
original prompt's list; the record now holds twelve entries. Neither new entry is a claim that
was made and then withdrawn in an unsent draft, as #1–#10 are: both are defects in a signed
record, recorded here without editing that record.

**On item 8, the one the prompt asks about specifically — how long it stood
and what was built on it:**

- **How long:** the claim appears, worded almost identically, in three
  places this session found (`CLAUDE.md`'s "Attention / screen-orientation"
  section, `stage1_step4_vectors.py`'s own docstring, and
  `docs/PROJECT_STATE.md`) — a search for "chin-to-chest" across the
  repository's history finds no dated point at which it entered any of
  them with a cited verification method. It survived at least two
  dedicated investigations before being tested directly: `PITCH_DIAGNOSTIC.md`
  (a later, more careful frame-by-frame scan that found ≤4.4°, not ~0.1°,
  and whose own author declined to rule out the subject simply not moving
  enough) and the "PITCH: SEPARATE THE FINDING FROM ITS EXPLANATION" task
  (which found no documented verification method anywhere and formally
  separated the finding from its claimed mechanism, without yet refuting
  the magnitude itself). It was only directly refuted — not merely
  cast into doubt — by the "PHYSICAL RUN SESSION" task's real,
  graded-intensity, independently-judged capture.
- **What downstream reasoning was built on it:** the ROI feasibility
  verdict's original "magnitude ceiling" framing (item 7 above, ≤4.4°
  vs. a required 8.84°, a ≈2.0× shortfall) was built directly on the same
  family of evidence this claim belonged to; the D8 attention-validity
  risk pre-declaration in the sign-off response (§4.14, an elevated-risk
  flag for the client's own attention-validity criterion) cites the pitch
  finding as its reason; and CLAUDE.md's own "Attention /
  screen-orientation" section used it to justify treating pitch as
  permanently unfixable rather than an open mechanism question. **The
  sign-off response's own §4.14 pre-declaration and CLAUDE.md's
  screen-orientation section now both carry the corrected reasoning** (two
  later tasks in this same engagement). None of this downstream reasoning
  has been retracted wholesale — the PRACTICAL conclusion (vertical ROI
  attribution is not deliverable) is unchanged through every correction;
  what moved, twice, is the reason claimed for it. **The D8 elevated-risk
  pre-declaration itself stands, on the revised premise**: not that pitch
  cannot register at all, but that face-detection rate collapses during
  look-down (0.08%–27.5% across the graded attempts), which is what makes
  `oriented_rate` read close to 1.0 — a missingness artefact, not evidence
  of orientation.
- **The correction's own reach was found late, in a later pass, and that
  is itself part of this record.** The claim did not live only in
  `CLAUDE.md`, `stage1_step4_vectors.py`, and `docs/PROJECT_STATE.md` — it
  also lived in `D0PA1_Section19_SignOff_Response.docx` §4.14 and
  `D0PA1_Build_Status_Report.docx` §5.4, both client-facing, both unsent.
  In the Build Status Report the claim was not merely present in body
  text — it was the section's own **heading** ("Attention pitch detection
  is structurally unreliable"). Both instances survived a first, dedicated
  correction pass because they sit **inside `w:tbl` elements**, and the
  audit method used (`python-docx`'s `Document.paragraphs`) enumerates
  body-level paragraphs only and silently excludes every paragraph inside
  a table cell — the first retry reported the text as absent from the
  repository entirely, a false negative produced by the audit tool, not
  evidence the text was actually gone. A second pass, enumerating every
  `<w:p>` in `word/document.xml` directly regardless of ancestry, found
  both. **Both documents are now corrected — no instance of the retracted
  figure or mechanism survives in either, outside the sentences that
  explicitly retract them** (verified by a further multi-term sweep, since
  a single exact-phrase search is also insufficient: the Build Status
  Report said "not fixable **with** a single webcam" where the sign-off
  response said "**within**"). This is the same claim, entry #8, with its
  true reach now documented — not an eleventh correction.

**A noted internal finding, not counted as an eleventh correction — the
classification is open, and that is a human call, not this session's:**
during the nine-attempt A/V sync work, an omission-text draft attributing
the audio-side registration failure to "elevated ambient noise" was
prepared for CC-001, on the basis of a diagnostic statistic
(`compute_diagnostic_window`'s `max_value_in_window`) that a later code
review found could report pre-stimulus noise as though it were the
stimulus's own response. The attribution was withdrawn before it reached
CC-001 or any client-facing document — **it never left this repository,
the same category the ten corrections above already occupy.** Whether
withdrawing an internal draft before it reached a client document counts
as an eleventh correction (a wrong claim, caught and fixed) or as a
different category (an internal working note that did its job — surfacing
the finding via a check made before, not after, sending anything) is left
open here for the methodology owner to decide. **The count above stays at
ten** pending that decision. See `docs/PROJECT_STATE.md`'s "Soak and sync
outcomes" section and §6 above for the full record of what was found and
corrected.

---

## 11. Task 4 — the audio scope-change record

**What was decided.** The client's own keep-or-formally-remove decision on
`Δ_audio` was made in the opposite direction from the sign-off response's
own recommendation (Decision A, which recommends formal removal): **audio
is RETAINED**, and acquisition was authorised and built.

**What has been built since that decision** (the "AUDIO PART A" task):

- An audio acquisition instrument (`audio_acquisition.py`) — its own
  thread, structurally decoupled from video capture/processing the same
  way those two threads are decoupled from each other; per-chunk
  integrity logging (level, timing, dropout/overrun counts, two
  independently-sourced timestamps) to its own file
  (`logs/audio_chunk_integrity.jsonl`); no content analysis anywhere in
  the module (amplitude only — peak, RMS, clipping).
- A separate, independent audio consent question — declining it means the
  acquisition module's device-opening code is architecturally
  unreachable, machine-checked (`tests/test_consent_audio_gate.py`).
- Raw audio's storage location as env-var configuration, never a literal
  path in any committed file (`privacy/audio_storage_config.py`).
- The privacy/media guard extended to eight additional audio container
  formats, by extension AND by magic-byte content sniffing, proven
  fail-then-pass on real payloads.
- The D1 feature-separation guard extended to cover `audio_acquisition.py`
  itself as direct U_t content (not merely a module that re-exports
  `features.audio`) — a real gap found by audit, fixed, proven
  fail-then-pass.

**What remains unbuilt, deliberately, unchanged by "retained":** no audio
FEATURE of any kind — no prosody, no arousal-from-voice, no
emotion-from-speech, no valence, no stress, no spectral features, no
transcription, no speech detection. `features/audio.py` (the U_t feature
stub) is still intentionally empty. **Audio feature definitions remain the
client's to define, exactly as strictly as every other new-signal
definition in this project** — this engagement has not proposed, and will
not proactively invent, any.

**Change-control status.** Retaining audio is a substantive change against
`D0PA1 POC Scope & Acceptance v0.5.1` (frozen) and against the sign-off
response's own proposed direction. Per the client's own §18/§12, this
requires documented change control. **That change-control process has not
yet run.** `docs/AUDIO_ACQUISITION.md` §6, `CLAUDE.md`'s own `U_t` section,
and `docs/PROJECT_STATE.md` are the engineering record that the decision
exists and what it produced — they are not the change-control record
itself, which remains a separate, not-yet-done step.

---

## 12. Task 5 — what is actually outstanding

One list, every open item in exactly one bucket. An item needing two kinds
of thing is split into two rows, per this task's own instruction.

### Needs the client's harness

- D2 prediction target (action classes, horizon, tie/rapid-succession handling)
- Real `A_t`/ROI attention features beyond the built-and-tested aggregation
  math (dwell/switching/persistence/coverage — `ROIWindowAccumulator` is
  done; only the supplied event stream is missing)
- The leakage and time-shuffle controls' run on real trial data
- D3/D7's reliability and baseline machinery run on real sessions (also
  needs subject time — see its own row below, this is the harness half of
  a split item)
- `CanonicalLogWriter` wired into a real capture loop
- The D4 confirmatory reproduction (archived real video + real logged
  feature stream)
- The harness acceptance check itself (not started, per the response's own
  §4.2 correction)

### Needs a client decision

- Second-camera sensor swap — pending hardware procurement AND an FPS
  feasibility test once hardware exists (two needs, kept as one bucket
  entry since the decision — procure hardware — gates both)
- Session length and expected ABANDON/NO_ACTION frequency (Decision C) —
  the two largest levers in the D6 precision simulation
- The synthetic-recovery success threshold, and the eight stopping/
  exclusion rules — **narrowed this task**: δ_Gate3/δ_attention/δ_audio/
  δ_latent (0.05 nats) and the blink-positive pass criterion were the other
  two items in this bucket's original "every proposed threshold" wording;
  both are now closed, see "Done since this list was first written" below
- The unified raw-media-root proposal (`docs/PRIVACY_AND_RETENTION.md`'s
  proposed, not decided, pattern) — **explicitly left open by the client's
  own record**, `D0PA1_Client_SignOff_001.md` §6, even though the
  per-modality retention/location decision it depends on is now made
- The audio scope change's own §18 change-control sign-off (CC-001 itself,
  `docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md` §9)
  — a **different instrument** from `D0PA1_Client_SignOff_001.md`; CC-001's
  own signature block is still blank. `D0PA1_Client_SignOff_001.md` §4
  confirms the §19 row 19/23 reclassification CC-001 §7 proposed, which is
  not the same act as signing CC-001 itself

**Closed this task, `D0PA1_Client_SignOff_001.md` (signed 2026-09-19) —
removed from the bucket above rather than struck through, since they were
never a machine-time item:**

- ~~δ_Gate3/δ_attention/δ_audio/δ_latent at 0.05 nats~~ — **ACCEPTED (§2)**,
  now frozen fields in `simulation/config.py`'s `PreRegisteredConfig`. Also
  fixed as part of the same record: the response's own §4.7 leakage-control
  section stated its threshold as "0.10 macro-F1 points" when δ_Gate3 is
  defined in nats and the document itself forbids that conversion — now
  corrected, in the response `.docx` and `docs/MATRIX_ROW_MAP.md` row 9, to
  0.10 nats.
- ~~The blink-positive pass criterion~~ — **ACCEPTED (§3)**, values
  unchanged from what `controls/blink_positive.py` already stored (F1≥0.80,
  count within ±20% on ≥8/10 clips, ±150ms matching tolerance).
- ~~The actual retention period and storage location for raw media~~ —
  **DECIDED (§5)**: 90 days (`RAW_MEDIA_RETENTION_DAYS` in
  `privacy/retention.py`), and a defined folder outside `C:\Dopaland-POC`
  per modality (`privacy/video_storage_config.py`, new this task, mirroring
  `privacy/audio_storage_config.py`'s existing pattern). Derived-feature
  logs' own retention/location is unaddressed by this decision — "no
  change" per the record's own §5.2 — and remains a placeholder.
- §19 rows 19 and 23's reclassification — **CONFIRMED (§4)**, applied in
  `docs/MATRIX_ROW_MAP.md` and the response `.docx`; counts now 12/6/11/1.

### Needs hardware that does not exist

- A second physical camera (confirmed again this task — indices 1–3 all
  fail to open; only one camera exists on this machine)

### Needs subject time

- D3/D7's three-session, fixed-protocol, matched-unit reliability data
  (the subject-time half of the split item above)
- 10 real one-minute blink clips + manual frame-by-frame counts
- Cross-person confirmation of the pitch/ROI finding (the same ≥8-person
  Gate-2-style protocol already specified in `docs/ROI_FEASIBILITY.md` §6)

### Needs nothing but machine time

**Empty as of this task — both items below were closed this session.**
Neither disappeared; see where each actually landed, immediately below.

**Done since this list was first written ("THE LAST GAP BEFORE THE
DOCUMENTS GO" task) — kept here, struck through in spirit rather than
silently deleted, so a reader comparing this list against an earlier
version can see what moved and why:**

- ~~The empty-scene control itself~~ — **RUN.** See §4 above: zero
  false-signal events across 17,888 real frames, ten real minutes.
- ~~An extended stability soak run from an interactive terminal~~ — **RUN,
  three times, and CLOSED under its own frozen rule's stopping condition.**
  Not a PASS — 73.2 min INCONCLUSIVE, 140.2 min VOID (scene-validity
  precondition failed both times) — but no longer outstanding as an
  action: the launch-context blocker that produced this bucket's original
  entry is resolved (both later runs reached 73 and 140 minutes with clean
  exits), and the rule's own stopping condition means no fourth run is
  planned without a new reason. Full detail in
  `docs/PROJECT_STATE.md`'s "Soak and sync outcomes" section. The standing
  claim remains the POC-era 41-minute soak — this closure does not upgrade
  it.

**Dispositioned this task, NOT resolved, deliberately kept as its own
outstanding item rather than merged into "Done" above — this is the
distinction this list's own instruction says matters:**

- **A real audio/video sync measurement re-attempt with a different
  visual event** — attempted, four more times (nine total across five
  sessions), with two real code defects found and fixed along the way and
  video-side registration fully resolved as a genuine result. Audio-side
  registration still fails and **the cause is not characterised** — an
  earlier ambient-noise attribution was withdrawn (see §10's noted
  internal finding) and not replaced with a new one. This item no longer
  "needs machine time" because no further attempts are planned — it is
  closed as a line of work, under a pre-declared stopping condition, and
  recorded as a **documented omission under the client's §21** (infeasibility
  stated rather than implemented), not as a solved measurement. Δ_audio
  remains not computable. Full detail in `docs/PROJECT_STATE.md`'s "Soak
  and sync outcomes" section and §6/§10 above.
- ~~Rewording §4.11's residual "clean object store" bullet~~ — **FIXED**,
  to the same durable wording §4.27 already used.
- ~~Updating `docs/MATRIX_ROW_MAP.md` row 16 and the response's own item
  16~~ — **DONE.** Both now read `EVIDENCED` and name the two controls
  separately (§4 and §8 above).
