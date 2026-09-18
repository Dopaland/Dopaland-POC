# A/V Sync — two code checks before anything is written down

> Paste everything below the rule into the Claude Code agent.
>
> **No run. No fix. No edit.** This is a read, and it decides whether the documented-omission
> draft is honest or premature.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

**This task changes no code and runs nothing.** Read, verify, report. The stopping condition on
sync *attempts* has fired and stands — nothing here proposes another run. But a documented
omission must not be written into a client document while a specific, checkable bug hypothesis
is outstanding, and there are two.

## Context

Attempt 8 (session `a6ce084e`, 500 ms flash, 150 ms full-amplitude click, confirmed-reference
pairing) produced 6 matched of 20: **1 video miss, 14 audio misses.** Video registration is
resolved — 19/19 emissions detected at 1.09×–142× the threshold gap. The remaining questions
are about the reference timestamps and the audio detector.

---

## CHECK 1 — which edge does `flash_render_completed_ts` mark?

Attempt 8's offset median is **−502.5 ms**, within 2.5 ms of the **500 ms flash duration**.

The hypothesis: the video onset fires at the **start** of the flash, but
`flash_render_completed_ts` is recorded when the flash **finishes** — after the hold elapses
and the window is cleared. If so, every video onset lands one flash-duration "before" its own
reference, by construction, and the −502.5 ms is a systematic artefact rather than a latency.

**Read the code and answer precisely:**

1. At exactly what point in `_emit_flash_and_click_diagnostic` (and the non-diagnostic emitter,
   if it now records the same field) is `flash_render_completed_ts` assigned — **before** the
   500 ms hold begins, or **after** it ends?
2. Same question for `audio_first_callback_ts`: does the first output callback fire at the
   **start** of playback, or after the buffer has been consumed?
3. If the two references mark different edges of their respective stimuli, say so plainly and
   state **by how much** that biases the computed offset.
4. Cross-check against the earlier evidence: in the diagnostic session `0e6b2a1a` the flash was
   ~3 frames and `flash_render_completed_ts` landed **69–159 ms** after scheduling. Is that
   consistent with your reading of (1)? A ~100 ms flash whose "completed" timestamp lands
   ~69–159 ms after scheduling would be.

**Do not fix anything.** Report what the code does.

---

## CHECK 2 — the audio misses that should not have missed

The Part C analysis found emissions logged as `no_audio_onset_within_window` whose own
diagnostic snapshot showed the signal **exceeding** threshold — **idx 12 at 3.43×** and
**idx 19 at 3.23×**.

For those two emissions specifically, determine which of these is true:

- **(a)** An onset fired, but outside the ±500 ms pairing window. If so, give its actual
  timestamp and distance from the reference.
- **(b)** No onset fired at all, because the live rolling baseline at the true peak instant
  differed from the pre-window snapshot the diagnostic records. If so, quantify the difference.
- **(c)** An onset fired inside the window but pairing rejected it for some other reason.

These have different meanings: **(a)** is a window-width problem, **(b)** is a limitation of the
diagnostic's own snapshot method, **(c)** is a pairing bug. Name which, with the evidence.

---

## Also report, without investigating further

Audio misses went from **7–9 of 19** in the diagnostic run (original click) to **14 of 20** in
attempt 8 (lengthened, full-amplitude click). A change made specifically to help audio appears
to have made it worse.

State that comparison plainly as a fact in the record. **Do not diagnose it, do not propose a
cause, and do not propose a fix** — it is context for whoever decides what happens next, not a
task here.

---

## What to conclude

End your report with one of exactly these two statements:

- **"Both checks clean — the documented-omission draft stands."** The −502.5 ms is not a
  reference artefact and the audio misses are genuine detection failures. Nothing here changes
  the Part C conclusion.
- **"Check N found a defect."** Describe it precisely, and state that this constitutes a new
  reason under the stopping rule — a bug fix rather than another hopeful attempt. **Do not fix
  it in this task**, and do not propose attempt 9; that is a human decision.

**Do not commit. Do not edit CC-001. Do not change any code.**
