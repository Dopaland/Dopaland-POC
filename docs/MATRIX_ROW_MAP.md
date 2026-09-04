# §19 Matrix Row Map

Maps this repository's contents to the 30 rows of the client's §19 sign-off matrix
(`docs/preregistration/D0PA1_PreRegistration_Clarifications_v0.7.pdf`, §19). That
numbering exists only in the client document; this file is what lets a session working
in this repository find, for any row, what (if anything) here evidences it.

**Two status columns, deliberately kept separate.** `docs/preregistration/D0PA1_Section19_SignOff_Response.docx`
(current version) now assigns each row one of its own four statuses (`RETURNED ·
EVIDENCED` / `RETURNED · BUILT, NOT YET RUN ON REAL DATA` / `RETURNED` /
`DECISION REQUIRED`). This file's own **Repo status** column is derived independently,
from reading the repository directly — the two are reconciled below, and **where they
disagree, both are shown rather than one silently adopted.** `docs/RESPONSE_VERIFICATION.md`
is the evidence backing every repo-status claim here; read that first for the detailed
per-claim verification this reconciliation is built on.

**Repo status vocabulary** (unchanged from the previous version of this file):

- `IMPLEMENTED` — code exists, is tested, and the capability works as built.
- `IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA` — the code exists and is tested against
  synthetic input; it has never touched a real recording or real session.
- `DEFINED-NOT-IMPLEMENTED` — the shape of the answer is described somewhere (a formula,
  a required return, a doc), but no code computes it.
- `BLOCKED-ON-CLIENT-DECISION` — cannot proceed until an external decision lands.
- `NOT-APPLICABLE-IN-REPO` — the row's evidence is a collection-protocol or governance
  matter, not something that can live in this repository as code.

G1 applies to this document too: every status below is a factual description of what
exists. None of it is a claim that any threshold, decision rule, or verdict has been
applied — those remain for a human, after sign-off, against real data.

