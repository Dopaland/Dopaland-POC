# Blink Positive Control — the agent prompts either side of your work

**Part A** the agent runs now, **before you record anything.** One of its checks can invalidate
the recording protocol — better to find that out before ten clips exist than after.

**Part B** is yours: `BLINK_CONTROL_AND_COMMIT.md` Part A. Record, count manually, *then* look
at detector output.

**Part C** the agent runs once your manual counts exist.

---

# PART A — Pre-flight (paste now)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

The blink positive control (§19 row 15) is about to be run for real. Its criterion was frozen
and signed on 2026-09-18 (`docs/preregistration/D0PA1_Client_SignOff_001.md` §3): event
F1 ≥ 0.80 AND per-clip count within ±20% on ≥ 8 of 10 clips, event-matching tolerance ±150 ms.

**This is a check. Change nothing. Report findings.**

## Check 1 — the one that can stop the whole thing

**Can the blink detector run against an archived video file at all?**

The response's §4.15 specifies ten one-minute *clips* compared against manual counts, and D4's
discipline says analysis runs from archived inputs rather than live capture. But the detector
consumes aperture values produced by the live pipeline.

Trace the actual path and answer plainly:

- Is there a route from a recorded video file → aperture values → `controls/blink_positive.py`?
  `analyze_video.py` exists — does its output feed the blink detector, and in which mode?
- If that route does **not** exist, say so and **stop**. Do not build it. A control that can only
  be run live cannot be re-run, and the operator needs to know that *before* recording, because
  it changes the protocol fundamentally — they would have to capture live with simultaneous
  recording rather than record and analyse afterwards.

## Check 2 — criterion values match the signed record

Confirm `controls/blink_positive.py` holds exactly: event F1 threshold 0.80, per-clip tolerance
±20%, minimum 8 of 10 clips, event-matching tolerance ±150 ms. Report any discrepancy with the
signed §3 rather than correcting it.

## Check 3 — G1

Does `blink_positive.py` **compute metrics**, or does it **emit a verdict**? It must do the
former only. A frozen criterion does not license code to apply it — the human still does that,
exactly as with the soak. Report what the code actually does.

## Check 4 — where do manual counts go?

The operator is about to count ten minutes of footage by hand and needs to know the input format
**before** they start, not after.

- Is there a defined schema or loader for manually-annotated blink onsets?
- If yes, state the exact format — field names, timestamp units, file layout — so counts can be
  recorded directly into it.
- If no, state that plainly and propose a minimal format. **Do not implement it yet.**

## Check 5 — storage, before any media exists

Recording ten clips creates raw media, which is now governed by signed policy:
90-day retention, stored **outside** `C:\Dopaland-POC`.

- Is `D0PA1_VIDEO_RAW_STORAGE_LOCATION` set in this environment?
- Does the code raise when it is unset, rather than silently defaulting to a path inside the repo?
- Confirm `.gitignore` and the pre-commit hook cover the clip formats that will actually be
  produced.

Report all five. **Change nothing. Do not commit.**

---

# PART B — Yours

`BLINK_CONTROL_AND_COMMIT.md` Part A. The three things that decide whether this is worth running:

1. **Freeze the counting rule and date it before recording.**
2. **Blink naturally — do not perform blinks.**
3. **Count all ten clips manually before you look at any detector output.**

Record glasses per clip.

---

# PART C — Compute and report (paste when your manual counts exist)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`.
G1–G5 bind this task.

Ten clips have been recorded and manually counted. The manual counts were completed **before**
any detector output was viewed. Run the detector against the archived clips and report.

**Report, per the response's §4.15:**

1. **Event-level precision and recall, separately**, plus event F1, at ±150 ms tolerance.
   Separately — a blended figure hides which way the detector errs, and over-detection and
   under-detection have different consequences.
2. **Per-clip count agreement** — each clip's manual count, detector count, percentage
   difference, and whether it falls within ±20%. State how many of ten pass.
3. **Bland–Altman** on the ten paired counts.
4. **Both ways if any clip involved glasses** — all-clips and excluding-glasses, following the
   Gate 2 flagged-baseline rule. The gap between the two figures is itself a finding.
5. **The ambiguity count** from the manual annotation, reported but not counted as blinks.

**Then state the frozen criterion and the observed values side by side. Do not declare PASS or
FAIL** — the human applies it, as with every other frozen rule in this project (G1).

**If the result falls short**, that is a real finding about this detector. It is not a reason to
re-record with different clips, and you should not propose that. Same rule that governed the
soak.

**Finally, state narrowly what a pass would license:** blink-count *detection*, and nothing else.
No psychological interpretation of blinking. Detector validation is not construct validation.

**Do not commit. Do not update any §19 row status** — that follows the human's verdict, not your
computation.
