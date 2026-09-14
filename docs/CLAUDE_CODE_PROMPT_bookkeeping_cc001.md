# Prompt for the Claude Code agent — bookkeeping, then CC-001 registration

> Paste everything below the line as a single message.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. Guardrails G1–G5 bind this task.

This task is **markdown only.** Do not touch any `.docx`, and do not touch any `.py`. The two
preregistration documents were corrected in the previous two tasks and are now clean; this
task records that fact in the engineering documents and registers the audio change-control
record. Two parts, in order.

---

# PART 1 — Bookkeeping

## 1.1 `docs/CLIENT_FIGURES.md` §10 — amend correction entry #8, do **not** add an eleventh

Entry #8 is the pitch claim (`≈0.1°`, "structural", "unfixable"). Its recorded reach is
incomplete. Amend that entry to state what was actually found across the two correction passes
that followed:

- The claim did not live only in `CLAUDE.md`, `stage1_step4_vectors.py` and `PROJECT_STATE.md`.
  It also lived in **`D0PA1_Section19_SignOff_Response.docx` §4.14** and in
  **`D0PA1_Build_Status_Report.docx` §5.4** — both client-facing, both unsent.
- In the Build Status Report the **section heading itself** asserted it
  ("Attention pitch detection is structurally unreliable"), so the claim was not merely present
  in body text but was the section's title.
- It survived a dedicated correction pass because both instances sit **inside `w:tbl`
  elements**, and the audit method used (`python-docx`'s `Document.paragraphs`) enumerates
  body-level paragraphs only. The first retry reported the text as absent from the repository
  entirely — a false negative produced by the tool, not by the text being missing.
- Both documents are now corrected. No instance of the retracted figure or mechanism survives
  in either, outside the sentences that explicitly retract them.

**Do not increment the corrections count to eleven.** This is the same claim, entry #8, with
its true reach now documented — not a new false claim. §10's own opening paragraph is about an
arithmetic mismatch in a count; inflating that count here would repeat the error it exists to
record. If you believe a separate entry is warranted, **say so in your report and leave the
count alone** — that judgment is the methodology owner's, not yours.

Also update §10's closing paragraph (the one ending "...what moved, twice, is the reason
claimed for it") to note that the downstream documents named there — the sign-off response
§4.14 pre-declaration and `CLAUDE.md`'s screen-orientation section — now carry the corrected
reasoning, and that the D8 elevated-risk pre-declaration **stands**, on the revised premise:
detection-rate collapse during look-down (0.08%–27.5%) making `oriented_rate ≈ 1.0` a
missingness artefact, rather than the retracted claim that pitch cannot register at all.

## 1.2 `docs/PROJECT_STATE.md` — record this phase

Add a subsection under §1 (or wherever this document records completed phases) covering:

- Both preregistration `.docx` files are now free of the retracted pitch claim. Specific
  locations corrected: sign-off response §4.14 (two paragraphs replaced with four, one
  redundant paragraph subsequently removed) and Build Status Report §5.4 (heading plus two
  paragraphs replaced with three).
- Two internal contradictions were also fixed in the sign-off response's closing section:
  "Eight rows" → "Six rows" (verified against `docs/MATRIX_ROW_MAP.md`: rows 3, 4, 9, 15, 18,
  30), and the stale clause "the null-input control has no camera run" removed, which had
  contradicted that document's own §4.16 and §6.
- `docs/MATRIX_ROW_MAP.md` row 14's citation of §4.14 was checked and is **correct** — it was
  briefly suspected of being wrong as a consequence of the same false negative, and was not
  changed.

## 1.3 `docs/PROJECT_STATE.md` §4 — add a documented methodological hazard

Section 4 is "What a future session must NOT do". Add an entry, because this one cost two
rounds and produced a confident false negative about a client-facing document:

> **Never audit a `.docx` in this repository using `python-docx`'s `Document.paragraphs`
> alone.** It enumerates body-level paragraphs only and silently excludes every paragraph
> inside a table cell. Substantial parts of both preregistration documents live inside
> `w:tbl` elements. Any search, audit or verification of these documents must enumerate every
> `<w:p>` in `word/document.xml` regardless of ancestry — and a verification pass must not use
> the same method as the edit pass, or it inherits the same blind spot. A clean result from a
> method that cannot see half the document is not a clean result.

Also note there that a substring search for an exact phrase is insufficient: the Build Status
Report said "not fixable **with** a single webcam" where the sign-off response said "**within**",
and only a multi-term search caught it.

## 1.4 `CLAUDE.md` — one addition

In the "Attention / screen-orientation" section that already carries the retraction, add a
short note that **both client-facing preregistration documents now carry the corrected
wording**, so a future session does not re-open the question of whether they were updated.
Change nothing else in that section; its retraction text is already correct.

---

# PART 2 — Register CC-001 (the audio change-control record)

A draft change-control record now exists at
`docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`. It is **DRAFT, PROPOSED,
NOT IN FORCE** — unreviewed by the vendor, unsigned by the client, and its §8 cost-and-schedule
impact is deliberately blank pending a human. Register its existence; do not advance its status.

## 2.1 `docs/AUDIO_ACQUISITION.md` §6 — update the stale sentence

§6 currently states that the change-control process "has not yet run" and that the
change-control record "is a separate, not-yet-done step." The second half is now stale.
Update it to say that a draft record exists at the path above, that it is proposed and not in
force, that its cost-and-schedule impact section is intentionally unfilled pending the vendor,
and that the client's §18 process has still not run. **Keep the existing distinction intact** —
that document is the engineering record of what the decision produced, and is still not the
change-control record itself.

## 2.2 `docs/PROJECT_STATE.md` "Needs a client decision" — add CC-001

Add it as a named pending item: the §18 change control for audio retention, drafted and
awaiting vendor review, a cost figure, and Gargi's signature. Note its blocking consequence
plainly — **retention does not lift §10.9 until the clock-synchronisation measurement exists**,
so `Δ_audio` is not yet computable regardless of what was built.

## 2.3 Do **not** apply the matrix reclassification

The draft proposes moving §19 row 19 (modality ablation) and row 23 (audio acquisition) off
DECISION REQUIRED, changing the counts to 12 / 6 / 11 / 1. **That is a proposal requiring the
client's confirmation. Do not apply it to `docs/MATRIX_ROW_MAP.md` or anywhere else.** Rows 19
and 23 stay exactly as they are. If you want to note that a reclassification is proposed and
pending, do so as a clearly-marked pending note that does not change any row's status — the
vendor proposes, the client signs, and code does not decide what a status means (G1).

---

## Verification

1. `git diff --stat` — only markdown files changed. **Zero `.docx` and zero `.py` in the diff.**
2. `docs/MATRIX_ROW_MAP.md` — rows 19 and 23 still read DECISION REQUIRED; the four counts are
   still 12 / 6 / 9 / 3; row 14 unchanged.
3. `docs/CLIENT_FIGURES.md` §10 — the corrections count is still ten.
4. Golden snapshot still
   `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`; full test suite passing.
   Markdown edits cannot move either, so any change means something else did.
5. `git status` — no media, audio, `.env` or credential anywhere in the tree (G4).

**Do not commit.** Report the diffs, the verification output, and — plainly, without
substituting an approach — anything you could not do or judged differently.
