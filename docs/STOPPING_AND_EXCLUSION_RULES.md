# Stopping and Exclusion Rules

Row 29 of the §19 sign-off matrix (`docs/MATRIX_ROW_MAP.md`). Required by
`docs/preregistration/D0PA1_PreRegistration_Clarifications_v0.7.pdf` §16 ("Stopping and
exclusion rules — NEW... Added because outcome-dependent exclusion is one of the few
remaining routes to an unfalsifiable result").

## The binding principle

**Exclusions are rule-based and applied independently of outcome. Trials are not removed
because they make the result look worse.** Every exclusion is logged with its rule, its
trigger, and its timestamp, and the exclusion count is reported alongside results — not
folded silently into a smaller denominator. This principle is not negotiable and applies
regardless of which specific rules are eventually chosen below.

## What this document is, and is not

§16 asks the vendor to **return** explicit, pre-specified rules for eight named
categories. It does not itself state what those rules should be — it names the
categories that need one. **This document transcribes exactly that: the eight
categories, and nothing invented to fill them.** Checked directly against this
repository and the client's own document — neither contains actual rule content
(threshold values, repeat-vs-discard decisions, what counts as "corrupted") for any of
the eight. Per this task's explicit instruction, that absence is recorded as an open
item, not filled in here.

## The eight categories — status: OPEN for all eight

| # | Category | What must be pre-specified | Status |
|---|---|---|---|
| 1 | Collection stopping | The rule that ends data collection (a fixed session/trial count, a precision target from D6, a calendar bound, or some combination) | OPEN — no rule proposed anywhere in this repository or the client's addendum |
| 2 | Invalid trial | What makes a single trial invalid (e.g. no face detected for the whole trial, quality-gate rejection throughout, a logged hardware fault) and whether an invalid trial is dropped, retried, or logged as a real outcome (e.g. `NO_ACTION`/missingness, per D0PA1 hard constraint #8) | OPEN |
| 3 | Corrupted recording | What counts as corrupted (truncated file, unreadable codec, detected clock discontinuity) and the disposition (discard the recording, discard only the affected span, flag for review) | OPEN |
| 4 | Device failure — repeat or not | Whether a session interrupted by a device/hardware failure is repeated, and if so, on what schedule and whether the partial session's data is retained or discarded | OPEN |
| 5 | Aborted session | Distinct from device failure: what happens when the *participant* (the single subject) stops a session early — whether the partial session data enters analysis at all, and under which representation (session_z/persistent_z both assume a complete session; a partial one may need its own handling) | OPEN |
| 6 | Missing modality | What happens to a trial/session when one modality (e.g. audio, if retained) is unavailable while others are present — whether the trial is still usable for the available modalities' analyses, per-signal, as the missingness-reason vocabulary (`schema/canonical_log_v1.json`) already anticipates, or excluded entirely | OPEN |
| 7 | Trial and session exclusion | The general exclusion criteria beyond the specific cases above — e.g. a session whose calibration was flagged `possibly_not_neutral` (`features/x_core.py:classify_calibration_quality`), or a window flagged `low_confidence` (`features/episodes.py:classify_window_confidence`). This repository already computes and logs both flags (existing, tested code) — but flagging is not the same as an exclusion decision, and no rule yet says whether/how a flagged window or session is excluded from a given analysis | OPEN — the flags exist; the exclusion rule built on them does not |
| 8 | Repeated-trial eligibility | Whether trials repeated within a session (e.g. after a device-failure retry, or a flagged-and-redone calibration) remain eligible for analysis, and if so, whether all repeats are kept, only the last, or some other rule (the POC's own Gate 2 capture tool already had a related but distinct convention — max 2 calibration re-runs per person, never "re-run until clean" — see CLAUDE.md's POC GATE 2 section; that convention is POC-era and does not automatically transfer to D0PA1's own protocol without being restated here) | OPEN |

## What already exists that these rules would build on

Not rules themselves, but the closest existing machinery a future rule could reference
rather than reinvent:

- **Missingness is already logged, never dropped**, at the signal level
  (`features/signal_quality.py`, `schema/canonical_log_v1.json`'s fixed
  `missingness_reason` vocabulary) — a session/trial-level exclusion rule should reuse
  this vocabulary rather than invent a second one, the same discipline `analysis/baselines.py`
  already follows when it needed a new reason (`no_prior_history`).
- **Two existing quality flags** (`classify_window_confidence`'s `low_confidence`,
  `classify_calibration_quality`'s `possibly_not_neutral`) already mark exactly the kind
  of session/window condition an exclusion rule (category 7) would act on — they compute
  and log a flag today; they do not decide an exclusion.
- **The POC's Gate 2 max-2-recalibration convention** (CLAUDE.md's POC GATE 2 section) is
  a precedent for category 8's shape (a bounded retry count, never "retry until clean"),
  not a D0PA1 answer by itself.

## What must NOT be done with this document

Per G1 and G2: no code in this repository may implement any of the eight rules above
until a human has proposed and the client has signed off on the actual content — a
threshold, a repeat count, a disposition. Writing `if session_incomplete: discard()`
anywhere before that sign-off would be exactly the kind of outcome-independent-on-paper,
outcome-dependent-in-practice rule §16 exists to prevent (a rule chosen or silently
tuned after seeing what the data look like). This document's job is to make the eight
gaps visible and trackable, not to close them.
