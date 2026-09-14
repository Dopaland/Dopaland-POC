# D0PA1 — Pending Task Closure Pack

**Produced:** 2026-09-13 · **Against repo:** `C:\Dopaland-POC` (read directly, not from the status report)
**Scope:** the four items that were closable without the client's harness, a client decision,
absent hardware, or subject time.

**What this document is:** vendor-side scope and wording. It contains **no code changes** —
Parts A and D hand exact, self-contained text to the Claude Code agent. It introduces **no
threshold, verdict or pass/fail into code** (G1), and **tunes nothing against existing data** (G2).

---

# Part A — Retire the refuted pitch claim (Correction #8)

## A.1 Where the retracted claim is still live — verified by direct file read

| # | Location | State | Severity |
|---|---|---|---|
| 1 | `CLAUDE.md` lines 668–700 | **Already corrected.** Carries the retraction, the −43.1° data, and the "root cause is NOT settled as purely structural" reopening. No action. | — |
| 2 | `docs/PROJECT_STATE.md` lines 98, 469–470, 653–667 | **Already corrected.** Explicitly names the "~0.1 deg, structural, not fixable" claim as the thing being retracted. No action. | — |
| 3 | `stage1_step4_vectors.py` module docstring, lines **102–118** | **STALE — asserts the retracted claim as current fact**, including "pitch stayed ~0.1deg", "Root cause is STRUCTURAL", "fixable only by a different sensing approach". | **High** — this is the canonical design-rationale docstring the whole attention block points at. |
| 4 | `features/attention.py` `compute_v_so` docstring, lines **144–149** | **STALE** — "UNRELIABLE by structural limit of single-camera landmark head-pose … not a bug". | **High** — nearest comment to the live computation. |
| 5 | `D0PA1_Section19_SignOff_Response.docx` §4.14 (Item 14 · D8) | **STALE, AND CLIENT-FACING.** Two paragraphs assert "measured pitch stayed at approximately 0.1° and the oriented-rate stayed at 1.0" and "It is not fixable within a single webcam at this resolution." | **Critical** — this is the unsent document. It must not leave the repo carrying a retracted claim. |

`PITCH_DIAGNOSTIC.md` contains a `0.1°` only as the low end of a measured range on `test_clip.mp4`
— a different, legitimate number. **Do not edit it.**

## A.2 The correct position, stated once

Three things are now true at the same time, and the honest framing has to hold all three:

1. **The magnitude claim is false.** "~0.1°" had no documented verification method anywhere in
   this repository, and real graded-intensity capture registered pitch as large as **−43.1°**
   (two maximal attempts averaging −31.6° and −15.2°, both judged "genuine maximal" in real time
   before any number was shown), with magnitude scaling roughly with commanded intensity
   (small ≈6°, medium ≈2–3°, maximal ≈15–32°).
2. **The practical conclusion is unchanged.** Pitch-based ROI attribution is still not viable.
3. **The reason changed, and the new reason is better evidenced.** The problem is not that pitch
   fails to register — it is that **face detection rate collapses during look-down (0.08%–27.5%)**,
   even on attempts where pitch registered at large magnitude. `oriented_rate` still reads near 1.0
   because most window-samples are **missing**, not because they read as oriented. That is a
   missingness artefact.

Two things remain unexplained and must be stated, not smoothed: the **sign inconsistency** between
the medium and maximal readings, and **why detection collapses this hard**. The mechanism question
(M1/M2/M3 in `docs/ROI_FEASIBILITY.md` §2.4a) is **reopened, not closed**.

## A.3 Effect on Decision 29 — the pre-declaration survives, its premise is replaced

Decision 29 pre-declared D8 attention validity as at-risk. **That declaration stands and should not
be withdrawn.** Only its stated reason changes:

> **Old premise (retracted):** pitch cannot register at all, so look-down is invisible.
> **New premise (evidenced):** pitch registers, but the face is detected too rarely during look-down
> for an episode-level oriented-rate to be trustworthy — and `oriented_rate ≈ 1.0` under those
> conditions reflects missingness, not orientation.

