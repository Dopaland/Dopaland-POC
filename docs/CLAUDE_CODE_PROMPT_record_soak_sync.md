# Claude Code prompt — record the soak and sync outcomes

> Paste everything below the rule.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

**Markdown only.** No `.docx`, no `.py`. Two completed lines of work exist only in conversation
and in a frozen rule file kept deliberately outside this repository. Record them here, in the
documents that already exist. **Do not create a new status document** — this repo already has
three overlapping ones and keeping them in sync has been a recurring source of error.

---

## Part 1 — The stability soak is closed

Three interactive runs. Record all of it:

- **2026-09-14, 73.2 min** — stopped by operator. `clean_exit: true`. Verdict INCONCLUSIVE under
  the then-current rule (no scene precondition existed). `detect_rate` ≈ 0 for 71 of 73 minutes
  — the printed photo had slipped from frame.
- **2026-09-16, 140.2 min** — stopped by operator. `clean_exit: true`. **VOID** under the
  scene-validity precondition: mean `detect_rate_60s` 0.493 against a required ≥ 0.90. The
  subject was a person present intermittently rather than an unattended screen. Criteria
  computed and **capped by VOID, never counted as passes**: FPS drift ratio 1.015, FPS floor
  19.7/24.76, memory Δ +2.1 MB over 130 min, no leak signature across 4 windows, liveness clean.
- **Closed under the rule's own stopping condition.** No fourth run without a new reason — a
  capture-path code change, a client request, or a specific stability concern that actually
  arises.

**The two standing statements, which must be kept apart:**

1. **The only validated stability claim:** *"stability demonstrated over a 41-minute continuous
   soak"* (POC era, passed against POC criteria).
2. **Raw observation, not a pre-registered result:** two interactive runs of 73.2 and 140.2
   minutes, both clean exits, no FPS drift, no floor breach, no memory growth, no stalls —
   **under intermittent or near-zero detection load, neither satisfying the scene-validity
   precondition.**

Statement 2 is true and useful. **It is not a stability result and must never be written as
one.**

**Also record two things worth keeping:**

- The ~90-second self-termination is established as **launch-context dependent**, not a defect.
  Two interactive runs reached 73 and 140 minutes with clean exits. `cv2.getWindowProperty`
  shutdown logic was never modified (G5).
- **FPS under genuine detection load is ~29** (28.9–29.8 at `detect_rate ≈ 1.0`), matching the
  POC baseline. An earlier 20.66 floor was a startup-ramp artefact, not a regression. This
  closes an open question raised during the soak work.

Note that the frozen acceptance rule lives **outside this repository**, by the same convention
as `GATE2_SCORING_RULE.md` and `ORIENTATION_SCORING_RULE.md`. Record that it exists and where
the convention puts it; do not copy it in.

---

## Part 2 — A/V synchronisation is a documented omission

**Nine attempts across five sessions.** Record:

- Stimulus changed twice: hand-clap with motion detection → brief luminance flash → 500 ms held
  flash with a lengthened click.
- **Two defects found by code review and corrected before the final attempt:** the video
  reference marked the *end* of the flash while the audio reference marked the *start* (biasing
  every offset by ≈ −`flash_duration_ms`; predicted −500 ms, observed −502.5 ms); and the
  diagnostic's `max_value_in_window` spanned the full ±1 s window, so pre-stimulus noise could
  be reported as the stimulus response.
- **Video-side registration was diagnosed and fixed** — a real, durable result. 19/19 emissions
  register cleanly at 19–72× the detection threshold. The 500 ms flash duration was the
  mechanism; a ~3-frame flash against a ~33 ms exposure period made detection a coin flip.
- **Emitter confirmed working** in every attempt from the diagnostic session onward — flash
  render and audio callback timestamps recorded directly, not assumed.
- **Audio-side registration fails, and the cause is NOT characterised.** State exactly that.
  An earlier attribution to ambient noise rested on the statistic since found defective and
  **must not be repeated or replaced with a new one.** "We do not know why" is the supportable
  statement.
- **Consequence:** Δ_audio cannot be computed. §10.9's condition is **not** lifted by the
  acquisition build alone.
- Closed under a pre-declared stopping condition. No further attempts proposed.

**One refinement to check before you write it.** Across attempts 1–5 the stimulus was a hand
clap and audio-side detection worked every time; attempts 6–9 used a speaker-emitted click and
audio misses ran 13, 7–9, 14, 18. **Verify from the code whether the audio onset detector is
the same across both eras.** If it is, the honest and narrower claim is:

> The audio onset detector registers real acoustic transients — a hand clap was detected in
> every attempt that used one. What fails is the speaker-emitted click reaching the microphone
> at a detectable level. Why, is not established.

**If you cannot verify the detector is the same, do not make that claim** — write the broader
"audio-side registration fails" version instead, and say why you could not narrow it.

---

## Part 3 — Status bookkeeping

**`docs/PROJECT_STATE.md`** is the cold-start document; make it current. Its "needs nothing but
machine time" bucket should now be empty — both items in it are closed.

**The NOT TRACEABLE list changes shape, and the distinction matters:**

- Previously two items: the audio sync figure, and real reliability figures (SEM/RC/CV).
- Now **one untraceable** — real SEM/RC/CV, still needing three matched-protocol sessions and
  the harness half — and **one dispositioned**: A/V sync, moved from "open gap, cause unknown,
  attempts ongoing" to "documented omission under §21, no further work proposed."

**A disposition is not a closure.** Do not write the sync item as resolved, and do not drop it
from the outstanding list.

**Do not change any §19 row status.** Row 23 stays DECISION REQUIRED pending the client; the
counts stay 12 / 6 / 9 / 3. CC-001 §6(a) is where the omission belongs, and **editing CC-001 is
not part of this task.**

---

## One judgment call to flag, not to make

The retracted ambient-noise attribution was drafted into omission text headed for CC-001, then
withdrawn when the defective statistic was found. It never left the repository — the same
category as the existing ten corrections.

**Whether that constitutes an eleventh correction or an internal finding is the methodology
owner's call, not yours.** Record the facts in `docs/CLIENT_FIGURES.md` §10 as a noted internal
finding, **leave the count at ten**, and say plainly in your report that the classification is
open for a human to decide.

---

## Verification

1. `git diff --stat` — markdown only. Zero `.docx`, zero `.py`.
2. No new status document created.
3. `docs/MATRIX_ROW_MAP.md` — all 30 row statuses unchanged against `git show HEAD:...`; counts
   still 12 / 6 / 9 / 3.
4. `docs/CLIENT_FIGURES.md` §10 — corrections count still **ten**.
5. Golden snapshot still `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`;
   full test suite passing. Markdown cannot move either.
6. `git status` — no media, audio, `.env` or credential (G4).

**Do not commit.** Report the diffs, the verification output, whether you could verify the
audio-detector question in Part 2, and anything you could not do — plainly, without substituting
an approach.
