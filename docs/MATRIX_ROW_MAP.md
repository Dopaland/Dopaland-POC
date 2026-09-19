# §19 Matrix Row Map

Maps this repository's contents to the 30 rows of the client's §19 sign-off matrix
(`docs/preregistration/D0PA1_PreRegistration_Clarifications_v0.7.pdf`, §19). That
numbering exists only in the client document; this file is what lets a session working
in this repository find, for any row, what (if anything) here evidences it.

**Two status columns, deliberately kept separate.** `docs/preregistration/D0PA1_Section19_SignOff_Response.docx`
(current version — the third committed, corrected against the second pass's
verification findings; see `docs/preregistration/README.md`) now assigns each row one
of its own four statuses (`RETURNED · EVIDENCED` / `RETURNED · BUILT, NOT YET RUN ON
REAL DATA` / `RETURNED` / `DECISION REQUIRED`). This file's own **Repo status** column
is derived independently, from reading the repository directly — the two are
reconciled below, and **where they disagree, both are shown rather than one silently
adopted.** `docs/RESPONSE_VERIFICATION.md` is the evidence backing every repo-status
claim here; read that first for the detailed per-claim verification this
reconciliation is built on.

**Status counts, re-derived from the current §4 table directly** (not carried forward
from the previous version of this file): counting the 30-row table row by row gives
**11 `RETURNED · EVIDENCED`, 7 `RETURNED · BUILT, NOT YET RUN ON REAL DATA`, 9 plain
`RETURNED`, 3 `DECISION REQUIRED`** — summing to 30, and matching the response's own
§6 summary exactly (see `docs/RESPONSE_VERIFICATION.md` §5 for the row-by-row count).

**⚠️ Now stale by one row, deliberately left un-recomputed until the response
document's own §4/§6 are updated to match** ("THE LAST GAP BEFORE THE DOCUMENTS
GO" task): row 16 (null-input control) moved to `EVIDENCED` below, since the
genuine empty-scene control was finally run this task with a real, clean
result. That makes the CORRECT current count **12 EVIDENCED, 6 BUILT-NOT-RUN,
9 RETURNED, 3 DECISION REQUIRED** (still 30) — but the response document's own
§4/§6 text has been updated to match this in the same task (see row 16's own
entry below), so by the time this file and the response document are both
read together, the counts agree again. This note exists only so a reader
comparing this line's OLD "11/7/9/3" text against the actually-current
document does not read that as a fresh discrepancy — it was true when
written, one row moved on a specific, dated, cited basis, and both documents
were updated together.