This is a stronger position than the one it replaces: it is grounded in a real, independently-judged
session with logged data (`logs/orientation_trials.jsonl`), rather than in an unverified figure.
**Declared before Gate 2 is run, not discovered after.**

## A.4 Exact replacement text — `stage1_step4_vectors.py`, replacing lines 102–118

```
V_so is a PILOT feature, NOT POC-ready, and is NOT wired into the demo
UI as an attention reading (stage3_demo_ui.py reads ONLY its yaw_deg
field, surfaced as a clearly-labelled EXPERIMENTAL badge; pitch, the
blended orientation_score and oriented are never displayed). Directed
testing found: YAW (left/right) is detected reliably. PITCH (looking
up/down) is NOT USABLE for ROI attribution -- but the reason recorded
here previously was wrong, and is RETRACTED.

RETRACTED, DO NOT REINSTATE: the claim that on a maximal, sustained,
verified chin-to-chest look-down "MediaPipe-derived pitch stayed
~0.1deg", and that the root cause was STRUCTURAL and not fixable here.
No documented verification method for that figure ever existed in this
repository (docs/ROI_FEASIBILITY.md 2.4a found this first), and a real,
graded-intensity, independently-judged capture contradicts it: maximal
held look-down attempts registered pitch as large as -43.1deg (-31.6deg
and -15.2deg averages across two attempts, both judged "genuine maximal"
in real time BEFORE any number was shown), with magnitude scaling
roughly with commanded intensity (small ~6deg, medium ~2-3deg, maximal
~15-32deg). Data: logs/orientation_trials.jsonl, graded_pitch_capture.py.

WHAT IS ACTUALLY WRONG -- the current, evidence-backed position:
FACE DETECTION RATE collapses during look-down (0.08% to 27.5% across
the graded attempts), even on the attempts where pitch DID register at
large magnitude. Because most window-samples are MISSING rather than
present-and-centred, oriented_rate still reads close to 1.0. That is a
MISSINGNESS artefact, not a reading of "oriented". Two facts remain
unexplained and must not be smoothed over: a sign inconsistency between
the medium and maximal readings, and why detection collapses this hard.

CONSEQUENCE -- UNCHANGED: pitch-based ROI attribution is not viable
today, and a yaw-only signal cannot honestly be presented as
"attention"/"engagement"/"focus"/"distraction", because the most common
disengagement cue is looking down. Doing so would overclaim, the same
dishonesty the pain-axis rule (V_bf) forbids.
MECHANISM -- NOW OPEN: face foreshortening remains a plausible
contributor, and yaw_pitch_roll_from_matrix remains provably exact on
synthetic rotations, but "structural, not fixable here" is no longer a
position this docstring may assert. The M1/M2/M3 question in
docs/ROI_FEASIBILITY.md 2.4a is REOPENED, not closed.

DO NOT tune pitch here on the strength of this comment (G2). Any change
is pilot work with its own pre-registered test.
```

## A.5 Exact replacement text — `features/attention.py`, replacing lines 144–149

*(Also note: the stale `stage1_step4_vectors.py` docstring says `stage3_demo_ui.py` "never imports or
reads it". That is itself out of date — per `CLAUDE.md` line 708, the demo now reads `compute_v_so()`'s
`yaw_deg` field only, as a labelled EXPERIMENTAL badge. The A.4 replacement text corrects this too.)*

```
    PILOT-ONLY, NOT POC-ready: pitch_deg's contribution below is NOT
    USABLE for ROI attribution. The previous wording here -- "UNRELIABLE
    by structural limit of single-camera landmark head-pose ... not a bug
    in this formula" -- is RETRACTED as a settled mechanism claim. See the
    RETRACTED block in stage1_step4_vectors.py's module docstring and
    docs/PROJECT_STATE.md. Real graded-intensity capture registered pitch
    up to -43.1deg, so the "~0.1deg" premise that claim rested on is
    false. The evidenced problem is that FACE DETECTION RATE collapses
    during look-down (0.08%-27.5%), which makes oriented_rate read near
    1.0 out of MISSINGNESS, not orientation. yaw_deg's contribution is
    reliable. Do NOT change the computation below on the strength of this
    comment, and do not tune pitch (G2).
```

