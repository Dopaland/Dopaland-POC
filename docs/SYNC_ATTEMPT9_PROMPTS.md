# A/V Sync — attempt 9, the last one either way

Two confirmed defects, both found by reading code rather than running anything:

- **The video reference marks the wrong edge.** `flash_render_completed_ts` is assigned *after*
  the flash hold ends; `audio_first_callback_ts` marks the *start* of playback. Every attempt-8
  offset is biased by ≈ −`flash_duration_ms` (predicted −500 ms, observed −502.5 ms).
- **The diagnostic's audio statistic measured the wrong thing.** `max_value_in_window` spans the
  whole ±1 s window including time *before* the stimulus, so pre-click ambient noise could
  dominate it. The audio characterisation from attempts 7 and 8 does not hold up.

**What this does and does not justify.** Fixing the reference edge does **not** improve the
match rate — video already paired 19 of 20 with the wrong reference. **Audio is the binding
constraint at 14 misses, and neither defect touches it.** Attempt 9 is justified only because
the audio evidence was never valid, so there is currently no honest basis for either a
measurement or a stated cause.

**Stopping condition, declared now and final.** If attempt 9 does not produce **≥ 20 matched
events**, the omission text in Part C goes out as written — with *"cause not characterised"*
stated plainly. **There is no attempt 10**, and no further diagnostic. This line of work ends
with attempt 9 regardless of its outcome.

---

# PART A — Two fixes (paste now)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

You confirmed both defects below yourself in the read-only check. Fix exactly these two things
and nothing else.

## Fix 1 — the video reference must mark the flash's start edge

In `_emit_flash_and_click`, `flash_render_completed_ts` is assigned after the hold loop exits.
Record instead the timestamp at which the **first white frame is presented** — immediately
after the first `cv2.imshow` / `cv2.waitKey` pair inside the loop, not before the loop and not
after it.

Name the field for what it measures. `flash_render_completed_ts` is now actively misleading;
`flash_first_frame_ts` or similar is honest. Keep recording the end-of-hold timestamp as a
**separate** field — it is useful for confirming the hold actually lasted its configured
duration.

**Any offset computed under the new reference is not comparable to sessions `04d5cb0f`,
`0e6b2a1a` or `a6ce084e`.** Stamp the run output so that is unmistakable.

## Fix 2 — the diagnostic max must be taken post-stimulus only

`compute_diagnostic_window`'s `max_value_in_window` currently spans the full ±1 s window,
including time before the stimulus. For idx 12 and idx 19 it reported pre-click ambient noise
as though it were the click's response.

**Compute the max over the post-reference portion of the window only.** Keep the pre-reference
samples for the baseline — that part is correct and should not change.

Also report, per emission, the **pre-reference max** as its own separate field. When a
pre-stimulus noise event is larger than the stimulus response, that is worth seeing rather than
hiding, and it is what would have caught this defect earlier.

## Constraints

- **Change nothing else.** Not `k_v`, not `k_a`, not either detector, not the flash duration,
  not the click, not the ±500 ms pairing window (G2).
- **G1:** no threshold, pass/fail or verdict. Computes and stores.
- **G4:** scalars and timestamps only.
- `config_hash` should be **unchanged** — neither fix alters a configured value. If it changes,
  stop and report why.
- Tests for both fixes against synthetic input: a stimulus with a known start edge, and a
  window containing a large pre-reference spike that must no longer contaminate the max.

Report what you changed, the tests, and anything you could not do. **Do not commit.**

---

# PART B — Run it (you)

Lights off, laptop facing the wall, speakers unmuted, quiet room, real interactive terminal.

```
cd C:\Dopaland-POC
python av_sync_flash.py --diagnose --subject-id P01
```

**≥ 25 emissions, roughly 13 minutes.** Keep `--diagnose` on — if this fails, the corrected
traces are what make the omission write-up honest.

The room being quiet matters more than anything else you control, and it is the one variable
that has never been held steady across these attempts.

---

# PART C — Parse, and write the ending either way (paste after)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`.
G1–G5 bind this task.

Attempt 9 has been run with a corrected video reference edge and a post-stimulus-only
diagnostic max. **This is the final attempt regardless of outcome.**

Report:

1. **Matched event count.** Threshold: **≥ 20**.
2. **Audio response, characterised properly for the first time.** Using the corrected
   post-reference max: does the click produce a detectable step? Give the distribution of
   excess-over-baseline ratios. **Also give the pre-reference max per emission**, so
   pre-stimulus noise is visible rather than silently inflating anything.
3. **Video**, same treatment. Confirm the bimodality is still resolved.
4. **Unpaired emissions with reasons.** None dropped.

## If ≥ 20 matched

Report median offset, IQR, MAD, Theil–Sen drift, with the **33 ms frame-period floor stated
alongside the spread**. State explicitly that this offset uses a corrected video reference and
is **not comparable** to any prior session.

Then state what it means for **CC-001 §6(a)** and **CC-001-A** — whether the outstanding
condition is satisfied, and whether Δ_audio becomes computable.

## If fewer than 20 matched

The stopping condition is final. **Do not propose attempt 10 and do not propose further
diagnostics.** Draft — as a proposal for human review, not an edit — the documented-omission
text for CC-001 §6(a) and CC-001-A, and it must say these things honestly:

- **Nine attempts across five sessions.** The stimulus changed twice; the reference timing and
  the diagnostic statistic were each found defective and corrected.
- **Video-side registration was diagnosed and fixed** — a real result worth stating.
- **Audio-side registration fails, and the cause is NOT characterised.** Say exactly that. The
  earlier attribution to ambient noise rested on a statistic since found to measure
  pre-stimulus noise, and must not be repeated. **Do not substitute a new plausible-sounding
  cause** — "we do not know why" is the honest statement and the only supportable one.
- **Δ_audio cannot be computed**, and §10.9's condition is not lifted by the acquisition build
  alone.
- Offered under the client's §21 request that infeasibility be stated rather than implemented.

**Do not commit. Do not edit CC-001.**
