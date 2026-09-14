# Prompt for the Claude Code agent — the last two, and a full read

> Paste everything below the line as a single message.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. Guardrails G1–G5 bind this task.

**Two markdown files only**: `docs/MATRIX_ROW_MAP.md` and `docs/RESPONSE_VERIFICATION.md`.
No `.docx`, no `.py`, nothing else.

Both findings from your sweep were checked independently and both are real. One of them is a
contradiction sitting one paragraph below a correction you made in the previous task — because
that task was scoped to a single table row. That is the third time in this sequence that a
narrow scope has left a stale statement adjacent to a corrected one. The final instruction of
this task exists to end that pattern.

---

## Edit 1 — `docs/MATRIX_ROW_MAP.md`, the "Row 27 — RESOLVED" bullet

Replace this sentence:

```
One residual textual gap remains (§4.11's bullet list, unreworded) — noted in the row's own entry above and in `docs/RESPONSE_VERIFICATION.md` §5, but it does not affect the object store's actual, current state.
```

with:

```
The residual textual gap noted here previously (§4.11's bullet list, unreworded) has since been closed: that bullet now carries the same durable wording as §4.27, and the phrase "clean object store" occurs nowhere in the document. Nothing about this row remains open.
```

Leave the rest of the bullet — the reworded fsck claim and the live `git gc` confirmation —
exactly as it is.

## Edit 2 — `docs/RESPONSE_VERIFICATION.md`, the "Net:" paragraph

This paragraph now contradicts the §5 table row directly above it. Replace:

```
**Net: four of five findings fully corrected exactly as described; one (the fsck
claim) corrected in its primary location but with one residual unreworded mention
elsewhere in the same document, reported rather than silently accepted as complete.**
```

with:

```
**Net: five of five findings fully corrected. Four were correct as described at the time of this pass. The fifth (the fsck claim) was corrected in its primary location then, with one residual unreworded mention elsewhere in the same document — recorded here rather than silently accepted as complete, and closed in a later task; the §5 table row above carries the confirmation.**
```

Keep the sentences that follow — "No new issues were introduced by this revision…" and the
rest — unchanged.

---

## Then: read both files end to end

Not a grep. **Open and read `docs/MATRIX_ROW_MAP.md` and `docs/RESPONSE_VERIFICATION.md` in
full**, from first line to last, and check every statement asserting that something is open,
missing, unreworded, not yet done, contradictory, or awaiting a second pass, against what is
actually true in the repository today.

You already established in the previous sweep that these are genuinely still open, and they are
not in question: row 2's D2 disagreement, rows 5/10/25's classification boundary, row 22's
sensor swap, row 30's storage-location decision, §2's V_pd-figure completeness gap, §3.4's
boundary inconsistency. You do not need to re-litigate those.

What you are looking for is anything *else* — including in prose sections, summary paragraphs,
headers and footnotes, not only table cells, since both misses so far were outside the table
rows. **Report what you find. Do not edit any of it.**

If the read finds nothing further, **say so explicitly, and say that you read both files in
full rather than searched them.** A stated null result from a read that actually happened is
the deliverable here; silence is not.

---

## Verification

1. `git diff --stat` — exactly two markdown files.
2. Neither file asserts the §4.11 gap as open anywhere; every remaining mention is
   historical, describing wording that was corrected.
3. `docs/MATRIX_ROW_MAP.md`: counts still 12 / 6 / 9 / 3; row 27 still `EVIDENCED`; rows 19
   and 23 still `DECISION REQUIRED`. Diff all 30 status columns against
   `git show HEAD:docs/MATRIX_ROW_MAP.md` — zero differences.
4. Golden snapshot still
   `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`; full test suite passing.
5. `git status` — no media, audio, `.env` or credential anywhere (G4).

**Do not commit.** Report the diff, the verification output, and the result of the full read —
including a null result, stated as one.