## A.6 Exact replacement text — sign-off response §4.14, the two stale paragraphs

Replace, verbatim, the paragraphs beginning *"Directed testing during the POC established…"* and
*"The root cause is not a bug…"* with:

> Directed testing established that horizontal head orientation (yaw) is detected reliably. Vertical
> orientation (pitch) is not usable for ROI attribution — but I am correcting the reason I gave for
> that in an earlier draft, because the reason was wrong.
>
> The earlier draft stated that on a maximal, sustained chin-to-chest look-down, measured pitch
> stayed at approximately 0.1°, and attributed this to a structural limit of single-camera landmark
> head-pose. That figure had no documented verification method anywhere in the repository, and a
> subsequent graded-intensity capture, judged independently in real time before any number was
> shown, contradicts it: maximal held look-down attempts registered pitch as large as −43.1°, with
> magnitude scaling roughly with commanded intensity. I am retracting the figure and the mechanism
> claim built on it.
>
> The practical conclusion is unchanged, and the evidence for it is now better. What fails during
> look-down is not the pitch measurement but face detection itself: detection rate fell to between
> 0.08% and 27.5% across the graded attempts, including on attempts where pitch registered at large
> magnitude. Because most window-samples are missing rather than present, the oriented-rate still
> reads close to 1.0 — a missingness artefact, not a reading of orientation. Two facts remain
> unexplained and I am not smoothing them over: a sign inconsistency between the medium and maximal
> readings, and why detection collapses this severely. The mechanism question is reopened, not
> settled.
>
> The consequence for this row is what it was: the most common disengagement cue is looking down,
> and this signal cannot see it reliably. Your §11 failure rule already provides for that outcome,
> which is why I am declaring the expectation now rather than presenting it afterwards. I would
> rather show you a retracted claim and the data that retracted it than carry a tidy sentence I
> cannot support.

---

# Part B — §18 change control for audio retention

Delivered as a separate document: **`D0PA1_Section18_ChangeControl_Audio_DRAFT.md`**.

Summary of what it settles, and one thing it surfaces that was not in the status report:

- The change-control record did not exist; `docs/AUDIO_ACQUISITION.md` §6 explicitly says so and
  correctly declines to be it. The draft is now that record.
- It separates what was built (acquisition, consent, integrity logging, privacy guard, separation
  guard) from what was explicitly not (no audio feature, `features/audio.py` still an empty stub).
- **It records that retention does not yet lift §10.9.** §4.23's own retention condition — a
  documented clock-synchronisation method with measured drift — is unmet, so Δ_audio is not yet
  computable. Retention bought a capability that is not usable until Part D succeeds.
- **New finding:** the client's audio decision silently resolves **§19 rows 19 and 23**, both still
  recorded as DECISION REQUIRED. Proposed reclassification moves the counts to
  **12 / 6 / 11 / 1**. The vendor proposes; Gargi confirms.

---

# Part C — §19 matrix row 16, and two defects found in the sign-off document

## C.1 Row 16 is correctly worded — my earlier flag is resolved

I flagged a risk that row 16's upgrade to EVIDENCED might rest on `excursion_count = 0` rather than
on the null result. **It does not.** Both `docs/MATRIX_ROW_MAP.md` row 16 and the response's §4.16
state explicitly that because calibration never completed, the excursion detector never had a
baseline, so the false-event-rate metric is **"reported as not-yet-computable, not as zero."** Both
also keep the quiet-sitting baseline and the empty-scene control distinct, and §4.16 additionally
flags that the V_pd robust-scale figures cited in its own text come from a *third* unrelated session.
No action.

## C.2 Defect 1 — the closing section contradicts §4.16 within the same document

The response's closing "Built is not the same as validated" paragraph still reads:

> "…**the null-input control has no camera run**, the blink control has no clips, the leakage control
> cannot establish its expected direction on synthetic input, and the reliability machinery has no
> reliability sessions."

This is **directly contradicted** by §4.16 ("Both have now been run against a real camera, for real")
and by §6 ("updated: the null-input control's empty-scene run is now among them"). The update was
applied to §4 and §6 and missed in the closing.

