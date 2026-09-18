# Claude Code prompt — one heading fix, then commit

> Paste everything below the rule.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

Two parts: one small correction, then commit the working tree.

---

## Part 1 — CC-001-A's heading

In `docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`, the appendix heading
still describes "the outstanding sync measurement" while its body now records the item as
closed. The previous task's instruction said to keep the heading; that instruction was wrong
given the body was replaced wholesale.

Change the heading so it matches the body — the item is closed, not outstanding. Keep the
`CC-001-A` reference intact so cross-references from §6(a) and elsewhere still resolve.

**Then check both preregistration documents and `docs/MATRIX_ROW_MAP.md` for any other heading,
label, table caption or cross-reference that still describes the sync measurement as
outstanding, pending, or awaiting an attempt.** Body text has been corrected twice now;
headings and labels have not been swept. Fix any you find, and list them in your report.

**Nothing else changes.** No status, no count, no cost section.

---

## Part 2 — Commit the working tree

**Derive everything from the actual `git status` and `git diff`.** Do not trust any file list,
including the one below — it is orientation, not instruction.

### Before committing

1. **G4 first.** No media, audio, `.env`, credential or raw participant data staged or
   untracked anywhere. Check independently of the pre-commit hook.
2. Golden snapshot returns `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`.
3. `tests/test_feature_separation.py` — all checks pass.
4. Full test suite passing.

**If any fail, stop and report. Do not commit.**

### Commit structure

Logical commits, not one blob. Match the existing history's message style. Roughly what the
tree should contain:

| Commit | Contents |
|---|---|
| A/V sync: diagnostic mode, reference-edge fix, post-stimulus diagnostic max | `av_sync_flash.py` and `tests/test_av_sync_flash.py` — attempts 8 and 9 |
| Record soak closure and sync disposition | `docs/CLIENT_FIGURES.md`, `docs/PROJECT_STATE.md` |
| CC-001: record A/V sync as a documented omission | the CC-001 draft and `docs/MATRIX_ROW_MAP.md` row 23 |
| Add process prompt records | the `docs/CLAUDE_CODE_PROMPT_*.md` and runsheet files |

Each message says **what changed and why.**

### One thing to handle

`docs/PROJECT_STATE.md` carries a section labelled **"NOT YET COMMITTED."** That stops being
true the moment you commit. Once the commits exist, update it to reference the real hashes and
fold it into the document's HEAD-pointer chain, then add a follow-up commit for that change.

The same gap was flagged and fixed once before; it recurs because the label can only be
corrected after the commit it describes exists.

---

## Verification

1. Report every commit with its hash and message.
2. Final `git status` clean.
3. Golden snapshot and full suite still pass **on the committed tree**.
4. `docs/MATRIX_ROW_MAP.md` — 30 row statuses unchanged against the pre-task state; counts
   still 12 / 6 / 9 / 3.
5. CC-001's cost and schedule section (§8) still empty and untouched.
6. No media, audio, `.env` or credential anywhere in history added by these commits.

**Do not push** — there is no remote, and adding one is not part of this task.

Report plainly anything you could not do or judged differently.
