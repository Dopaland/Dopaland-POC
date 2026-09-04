# Pre-Registration Documents — README

## What is in this directory

- **`D0PA1_PreRegistration_Clarifications_v0.7.pdf`** — the client's document. From
  Gargi (DOPALAND) to Debanjan. The operational addendum to `D0PA1 POC Scope &
  Acceptance v0.5.1` (frozen), responding to the vendor's own earlier §16 Feasibility
  Classification. Contains the D1–D8 operational clarifications and the §19 sign-off
  matrix (30 rows, all marked `OPEN` in the client's own copy — nothing has been
  returned against it yet). **Committed unmodified**, byte-identical to the copy in
  `C:\Users\Abcom\Downloads\` at the time of this commit — verified by SHA256 before
  committing.
- **`D0PA1_Build_Status_Report.docx`** — the vendor's document. From Debanjan to
  Gargi. A factual account of what existed in the repository as of 2026-08-26,
  written as a companion to a sign-off response, with each of 11 earlier capability
  claims re-audited against code and marked VERIFIED/PARTIAL. **Committed unmodified**,
  byte-identical to the source copy — verified by SHA256 before committing.
- **`D0PA1_PreRegistration_SignOff_Response_DRAFT.md`** — **NOT a document prepared
  for the client.** See "What has NOT been sent" below.

## Dates each was prepared

- `D0PA1_PreRegistration_Clarifications_v0.7.pdf` — 2026-08-20 (file modification
  date on the source copy; the document's own text carries no separate authored date).
- `D0PA1_Build_Status_Report.docx` — 2026-08-26 (same basis).
- `D0PA1_PreRegistration_SignOff_Response_DRAFT.md` — drafted in this session,
  2026-09-04. Not a "prepared for the client" date in the same sense as the other two —
  see below.

## What has been SENT to the client, stated honestly

**The Build Status Report and the Clarifications addendum are the only two documents
in this set known to have already changed hands** (the addendum from Gargi to
Debanjan; the status report was written as a companion to a response — implying a
response was sent or was about to be — but no copy of that response could be found
anywhere on this machine when this session searched for it).

**The sign-off response draft in this directory has NOT been sent to anyone, and was
NOT prepared for the client in the sense the other two documents were.** It was
drafted in this coding session, against the repository's factual state, at the
explicit direction of the person running this session, specifically because no such
document existed anywhere to commit. It requires human review — adding the business/
scientific judgment calls (δ thresholds, retention period, protocol design decisions)
this draft deliberately left as `OPEN` — before it is fit to send. **A commit timestamp
on this file records when it existed in this repository, in this form. It does not
record, and must not be read as recording, when a response was delivered to the
client** — because, as of this commit, none has been.

## Change control

Per the client's own §18: any substantive change to the prediction target, feature
definitions, baseline mapping, primary metric, any threshold, sample-size logic,
inclusion/exclusion rules, model family, or acceptance criterion — once genuinely
signed off — is made as a **dated commit**, never as a silent edit to a committed
document. `docs/STATUS_REPORT_ERRATA.md` in this same directory is the concrete
example: the Build Status Report itself is not edited; superseded claims are corrected
by a dated erratum that names the module and commit that superseded each one.

## The build status report is a point-in-time snapshot

`D0PA1_Build_Status_Report.docx` describes the repository **as of 2026-08-26**. It
predates Gate 0 (provenance, config hashing, the data manifest, the variant log), the
canonical log schema, the MAD baseline, per-signal missingness/confidence, continuous
FPS logging, the coverage metric, all five controls, and the reproduction command —
all of which now exist. See `docs/STATUS_REPORT_ERRATA.md` for the itemised
correction. The original document is retained unedited specifically so this contrast
is checkable, the same discipline `docs/AUDIT_A_COLUMN.md` already applies to its own
history.
