# Claude Code prompt — commit the working tree

> Paste everything below the line.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. Guardrails G1–G5 bind this task.

Several tasks' worth of work is sitting uncommitted. This task commits it. **Derive everything
from the actual `git status` and `git diff` — do not trust any list of files given to you,
including any you may find in the documents here.** Some commits have already landed
(`d9f00d6` is current HEAD as of the last soak); the tree state is whatever it actually is now.

## Before committing anything

1. **G4 check first.** Confirm no media file, audio file, `.env`, credential or raw participant
   data is staged or untracked anywhere in the tree. `.githooks/pre-commit` should catch it, but
   check independently — git history is permanent and a repo that has ever held face or audio
   data is compromised for life.
2. Golden snapshot: `tests/test_refactor_snapshot.py` must return
   `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`.
3. `tests/test_feature_separation.py` — all checks pass.
4. Full test suite passing.

**If any of these fail, stop and report. Do not commit.**

## Commit structure

**Group by logical change, not one giant commit.** The client will inspect this history, and a
single "various fixes" commit destroys exactly the inspectability this engagement's credibility
rests on. Match the existing history's message style — read several recent commits first.

Suggested grouping, adjust to what the tree actually contains:

| Commit | Contents |
|---|---|
| Retract the pitch claim | The two docstring replacements and both `.docx` §4.14 / §5.4 corrections — one logical change: correction #8 retired everywhere it lived |
| Fix sign-off response internal contradictions | "Eight rows" → "Six rows"; removal of the stale null-input clause |
| Add A/V sync measurement instrument | `av_sync_flash.py` and `tests/test_av_sync_flash.py` |
| Add soak checkpoint logging | The `stage3_demo_ui.py` additive change |
| Bookkeeping | `CLIENT_FIGURES.md`, `PROJECT_STATE.md`, `CLAUDE.md`, `AUDIO_ACQUISITION.md`, `MATRIX_ROW_MAP.md`, `RESPONSE_VERIFICATION.md` |
| Add change-control records and closure documents | CC-001 and CC-002 drafts, the closure pack, the process prompts under `docs/` |

Each message states **what changed and why**, not just what files moved.

## Two things to handle while you're in there

**1. `docs/PROJECT_STATE.md` has a subsection labelled "not yet committed."** That label stops
being true the moment you commit. Once the commits exist, update that subsection to reference
the actual commit hashes and fold it into the document's HEAD-pointer chain, then amend or add
a follow-up commit for that change. This was flagged as a known gap in an earlier task.

**2. `SOAK_OPERATOR_RUNSHEET.md` at the repo root is superseded** — it was replaced by a merged
runsheet that lives outside the repo. If it is still present, delete it rather than committing
it; two copies of a procedure is how they drift apart. If it is already gone, say so.

## The prompt files under `docs/`

Several `CLAUDE_CODE_PROMPT_*.md` files are in `docs/`. **Commit them.** They are the record of
exactly what instruction produced each correction, and this engagement's value rests on the
client being able to inspect how the work was done, not only its result.

## After committing

Report: the commits you made with their hashes and messages, the final `git status`, and
confirmation that the golden snapshot and full suite still pass on the committed tree.

**Do not push.** There is no remote configured, and adding one is not part of this task.

Report plainly anything you could not do, or judged differently. Do not substitute an approach.