**Audio decision recorded (not yet reflected in any status).** The client's
keep-or-formally-remove decision on Δ_audio has been made — RETAINED,
acquisition authorised — reversing the sign-off response's own §4.23
recommendation. This is a substantive scope change against frozen Scope
v0.5.1 and is drafted for the client's §18 change control as CC-001
(`docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`), which
is PROPOSED and NOT IN FORCE. CC-001 proposes moving rows 19 and 23 off
DECISION REQUIRED, which would make the counts 12 / 6 / 11 / 1. **That
reclassification is NOT applied here and must not be applied until the
client confirms it.** The counts above remain 12 / 6 / 9 / 3, and rows 19
and 23 remain DECISION REQUIRED. Their rationale text has been corrected to
state what is factually true as of the audio acquisition build; correcting
a false statement is not a status change.

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
| 7 | Gate 3 rule | RETURNED | DEFINED-NOT-IMPLEMENTED | Yes | Formula accepted from the client's own §5.3 text; `δ_Gate3 = 0.05 nats`, derived from context-baseline information gain (§4.7), **ACCEPTED by the client** (`D0PA1_Client_SignOff_001.md` §2, 2026-09-18) and now a frozen field in `simulation/config.py`'s `PreRegisteredConfig` — no code computes the rule itself, correctly (G1; no real M_core/M0b exists). |
| 8 | Verdict rule | RETURNED | DEFINED-NOT-IMPLEMENTED | Yes | Same reasoning as row 7; `δ_attention`/`δ_audio`/`δ_latent` all **ACCEPTED at 0.05 nats** (`D0PA1_Client_SignOff_001.md` §2), δ_audio conditionally since Δ_audio is not currently computable (§2.4(b), row 23). All four now frozen fields in `simulation/config.py`. No code computes a verdict anywhere (G1). |
| 9 | Leakage controls | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `controls/leakage.py`; injected-leak figures (+0.66 vs -0.02) and the pluggable-source claim both re-verified live this session. "What counts as substantial" is now proposed (`2 × δ_Gate3`, i.e. 0.10 macro-F1 points). |
| 10 | Split hygiene | RETURNED | IMPLEMENTED | Yes | `chronological_split`/`build_features`, verified in `tests/test_precision.py`. Arguably also earns `EVIDENCED` by the row-6/11/13 standard, same observation as row 5. |
| 11 | D4 reproducibility | EVIDENCED | IMPLEMENTED | Yes | Two live runs of `reproduce.py` this session, diffed byte-identical except `experiment_id`/`captured_at_utc`, exactly as claimed. Ten seeds confirmed, all named. |
| 12 | D5 actual action | RETURNED | NOT-APPLICABLE-IN-REPO | Yes | Named funded-phase item; nothing to build. Accepted-as-written wording matches CLAUDE.md's own constraint. |
| 13 | D6 precision simulation | EVIDENCED | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA (my earlier framing) → revised to IMPLEMENTED | Yes (after revision) | Three sweep passes confirmed by artefact count; worst-cell (0.034) and realistic-cell spread (0.013–0.043, mean 0.021) both verified exactly against `artefacts/precision_analysis_v2.md`. Revising my own earlier "never-run-on-real-data" framing for this row: D6's deliverable is inherently a synthetic feasibility study (per the client's own §9), so "real data" was never the bar for this row — `EVIDENCED` is the more accurate repo status, and my prior version of this file was arguably too conservative here. |
| 14 | D8 attention validity | RETURNED | DEFINED-NOT-IMPLEMENTED | Yes | Statistic/null/failure-rule all now proposed in §4.14; no code computes any of it (correctly — D0PA1's own Gate 2 has not run). The V_so pitch-unreliability pre-declaration is real and matches CLAUDE.md's own finding. |
| 15 | Positive control (blink) | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `controls/blink_positive.py`; F1 1.0/0.615 and the AST criterion-check both re-verified live this session. Criterion (F1≥0.80, count within ±20% on ≥8/10 clips, ±150ms matching tolerance) **ACCEPTED by the client** (`D0PA1_Client_SignOff_001.md` §3, 2026-09-18), values unchanged from what was already stored. No real clip exists. |
| 16 | Null-input control | EVIDENCED (updated this task — see note) | IMPLEMENTED, run against real data | Yes | `controls/null_input.py`. **Two distinct real runs now exist and must never be conflated (found and corrected this task):** (a) the **quiet-sitting baseline** — subject present, sitting still, blank screen, 10 real minutes ("PHYSICAL RUN SESSION" task) — this is what the row's own original §4.16 text ("Person still, blank screen") actually specifies, and it produced the real per-signal std/mad_scale dispersion figures (`docs/CLIENT_FIGURES.md` §3), not a genuinely-null result, since a real detected subject was present for part of the run; (b) the **empty-scene control** — camera on, no subject at all, 10 real minutes ("THE LAST GAP BEFORE THE DOCUMENTS GO" task) — a genuinely different, harder test: 0/17,888 frames detected, every signal `insufficient_samples`, `calibration_completed: false` (correctly, post the Task-1.3 calibrator fix), and **zero false-signal events of any kind across an exhaustive per-sample scan** — no face, no pose, no composite/covariate value, no yaw reading, ever, in 10 real minutes. This second run is what the row's own closing sentence ("settles this on genuinely null input") actually asked for, and it had never been run until this task. The V_pd robust-scale figures (1.6e-4 vs SD 2.6e-3, ratio ~16.75) cited in §4.16's own text are from a THIRD, unrelated real session's calibration phase (`docs/RESPONSE_VERIFICATION.md` §2) — not from either control above; the quiet-sitting baseline's own ratio is ≈3.36×, a different number from different data (`docs/CLIENT_FIGURES.md` Task-2 claim 1). |
| 17 | Negative control | EVIDENCED | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA (my earlier framing) → revised to IMPLEMENTED | Yes (after revision) | Unaware-caller verification re-confirmed live this session in two separate test files. Revising my earlier framing: this control's entire deliverable (a meaningless signal, wired in automatically) needs no real data to be complete — the response's `EVIDENCED` is the more accurate call, same reasoning as row 13. |
| 18 | Time-shuffle | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA | Yes | `controls/time_shuffle.py`; diagnostic-only stamping confirmed in the output itself, not just documentation. |
| 19 | Modality ablation | DECISION REQUIRED | BLOCKED-ON-CLIENT-DECISION | Yes | Contingency on Decision A is discharged — the client retained Δ_audio. δ_audio = 0.05 proposed on the same reasoning as the other components, to be revisited once acquisition quality is known, since an unmeasured modality's achievable contribution cannot be sensibly bounded in advance. Note the dependency: the ablation cannot be run until the clock-synchronisation measurement exists (see row 23). Status held at DECISION REQUIRED: a reclassification to RETURNED is proposed in CC-001 and awaits the client's confirmation. |
| 20 | Context stress test | RETURNED | NOT-APPLICABLE-IN-REPO | Yes | Collection-protocol item; nothing to build now. |
| 21 | Synthetic recovery | EVIDENCED | IMPLEMENTED | Yes (reclassified) | **Resolved.** The response was updated to `EVIDENCED`, accepting the reasoning flagged in the prior version of this file: the row's entire deliverable is a synthetic study by design (per the client's own §10.7), so "never run on real data" was the wrong bar. `simulation/latent_recovery.py` is real, tested code; both metrics (Pearson r, standardised RMSE) are reported across a real sweep. The success-threshold sign-off is separately and correctly still open — a different sub-claim from whether the machinery itself is "done." |
| 22 | Sensor swap | DECISION REQUIRED | BLOCKED-ON-CLIENT-DECISION | Yes | Pending hardware + FPS feasibility test (Decision B). |
| 23 | Audio acquisition | DECISION REQUIRED | BLOCKED-ON-CLIENT-DECISION | Yes | Client decision made — Δ_audio RETAINED, acquisition authorised. Acquisition is built and has been exercised against a real microphone: capture thread, per-chunk integrity logging, independent consent (architecturally unreachable when declined), env-var-only storage config, privacy guard and separation guard both extended (`audio_acquisition.py`; `docs/AUDIO_ACQUISITION.md`). **No clock-synchronisation method between audio and video exists** — nine attempts across five sessions did not produce a usable measurement (video-side registration was diagnosed and fixed in the later attempts; audio-side registration still fails, cause not characterised), so no offset, spread or drift figure exists. This is now closed as a documented omission under CC-001 §6(a) (`docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`), not open work. §4.23's own retention condition is therefore unmet and Δ_audio is not yet computable. No audio FEATURE exists or is planned; `features/audio.py` remains an empty stub. Status held at DECISION REQUIRED: a reclassification to RETURNED (conditional) is proposed in CC-001 (`docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`) and awaits the client's confirmation. |
| 24 | LLM read | EVIDENCED | IMPLEMENTED | Yes | Prompt-content claim (z-scores + label + fixed text only) re-verified against the real logged exchange in `docs/PRIVACY_EVIDENCE.md` §4. |
| 25 | V_es / V_pd wording | RETURNED | IMPLEMENTED | Yes | Exact required phrase codified in CLAUDE.md and shown in real use. Arguably `EVIDENCED` by the row-5/10 standard — same minor inconsistency noted there, not re-flagged separately. |
| 26 | A-column verification | EVIDENCED | IMPLEMENTED | Yes | "9 VERIFIED, 2 PARTIAL, 0 NOT FOUND" re-confirmed exactly against `docs/AUDIT_A_COLUMN.md`. |
| 27 | Repository / provenance | EVIDENCED | IMPLEMENTED, partially | Yes (resolved) | The genuine pre-registration response is now committed (superseding three earlier versions across this repository's history — see `docs/preregistration/README.md`). Variant log's 8 retrospective entries re-confirmed exactly. **The fsck sub-claim is now resolved on both sides**: the response's §4.27 wording was corrected from an unqualified "returns clean" to the durable claim (pruned after hook verification; a dangling object from routine commit activity is not evidence of anything) — and this session actually ran `git reflog expire --expire=now --all` + `git gc --prune=now`, after which `git fsck --full --strict` returns clean (no output, exit code 0). That residual gap is now closed: §4.11's bullet was subsequently reworded to match §4.27 and today reads "no media file or credential has ever entered this history — the durable, checkable claim. See §4.27." The phrase "clean object store" no longer occurs anywhere in the document — verified by reading `word/document.xml` directly, not via `Document.paragraphs` (see `docs/PROJECT_STATE.md` §4). Still not done: a tagged frozen release; genuine held-out-data storage separation (both correctly acknowledged as open in the response itself). |
| 28 | Canonical schema | EVIDENCED | IMPLEMENTED | Yes | This row's status correctly moved from the earlier draft's plain `RETURNED` to `EVIDENCED` — the schema and writer are real, tested code today (`tests/test_canonical_log.py`, 4 invariants re-verified live this session), not merely defined. Still not wired into any live capture loop, as the response itself states. |
| 29 | Stopping / exclusions | EVIDENCED | DEFINED-NOT-IMPLEMENTED | Not a real disagreement — different axis | `docs/STOPPING_AND_EXCLUSION_RULES.md` (committed, dated) is what the response's `EVIDENCED` refers to — a definition committed as a dated document, which is true. My repo status measures something else (no *code* enforces these rules yet), which is also true and expected pre-sign-off (implementing an exclusion rule before the client signs it would apply an unagreed rule). Both statements hold simultaneously; not a factual conflict. |
| 30 | Privacy / retention | BUILT, NOT YET RUN ON REAL DATA | IMPLEMENTED, partially | Yes | `privacy/retention.py`; dry-run default and the real dry-run over `logs/` (49 scanned, 0 expired, directory unchanged) both re-verified live this session. Storage-location decision correctly still open in both. |

## Summary of disagreements — updated after the corrected response

Two of the three prior disagreements are now resolved by the corrected document
(row 21 reclassified; row 27's fsck claim reworded and the object store actually
pruned clean this session). One remains, and one is unchanged as a judgment call:

- **Row 2 (D2) — still disagree, but the self-contradiction is gone.** The internal
  clash (§2 saying "in progress" while §4.2 said "has not started") is resolved — §2
  no longer asserts a status at all. The substantive difference remains: the row is
  still labelled plain `RETURNED`, while §4.2's own text says everything in the row is
  "conditional on a check that is outstanding... the single item blocking this row,"
  and this repository contains no trace of a delivered harness either way. My
  `BLOCKED-ON-CLIENT-DECISION` stands — this is now a labelling-strictness difference
  rather than a contradiction, worth noting as a softer disagreement than before.
- **Rows 5, 10, 25 — still an open boundary-drawing observation**, not a factual
  error: these rows' deliverables look synthetic-complete by the same standard that
  now earns rows 6, 11, 13, and 21 `EVIDENCED`, but remain plain `RETURNED`. Not
  corrected in this revision (only row 21 was); still worth a deliberate second look,
  still not asserted as wrong.
- **Row 21 — RESOLVED.** Reclassified to `EVIDENCED` in the corrected response,
  matching this file's own `IMPLEMENTED` repo status. No longer a disagreement.
- **Row 27 — RESOLVED.** The response's fsck claim was reworded to the durable form,
  and this session's own `git reflog expire` + `git gc --prune=now` left
  `git fsck --full --strict` returning clean (confirmed live, this session). The
  residual textual gap noted here previously (§4.11's bullet list, unreworded) has
  since been closed: that bullet now carries the same durable wording as §4.27, and
  the phrase "clean object store" occurs nowhere in the document. Nothing about this
  row remains open.
- **Rows 13, 17 — no change.** These were self-corrections to this file's own prior
  framing, not disagreements with the response; they stand as previously recorded.

No row disagreement remains where the response claims something the repository does
not support on a testable, non-judgment-call basis. What remains is one labelling
question (row 2) and one open judgment call about category boundaries (rows 5/10/25).