**Fix:** strike the null-input clause. The other three remain true.

> "…the blink control has no clips, the leakage control cannot establish its expected direction on
> synthetic input, and the reliability machinery has no reliability sessions."

## C.3 Defect 2 — an arithmetic mismatch between §6 and the closing

- §6 states: "Twelve … **Six** are built and tested but have never been run against real data … Nine
  … Three."
- The closing states: "**Eight** rows are implemented and tested but have never touched real data."

I counted `MATRIX_ROW_MAP.md` directly: BUILT-NOT-RUN = rows **3, 4, 9, 15, 18, 30 = six.**
EVIDENCED = 12, RETURNED = 9, DECISION REQUIRED = 3. Total 30. **§6 is right; the closing is stale
by the same edit that caused Defect 1.**

**Fix:** "Eight rows" → "Six rows".

Note this is the same class of error as the previously-flagged "eight corrections vs. a 10-item list"
mismatch. **Counts stated in prose are the highest-risk claims in this document**, because they are
the ones a client can falsify with a pocket calculator. Recommend a single pass that derives every
count in §6 and the closing from `MATRIX_ROW_MAP.md` rather than restating them.

## C.4 The open judgment call — rows 5 / 10 / 25 vs 6 / 11 / 13

Unresolved, and I am deliberately not resolving it unilaterally: rows 5 (primary metric / U),
10 (split hygiene) and 25 (V_es / V_pd wording) are classified plain RETURNED, while rows 6, 11 and
13 are EVIDENCED on what looks like a comparable amount of implementing code.

**Recommendation: leave them RETURNED.** The asymmetry costs nothing and errs toward under-claiming,
which is the direction G3 points. Upgrading three rows on a debatable standard, in a document whose
credibility rests on not over-claiming, is a poor trade for three status labels. If you disagree,
the fix is to state the classification standard explicitly in §6 and apply it consistently — not to
move three rows quietly.

---

# Part D — Light-flash A/V sync protocol (replaces the failed clap-motion method)

**Closes:** CC-001-A, and one of the exactly two remaining NOT TRACEABLE items.
**Blocked on:** machine time and one physical run. Nothing else.

## D.1 Why the previous method failed, and what changes

Five attempts across two sessions failed on the **video side every time** — audio transient
detection worked. The failure mode is inherent to the stimulus: a clap is detected in video as
*motion*, and a motion heuristic cannot distinguish the clap from ordinary movement. Tightened, it
found 0–3 events; loosened, it false-matched.

**The change is the stimulus, not the detector.** Replace motion with a **global luminance step**,
which a trivial threshold detects unambiguously and which nothing else in a static scene produces.

## D.2 Stimulus design

A single software-timed event observable by **both** sensors:

- The script emits a **short click/tone** through the laptop speakers, and in the **same instant**
  renders a **full-screen white flash** (2–3 frames) on the laptop display.
- The camera is pointed at a subject or a static object **illuminated by that display**, so the
  flash produces a large mean-luminance step in the captured frame.
- Because both are emitted by one process, each event has a **known software emission timestamp**,
  which additionally yields audio-path and video-path latency *separately*, not just their
  difference.

Physical propagation is negligible at this scale: sound over ~0.5 m ≈ 1.5 ms against a 33 ms frame
period. **Safety:** one flash per ~30 s. Do not flash in the 3–60 Hz band.

## D.3 Detection rules — PRE-REGISTERED, frozen before the run (G1)

Both constants live in the versioned, hashed configuration, **not** in code — same treatment as the
δ parameters.

**Video onset.** Mean luminance of the **raw grayscale frame**.
⚠️ **Must be computed before CLAHE.** CLAHE normalises local contrast and will actively suppress a
global luminance step — running the detector on the post-CLAHE frame is the single most likely way
this attempt fails the same way the last five did.
Event = first frame whose mean luminance exceeds the rolling-median baseline by ≥ `K_v` × robust MAD.

**Audio onset.** Short-time energy, 5 ms hops. Event = first hop whose energy exceeds the
rolling-median baseline by ≥ `K_a` × robust MAD.

