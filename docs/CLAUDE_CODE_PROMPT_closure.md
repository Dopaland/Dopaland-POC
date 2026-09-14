# Prompt for the Claude Code agent — D0PA1 closure work

> Paste everything below the line into the Claude Code agent, as a single message.
> It is self-contained: it assumes no memory of any previous session.

---

**Read `CLAUDE.md` in full before doing anything else.** You are working in
`C:\Dopaland-POC`, the D0PA1 vendor project — a paid, client-governed, pre-registered
single-subject study. The five guardrails G1–G5 in `CLAUDE.md` bind everything below.
Two of them are load-bearing for this task and I am restating them so you cannot miss them:

- **G1 — the pipeline never scores itself.** Nothing you write may contain a threshold,
  a pass/fail, an "acceptable" range, or a verdict. Code computes and stores numbers.
  A human applies a pre-registered rule afterwards.
- **G5 — do not modify the validated path.** Do not change
  `features/x_core.py`, `features/episodes.py`, `features/geometry.py`, or the
  two-thread capture architecture. Task 1 below edits docstrings only and changes no
  executable line.

There are four tasks. Do them in order. **Do not commit anything** — leave all changes in
the working tree and report the diffs; a human reviews them before they enter git history.

Background you need for Task 1, stated once: a previously-documented claim in this repo —
that on a maximal chin-to-chest look-down, pitch stayed at approximately 0.1°, and that the
cause was structural and unfixable — **has been retracted.** It had no documented
verification method, and a real graded-intensity capture registered pitch as large as
−43.1°. `CLAUDE.md` and `docs/PROJECT_STATE.md` already reflect the retraction. Three other
places do not. You are fixing those three. Do not re-derive or re-argue the finding; the
replacement text below is final and was written by the project's methodology owner.

---

## Task 1 — Replace three stale docstrings/passages carrying the retracted pitch claim

### 1a. `stage1_step4_vectors.py`

In the module docstring, replace **lines 102–118** — the block beginning
`V_so is a PILOT feature, NOT POC-ready,` and ending
`"Attention / screen-orientation -- PILOT, not POC" note).` — with exactly this text.
Keep the surrounding `--- PILOT STATUS ... ---` header line and the closing `"""` intact.

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

### 1b. `features/attention.py`

In the `compute_v_so` docstring, replace **lines 144–149** — the paragraph beginning
`PILOT-ONLY, NOT POC-ready: pitch_deg's contribution below is UNRELIABLE` and ending
`computation below on the strength of this comment.` — with exactly this text, preserving
the existing 4-space docstring indentation:

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

### 1c. `docs/preregistration/D0PA1_Section19_SignOff_Response.docx`, §4.14

This is a **client-facing document that has never been sent.** Edit it with `python-docx`.
Note that a single visible paragraph may be split across multiple runs — locate paragraphs
by their full concatenated text, then rewrite the paragraph's runs rather than assuming one
run per paragraph. Preserve the paragraph's existing style.

In §4.14 (Item 14 · D8 — Attention validity), find the two consecutive paragraphs beginning:

- `Directed testing during the POC established that horizontal head orientation (yaw) is detected reliably...`
- `The root cause is not a bug. The rotation decomposition is provably exact on synthetic rotations...`

Replace those **two** paragraphs with these **four** paragraphs:

```
Directed testing established that horizontal head orientation (yaw) is detected reliably. Vertical orientation (pitch) is not usable for ROI attribution — but I am correcting the reason I gave for that in an earlier draft, because the reason was wrong.
```
```
The earlier draft stated that on a maximal, sustained chin-to-chest look-down, measured pitch stayed at approximately 0.1°, and attributed this to a structural limit of single-camera landmark head-pose. That figure had no documented verification method anywhere in the repository, and a subsequent graded-intensity capture, judged independently in real time before any number was shown, contradicts it: maximal held look-down attempts registered pitch as large as −43.1°, with magnitude scaling roughly with commanded intensity. I am retracting the figure and the mechanism claim built on it.
```
```
The practical conclusion is unchanged, and the evidence for it is now better. What fails during look-down is not the pitch measurement but face detection itself: detection rate fell to between 0.08% and 27.5% across the graded attempts, including on attempts where pitch registered at large magnitude. Because most window-samples are missing rather than present, the oriented-rate still reads close to 1.0 — a missingness artefact, not a reading of orientation. Two facts remain unexplained and I am not smoothing them over: a sign inconsistency between the medium and maximal readings, and why detection collapses this severely. The mechanism question is reopened, not settled.
```
```
The consequence for this row is what it was: the most common disengagement cue is looking down, and this signal cannot see it reliably. Your §11 failure rule already provides for that outcome, which is why I am declaring the expectation now rather than presenting it afterwards. I would rather show you a retracted claim and the data that retracted it than carry a tidy sentence I cannot support.
```

**Verify by re-extracting `word/document.xml` after writing and confirming the new text is
present and the old text is absent.** Do not trust the write; check it.

---

## Task 2 — Fix two internal contradictions in the same .docx

Both are in the closing section, under the line beginning
`Three statements I want to make plainly`. Both were caused by an earlier edit that updated
§4 and §6 and missed the closing.

