# Prompt for the Claude Code agent — correct two false rationale statements in the matrix map

> Paste everything below the line as a single message.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. Guardrails G1–G5 bind this task.

This task edits **one file only: `docs/MATRIX_ROW_MAP.md`.** Do not touch any `.docx`, any
`.py`, or any other markdown file.

A previous task instructed you not to touch this file at all. That instruction was too broad,
and this task narrows it. The reasoning matters, so apply it rather than just the edit:

> **A row's STATUS is the client's to confirm. A row's factual RATIONALE has to be true
> regardless.** "Awaiting sign-off" does not license a false statement sitting in the repo's
> own tracking document. Two rationale cells currently assert things that stopped being true
> when the client retained Δ_audio and acquisition was built.

**No status changes in this task. No count changes. Rows 19 and 23 both stay
DECISION REQUIRED, and the four counts stay 12 / 6 / 9 / 3.**

---

## Edit 1 — row 23, rationale cell

Currently reads: `No microphone/capture/clock-sync exists (Decision A).`

This is false. A microphone module, a capture thread, per-chunk integrity logging, independent
consent and env-var-only storage config all exist (`audio_acquisition.py`,
`stage1_step7_consent.py`, `privacy/audio_storage_config.py`; see `docs/AUDIO_ACQUISITION.md`).
Only the clock-synchronisation method is genuinely absent.

Replace the rationale cell with:

```
Client decision made — Δ_audio RETAINED, acquisition authorised. Acquisition is built and has been exercised against a real microphone: capture thread, per-chunk integrity logging, independent consent (architecturally unreachable when declined), env-var-only storage config, privacy guard and separation guard both extended (`audio_acquisition.py`; `docs/AUDIO_ACQUISITION.md`). **No clock-synchronisation method between audio and video exists** — five measurement attempts across two sessions failed on the video side, so no offset, spread or drift figure exists. §4.23's own retention condition is therefore unmet and Δ_audio is not yet computable. No audio FEATURE exists or is planned; `features/audio.py` remains an empty stub. Status held at DECISION REQUIRED: a reclassification to RETURNED (conditional) is proposed in CC-001 (`docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`) and awaits the client's confirmation.
```

## Edit 2 — row 19, rationale cell

Currently reads: `Contingent on the audio keep/remove decision (Decision A in the response).`

The contingency is discharged — the decision was made. Replace with:

```
Contingency on Decision A is discharged — the client retained Δ_audio. δ_audio = 0.05 proposed on the same reasoning as the other components, to be revisited once acquisition quality is known, since an unmeasured modality's achievable contribution cannot be sensibly bounded in advance. Note the dependency: the ablation cannot be run until the clock-synchronisation measurement exists (see row 23). Status held at DECISION REQUIRED: a reclassification to RETURNED is proposed in CC-001 and awaits the client's confirmation.
```

## Edit 3 — a note near the file's existing status/count note

This file already carries a note recording that 12 / 6 / 9 / 3 is current. Add alongside it,
without altering the existing counts:

```
**Audio decision recorded (not yet reflected in any status).** The client's keep-or-formally-remove decision on Δ_audio has been made — RETAINED, acquisition authorised — reversing the sign-off response's own §4.23 recommendation. This is a substantive scope change against frozen Scope v0.5.1 and is drafted for the client's §18 change control as CC-001 (`docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`), which is PROPOSED and NOT IN FORCE. CC-001 proposes moving rows 19 and 23 off DECISION REQUIRED, which would make the counts 12 / 6 / 11 / 1. **That reclassification is NOT applied here and must not be applied until the client confirms it.** The counts above remain 12 / 6 / 9 / 3, and rows 19 and 23 remain DECISION REQUIRED. Their rationale text has been corrected to state what is factually true as of the audio acquisition build; correcting a false statement is not a status change.
```

---

## Verification

1. `git diff --stat` — **`docs/MATRIX_ROW_MAP.md` and nothing else.**
2. Rows 19 and 23: status column still reads `DECISION REQUIRED` in both; the
   response-status column (`BLOCKED-ON-CLIENT-DECISION`) unchanged in both.
3. No other row's status changed — diff every row's status column against `git show
   HEAD:docs/MATRIX_ROW_MAP.md` and confirm only the two rationale cells and the added note
   differ.
4. Counts: 12 EVIDENCED / 6 BUILT-NOT-RUN / 9 RETURNED / 3 DECISION REQUIRED still stated,
   and still the true tally of the table's own status column.
5. The phrase `No microphone/capture/clock-sync exists` no longer appears in the file.
6. Golden snapshot still
   `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`; full test suite passing.
7. `git status` — no media, audio, `.env` or credential anywhere in the tree (G4).

**Do not commit.** Report the diff, the verification output, and — plainly, without
substituting an approach — anything you could not do or judged differently. In particular, if
you find any *other* rationale cell in this file asserting something that is no longer true,
**report it and do not edit it**; scope creep in a client-tracking document is its own hazard.
