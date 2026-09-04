# Response Verification

Every implementation-status claim in `docs/preregistration/D0PA1_Section19_SignOff_Response.docx`
(current version, committed alongside this file) checked against the repository —
by re-running the test suite that settles each claim, by direct computation where a
specific figure was quoted, and by reading the code where a structural claim was made.
**This document reports findings. It does not edit the response** — corrections are
for the response's author to make.

**Methodology.** Every test below was re-run in this session, not recalled from a
prior one (`python tests/test_<name>.py`, `pytest` is not installed). Every quoted
numeric claim was checked against the actual current output, not against documentation
describing a past run. One claim (§4.16's V_pd figures) had no existing script or
document behind it in this repository at all — it was independently reproduced from a
real session log, methodology inferred and stated explicitly, so a reader can judge the
reproduction on its own terms.

**Result: 27 of 27 checkable implementation-status claims VERIFIED.** Two structural
findings, described in full in §3 below, are not about any single claim being wrong —
one is an internal arithmetic inconsistency inside the response document itself, the
other is a live git-repository state that no longer matches a claim about the object
store. Both are reported plainly rather than smoothed over.

---

## 1. Per-claim verification

| § | Claim | Settled by | Result |
|---|---|---|---|
| 4.1 | "Three checks: a static import-graph parse... a static call-graph check... and a runtime check" | `python tests/test_feature_separation.py` | **UNDERSTATED.** The test currently runs **four** checks — `[1/4]` import graph, `[2/4]` call graph, `[3/4]` runtime monkeypatch, **`[4/4]` compatibility-shim isolation** (`check_shim_isolation`). The fourth check exists, is documented in `docs/D1_DEPENDENCY_MAP.md` §9 as "added same task," and was itself separately demonstrated failing on a deliberate violation (documented in that same section). The response describes the test's earlier, three-check state. |
| 4.1 | "The test has been observed to fail... the failure output is recorded" | `docs/D1_DEPENDENCY_MAP.md` §6 (lines 205–231) | **VERIFIED.** Real pasted failure output exists for checks 1–3 (a deliberately introduced `ATTENTION_ORIENTED_SCORE_THRESHOLD` import), and separately for check 4 in §9. |
| 4.3 | "SEM 0.1896 where 0.1826 is expected" | `python tests/test_reliability.py`, check 14 | **VERIFIED exactly.** Re-run today: `computed_sem: 0.18960167376454515`, `expected_sem_1_over_sqrt_T: 0.18257418583505536`, `relative_error: 0.03849` (3.8%). |
| 4.3 | Guarded ICC "raises on a single-unit structure with an explanatory message" | Same test, check 10 | **VERIFIED.** Raises with the exact message quoted in the response, word for word. |
| 4.3 | "No reliability RESULT exists... a structural smoke test that reports no magnitudes at all" | `python tests/test_reliability_smoke_real_logs.py` | **VERIFIED.** Confirmed by reading the module's own docstring and by the actual printed output: no SEM/RC/CV/Bland-Altman/ICC number appears anywhere in the run. |
| 4.4 | Temporal-rule test "bit-identical whether or not that session's data is present" | `python tests/test_baselines.py`, check 1 | **VERIFIED exactly.** `center_original: 0.008013792940586562` = `center_mutated: 0.008013792940586562`; `scale_original`/`scale_mutated` likewise identical. |
| 4.4 | Leaky-selector proof "produced visibly different values" | Same test, check 2 | **VERIFIED.** `leaky_center_original: 0.357...` vs `leaky_center_mutated: 0.743...`; `leaky_scale_original: 0.991...` vs `leaky_scale_mutated: 1.788...` — clearly different, confirming the test is not vacuous. |
| 4.4 | Session 1 "emits every row with value null, missingness flag set and reason no_prior_history... never dropped and never falling back" | Same test, check 3 | **VERIFIED.** `n_s0_rows: 20`, `n_s0_expected: 20`, `all_missing: True`, `all_reason_correct: True`. |
| 4.9 | "an injected leak... produced +0.66 against a clean baseline's −0.02" | `python tests/test_leakage.py`, check 4 | **VERIFIED almost exactly.** `clean_delta_point: -0.0227` (rounds to -0.02), `leaked_delta_point: 0.6625` (rounds to 0.66). |
| 4.9 / 4.17 | Negative control "verified by calling the harness the way an unaware caller would" | `python tests/test_leakage.py` check 2; `python tests/test_precision.py` check 5 | **VERIFIED.** Both checks call the machinery with no mention of negative controls anywhere in the call and confirm `delta_negative_control` returns populated. |
| 4.11 | "Run twice in a clean checkout and diffed: all six results tables and the figure are byte-identical. The only difference is a timestamp and its derived run id" | `python reproduce.py` run twice this session, `diff -rq` on the output | **VERIFIED exactly.** Only `reproduction_output/00_provenance.json` differed; the diff was exactly `captured_at_utc` and `experiment_id`, nothing else, across both runs performed live in this session. |
| 4.11 | The matplotlib hash-salt/timestamp defect and the `reproduction_output/` gitignore defect, found and fixed | `docs/D4_REPRODUCIBILITY.md` §2.4–2.5; `.gitignore` line 50 | **VERIFIED.** Both defects are documented with before/after evidence, and `reproduction_output/` is present in `.gitignore` today. |
| 4.11 | "Ten stochastic components are enumerated and all are seeded; none was found unseeded" | `reproduce.py` lines 78–87 | **VERIFIED.** Exactly ten `SEED_*` constants exist, one per stochastic component named in the surrounding code. |
| 4.13 | "Run, in three passes" | `artefacts/` directory contents | **VERIFIED as a reasonable characterization.** Three distinct sweep artefacts exist (`d6_sweep_results.json` = Pass 1, `d6_sweep_pass2_results.json` = Pass 2, `d6_finalisation_results.json` = finalisation), matching `precision_analysis_v1.md`/`v2.md`. The metric-comparison and clip-epsilon work are additional, smaller addenda layered on top (documented as "Addendum 2"/"Addendum 3" within `v2.md`, not as a fourth "pass") — consistent with "three passes," not a separate claim about total work volume. |
| 4.13 | Worst-cell half-width "reaches 0.034" (25 min, rare=0.02) | `artefacts/precision_analysis_v2.md` line 313 | **VERIFIED exactly.** Table value: `0.0339` — rounds to 0.034. |
| 4.13 | Realistic-cell spread "ran from 0.013 to 0.043, mean 0.021" | Same file, line 318 (45 min, rare=0.05 row) | **VERIFIED.** `mean 0.0209` (→0.021), `min 0.0126` (→0.013), `max 0.0433` (→0.043). |
| 4.13 | "That spread did NOT shrink when bootstrap replicates were quadrupled" | Same file, lines 282–291 | **VERIFIED.** Documented `n_boot=50→200` comparison at the same cell shows range widening (0.0223 → 0.0307), not shrinking, exactly as claimed. |
| 4.15 | "a clean case returns precision, recall and F1 of 1.0; a deliberately degraded case... drops F1 to 0.615" | `python tests/test_blink_positive.py`, checks 8–9 | **VERIFIED exactly.** `clean_f1: 1.0`, `degraded_f1: 0.6153846153846153` (rounds to 0.615). |
| 4.15 | "verified by parsing the module's own syntax tree and confirming none of the three criterion field names appears in any comparison" | Same suite, check 11 | **VERIFIED.** `violations: []`. |
| 4.16 | "V_pd's robust scale is approximately 1.6e-4, roughly sixteen times smaller than its own standard deviation of 2.6e-3" | Independently recomputed this session (see §2 below) | **VERIFIED, and independently reproduced** — see §2 for the full account; this claim had no existing script or document behind it anywhere in the repository before this check. |
| 4.16 | "The camera loop is untested" (null-input control) | `controls/null_input.py`; `tests/test_controls.py` (module docstring, both read) | **VERIFIED.** The test file's own docstring states the camera-loop orchestration is not covered; only `compute_dispersion`/`ExcursionDetector`/config hashing are tested. |
| 4.24 | Prompt "contains z-scores, the anonymous participant label, and fixed instructional text. Nothing else." | `docs/PRIVACY_EVIDENCE.md` §4 (a real, verbatim logged prompt) | **VERIFIED.** The quoted real prompt contains exactly two z-scores, `person_label=P04`, and fixed instructional text — no other content. |
| 4.26 | "9 VERIFIED, 2 PARTIAL, 0 NOT FOUND" | `docs/AUDIT_A_COLUMN.md`, summary lines | **VERIFIED exactly**, both in the original 2026-08-22 summary and the 2026-08-24 update. |
| 4.27 | "The object store was pruned and git fsck --full --strict returns clean" | `git fsck --full --strict`, run this session | **NO LONGER TRUE — see §3.2.** One dangling tree object exists in the object store today. It is almost certainly a benign byproduct of this verification session's own sequence of `git add`/`git commit` operations, not a re-introduced defect from before — but the literal claim, checked right now, does not hold. |
| 4.27 | "Eight entries were backfilled to cover work done before it existed, and each is marked as a retrospective entry" | `logs/variant_log.jsonl`, read directly | **VERIFIED exactly.** 9 total entries, 8 marked `"retrospective": true` (the 9th is the original, contemporaneous, non-retrospective entry). |
| 4.28 | "All four invariants are enforced in code and directly tested" | `python tests/test_canonical_log.py` | **VERIFIED.** All four (subject_id required; context/device locked per session; missingness cross-checked in both directions; per-field timestamp monotonicity) pass, plus session-header-uniqueness and validator-rejection checks. |
| 4.30 | "A deletion routine is implemented and writes a deletion log... The routine defaults to dry-run... a real dry run over the existing logs directory that scanned every file, deleted nothing and left the directory unchanged" | `python tests/test_retention.py`; `python -m privacy.retention`, both run this session | **VERIFIED.** `RetentionConfig().dry_run` is `True` by default; a live dry-run against the real `logs/` directory scanned 49 files (the 50th, `variant_log.jsonl`, is permanently excluded by design), found 0 expired, deleted nothing — `logs/` held 50 files before and 50 after. |

---

## 2. §4.16's V_pd figures — independent reproduction, methodology stated

This claim had **no existing script, test, or document behind it anywhere in this
repository** before this verification pass — a genuinely new computation, not a
citation of prior work (`docs/RELIABILITY.md`'s similarly-shaped `1.6e-4`/`16×` figures
are a **synthetic** exploration targeting an *assumed* value the client is described as
already expecting; they are a different computation from what §4.16 describes as
"computed on one existing session as a factual observation").

Reproduced directly: scanning every `logs/session_*.jsonl` file's `calibration_complete`
record for a `v_pd` standard deviation near `2.6e-3` found exactly one match —
`session_eb41ba71-7b48-4126-ae6f-8162b79ca890.jsonl` (`std: 0.002623938...`). Extracting
that session's own calibration-phase `v_pd` samples (`calibration_status: "calibrating"`,
n=653) and running them through the real, unmodified `features.robust_baseline.mad_stats`
gives:

```
std          = 0.0026258737763999204   (matches "2.6e-3" claim)
mad_scaled   = 0.00015672345352159603  (matches "1.6e-4" claim)
ratio        = 16.75                   (matches "roughly sixteen times")
```

**This independently confirms the claim to high precision** using the exact function
the rest of this codebase uses for robust dispersion. One completeness gap, not a
correctness one: **no script or test in this repository performs or records this
computation** — a future session could not re-derive it without knowing (a) which of
17 real sessions to use and (b) that "robust scale" here means the calibration-phase
samples specifically, not the whole-session stream (the whole-session computation, also
checked this session across all 17 real logs, does not reproduce these figures for any
session). Worth committing as a small script or test if this figure is meant to be
citable going forward.

---

## 3. Structural findings — not about any single claim

### 3.1 §6's "Five" is an arithmetic error against the response's own §4 table

The response's closing summary (§6) states: *"Twenty-seven items are returned with
operational definitions ready for sign-off. **Five of those carry implementing code and
inspectable artefacts today.**"*

Counting the response's own §4 sign-off matrix table directly: rows marked
`RETURNED · EVIDENCED` (the status that means "a definition is provided AND the
implementing code exists... with a commit and an inspectable artefact," per the
response's own §1 definition) are rows **1, 6, 11, 13, 17, 24, 26, 27, 28, 29 — ten
rows, not five.** (Separately, 8 more rows are `RETURNED · BUILT, NOT YET RUN ON REAL
DATA` — implementing code exists but has not touched real data — which is a distinct
and correctly-separate category from "carries implementing code and inspectable
artefacts.")

The companion Build Status Report's own §8 gets this count right on its own terms:
*"Ten of those are exercised; eight are built but untested against real data."* Ten
matches the §4 table exactly. Five, in the sign-off response's §6, does not — it looks
like a stale figure carried over from an earlier draft rather than recomputed against
the current 30-row table. **This is worth a fix before sending**, since §6 is the
section most likely to be read on its own.

### 3.2 `git fsck --full --strict` no longer returns clean

Re-run in this session: `git fsck --full --strict` reports one dangling tree object.
Inspected directly (`git cat-file -p`) — it is a whole-repository top-level tree
snapshot containing only ordinary tracked files and directories (`.gitignore`,
`CLAUDE.md`, `docs/`, `privacy/`, etc.), **no media, no secret, nothing resembling raw
participant data.** It is almost certainly an intermediate tree object generated by
this verification session's own sequence of `git add`/`git rm`/`git commit` calls
(five commits were made in this session before this check ran), not a re-introduced
defect from before those guards were verified. It was **not pruned** as part of this
task — this is a verification report, and clearing it is a repository-maintenance
action distinct from documentation. **The response's "returns clean" claim, checked
live right now, does not hold**, and should either be re-verified (`git gc --prune=now`,
then re-run `git fsck`) immediately before the response is actually sent, or the claim
should be softened to describe when it was last confirmed clean rather than an
unqualified present tense.

### 3.3 An internal contradiction about the harness acceptance check

§2 of the response states the controlled environment/ROI harness question is "now
closed... it is resolved, **subject to my acceptance check... which is in progress**."
§4.2's own "Implementation status" paragraph, later in the same document, states:
*"CORRECTION TO AN EARLIER DRAFT: the acceptance check has **NOT** been performed... **It
has not started** — the harness package has not yet been opened."* These two statements
directly contradict each other within the same document — one says "in progress," the
other explicitly corrects that framing to "has not started." Nothing in this repository
can settle which is current (no harness exists here either way), so this is reported as
an internal-consistency finding, not a repository-verification result — but it is worth
resolving before sending, since §2 is read before §4.2 and a reader following the
document in order would form the wrong impression.

### 3.4 A possible inconsistency in the EVIDENCED/BUILT-NOT-RUN boundary (observation, not an error)

Rows 6 (Uncertainty), 11 (D4), and 13 (D6 precision simulation) are marked
`EVIDENCED` on the reasoning that their entire deliverable is either pure
machinery/convention or an inherently-synthetic simulation study — neither ever
requires real recorded data to be "done." By that same reasoning, **row 5 (Primary
metric / U)** and **row 21 (Synthetic latent recovery)** look like they could
plausibly belong in the same category: row 5's oriented-utility convention is
implemented in code (`simulation/precision.py`'s `Metric` abstraction) and its
justifying evidence (the log-loss-vs-macro-F1 decidability comparison) has been run
and reported, exactly like row 13's; row 21's deliverable is explicitly "validate the
machinery under known assumptions" (per the client's own §10.7), which is precisely
what has been done and reported, exactly like row 6's bootstrap-CI machinery. Instead
both are marked plain `RETURNED` (row 5) and `BUILT, NOT YET RUN ON REAL DATA` (row
21). This is not a factual error — it is the document author's own boundary-drawing
choice, and reasonable people could place these rows either way — but it is
inconsistent with the boundary the response itself appears to draw for rows 6/11/13,
and is flagged here as something worth a deliberate second look rather than left as an
unexamined inconsistency.

---

## 4. Anything not checkable from this repository

- Whether Amendment 1 (DOPALAND-owned remote), the delivered ROI harness, or any other
  artifact described as coming from the client actually exists — none of this is, or
  should be, present in this repository yet. Not a repository-verification question.
- Future-tense claims ("the report will state...", "I would rather...") — these are
  intentions for the eventual final report, not present-tense claims about this
  repository's current state, and are correctly outside this document's scope.