**2a.** In the paragraph beginning `Built is not the same as validated`, the phrase
`Eight rows are implemented and tested but have never touched real data` is wrong.
The correct figure is **six**, which you must verify rather than take from me: count the rows
in `docs/MATRIX_ROW_MAP.md` whose status is `BUILT, NOT YET RUN ON REAL DATA`. Change the word
`Eight` to `Six` only if your count returns six. **If your count returns anything else, stop,
change nothing in the document, and report the discrepancy** — a wrong count is the exact class
of error this fix exists to remove, and guessing would reproduce it.

**2b.** In that same paragraph, the clause `the null-input control has no camera run,` is now
false — §4.16 of the same document states both null-input runs have been performed against a
real camera. Delete that clause so the sentence reads:

```
Six rows are implemented and tested but have never touched real data — the blink control has no clips, the leakage control cannot establish its expected direction on synthetic input, and the reliability machinery has no reliability sessions.
```

Leave the rest of the paragraph unchanged. Re-extract and verify as in 1c.

---

## Task 3 — Build `av_sync_flash.py`

A new standalone script at the repo root. Its purpose is to measure the offset, spread and
drift between the audio stream and the video stream.

Context you need: five previous attempts used a **clap** plus video **motion** detection and
failed on the video side every time — loosened, the motion heuristic false-matched on ordinary
movement; tightened, it found 0–3 events. **The stimulus is what changes here, not the
detector's rigour.** A global luminance step is detectable by a trivial threshold and nothing
else in a static scene produces one.

Build:

1. **Emitter.** On a fixed schedule — one event roughly every 30 s, ≥ 20 events across a run of
   ≥ 10 minutes — simultaneously (a) play a short click or tone through the speakers and
   (b) render a full-screen white flash for 2–3 frames. Record the software emission timestamp
   for each event. Do not flash at rates in the 3–60 Hz band.
2. **Video onset detector**, on the mean luminance of the **raw grayscale frame**.
   **CRITICAL: compute this BEFORE CLAHE.** `apply_clahe` runs at
   `stage1_step4_vectors.py:400` on every frame; CLAHE normalises local contrast and will
   actively suppress a global luminance step. Reading a post-CLAHE frame is the single most
   likely way this attempt fails exactly as the previous five did.
   Onset = the first frame whose mean luminance exceeds a rolling-median baseline by
   `K_v × robust MAD`.
3. **Audio onset detector**, on short-time energy in 5 ms hops. Onset = the first hop whose
   energy exceeds a rolling-median baseline by `K_a × robust MAD`.
4. **Pairing.** For each emission, take the nearest video onset and the nearest audio onset
   within ±500 ms. **Unpaired emissions are logged as missing with a reason, never dropped.**
5. **Output to `logs/`.** Per-event records — emission timestamp, video onset, audio onset, or
   explicit missingness flags — plus a run summary carrying: median offset
   (video onset − audio onset), IQR, MAD, a Theil–Sen drift slope of per-event offset against
   elapsed time, and the frame-period quantisation floor in milliseconds.

Hard constraints:

- **G1.** `K_v` and `K_a` live in the versioned, hashed configuration — the same treatment the
  δ parameters get — **not hardcoded**. The script must contain no pass/fail, no "acceptable
  sync" threshold, and no verdict of any kind. It computes and stores.
- **G4.** No audio and no video content is ever written to disk. Onsets, energies, timestamps
  and counts only.
- The summary output must state the frame-period resolution floor (≈33 ms at 30 FPS) alongside
  every spread figure. A spread below that floor is not resolvable by this method and must not
  be presented as if it were.
- **Tests.** Unit-test both onset detectors against synthetic signals with known injected
  onsets, and test the pairing logic including the unpaired-emission path.

---

## Task 4 — Add soak checkpoint logging

`stage3_demo_ui.py --soak` currently self-terminates early when launched from a backgrounded
context, because `cv2.getWindowProperty(...)`-based shutdown logic false-triggers there. **This
is not a defect and you must not change that shutdown logic** — it is on the validated demo path
(G5), and the fix is to launch interactively, which a human will do.

What you add is observability only: append one checkpoint record every 60 seconds to `logs/`,
containing `elapsed_s`, `frames_total`, `fps_median_60s`, `rss_mb`, and `detect_rate_60s`.

- Make this **opt-in via the existing `--soak` flag only**, so no other run path changes.
- **G1:** record the numbers. Do not evaluate them, do not compare them to any bound, do not
  emit any warning, status or verdict based on them. The acceptance criteria are frozen by a
  human before the run and applied by a human afterwards.
- **G4:** no video, no images.

---

## Verification before you report back — run all of these

1. `tests/test_refactor_snapshot.py` — the golden regression snapshot must still be
   `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`. Tasks 1, 2 and 4 change
   no computed value, so **any change to this hash means you altered behaviour and must stop and
   report it**, not adjust the snapshot.
2. `tests/test_feature_separation.py` — all four checks must still pass.
3. The full test suite — all 26 test files.
4. Re-extract both edited passages from the .docx and confirm the new text is present and the
   old text is gone.
5. `git status` — confirm no raw media, no audio, no `.env`, no credential has entered the
   working tree (G4).

## How to report back

State plainly:

- The exact files you changed and the diffs.
- Your independent count of `BUILT, NOT YET RUN ON REAL DATA` rows in `docs/MATRIX_ROW_MAP.md`,
  and whether it matched six.
- The test results, including the golden snapshot hash you actually observed.
- **Anything above you could not do, or did differently, stated plainly rather than worked
  around.** A reported gap is correct behaviour here; a silently substituted approach is not.
- Do not commit. Leave the changes in the working tree for human review.
