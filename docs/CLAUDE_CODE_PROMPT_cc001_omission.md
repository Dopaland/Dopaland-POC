# Claude Code prompt — fold the sync omission into CC-001, fix one stale count

> Paste everything below the rule.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

**Markdown only.** Two files:
`docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md` (CC-001) and
`docs/MATRIX_ROW_MAP.md`. No `.docx`, no `.py`, nothing else.

**Do not touch CC-001 §9 (cost and schedule).** It is deliberately blank and is not in scope
for this or any agent task.

---

## Edit 1 — CC-001 §6(a)

§6(a) currently reads as an outstanding condition with a redesigned attempt pending. That is no
longer true: the work is complete and closed. Replace the §6(a) block with:

```
**(a) A documented clock-synchronisation method between audio and video, with measured drift —
NOT SATISFIED, AND CLOSED AS A DOCUMENTED OMISSION.**

Nine attempts across five sessions did not produce a usable measurement. The stimulus changed
twice — hand clap with motion detection, then a brief luminance flash, then a 500 ms held flash
with a lengthened click. Two defects were found by code review and corrected before the final
attempt: the video reference timestamp marked the *end* of the flash while the audio reference
marked the *start*, biasing every offset by approximately one flash duration (predicted
−500 ms, observed −502.5 ms); and the diagnostic statistic used to characterise response
strength spanned the full window including pre-stimulus time, so ambient noise could be
reported as the stimulus response.

**Video-side registration was diagnosed and fixed** — a real and durable result. Nineteen of
nineteen evaluable emissions register cleanly at 19×–72× the detection threshold. The mechanism
was flash duration: a ~3-frame flash against a ~33 ms camera exposure period made detection
close to a coin flip, and a 500 ms held flash removed the problem entirely. Emitter operation
is confirmed directly from the diagnostic session onward — flash render and audio callback
timestamps are recorded, not assumed.

**Audio-side registration fails, and the cause is not characterised.** An earlier attribution to
ambient noise rested on the diagnostic statistic since found defective; it does not stand and is
not replaced with another. There is a specific reason the cause cannot be recovered from this
record: **the stimulus and the onset detector changed together at attempt 6** — attempts 1–5
used a hand clap with a percentile-threshold detector, attempts 6–9 a speaker-emitted click with
a rolling-median-plus-MAD detector — and no attempt isolates one from the other.

**Consequence:** Δ_audio cannot be computed. §10.9's condition is not lifted by the acquisition
build alone. A working acquisition pipeline is not a working synchronisation measurement.

This is stated under your §21 request that infeasibility be reported rather than implemented. It
is a legitimate, evidenced outcome: the video half is solved, the audio half is not, and why it
is not is honestly unknown. No further attempts are proposed.
```

## Edit 2 — CC-001-A (the appendix)

The appendix describes the sync measurement as outstanding, blocked on nothing but machine time,
with a completion test. Replace it with a closure record. Keep the heading; replace the body:

```
**Closed.** Nine attempts across five sessions; see §6(a). The completion test defined here —
a reported offset with a stated spread across ≥ 20 matched events plus a drift estimate — was
not met: the best attempt produced 6 matched events of 20, the final attempt 2 of 20.

The alternative outcome this appendix allowed for — "an explicit statement that the measurement
failed again and why" — is what was delivered, with the qualification that the *why* is
established only for the video half. This item is closed and requires no further work.
```

## Edit 3 — CC-001 §7, the row 23 basis line

§7 proposes reclassifying row 23 with the basis that the sync measurement is "outstanding and
blocking." That wording implied pending work. Update the **basis text only** to state that the
condition is now a documented omission under §6(a) rather than outstanding work.

**Do not change the proposed status, and do not change the proposed counts.** The
reclassification remains a proposal awaiting the client's confirmation.

## Edit 4 — `docs/MATRIX_ROW_MAP.md` row 23

Row 23's rationale says **"five measurement attempts across two sessions failed."** The real
figure is **nine attempts across five sessions.** Correct the count and note that the item is
now a documented omission under CC-001 §6(a).

Same principle as the previous correction to this row: **a row's status is the client's to
confirm; a row's factual rationale has to be true regardless.** Row 23 stays
`DECISION REQUIRED`. The counts stay **12 / 6 / 9 / 3**.

---

## Verification

1. `git diff --stat` — exactly the two files named. Zero `.docx`, zero `.py`.
2. **CC-001 §9 unchanged** — confirm by diff that the cost and schedule section was not touched.
3. `docs/MATRIX_ROW_MAP.md` — all 30 row statuses unchanged against `git show HEAD:...`; counts
   still 12 / 6 / 9 / 3; the phrase "five measurement attempts across two sessions" no longer
   appears.
4. Search both files for any surviving claim that the sync measurement is pending, outstanding,
   or awaiting a further attempt. **Report any you find; do not edit beyond the four edits
   above.**
5. Golden snapshot still `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`;
   full test suite passing.
6. `git status` — no media, audio, `.env` or credential (G4).

**Do not commit.** Report the diffs, the verification output, and anything you could not do —
plainly, without substituting an approach.
