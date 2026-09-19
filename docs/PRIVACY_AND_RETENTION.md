# Privacy and Retention

Row 30 of the §19 sign-off matrix (`docs/MATRIX_ROW_MAP.md`). Required by
`docs/preregistration/D0PA1_PreRegistration_Clarifications_v0.7.pdf` §17 ("Privacy and
retention — NEW... Added because it must be documented before recordings exist, not
after").

**§17 asks for six things**: the actual storage location, access control, retention
period, subject/session pseudonymisation scheme, raw video/audio retention rule, and
the feature-extraction-and-deletion rule where raw data is discarded. This document
states which of those six are implemented as code today, and which are policy
statements not yet decided — the two must not be blurred (this task's own instruction).

---

## ACTUAL IMPLEMENTED BEHAVIOUR

### Retention and deletion mechanism (`privacy/retention.py`)

- **Retention period and storage location are CONFIG parameters**, not literals —
  `RetentionConfig.retention_days` and `RetentionConfig.storage_location`, both hashed
  via `config_hash()` (the same short-SHA256-prefix pattern every other `*Config`
  class in this codebase uses), so whichever values actually governed a real deletion
  run are inspectable and reproducible from the hash alone.
- **A deletion routine exists** (`run_retention()`) that scans `storage_location` for
  files whose modification time is at or past `retention_days`, and — only when
  explicitly told to — removes them.
- **A deletion log is written**, one record per deleted file (`logs/deletion_log.jsonl`
  by default), carrying the file's path, basename, size, original mtime, age at
  deletion, a SHA256 of its content computed immediately before removal, the retention
  period that triggered the deletion, and the config hash. This is what makes "old data
  is deleted" a **verifiable** claim rather than an asserted one — a reader can check
  the log against what remains on disk.
- **Dry-run is the default, twice over**: `RetentionConfig.dry_run` defaults to `True`
  (a report of what *would* be deleted, with nothing removed and nothing written to
  the deletion log), and the CLI entry point (`python -m privacy.retention`) requires
  an explicit `--execute` flag on top of that before it will disable dry-run. A
  deletion tool whose default is to delete is a hazard — this one needs two separate,
  deliberate opt-ins before it deletes anything.
- **Two files are permanently excluded from the scan** regardless of age:
  `deletion_log.jsonl` (its own audit trail) and `variant_log.jsonl` (the one other
  committed exception in `logs/`, per Gate 0 A5). Retention governs raw/derived
  *session* data, not this repository's own provenance records that happen to share
  the same directory.
- **Verified, not assumed**: `tests/test_retention.py` (8 checks, all against a
  throwaway temp directory — never this repository's real `logs/`) confirms dry-run
  deletes nothing and writes no log, a real run deletes exactly the expired files and
  keeps the fresh ones, the deletion log records match what was actually removed, the
  never-delete basenames are never scanned, and a nonexistent `storage_location`
  returns an empty scan rather than raising. Separately, a real dry-run against this
  repository's actual `logs/` directory was performed as part of this task: 49 files
  scanned (`variant_log.jsonl` excluded), 0 expired under the placeholder 365-day
  period, 0 would be deleted — `logs/` was confirmed untouched (50 files, unchanged)
  before and after.

### What the placeholder default values are, and are not

`RetentionConfig`'s defaults (`retention_days=365.0`, `storage_location` = this
checkout's actual `logs/` path) exist so the mechanism above is testable end-to-end.
**Neither is a policy decision** — see the two open items below.

---

## DECIDED — `D0PA1_Client_SignOff_001.md` §5 (2026-09-18)

**This section supersedes, for RAW MEDIA specifically, the two "not yet implemented"
items that used to head this list.** The scope of the decision is precise and must not
be over-read: it decides raw video/audio retention and location. It does **not**
decide derived-feature logs' own retention or location — those remain exactly as
described further below, unaddressed, "no change" per the sign-off record's own §5.2.

- **Raw media retention period: 90 days, then automatic deletion.** `RAW_MEDIA_RETENTION_DAYS = 90.0`
  in `privacy/retention.py` — a named, separate constant, deliberately NOT a change to
  `RetentionConfig`'s own bare class-level default (`365.0`, unchanged, still the
  generic placeholder governing whatever `storage_location` a caller points it at).
  Applying 90 days silently to that default would misrepresent derived-logs retention
  as decided when the client's own record says the opposite. A caller retaining raw
  media constructs `RetentionConfig(retention_days=RAW_MEDIA_RETENTION_DAYS,
  storage_location=<resolved config>)` explicitly.
- **Raw media storage location: a defined folder outside `C:\Dopaland-POC`, per
  modality, via an environment variable — no committed literal, ever.** Video now has
  its own module, `privacy/video_storage_config.py`, mirroring
  `privacy/audio_storage_config.py`'s already-stricter pattern exactly:
  `D0PA1_VIDEO_RAW_STORAGE_LOCATION` read at call time, no default, raises loudly if
  unset. **The unified-raw-media-root proposal below is explicitly NOT what was
  decided** — the sign-off record's own §6 lists it as still open. Two independent,
  per-modality environment variables is the decided-and-implemented state; unifying
  them under one root remains a proposal, not applied.
- **Reason recorded in the sign-off record itself, not re-derived here:** a 90-day
  retention window means raw media exists for 90 days, and inside a git working tree
  a stray `git add -f` / `--no-verify` / unset `core.hooksPath` / fresh clone / GUI
  staging each bypass `.gitignore` and the pre-commit guard — under G4 a repository
  that has ever held such media is compromised permanently. Moving raw media outside
  the tree removes the only mechanism by which a 90-day window becomes an irreversible
  one; the guards remain a second layer, not the only one.

## NOT YET IMPLEMENTED (policy, not code)

- **Derived-feature logs' own retention period — separate from, and unaddressed by,
  the raw-media decision above.** No retention period has been proposed to or agreed
  with the client for `logs/` itself. `RetentionConfig`'s bare default of `365.0` days
  remains an engineering placeholder for testing the mechanism, not a recommendation.
  Whatever period is eventually decided is a config value the mechanism above already
  accepts — no code change is needed to apply it, only a decision.
- **Derived-feature logs' own storage location — separate from, and unaddressed by,
  the raw-media decision above; the client's own §5.2 says "no change."** Derived-
  feature logs currently sit inside this repository's working directory (`logs/`),
  untracked but physically present, and stay there — low risk, since they carry no
  imagery, only numeric values and anonymous participant codes. `RetentionConfig.storage_location`
  keeps the current path as its default for exactly this reason.
- **Access control.** No access-control mechanism (file permissions, encryption at
  rest, a controlled-access store) exists anywhere in this repository. This is
  unaddressed, not partially addressed.
- **Subject/session pseudonymisation scheme, as a documented policy.** The
  *mechanism* — anonymous `person_label`/`subject_id` codes, never a name, stamped on
  every record — is real and has existed since the POC (verified directly:
  `docs/PRIVACY_EVIDENCE.md` checked 15,619 real sample records and found `person_id`
  null in all of them, and 32 distinct `person_label` values, all anonymous codes).
  What does not exist is a *written pseudonymisation policy document* — the code
  behaviour and a stated policy are not the same artefact, and only the former exists.
- **Raw video/audio retention rule — the RULE is now decided (see "DECIDED" above,
  90 days, per-modality outside-repo location); nothing exists yet for it to
  GOVERN.** There is still no raw video or audio anywhere in this repository
  (verified by content-scan, not just extension — see `PROVENANCE.md` and
  `docs/PRIVACY_EVIDENCE.md`'s magic-byte scan). The rule is written and the config
  mechanism accepts it (`RAW_MEDIA_RETENTION_DAYS`, `privacy/video_storage_config.py`,
  `privacy/audio_storage_config.py`); applying it to a real raw-media collection is
  what remains, once the confirmatory study actually records any.
- **The feature-extraction-and-deletion rule connecting the two** ("if waveforms are
  discarded after feature extraction, document the transformation and the deletion
  rule so the claim is verifiable" — the client's own §17 wording). No raw-to-feature
  extraction pipeline with a documented, immediate raw-deletion step exists yet,
  because no raw video/audio collection exists yet either. The deletion-*logging*
  mechanism this task built is the verifiability half of that eventual rule; the
  extraction-and-immediate-deletion procedure itself is not yet designed.

## Named open item: raw media of BOTH kinds has no decided, documented home (Task 4, "ENVIRONMENT AUDIT, SYNC MEASUREMENT, G5 RIPPLE CHECK")

**Superseded for the LOCATION half, by `D0PA1_Client_SignOff_001.md` §5.2
(2026-09-18) — see "DECIDED" above.** Video now has its own module,
`privacy/video_storage_config.py`, matching audio's env-var-only,
raises-if-unset pattern exactly. The section immediately below is the
historical record of the gap as that earlier task found it (video on a
permissive `logs/`-default placeholder, audio on a strict env-var) — kept
for its own record, not rewritten, since the finding was real and the
reasoning for naming it as one gap still explains why the fix mirrors the
existing audio pattern rather than inventing a third. What it does NOT
supersede: the unified-single-root proposal below remains exactly as
proposed and unapplied — the client's own §6 leaves that specific question
open.

**Stated as one named gap, not two separate ones, because it is the same
unresolved decision showing up twice:**

- **Raw video** has never had a storage location decided anywhere in this
  repository's history. `RetentionConfig.storage_location`'s default
  (`logs/`, inside this checkout) is explicitly labelled above as a
  placeholder for testing the mechanism, not a decision — and the retention
  and deletion machinery therefore points, by default, at something
  unsettled: a directory inside the repository's own working tree, which is
  not the same thing as "outside the repository, access-controlled" (§17's
  own requirement).
- **Raw audio** was built this phase (`privacy/audio_storage_config.py`)
  with NO default at all — `resolve_audio_storage_config()` reads
  `D0PA1_AUDIO_RAW_STORAGE_LOCATION` from the environment and raises if
  unset, deliberately avoiding even a placeholder literal, given audio's
  elevated identifiability. This is stricter than the video pattern, but it
  is stricter in the sense of "refuses to guess," not in the sense of
  "resolves the question" — an unset environment variable is still an
  undecided location, just one that fails loudly instead of defaulting
  quietly.

**The result: two different placeholder patterns (a permissive default vs.
a hard-fail-if-unset), pointing at the same underlying unresolved fact —
this project has never decided where raw participant media actually
lives.** That is worth naming as one gap rather than leaving it implicit in
two separate modules' docstrings, because a future session extending either
mechanism could otherwise "fix" one without noticing the other was never
answered either.

### Proposed resolution — a pattern, not a decision

**Proposed, not implemented, not decided** — per this task's own
instruction, this is the client's and the user's decision to make, not
this repository's to resolve by writing code:

1. **One environment variable naming a raw-media root, outside the
   repository** (e.g. `D0PA1_RAW_MEDIA_ROOT`), resolved the same way
   `privacy/audio_storage_config.py` already does — no committed literal,
   no default, raises loudly if unset. This generalises the stricter
   pattern already built for audio to video as well, rather than leaving
   video on the older, more permissive placeholder.
2. **Modality subdirectories under that one root** (`video/`, `audio/`),
   so a single decision (where the root lives, who controls access to it)
   governs both media types, rather than two independently-configured
   locations that could silently drift apart (e.g. video staying inside
   the repo checkout while audio moves outside it, which is close to
   today's actual inconsistent state).
3. **`RetentionConfig.storage_location` would point at the resolved root**
   (or a per-modality subpath under it) once this is decided, replacing
   today's `logs/`-inside-the-checkout default — the retention/deletion
   *mechanism* in `privacy/retention.py` does not change; only which path
   it is configured to scan does.
4. **Why one root rather than two independently-named variables**: a
   single decision point is easier for the client to review and sign off
   once (§17's own ask — "must be documented before recordings exist"),
   and it structurally prevents the two modalities from silently ending up
   under different access-control regimes without that being a deliberate
   choice.

This proposal is not applied anywhere in code. `privacy/audio_storage_config.py`
keeps its own env var, and `privacy/video_storage_config.py` (added once the
client decided raw media's location and retention, §5.2) was built to
MIRROR that same per-modality pattern, not to implement this unification —
two independently-named variables is the decided-and-implemented state, not
the one root this section proposes. Unifying them under a shared root
variable, if that is the direction chosen, is future work contingent on
that separate decision, not assumed here.

## What must NOT be done with this document

Per G2/G3: do not read the `365.0`-day / current-`logs/`-path defaults above as
proposed answers and quietly start treating them as settled. Both are placeholders
whose only job is to make the mechanism testable. A future session updating this
document once real policy values are agreed should replace this section's language,
not just the numbers in `privacy/retention.py`.