| # | Item | Response's status (§4) | Repo status | Agree? | Module(s) / document(s) / notes |
|---|---|---|---|---|---|
| 1 | D1 feature separation | EVIDENCED | IMPLEMENTED | Yes | `features/{geometry,x_core,episodes,attention,audio,context}.py`; `tests/test_feature_separation.py` (4 checks, not the 3 the response describes — see `docs/RESPONSE_VERIFICATION.md` §1); `docs/D1_DEPENDENCY_MAP.md`. |
| 2 | D2 prediction target | RETURNED (§2 called it "resolved"; §4.2's own correction says the acceptance check "has NOT been performed... has not started") | BLOCKED-ON-CLIENT-DECISION | **DISAGREE (softly)** | No code anywhere in this repo depends on or defines an action-class vocabulary; `schema/canonical_log_v1.json`'s `action_class` is still an open string. The response's own §4.2 "Implementation status" note admits the acceptance check hasn't started, which is consistent with my repo-derived status, not with §2's "resolved" framing — see `docs/RESPONSE_VERIFICATION.md` §3.3 for the internal contradiction this stems from. |
| 3 | D3 reliability | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `analysis/reliability.py`; SEM 0.1896/0.1826 and the ICC guard both re-verified live this session (`docs/RESPONSE_VERIFICATION.md` §1). |
| 4 | D7 baseline | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `analysis/baselines.py`; temporal-rule bit-identical test and the leaky-selector proof both re-verified live this session. |
| 5 | Primary metric / U | RETURNED | IMPLEMENTED | **DISAGREE (judgment call, see `docs/RESPONSE_VERIFICATION.md` §3.4)** | `simulation/precision.py`'s `Metric` abstraction is real, tested code, and its justifying evidence (log-loss-vs-macro-F1 decidability, ~2.1× average) has been run and reported — by the same reasoning that earns rows 6/11/13 `EVIDENCED`, this row looks under-classified as plain `RETURNED`. Not a factual error, a boundary-drawing inconsistency worth a second look. |
| 6 | Uncertainty | EVIDENCED | IMPLEMENTED | Yes | `bootstrap_ci_on_delta`/`bootstrap_ci_on_delta_refit`; resampled at episode level, never trial. The client's own §5.2 formal permutation test (its own exchangeability unit, ≥1000 permutations, an actual p-value) is still NOT built anywhere — `time_shuffle.py` is explicitly diagnostic-only and must not be read as satisfying this. |
| 7 | Gate 3 rule | RETURNED | DEFINED-NOT-IMPLEMENTED | Yes | Formula accepted from the client's own §5.3 text; `δ_Gate3 = 0.05 nats` is now proposed with a real derivation (context-baseline information gain, §4.7) — no code computes the rule itself, correctly (G1; no real M_core/M0b exists). |
| 8 | Verdict rule | RETURNED | DEFINED-NOT-IMPLEMENTED | Yes | Same reasoning as row 7; `δ_attention`/`δ_audio`/`δ_latent` all proposed at 0.05 nats with stated justification. No code computes a verdict anywhere (G1). |
| 9 | Leakage controls | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `controls/leakage.py`; injected-leak figures (+0.66 vs -0.02) and the pluggable-source claim both re-verified live this session. "What counts as substantial" is now proposed (`2 × δ_Gate3`, i.e. 0.10 macro-F1 points). |
| 10 | Split hygiene | RETURNED | IMPLEMENTED | Yes | `chronological_split`/`build_features`, verified in `tests/test_precision.py`. Arguably also earns `EVIDENCED` by the row-6/11/13 standard, same observation as row 5. |
| 11 | D4 reproducibility | EVIDENCED | IMPLEMENTED | Yes | Two live runs of `reproduce.py` this session, diffed byte-identical except `experiment_id`/`captured_at_utc`, exactly as claimed. Ten seeds confirmed, all named. |
| 12 | D5 actual action | RETURNED | NOT-APPLICABLE-IN-REPO | Yes | Named funded-phase item; nothing to build. Accepted-as-written wording matches CLAUDE.md's own constraint. |
| 13 | D6 precision simulation | EVIDENCED | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA (my earlier framing) → revised to IMPLEMENTED | Yes (after revision) | Three sweep passes confirmed by artefact count; worst-cell (0.034) and realistic-cell spread (0.013–0.043, mean 0.021) both verified exactly against `artefacts/precision_analysis_v2.md`. Revising my own earlier "never-run-on-real-data" framing for this row: D6's deliverable is inherently a synthetic feasibility study (per the client's own §9), so "real data" was never the bar for this row — `EVIDENCED` is the more accurate repo status, and my prior version of this file was arguably too conservative here. |
| 14 | D8 attention validity | RETURNED | DEFINED-NOT-IMPLEMENTED | Yes | Statistic/null/failure-rule all now proposed in §4.14; no code computes any of it (correctly — D0PA1's own Gate 2 has not run). The V_so pitch-unreliability pre-declaration is real and matches CLAUDE.md's own finding. |
| 15 | Positive control (blink) | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `controls/blink_positive.py`; F1 1.0/0.615 and the AST criterion-check both re-verified live this session. No real clip exists. |
| 16 | Null-input control | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `controls/null_input.py`; camera loop confirmed untested. The new V_pd robust-scale figures (1.6e-4 vs SD 2.6e-3, ratio ~16.75) were independently reproduced this session from a real log — see `docs/RESPONSE_VERIFICATION.md` §2. |
| 17 | Negative control | EVIDENCED | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA (my earlier framing) → revised to IMPLEMENTED | Yes (after revision) | Unaware-caller verification re-confirmed live this session in two separate test files. Revising my earlier framing: this control's entire deliverable (a meaningless signal, wired in automatically) needs no real data to be complete — the response's `EVIDENCED` is the more accurate call, same reasoning as row 13. |
| 18 | Time-shuffle | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `controls/time_shuffle.py`; diagnostic-only stamping confirmed in the output itself, not just documentation. |
| 19 | Modality ablation | DECISION REQUIRED | BLOCKED-ON-CLIENT-DECISION | Yes | Contingent on the audio keep/remove decision (Decision A in the response). |
| 20 | Context stress test | RETURNED | NOT-APPLICABLE-IN-REPO | Yes | Collection-protocol item; nothing to build now. |
| 21 | Synthetic recovery | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED | **DISAGREE (judgment call, see `docs/RESPONSE_VERIFICATION.md` §3.4)** | `simulation/latent_recovery.py` is real, tested code whose entire stated purpose (per the client's own §10.7) is validating machinery on synthetic ground truth before real data ever touches it — by the same reasoning that earns row 13 `EVIDENCED`, this row looks under-classified. The success-threshold sign-off is separately and correctly still open; that is a different sub-claim from whether the machinery itself is "done." |
| 22 | Sensor swap | DECISION REQUIRED | BLOCKED-ON-CLIENT-DECISION | Yes | Pending hardware + FPS feasibility test (Decision B). |
| 23 | Audio acquisition | DECISION REQUIRED | BLOCKED-ON-CLIENT-DECISION | Yes | No microphone/capture/clock-sync exists (Decision A). |
| 24 | LLM read | EVIDENCED | IMPLEMENTED | Yes | Prompt-content claim (z-scores + label + fixed text only) re-verified against the real logged exchange in `docs/PRIVACY_EVIDENCE.md` §4. |
| 25 | V_es / V_pd wording | RETURNED | IMPLEMENTED | Yes | Exact required phrase codified in CLAUDE.md and shown in real use. Arguably `EVIDENCED` by the row-5/10 standard — same minor inconsistency noted there, not re-flagged separately. |
| 26 | A-column verification | EVIDENCED | IMPLEMENTED | Yes | "9 VERIFIED, 2 PARTIAL, 0 NOT FOUND" re-confirmed exactly against `docs/AUDIT_A_COLUMN.md`. |
| 27 | Repository / provenance | EVIDENCED | IMPLEMENTED, partially | **DISAGREE on one sub-claim** | The genuine pre-registration response is now committed (this task, superseding two earlier versions — see `docs/preregistration/README.md`). Variant log's 8 retrospective entries re-confirmed exactly. **But**: `git fsck --full --strict`, re-run live this session, reports one dangling tree object — the response's "returns clean" claim does not hold right now (see `docs/RESPONSE_VERIFICATION.md` §3.2; assessed as benign, likely a byproduct of this session's own commits, not re-pruned as part of this documentation task). Still not done: a tagged frozen release; genuine held-out-data storage separation (both correctly acknowledged as open in the response itself). |
| 28 | Canonical schema | EVIDENCED | IMPLEMENTED | Yes | This row's status correctly moved from the earlier draft's plain `RETURNED` to `EVIDENCED` — the schema and writer are real, tested code today (`tests/test_canonical_log.py`, 4 invariants re-verified live this session), not merely defined. Still not wired into any live capture loop, as the response itself states. |
| 29 | Stopping / exclusions | EVIDENCED | DEFINED-NOT-IMPLEMENTED | Not a real disagreement — different axis | `docs/STOPPING_AND_EXCLUSION_RULES.md` (committed, dated) is what the response's `EVIDENCED` refers to — a definition committed as a dated document, which is true. My repo status measures something else (no *code* enforces these rules yet), which is also true and expected pre-sign-off (implementing an exclusion rule before the client signs it would apply an unagreed rule). Both statements hold simultaneously; not a factual conflict. |
| 30 | Privacy / retention | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED, partially | Yes | `privacy/retention.py`; dry-run default and the real dry-run over `logs/` (49 scanned, 0 expired, directory unchanged) both re-verified live this session. Storage-location decision correctly still open in both. |

## Summary of disagreements (Task 4's explicit ask)

- **Row 2 (D2):** the response's summary language ("resolved") is inconsistent with
  its own §4.2 correction ("has not started") and with this repository, which contains
  no trace of a delivered harness. My `BLOCKED-ON-CLIENT-DECISION` stands.
- **Rows 5, 10, 21, 25 (and arguably others):** a boundary-drawing inconsistency, not a
  factual error — rows whose entire deliverable is synthetic-complete (no real data
  ever required) are `EVIDENCED` in some cases (6, 11, 13) and not in others (5, 21).
  Flagged for a deliberate second look, not asserted as wrong.
- **Row 13:** revised my OWN prior framing (this file previously called D6
  `IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA`) — on reflection, that was the wrong bar for
  a row whose deliverable is inherently a synthetic study. Now `IMPLEMENTED`, agreeing
  with the response's `EVIDENCED`.
- **Row 17:** same self-revision as row 13, same reasoning.
- **Row 27:** the response's specific "git fsck returns clean" sub-claim does not hold
  as of this session's live check — see `docs/RESPONSE_VERIFICATION.md` §3.2.

No row disagreement found where the response claims MORE than the repository supports
on a testable, non-judgment-call basis, except row 2's summary-vs-detail contradiction
and row 27's fsck sub-claim — every other checkable figure in the response was verified
exact or near-exact against live re-runs this session.
