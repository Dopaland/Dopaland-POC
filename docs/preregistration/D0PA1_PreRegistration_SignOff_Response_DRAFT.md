# D0PA1 — Pre-Registration Sign-Off Response (DRAFT)

**Status: INTERNAL DRAFT. Not reviewed by Debanjan. Not sent to Gargi.**
Prepared in a coding session against the repository's actual state, so that the §19
matrix response is grounded in code and artefacts rather than memory or intent. Every
factual claim below is checked against this repository as of the commit this file is
part of — see `docs/MATRIX_ROW_MAP.md` for the same material with file-level citations.

**This draft does not propose any threshold, δ value, retention period, or verdict
rule.** Per guardrail G1, those are the vendor's and client's business/scientific
judgment calls, not something a coding session should invent. Every row requiring one
is marked `OPEN — pending [specific decision]` rather than filled with an invented
number. A human must review this draft, add the missing judgment calls, and decide
whether and how to send it, before it is a real response to anyone.

Responding to: `D0PA1_PreRegistration_Clarifications_v0.7.pdf` (§16 Feasibility
Classification response, "From: Gargi (DOPALAND) · To: Debanjan").
Companion to: `D0PA1_Build_Status_Report.docx`.

---

## 1. Status and governing documents

Acknowledged: Scope v0.5.1 remains frozen and authoritative where this addendum is
silent; this document is the requested operational return against the addendum's §19
matrix, not a scope review.

## 2. D1 — Feature-block separation

Built and enforced. `docs/D1_DEPENDENCY_MAP.md` is the full dependency map, traced to
source variables, reviewable by someone who did not write the code. Both exclusions
(attention **and** audio) are confirmed separately, each with three independent checks
(static import graph, static call graph, runtime monkeypatch) — plus a fourth check
closing a compatibility-shim blind spot the other three could not see. All four are
demonstrated to actually fail on a deliberately introduced violation before being
trusted (§6/§9 of that document). Five versioned manifests exist
(`features/manifests/*.json`).

**§2.3's lag diagnostic** (near-perfect X_core↔A_t correlation at zero lag as a
contamination flag) is not built — it needs real X_core and A_t data from the same
session, which does not exist yet. The architectural test (the dependency map + its
enforcement) is what currently stands behind this row; the diagnostic itself is future
work once real data exists.

## 3. D2 — Prediction target and horizon

**OPEN — blocked on the controlled software environment that would produce the ROI
set and the logged on-screen actions.** That environment does not exist in this
repository and is not something this session can build; it is the client-side/task-
harness deliverable referenced in `docs/D4_REPRODUCIBILITY.md`. Nothing under D2 (class
enumeration, prediction window, tie handling, class balance, weighting method) can be
returned until that environment exists.

## 4. D3 / D7 — Reliability, ICC and baseline

**The repeated-unit problem (§4.1) is answered at the code level**, not yet at the
protocol level: `analysis/reliability.py`'s `compute_icc()` takes the repeated unit as
an explicit, required argument and **raises** if fewer than 2 distinct units are given
— it cannot silently compute an uninterpretable number from a single-unit design. This
directly implements the distinction the addendum draws (three summary values across
three sessions = one unit, not multiple units). Absolute reliability measures (SEM, RC,
Bland–Altman, within-unit CV) are implemented and bootstrap-CI'd, and do not depend on
between-unit heterogeneity.

**Still open:**
- The actual repeated unit (which scripted episode(s) will be used) — a protocol design
  decision, not a code one.
- Evidence that the chosen units are matched/comparable across sessions — cannot exist
  before the reliability sessions are run.
- Which family (ICC vs. absolute measures) will actually be used, and why, for this
  study specifically — a proposal, not a code output.
- The heterogeneity/coverage design (episodes spanning the intended operating range,
  not maximised to inflate ICC) — a protocol design decision.