**Pairing.** Each emission has a known software timestamp; pair the nearest video onset and audio
onset within ±500 ms of it. Unpaired emissions are **logged as missing, never dropped**.

## D.4 Run specification

- Duration ≥ 10 minutes, **≥ 20 emissions**, with **≥ 3 in the first minute and ≥ 3 in the last** —
  drift is not estimable without spread across the run.
- Static scene. No one moves during the run.
- Log to `logs/`. **No audio or video content is written** (G4) — onsets and energies only.

## D.5 What gets reported — and the resolution floor, stated up front

- **Offset** = median(video_onset − audio_onset).
- **Spread** = IQR and MAD across paired events.
- **Drift** = Theil–Sen slope of per-event offset against elapsed time.
- **Resolution floor, stated in the same breath as the number:** video onset is quantised to the
  frame period, **≈33 ms at 30 FPS**. Any spread below ~33 ms is **not resolvable by this method**
  and must not be reported as if it were. This is precisely what made the earlier
  40 ms / 281 ms / 828 ms figures untrustworthy, and it is why they were correctly withheld.

**G1:** the script computes and stores. It contains **no** "acceptable sync" threshold and emits no
pass/fail. Whether the measured offset and drift are tolerable is a human judgment applied afterward
against a rule frozen beforehand.

**Completion test:** either a reported offset with spread over ≥ 20 matched events and a drift
estimate, **or** an explicit statement that attempt 6 failed and why. A noisy number reported as a
result is worse than a documented failure — attempt 3 was handled correctly and should be the
template.

## D.6 Self-contained prompt for the Claude Code agent

```
Read CLAUDE.md first, in full, before doing anything else. This repository is
C:\Dopaland-POC, the D0PA1 vendor project. The five guardrails G1-G5 in CLAUDE.md
bind this task.

TASK: build av_sync_flash.py, a new standalone script at the repo root. Do NOT
modify features/x_core.py, features/episodes.py, features/geometry.py, or the
two-thread capture architecture (G5).

PURPOSE: measure the offset, spread and drift between the audio stream and the
video stream, using a light-flash stimulus. Five previous attempts using a clap
plus video MOTION detection failed on the video side; the stimulus is what
changes, not the detector.

BUILD:
1. An emitter that, on a fixed schedule (one event every ~30s, >= 20 events over
   >= 10 minutes), simultaneously (a) plays a short click/tone via the speakers
   and (b) renders a full-screen white flash for 2-3 frames. Record the software
   emission timestamp for each event.
2. A video onset detector on MEAN LUMINANCE of the RAW GRAYSCALE FRAME. CRITICAL:
   compute this BEFORE CLAHE. CLAHE normalises local contrast and will suppress a
   global luminance step. Onset = first frame exceeding a rolling-median baseline
   by K_v * robust MAD.
3. An audio onset detector on short-time energy, 5ms hops. Onset = first hop
   exceeding a rolling-median baseline by K_a * robust MAD.
4. Pairing: for each emission, the nearest video onset and audio onset within
   +/-500ms. Unpaired emissions are LOGGED AS MISSING, never dropped.
5. Output to logs/: per-event records (emission_ts, video_onset_ts, audio_onset_ts,
   or explicit missingness flags with reasons), plus a run summary carrying
   median offset, IQR, MAD, Theil-Sen drift slope, and the frame-period
   quantisation floor in ms.

HARD CONSTRAINTS:
- G1: K_v and K_a live in the versioned hashed configuration, NOT hardcoded. The
  script computes and stores numbers. It must contain NO pass/fail, NO "acceptable
  sync" threshold, and NO verdict of any kind.
- G4: no audio and no video content is ever written to disk. Onsets, energies and
  timestamps only.
- Report the frame-period resolution floor (~33ms at 30 FPS) alongside every spread
  figure in the summary output. A spread below that floor is not resolvable by this
  method.
- Tests: unit-test the two onset detectors against synthetic signals with known
  injected onsets, and test the pairing logic including the unpaired-emission path.

Report back: the file you created, the tests you added, and anything in the above
you could NOT do, stated plainly rather than worked around.
```

