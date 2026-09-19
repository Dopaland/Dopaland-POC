# Blink Positive Control, and the Commit

**Two small things first, both yours, both two minutes:**

1. **Open `docs/preregistration/D0PA1_Client_SignOff_001.md` and put your own name and date in
   §7**, replacing what an agent typed there. That signature is the one place in this structure
   where a human act is the whole point.
2. **Decide derived-log retention.** The sign-off set 90 days for raw media and said nothing
   about derived feature logs, so a leftover default currently governs them. Derived logs are
   numeric with anonymous participant codes — indefinite retention is defensible. But record it
   as a decision, not a default.

Then Part A below is the work, and Part B commits everything.

---

# PART A — The blink positive control (you run this)

**What it is:** §19 row 15, the last item producing new evidence that isn't blocked on the
client's harness. Ten one-minute clips, manual blink counts, compared against detector output.

**What it's worth:** row 15 moves BUILT-NOT-RUN → EVIDENCED, and the two A-column items held at
PARTIAL for exactly this reason clear. Counts go to 13 / 5 / 11 / 1.

**The criterion is already frozen** — §3 of the sign-off, accepted 2026-09-18: event F1 ≥ 0.80
**AND** per-clip count within ±20% of the manual count on at least 8 of 10 clips, with an
event-matching tolerance of ±150 ms. Because it was frozen before this run, **you can apply it
afterwards.** That's the sequencing working.

## A.1 Before recording — freeze the counting rule

You cannot count blinks without an operational definition, and inventing one after seeing the
data is the same error as tuning a threshold to fit. **Write this down and date it before you
record anything.** Proposed:

> **A blink** = both upper eyelids make full contact with the lower lids and reopen, completing
> within approximately 500 ms.
> **Not a blink:** partial closures, however deep; a sustained closure longer than ~500 ms
> (that's a rest, not a blink); single-eye closures.
> **Ambiguous cases** are logged in a separate column and **not** counted either way — the count
> of ambiguities is itself reportable.

Change it if you disagree — but freeze whatever you choose before recording.

## A.2 Recording

- **Ten clips, one minute each.** You are P01.
- **Normal room lighting.** Not the dark setup used for the sync work.
- **Blink naturally. Do not perform blinks.** A performed blink is slower and more complete than
  a real one; a detector validated on performed blinks tells you nothing about real ones.
- **Vary the conditions across the ten** — different times of day, sitting slightly differently.
  Ten clips of the same minute repeated proves less than ten genuinely different ones.
- **Record whether glasses were worn, per clip.** Glasses reflecting into the iris is a *known*
  failure case (Pitfall #4). If you wear them normally, include them — and report the result
  **both ways**, all-clips and excluding-glasses, exactly as the Gate 2 flagged-baseline rule
  does. The gap between the two numbers is itself a finding.

**Storage:** these clips are raw media. Under the sign-off they go to the defined folder
**outside** `C:\Dopaland-POC`, retained 90 days, deleted via the routine that writes a deletion
log. This is the first application of that policy — get it right the first time.

## A.3 Count manually — before looking at any detector output

**This is the part that decides whether the control is worth anything.**

Count all ten clips by hand, frame by frame or in slow playback, and **record the onset frame or
timestamp of each blink** — the event-level F1 needs onsets, not just totals. Log ambiguities
separately.

**Do not run the detector, and do not look at its output, until all ten manual counts are
finished and written down.** Once you have seen the detector's answer you cannot un-see it, and
every subsequent judgement call drifts toward agreement. A positive control contaminated this
way looks like a pass and means nothing.

## A.4 Then run the detector

Run it **on the archived clips**, not live — same principle as D4's archived-input replay. Live
capture is not reproducible, and you want this re-runnable.

## A.5 Apply the frozen criterion

Report, per the response's own §4.15:

- **Event-level precision and recall, separately**, plus event F1, at ±150 ms tolerance
- **Per-clip count agreement** — the ±20% test, and how many of ten pass
- **Bland–Altman** on the ten paired counts
- Both ways if glasses are involved
- The ambiguity count

Then apply the criterion and record PASS or FAIL.

**If it fails, that is a real result about this detector** — not a test to re-run with different
clips. The same rule that governed the soak governs this.

**What a PASS licenses, narrowly:** blink-count *detection* works. Nothing about attention,
engagement, cognitive load, or any psychological construct. Detector validation is not construct
validation, and the response already commits to not blurring the two.

---

# PART B — Commit (paste to the Claude Code agent)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

Commit the working tree. **Derive everything from the actual `git status` and `git diff`** — do
not trust any list, including this one.

## Before committing

1. **G4 first.** No media, audio, `.env`, credential or raw participant data staged or untracked.
   Check independently of the pre-commit hook. **Note:** blink clips may now exist on this
   machine — confirm they are outside the repository entirely, per the signed storage policy.
2. Golden snapshot returns `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`.
3. `tests/test_feature_separation.py` — all checks pass.
4. Full test suite passing.

**If any fail, stop and report. Do not commit.**

## Commit structure

Logical commits, matching the existing history's message style. Roughly:

| Commit | Contents |
|---|---|
| Client sign-off 001: freeze δ thresholds, blink criterion, retention | `D0PA1_Client_SignOff_001.md`, `simulation/config.py`, `controls/blink_positive.py`, `privacy/retention.py`, `privacy/video_storage_config.py`, and their tests |
| Correct leakage-diagnostic unit to nats | The `.docx` §4.7 fix and `docs/MATRIX_ROW_MAP.md` row 9 |
| Apply rows 19/23 reclassification, counts to 12/6/11/1 | Matrix map and the response document |
| Reconcile status documents to the sign-off | `PROJECT_STATE.md`, `CLIENT_FIGURES.md` |

**The sign-off commit's message must record that `D0PA1_Client_SignOff_001.md` is signed by
DOPALAND on its stated date.** That commit becomes the durable evidence of when these values
were frozen, which matters more than any other line in this history.

## One check before you write that message

**Open `D0PA1_Client_SignOff_001.md` §7 and confirm the signature block is filled.** If it is
still blank, **stop and report** — do not fill it in, and do not commit the sign-off. An agent
must not author that field; it was already written by one once and is being corrected.

## Verification

1. Every commit with hash and message.
2. Final `git status` clean.
3. Golden snapshot and full suite pass **on the committed tree**.
4. `docs/MATRIX_ROW_MAP.md` — counts 12 / 6 / 11 / 1; rows 19 and 23 RETURNED; row 22 the only
   DECISION REQUIRED.
5. No media, audio, `.env` or credential in anything these commits add.
6. `simulation/config.py` — the δ values are present, hashed, and the test proving no
   decision-making code reads them back still passes (G1).

**Do not push.** Report anything you could not do, plainly.
