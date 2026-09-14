# Prompt for the Claude Code agent — close the last two stale statements

> Paste everything below the line as a single message.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. Guardrails G1–G5 bind this task.

This task edits **two markdown files only**: `docs/MATRIX_ROW_MAP.md` and
`docs/RESPONSE_VERIFICATION.md`. Do not touch any `.docx`, any `.py`, or any other file.

You reported in the previous task that row 27's "residual gap" sentence looked stale. **You
were right, and it has been verified independently by reading `word/document.xml` directly.**
§4.11's bullet in `D0PA1_Section19_SignOff_Response.docx` now reads:

> `Version control established, pre-commit guards in place; no media file or credential has
> ever entered this history — the durable, checkable claim. See §4.27.`

The phrase `clean object store` does not occur anywhere in that document. The gap both files
describe is closed, and two tracking documents still assert it is open.

Same principle as the previous task: **a status is the client's to confirm; a factual statement
has to be true regardless.** These are factual statements about a document's contents, and
they are false.

---

## Edit 1 — `docs/MATRIX_ROW_MAP.md`, row 27 rationale

Find and replace this sentence inside row 27's rationale cell:

```
One residual gap: §4.11's own bullet list still reads the old unqualified "clean object store" — not reworded to match §4.27 (see `docs/RESPONSE_VERIFICATION.md` §5).
```

with:

```
That residual gap is now closed: §4.11's bullet was subsequently reworded to match §4.27 and today reads "no media file or credential has ever entered this history — the durable, checkable claim. See §4.27." The phrase "clean object store" no longer occurs anywhere in the document — verified by reading `word/document.xml` directly, not via `Document.paragraphs` (see `docs/PROJECT_STATE.md` §4).
```

Leave the rest of row 27 untouched — including its closing "Still not done: a tagged frozen
release; genuine held-out-data storage separation", both of which remain true. **Row 27's
status stays EVIDENCED and the counts stay 12 / 6 / 9 / 3.**

## Edit 2 — `docs/RESPONSE_VERIFICATION.md` §5

In §5's table, the row whose finding column is `§3.2, fsck claim` currently carries the verdict
`CONFIRMED in §4.27, NOT fully carried through to §4.11`, followed by an explanation that
§4.11's bullet "still contains the unreworded phrase" and that it is "worth a second pass
before sending."

Replace that verdict and its explanation with:

```
**CONFIRMED in both sections.** §4.27 carries the durable claim as described. §4.11's bullet, recorded here at the time as still carrying the unreworded "clean object store", was corrected in a later task and now reads "no media file or credential has ever entered this history — the durable, checkable claim. See §4.27." Re-checked by reading `word/document.xml` directly: the phrase "clean object store" occurs nowhere in the document. The second pass this row called for was performed, and the finding is closed.
```

Keep the rest of the row — the finding name and the quoted §4.27 text — as it is. This is an
amendment to a dated verification record, not a rewrite of it: the original observation was
true when made, so the correction states that it was later addressed rather than deleting the
history of it.

---

## Verification

1. `git diff --stat` — **exactly two markdown files**. No `.docx`, no `.py`, nothing else.
2. `clean object store` — confirm it now appears in neither markdown file except where quoted
   as the historical wording being described.
3. `docs/MATRIX_ROW_MAP.md`: row 27 status still `EVIDENCED`; counts still 12 / 6 / 9 / 3;
   rows 19 and 23 still `DECISION REQUIRED` with the rationale text from the previous task
   intact.
4. Diff every row's status column against `git show HEAD:docs/MATRIX_ROW_MAP.md` and confirm
   no status changed in this task.
5. Golden snapshot still
   `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`; full test suite passing.
6. `git status` — no media, audio, `.env` or credential anywhere in the tree (G4).

**Do not commit.** Report the diff and the verification output.

**One closing instruction.** Both this task and the last began with you spotting a stale
statement in passing. Before you report back, run one deliberate sweep of
`docs/MATRIX_ROW_MAP.md` and `docs/RESPONSE_VERIFICATION.md` for any *other* cell asserting a
gap, defect or omission that a later task has since closed. **Report what you find. Do not
edit any of it.** If the sweep finds nothing, say so explicitly — a stated "nothing found" from
a sweep that actually ran is worth having, and is different from silence.