**D7's three representations are all computed** (`analysis/baselines.py`), with the
temporal rule (`B_person,t` and `S_person,t` both computed only from strictly-prior
sessions) enforced and proven with a mutation test, not just asserted
(`docs/D7_BASELINES.md`). Session 1 correctly emits `missing`/`no_prior_history` for
persistent_z, with no fallback. The shipped default estimator/window rule is
`robust_mad`/`expanding` — offered as the vendor's proposal, open for the client to
accept or counter-propose per §4.2's "pick one and justify it" instruction.

The claim→representation mapping (§4.3: POC claim → within-session calibrated;
deployment claim → persistent cross-session baseline) is accepted as stated and is not
altered by anything built so far.

## 5. Decision rules — the acceptance criteria

**§5.1 metric orientation is built as a real, working abstraction**
(`simulation/precision.py`'s `Metric`/`MACRO_F1_METRIC`/`NEG_LOG_LOSS_METRIC`), with `U`
defined so `Δ > 0` always means improvement regardless of which metric is active,
exactly as specified. A real comparison exists (`docs/D6_SIMULATION.md` §11) showing
log loss gives materially better decidability than macro-F1 on this generator's
synthetic data — offered as evidence for the primary-metric choice, not a demand that
it be adopted.

**§5.2 uncertainty**: bootstrap CIs are implemented, resampled at episode/session level
(never trial), always on the *difference*, with a refit-per-replicate variant that
captures training-sample variability too. **The formal permutation test is NOT built**
— its own pre-specified exchangeability unit, ≥1000 permutations, and an actual null
distribution/p-value are not implemented anywhere. `controls/time_shuffle.py` is a
related but explicitly distinct diagnostic (stamped
`not_a_permutation_test_pvalue: True` on every result) and must not be read as
satisfying this requirement.

**§5.3/§5.4 (Gate 3 rule, RETAIN/DROP/INCONCLUSIVE)**: the formulas are accepted as
specified. No code computes either, correctly — there is no real M_core/M0b (blocked on
D2) and no threshold has been proposed. **OPEN — `δ_Gate3`, `δ_attention`, `δ_audio`,
`δ_latent` all remain to be proposed and justified**, each separately, in units of `U`.
`artefacts/precision_analysis_v2.md` applies this exact arithmetic shape to illustrative
candidate δ values on simulated data only, explicitly not as a real verdict — useful
context for choosing real thresholds, not a substitute for choosing them.

## 6. Data integrity and temporal leakage

§6.2 split hygiene is implemented as specified (chronological, episode-respecting,
train-only fitted preprocessing, nested temporal model selection) —
`simulation/precision.py`, verified in `tests/test_precision.py`.

§6.3 leakage controls are built (`controls/leakage.py`, four variants) and exercised on
synthetic data only. **What counts as a substantial difference for this task is
OPEN** — unproposed, and cannot meaningfully be proposed from synthetic data alone (see
`docs/CONTROLS.md` §3's task-conditional caveat: this generator cannot even establish
the expected *direction* for the `post_action` variant).

§6.4 timestamp integrity: not yet checkable — no real capture session with the
described synchronisation requirements (webcam/audio/software events, ROI coordinates)
exists yet.

## 7. D4 — Reproducibility

Same-environment determinism is demonstrated, not just claimed: `reproduce.py` run
twice on this machine produced identical output for every results table and figure
except the two fields expected to differ (`experiment_id`, `captured_at_utc`).
Cross-environment tolerance is recommended (`1e-6` absolute,
`compare_results.py`) but not yet validated against a genuinely different machine — no
second machine was available this session. **The named-executor acceptance test (Gargi
running the command on a clean machine) has not happened.** The confirmatory scope
(regenerating a result from real archived video and a real logged feature stream) does
not exist yet — today's command regenerates the synthetic/self-contained analysis
machinery only.

## 8. D5 — Actual action

Acknowledged as a named funded-phase open item. No claim in this repository implies
on-screen action capture validates real-world/off-screen action.

## 9. D6 — Precision simulation

Built (`simulation/generator.py`, `simulation/precision.py`, five sweep passes,
`docs/D6_SIMULATION.md`). Serial dependence, learning, fatigue, class-frequency drift
and bursty missingness are all modelled and stated as invented assumptions, not
measured ones. The escape hatch is exercised for real: the worst grid cell (shortest
session × rarest class frequency) already shows some illustrative δ thresholds are
unreachable at the study's planned N — reported as arithmetic, offered as input to the
feasibility decision, not a recommendation. All of this is on synthetic data; no real
trial data exists to calibrate any generator assumption against.

## 10. Controls

Built and exercised on synthetic data (or, for null-input, only unit-tested at the
pure-computation level): positive blink control, null-input control, negative control,
leakage harness, time-shuffle. Full detail and per-control caveats in
`docs/CONTROLS.md`. Three items explicitly **OPEN, requiring a physical run this
session could not provide**:
- 10 real one-minute blink clips + manual counts (§10.1) — zero recorded.
- The null-input control's actual 10-minute camera run (§10.2) — never executed, live
  or otherwise.
- The pass criterion for the positive control (event-matching tolerance is
  implemented as `matching_tolerance_ms=150`; the pass criterion values stored in
  `controls/blink_positive.py` — `criterion_event_f1=0.80` etc. — are this session's
  *proposal*, hashed and traceable, never compared against anything in code; the
  client's sign-off on these specific numbers is still needed).

§10.5 modality ablation, §10.6 context stress test, §10.8 sensor swap, §10.9 audio
acquisition: all **OPEN**, blocked on the audio keep-or-remove decision, D2, hardware,
or a physical two-session recording, respectively — none is a code gap.

§10.7 synthetic latent recovery is built and run (`simulation/latent_recovery.py`,
`docs/D6_SIMULATION.md` §13) — the machinery-validation step the addendum requires
before M2 touches real data. **The recovery-error success threshold is OPEN** —
unproposed; this session's placeholder EMA pipeline reaches `pearson_r≈0.70`,
`rmse_std≈0.77` on its best synthetic grid cell, reported as a property of the
placeholder only, not compared against any threshold and not a preview of the eventual
method's performance.

## 11. D8 — Attention validity

**OPEN in full.** No statistic, null distribution, minimum effect, required N,
uncertainty interval, or failure rule has been proposed for D0PA1's own Gate 2 (distinct
from the POC's already-run, unrelated Gate 2 — see CLAUDE.md's naming-collision table).
One piece of directly relevant background, flagged honestly rather than discovered
later: pitch (looking up/down) is structurally unrecoverable from this single-camera
pipeline (confirmed empirically — a maximal, verified chin-to-chest look-down still
read ~0.1° pitch; root-caused to face foreshortening, not a fixable bug). Only yaw is
reliable. This elevates the risk that a D8 criterion covering the pitch axis fails,
however it is specified — flagged now, not after the test is run.

## 12. Scope corrections

§12.1 LLM read: accepted and implemented as a one-directional terminal call
(`Features → model → LLM interpretation → TERMINAL`), verified with a real logged
exchange (`docs/PRIVACY_EVIDENCE.md` §4). No code path feeds the LLM's output back into
feature extraction, calibration, state estimation, prediction, or model updating —
confirmed by reading the call graph; no dedicated automated test asserts this
structurally the way the D1 separation test does for attention/audio, which would be a
reasonable future hardening.

§12.2 wording: accepted and in use. The exact required phrase ("implemented; pilot-scale
candidate signals; not validated as psychological constructs") is codified in CLAUDE.md
and shown in a real logged agent prompt.

## 13. A-column verification

Done — `docs/AUDIT_A_COLUMN.md`, re-checked against committed code with commit
hashes and artefacts. Result: 9 of 11 items VERIFIED, 2 (blink detection, coarse
gaze) PARTIAL — both because the only logged artefact predates a real correction to
the code; neither has a post-correction live-camera confirmation yet.

## 14. Repository, provenance and data integrity

Raw/identifying data has never entered git history — verified by a whole-tree
magic-byte content scan, not just by extension, and re-confirmed with every
`docs/PRIVACY_EVIDENCE.md`-style check performed since. A data manifest is committed
(`manifest/data_manifest.csv`), a variant log is running (`logs/variant_log.jsonl`,
append-only, demonstrated not merely asserted), and this pre-registration is now
committed and pushed as part of this session's work (§14's own instruction).

**Still open:** a tagged, frozen confirmatory release (no git tag exists yet —
correctly, since confirmatory collection hasn't started); genuine held-out-data
storage separate from the working repository. Per the addendum's own escape hatch
("if a genuine separation is impractical for a single developer, say so and we record
the limitation rather than claiming a control that does not exist") — that is the
honest status today: no held-out storage separation exists, and none is claimed.

## 15. Canonical log and data manifest

Built and versioned (`schema/canonical_log_v1.json`, `schema/canonical_log_writer.py`),
including `context_id`/`device_id` as required fields on every record. **Not yet wired
into any live capture loop** — no real capture session writes through this schema
today; it exists and is validated in isolation.

## 16. Stopping and exclusion rules

See `docs/STOPPING_AND_EXCLUSION_RULES.md`. **All eight required categories are OPEN**
— named and tracked, no actual rule content proposed yet for any of them. This draft
does not fill them in; per this task's own instruction, inventing rule content here
rather than in a dedicated review would risk exactly the outcome-dependent,
after-the-fact rule-writing §16 exists to prevent.

## 17. Privacy and retention

See `docs/PRIVACY_AND_RETENTION.md`. A retention/deletion mechanism is built this
session (config-hashed retention period and storage location, a deletion log, dry-run
default). **The actual retention period and actual storage location remain OPEN
decisions** — the mechanism accepts either as a parameter without presupposing an
answer. Access control, a written pseudonymisation policy (distinct from the
already-real anonymous-code mechanism), and a raw-video/audio retention rule are all
**OPEN / not yet addressed**, the last because no raw video/audio exists to have a rule
for yet.

## 18. Change control

Acknowledged and followed by this session's own practice: `docs/STATUS_REPORT_ERRATA.md`
corrects the prior Build Status Report by dated erratum, not by silent edit — the same
discipline this section requires for any future substantive change.

## 19. Sign-off matrix

See `docs/MATRIX_ROW_MAP.md` for the full 30-row table with per-row module/document
citations and repository-derived status. Summary: several rows are genuinely
IMPLEMENTED and ready for the client's sign-off as built; several are
IMPLEMENTED-BUT-NEVER-RUN-ON-REAL-DATA (the mechanism is right, real data hasn't
touched it); several are correctly DEFINED-NOT-IMPLEMENTED because a threshold/verdict
must not be coded before sign-off (G1); several are BLOCKED-ON-CLIENT-DECISION (D2,
audio, sensor-swap hardware); a few are NOT-APPLICABLE-IN-REPO (collection-protocol
items, not code).

## 20. Execution sequence

This session's work corresponds to steps 1–4 of the client's own 16-step sequence
(Gate 0 infrastructure; null-input + negative control code, though the null-input
control's own live run has not happened; A-claim verification + D1 dependency map;
returning what can honestly be returned of the D2–D8 operational definitions and this
matrix). Step 5 (sign-off, pre-registration committed and pushed) is what this
session's commit accomplishes for the *committing* half — the actual sign-off remains
the client's and the vendor's to complete, not this document's to declare on their
behalf.

## 21. Final instruction

This draft is the operational-definitions-and-evidence-plan return against §19, to the
extent it can honestly be returned today. It is not a claim that every candidate
representation will succeed, and several of its own OPEN items are exactly the
uninterpretable-result risks (D8's pitch limitation, D2's block on nearly everything
downstream) the addendum asks to be surfaced rather than discovered later.
