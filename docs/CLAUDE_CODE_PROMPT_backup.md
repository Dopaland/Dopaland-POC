# Claude Code prompt — get the work off this machine

> Paste everything below the rule. **Do this before the laptop is returned.**

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

**Context: this machine is rented and is being returned.** There is no git remote — every
commit made in this project exists only on this disk. Several things of value are deliberately
gitignored or deliberately outside the repository, which means they are outside any backup too.

The goal is a verified, portable copy of everything that matters, and an honest inventory of
what still needs moving by hand.

---

## Step 1 — commit first

Anything uncommitted is not in a bundle. Commit the working tree — the aperture export, its
tests, and the prompt files under `docs/`.

Same discipline as before: G4 check, golden snapshot
`f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`, feature separation, full
suite. Logical commits, not one blob. **Stop and report if any check fails.**

## Step 2 — bundle the entire history

```
git bundle create dopaland-poc-<YYYYMMDD>.bundle --all
```

Write it **outside the repository** — the rented machine's Desktop is fine; it is going to be
copied off and then deleted with the machine anyway.

`--all` matters: every branch, every tag, the complete history. Not just HEAD.

## Step 3 — verify the bundle actually restores

**An unverified backup is not a backup.** Do both:

1. `git bundle verify <file>` — prerequisites and completeness.
2. **Clone from it into a temporary directory**, then confirm the restored clone's HEAD commit
   hash matches this repository's HEAD, and that its commit count matches. Report both numbers.

If the clone does not reproduce the same HEAD, **stop and report** — do not report success.

## Step 4 — inventory what the bundle does NOT contain

Git-ignored or out-of-tree material that would be lost. For each, report **path, size, and
whether it is recoverable from elsewhere**:

- **`logs/`** — the soak checkpoints, all nine A/V sync sessions, `orientation_trials.jsonl`,
  the null-input and empty-scene runs. **Every real measurement this project has produced.**
  The documents cite these; without them the claims have no underlying data. **Not recoverable.**
- **`models/`** — the MediaPipe `.task` bundles. Large, and **re-downloadable**, so low priority.
- **`reproduction_output/`, `artefacts/`** — check what is there and whether it is regenerable.
- **Any raw media anywhere on this machine** — see Step 6.
- **Frozen rule files kept outside the repository** by convention —
  `GATE2_SCORING_RULE.md`, `ORIENTATION_SCORING_RULE.md`, the soak runsheet and rule v3, the
  Downloads copy of the client sign-off. Search the likely locations and report what you find
  with paths. **Do not move them into the repository** — that convention is deliberate.

## Step 5 — stage everything for one copy operation

Put the bundle and copies of the not-in-git material into **one folder on the Desktop**, so the
human copies a single directory to a drive rather than hunting for pieces.

Write a `MANIFEST.txt` in that folder listing every item, its size, its original path, and one
line on why it matters. A future reader restoring this needs to know what they are looking at.

**Do not include raw media in that folder** — see Step 6.

## Step 6 — raw media, before the machine goes back

Rented hardware returning to a vendor is exactly the case the retention policy exists for.

- Search this machine for any video or audio recordings produced by this project.
- **Report what you find. Do not delete anything yet** — the human decides, and the deletion
  routine writes a verifiable deletion log, which is the point.
- If nothing exists, say so plainly; that is the expected and best answer.

---

## Report

- The commits made in Step 1, with hashes.
- The bundle's path and size.
- **Step 3's verification: the restored clone's HEAD hash and commit count, against this
  repository's.**
- The Step 4 inventory, with sizes, marking each recoverable or not.
- The staging folder path and its total size.
- What raw media exists, if any.

**Do not push** — there is still no remote. **Do not delete anything.**
