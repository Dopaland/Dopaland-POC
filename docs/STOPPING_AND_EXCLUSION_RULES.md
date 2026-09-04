# Stopping and Exclusion Rules

Row 29 of the §19 sign-off matrix (`docs/MATRIX_ROW_MAP.md`). Required by
`docs/preregistration/D0PA1_PreRegistration_Clarifications_v0.7.pdf` §16 ("Stopping and
exclusion rules — NEW... Added because outcome-dependent exclusion is one of the few
remaining routes to an unfalsifiable result").

**Corrected version.** An earlier version of this file concluded that none of the
eight required categories were covered anywhere — that conclusion was reached by
checking the client's request document (which only names the eight categories and does
not itself specify rule content) and this repository's code, but not the vendor's
actual §4.29 response, which had not yet been located on this machine. §4.29 of
`docs/preregistration/D0PA1_Section19_SignOff_Response.docx` does specify rule content
for all eight. This file now transcribes that content directly, rather than repeating
the earlier, incomplete search.

## The binding principle

Transcribed verbatim from §4.29: **"trials are not removed because they make the
result look worse. Every exclusion is logged with its rule, its trigger and its
timestamp, and the exclusion count is reported alongside the results."** This is not
negotiable and governs every rule below.

## Status: RETURNED · EVIDENCED (§4.29), all eight

Transcribed directly from §4.29 of `D0PA1_Section19_SignOff_Response.docx` — this is
the vendor's proposed rule content, **returned for the client's sign-off**, not yet a
confirmed, signed pre-registration record (per the response document's own §1: "Nothing
in this document is confirmed by appearing in it").

**Re-checked against the rebuilt response document.** The response was rebuilt (primary
metric moved to log loss, thresholds re-derived in nats — see
`docs/preregistration/README.md`) and §4.29 was re-read in full against the table below.
**The eight rules transcribed here are word-for-word unchanged** — §29 was never
metric-dependent, so the rebuild did not touch it. The only change in §4.29 itself: the
row's status moved from `RETURNED` to `RETURNED · EVIDENCED`, and an "Implementation
status" line was added — "These rules are now committed to the repository as their own
document, so they exist in dated form before collection rather than only inside this
response" — which is a correct description of this file's own existence, not new rule
content.

| # | Category | Rule, as transcribed from §4.29 |
|---|---|---|
| 1 | Collection stopping | "Collection stops at the pre-registered number of sessions and episodes fixed by the D6 simulation. It does not stop early because a result has appeared, and it does not extend because one has not." |
| 2 | Invalid trial | "A trial where the stimulus did not present correctly, where the action log and the screen event disagree, or where the participant was interrupted by an external event recorded at the time. Judged from the event log and the operator note, never from the value of the signal." |
| 3 | Corrupted recording | "A file failing checksum verification, or with unreadable or non-monotonic frame timestamps." |
| 4 | Device failure — repeat or not | "If a device fails mid-session, the session is terminated and repeated in full on a subsequent day. A partially completed session is retained in the manifest and marked, not deleted." |
| 5 | Aborted session | "Retained and marked aborted with the reason. Its data is excluded from confirmatory analysis but remains in the manifest and in the record." |
| 6 | Missing modality | "Logged as missing with a reason. The session is not excluded on that basis; the affected comparison reports reduced coverage." |
| 7 | Trial and session exclusion (general) | Not given its own separately-titled paragraph in §4.29 — covered by the binding principle itself (quoted above), which is the general criterion any specific exclusion (categories 2, 3, 4, 5) must satisfy: rule-based, independent of outcome, logged with rule/trigger/timestamp. Recorded here as covered-by-the-general-principle rather than by a dedicated named rule, so the distinction is visible rather than silently merged. |
| 8 | Repeated-trial eligibility | "Remain eligible provided the repeat was triggered by a rule above and not by the outcome. Every repeat is recorded with its trigger." |

## What already exists in this repository that these rules build on

Not part of §4.29 itself, but existing machinery the response's rules can act on
without reinvention:

- **Missingness is already logged, never dropped**, at the signal level
  (`features/signal_quality.py`, `schema/canonical_log_v1.json`'s fixed
  `missingness_reason` vocabulary) — directly usable for category 6's "logged as
  missing with a reason."
- **Two existing quality flags** (`classify_window_confidence`'s `low_confidence`,
  `classify_calibration_quality`'s `possibly_not_neutral`) are exactly the kind of
  signal-level condition category 2/7's "judged from the event log... never from the
  value of the signal" principle would need to be kept separate from — these flags are
  about signal quality, not the trial-validity judgment §4.29 describes as coming from
  the event log and operator note instead.
- **The data manifest** (`manifest/data_manifest.csv`, Gate 0 A4) is the natural home
  for the "retained in the manifest and marked, not deleted" requirement in categories
  4 and 5 — no code currently writes an aborted/device-failure marker into it; that
  remains implementation work, not yet built.

## What must NOT be done with this document

Per G1 and G2: no code in this repository may implement any of these eight rules as an
automatic decision until the client has signed off on §4.29 as returned. The rules
above are the vendor's **proposal**, not yet confirmed — writing
`if session_incomplete: discard()` anywhere before sign-off would apply a rule that
has not yet been agreed, which is a different risk from inventing one, but still not
this document's or this task's to resolve unilaterally.
