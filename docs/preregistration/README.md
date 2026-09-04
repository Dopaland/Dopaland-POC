# Pre-Registration Documents — README

## What is in this directory

- **`D0PA1_PreRegistration_Clarifications_v0.7.pdf`** — the client's document. From
  Gargi (DOPALAND) to Debanjan. The operational addendum to `D0PA1 POC Scope &
  Acceptance v0.5.1` (frozen), responding to the vendor's own earlier §16 Feasibility
  Classification. Contains the D1–D8 operational clarifications and the §19 sign-off
  matrix (30 rows, all marked `OPEN` in the client's own copy — this is the request,
  not a returned answer). **Committed unmodified**, byte-identical to the source copy
  — verified by SHA256 before committing.
- **`D0PA1_Build_Status_Report.docx`** — the vendor's document. From Debanjan to
  Gargi. A factual account of what existed in the repository as of 2026-08-26, with
  each of 11 earlier capability claims re-audited against code and marked
  VERIFIED/PARTIAL. **Committed unmodified**, byte-identical to the source copy.
- **`D0PA1_Section19_SignOff_Response.docx`** — **the vendor's real, substantive
  response to the §19 matrix.** From Debanjan to Gargi. Answers all 30 rows
  (27 `RETURNED`/`RETURNED · EVIDENCED`, 3 `DECISION REQUIRED`), with thresholds
  derived in nats against the multiclass-log-loss oriented utility `U`, the D6
  precision-simulation findings that motivated the metric change, and the reasoning
  behind every proposed value. **Committed unmodified**, byte-identical to the source
  copy — verified by SHA256 before committing.

## A prior mistake, corrected here

An earlier version of this directory contained a file named
`D0PA1_PreRegistration_SignOff_Response_DRAFT.md` — **an AI-agent-authored substitute**,
written in a previous session because no real response document could be found on this
machine at the time. That file has been **removed from this directory and from version
control** (see the commit that removes it). It was never a real response: it proposed
no numeric thresholds (by design, to avoid inventing business judgment calls) and
therefore could not have matched the real document's actual content — which uses a
different primary metric (log loss, not macro-F1) and derives real threshold values
from the precision simulation. Anyone who saw the earlier version should discard it and
use `D0PA1_Section19_SignOff_Response.docx` instead. This paragraph is the dated record
of that correction, not a silent removal.

## Dates each was prepared

- `D0PA1_PreRegistration_Clarifications_v0.7.pdf` — 2026-08-20 (file modification date
  on the source copy; the document's own text carries no separate authored date).
- `D0PA1_Build_Status_Report.docx` — 2026-08-26 (same basis).
- `D0PA1_Section19_SignOff_Response.docx` — supplied to this repository on 2026-09-04
  (the date it was placed on this machine and committed); the document's own content
  indicates it supersedes an earlier draft that used macro-F1 as the primary metric,
  itself prepared after the D6 precision simulation was run in three passes.

## What has been SENT to the client, stated honestly

**The Clarifications addendum has been sent — it originated from the client.** Whether
the Build Status Report and the §19 Sign-Off Response have been delivered to Gargi is
not something this repository or this session can independently confirm. **Stated
plainly, per this task's own instruction: the §19 Sign-Off Response has NOT been sent
to the client as of this commit.** A commit timestamp on any file in this directory
records when it existed here, in this form — it does not record, and must not be read
as recording, when (or whether) it was delivered to the client.

## Change control

Per the client's own §18: any substantive change to the prediction target, feature
definitions, baseline mapping, primary metric, any threshold, sample-size logic,
inclusion/exclusion rules, model family, or acceptance criterion — once genuinely
signed off — is made as a **dated commit**, never as a silent edit to a committed
document. `docs/preregistration/STATUS_REPORT_ERRATA.md` in this same directory is the
concrete example: the Build Status Report itself is not edited; superseded claims are
corrected by a dated erratum that names the module and commit that superseded each one.
The Sign-Off Response document itself already follows this discipline internally — its
own §5 records that an earlier draft's macro-F1-based thresholds were superseded by
log-loss-based ones once the precision simulation ran, and states why, rather than
silently presenting the revised numbers as if they were the first ones proposed.

## The build status report is a point-in-time snapshot

`D0PA1_Build_Status_Report.docx` describes the repository **as of 2026-08-26**. It
predates Gate 0 (provenance, config hashing, the data manifest, the variant log), the
canonical log schema, the MAD baseline, per-signal missingness/confidence, continuous
FPS logging, the coverage metric, all five controls, the reproduction command, and the
privacy/retention mechanism — all of which now exist. See
`docs/preregistration/STATUS_REPORT_ERRATA.md` for the itemised correction. The
original document is retained unedited specifically so this contrast is checkable, the
same discipline `docs/AUDIT_A_COLUMN.md` already applies to its own history.
