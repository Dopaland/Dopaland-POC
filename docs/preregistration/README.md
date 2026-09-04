# Pre-Registration Documents — README

## What is in this directory, and the current version of each

- **`D0PA1_PreRegistration_Clarifications_v0.7.pdf`** — the client's document. From
  Gargi (DOPALAND) to Debanjan. The operational addendum to `D0PA1 POC Scope &
  Acceptance v0.5.1` (frozen). Contains the D1–D8 operational clarifications and the
  §19 sign-off matrix (30 rows, all marked `OPEN` in the client's own copy — this is
  the request, not a returned answer). Unchanged since it first entered this
  repository. **Committed unmodified**, byte-identical to its source copy — verified
  by SHA256 before committing.
- **`D0PA1_Build_Status_Report.docx`** — the vendor's document. From Debanjan to
  Gargi. **Current version**, superseding one committed earlier in this repository's
  history. Describes the repository as of the date it was prepared, with each of 11
  earlier capability claims re-audited against code (9 VERIFIED, 2 PARTIAL), plus a
  three-way built/exercised · built-not-run-on-real-data · not-built breakdown of the
  D0PA1 infrastructure. **Committed unmodified**, byte-identical to its source copy.
- **`D0PA1_Section19_SignOff_Response.docx`** — the vendor's document. From Debanjan
  to Gargi. **Current version**, superseding two earlier versions committed in this
  repository's history. Answers all 30 §19 rows using four statuses (`RETURNED ·
  EVIDENCED`, `RETURNED · BUILT, NOT YET RUN ON REAL DATA`, `RETURNED`,
  `DECISION REQUIRED`), with thresholds derived in nats against the multiclass-log-loss
  oriented utility `U`, the D6 precision-simulation findings that motivated the metric
  change, and per-row "Implementation status" sections stating what has actually been
  built and tested. §4's own table now counts **11 EVIDENCED, 7 BUILT-NOT-YET-RUN, 9
  RETURNED, 3 DECISION REQUIRED** — independently recounted against the committed
  document, not taken on the document's own word (`docs/RESPONSE_VERIFICATION.md`'s
  2026-09-04 addendum). **Committed unmodified**, byte-identical to its source copy.

## The sequence — three revisions of the sign-off response exist in git history, none was ever sent

This is the **third** committed version of the sign-off response (the build status
report has had two). All earlier versions exist in git history (see `git log --
docs/preregistration/`) and **none was ever sent to the client** — this is a sequence
of draft revisions, not amendments to a delivered record, though the sequence is
recorded here so it stays legible to a later reader:

1. An **agent-authored substitute** for the sign-off response was committed first, in
   a session where no real document could be located on this machine. It proposed no
   thresholds and used no real metric — it was never a real response. Removed from
   version control entirely once the real document was found (see that commit's
   message for the full account).
2. The **first real versions** of both documents were committed next — a sign-off
   response using macro-F1 as the primary metric with thresholds in macro-F1 points,
   and a build status report describing the repository as of 2026-08-26 (predating
   most of the D0PA1 infrastructure now built). `STATUS_REPORT_ERRATA.md` was added
   alongside them to correct that build status report's now-superseded "not built"
   claims by dated erratum, per §18 change control, rather than editing the document.
3. **These current versions** (this commit) replace both. What changed and why:
   - **The primary metric moved from macro-F1 to negative multiclass log loss**,
     decided before sign-off after the D6 precision simulation (run in three passes)
     showed log loss gives materially better decidability (~2.1× on average, across
     every grid cell and effect size tested) and a roughly threefold-smaller
     across-seed spread in bootstrap half-width.
   - **Every threshold was re-derived in nats** from the information structure of the
     problem (the context-only baseline's own information gain over chance), not
     converted from the earlier macro-F1 values — the empirical ratio between the two
     metrics is not even constant across effect sizes, so a conversion would have been
     unsound as well as impermissible.
   - **Implementation statuses were updated** to reflect what has since been built:
     the response now distinguishes `RETURNED · EVIDENCED` (defined and built and
     exercised) from `RETURNED · BUILT, NOT YET RUN ON REAL DATA` (defined and built,
     synthetic-only) — a distinction the first real version did not make explicitly at
     the row-status level.
   - Because the build status report is now current and the errata document existed
     specifically to correct a since-superseded snapshot, **`STATUS_REPORT_ERRATA.md`
     is now obsolete and has been removed from version control** as part of this
     commit. It is not silently gone: this paragraph is the dated record that it
     existed, what it was for (correcting §6 of the 2026-08-26 build status report's
     "not built" table by dated erratum rather than editing the original), and why it
     no longer applies (that report has itself been rebuilt to be accurate, and — like
     every version before it — was never sent to the client, so there is no delivered
     record left for an erratum to correct against).
4. **This commit** replaces the sign-off response again, correcting five issues an
   independent verification pass found (`docs/RESPONSE_VERIFICATION.md`, 2026-09-04):
   the feature-separation test is now described as four checks (it runs four, the
   prior version said three), each stated as demonstrated failing before being relied
   on; the internal contradiction about the harness acceptance check is resolved (§2
   no longer asserts a status, §4.2 states plainly that the check has not been carried
   out); the §4.27 object-store claim is reworded from an unqualified "returns clean"
   (a claim any ordinary commit can invalidate) to the durable, checkable one — pruned
   after hook verification, a dangling object from routine commit activity is not
   evidence of anything, no media or credential has ever entered this history; the §6
   summary count is corrected from five to eleven `EVIDENCED` rows, matching §4's own
   table; and row 21 (synthetic latent recovery) is reclassified from `BUILT, NOT YET
   RUN ON REAL DATA` to `EVIDENCED`, accepting that its deliverable is a synthetic
   study by design, so "never run on real data" was the wrong bar — the same reasoning
   already applied to row 13. All five corrections were independently re-verified as
   actually present in the committed document, not assumed from the request that asked
   for them — see `docs/RESPONSE_VERIFICATION.md`'s dated addendum for the checks and
   one residual gap found (a `§4.11` bullet still reads "clean object store"
   unqualified — the fuller, correct rewording landed in `§4.27` but this earlier
   mention was not updated to match).

## What has been SENT to the client, stated honestly

**Neither `D0PA1_Build_Status_Report.docx` nor `D0PA1_Section19_SignOff_Response.docx`
has been sent to the client as of this commit** — this holds for the current versions
exactly as it held for both earlier, now-superseded versions. A commit timestamp on
any file in this directory records when it existed here, in this form. It does not
record, and must not be read as recording, when (or whether) it was delivered to the
client. The Clarifications addendum is the one document in this directory known to
have already changed hands, since it originated from the client.

## Change control

Per the client's own §18: any substantive change to the prediction target, feature
definitions, baseline mapping, primary metric, any threshold, sample-size logic,
inclusion/exclusion rules, model family, or acceptance criterion — once genuinely
signed off — is made as a **dated commit**, never as a silent edit to a committed
document. The response document's own §5 follows this discipline internally already,
recording plainly that its earlier macro-F1-based thresholds were superseded once the
precision simulation ran, and why, rather than presenting the revised numbers as if
they were the first ones proposed. This repository does the same at the file level:
each superseded version stays in git history rather than being edited in place.