---

# Part E — Extended stability soak, run interactively

**Closes:** correction #1 (the "multi-hour" claim vs 41 minutes of evidence).
**Blocked on:** machine time and your presence to launch it. Nothing else.

## E.1 Why the last two attempts died at ~90s

Diagnosed, not guessed: `stage3_demo_ui.py`'s shutdown logic uses
`cv2.getWindowProperty(...)`, which false-triggers under a backgrounded launch context. Both runs
**exited cleanly** — they did not crash. **This is not a code defect and must not be "fixed."**
Changing it would touch the validated demo path for the convenience of a test harness (G5).

**The fix is the launch context.** Run it from a real interactive terminal on the machine.

## E.2 Procedure

1. **Before launching:** disable sleep, display sleep and the screensaver. If the display sleeps,
   the HighGUI window can be destroyed and you get the same false trigger at hour two — which would
   be the most expensive way possible to learn this.
2. Open a real PowerShell or `cmd` window **directly on the machine** (not a backgrounded tool call,
   not a remote-driven shell).
3. `cd C:\Dopaland-POC`
4. `python stage3_demo_ui.py --soak`
5. Leave the window **visible and unminimised**. Do not lock the screen.

## E.3 Duration — pick one, honestly

- **Option A — 180 minutes.** The smallest duration that makes the word "multi-hour" literally true.
  Closes correction #1 by measurement.
- **Option B — don't run it; restate the claim.** "Stability demonstrated over a 41-minute continuous
  soak" is already accurate, already evidenced, and costs nothing.
- **Recommendation: A, but only if the machine is otherwise free.** Three hours of machine time buys
  you the ability to stop hedging a sentence in every future document, and a leak that only shows at
  hour two is exactly the kind of thing a client-facing study should find before collection rather
  than during. If the machine is needed for anything else this week, take B — it is an honest
  position, not a fallback.

**Scene note:** an empty scene is not a representative load, because no detection work happens. For a
realistic load without three hours of human time, place a **printed photograph or a second screen
showing a face** in the camera's view. Label the result as what it is: **a load and leak test, not a
behavioural test.** Do not let that distinction blur later.

## E.4 Acceptance criteria — freeze these BEFORE launching (G1)

Proposed by me, to be frozen by you before the run starts, and applied by you afterward. The script
logs numbers; it does not score itself.

| Dimension | Proposed criterion | Rationale |
|---|---|---|
| **FPS drift** | Median FPS over the final 10 min ≥ 0.85 × median FPS over minutes 0–10 | A 15% degradation is generous enough not to fire on thermal variation, tight enough to catch real drift |
| **FPS floor** | No 60-second window below **15 FPS** | The original Gate 1 bar. Reuses an existing frozen number rather than inventing one |
| **Memory bound** | End-of-run RSS ≤ (RSS at t = 10 min) + 150 MB | Measured against t=10min, not t=0, so startup allocation is excluded |
| **Leak signature** | No sustained monotone RSS increase > 10 MB per 30 min across ≥ 4 consecutive windows | Distinguishes a leak from ordinary allocator noise |
| **Deadlock** | Frame counter strictly increasing at every 60 s checkpoint; no processing-thread stall > 5 s | Direct liveness check |

**Checkpoint logging:** one record every 60 s to `logs/` — `elapsed_s`, `frames_total`,
`fps_median_60s`, `rss_mb`, `detect_rate_60s`. No video, no images (G4).

If the soak self-terminates early again despite an interactive launch, **report the elapsed time and
stop.** Do not adjust the shutdown logic to make the test pass — that is G2's failure mode wearing
a different hat.

---

# Part F — What this pack does *not* close

Stated so the boundary stays sharp:

- **Real reliability figures (SEM / RC / CV)** — still NOT TRACEABLE. Requires the 3-session
  matched-protocol data, which requires subject time. Nothing here changes that.
- Everything gated on the client's harness, the client's decisions, or the second camera —
  unchanged, and correctly so.
- The A/V sync figure is not closed by this pack either. Part D closes the *method*; the *figure*
  exists only after a successful run.
