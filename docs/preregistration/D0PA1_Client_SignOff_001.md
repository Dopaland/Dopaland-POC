# D0PA1 — Client Sign-Off Record 001

**Signatory: DOPALAND (client) · Date: 2026-09-18**

> **STATUS: SIGNED 2026-09-18 — IN FORCE (§7).** The items in §2–§5 are now the
> pre-registered, frozen values for this study: set before collection, applied by a
> human after it, and not revisable in light of results.
>
> **Capacity.** These are signed **client-side**. The values were proposed and justified by the
> modeller in `D0PA1_Section19_SignOff_Response.docx`; this record is the client's acceptance of
> them. Proposer and signer are different parties, which is the structure the governing documents
> assume.

---

## 1. Prerequisite — one correction that must land before signature

The sign-off response §4.7 derives every threshold in **nats** and states that converting
between nats and macro-F1 is *"unsound as well as impermissible"* — the empirical ratio drifts
from ~1.7× to ~2.4× with effect size.

The leakage-control section then reads:

> "A difference in U exceeding **2 × δ_Gate3, i.e. 0.10 macro-F1 points**"

δ_Gate3 is **0.05 nats**. Twice that is **0.10 nats**, not 0.10 macro-F1 points. The document
performs the conversion it forbids.

**Correction, which this record signs in its corrected form:** the leakage diagnostic threshold
is **0.10 nats**. The source document is to be corrected to match. Nothing else in that section
changes — the "2 ×" multiple and its reasoning stand.

**No item below is in force until this correction is applied.**

**Applied.** `D0PA1_Section19_SignOff_Response.docx` §4.7's leakage-control paragraph now reads
"0.10 nats"; `docs/MATRIX_ROW_MAP.md` row 9 carried the identical conflation and is corrected to
match. Both verified by direct re-extraction after editing, not assumed from the edit alone.

---

## 2. δ thresholds and the verdict rule — ACCEPTED

### 2.1 Values

| Threshold | Value | Status |
|---|---|---|
| δ_Gate3 | **0.05 nats** | Accepted |
| δ_attention | **0.05 nats** | Accepted |
| δ_audio | **0.05 nats** | Accepted, conditional — see §2.4 |
| δ_latent | **0.05 nats** | Accepted, exploratory status unchanged |
| Leakage diagnostic | **0.10 nats** (2 × δ_Gate3) | Accepted as corrected in §1 |

**Primary metric: multiclass log loss, in nats.** Macro-F1 is reported alongside for legibility
and is not a decision variable.

### 2.2 Derivation accepted with the number

A uniform predictor over five classes costs 1.609 nats; the context-only baseline M0b costs
1.337. The baseline therefore captures **0.272 nats** of structure over chance. A core model
adding less than a fifth of that is noise on top of context: 0.20 × 0.272 = 0.054 → **0.05 nats**.

The four δ values coincide **by argument, not by default** — each component carries a comparable
build, validation and failure-mode cost, so each clears the same bar.

### 2.3 Decision rules

```
Gate 3      LB[ U(M_core) − U(M0b) ] > δ_Gate3          → M_core beats baseline

Per component c ∈ { attention, audio, latent }, using δ_c :
RETAIN        lower bound of CI on Δ_c  >  δ_c
DROP          upper bound of CI on Δ_c  <  δ_c
INCONCLUSIVE  CI spans δ_c
```

**No code computes any of this.** The pipeline stores numbers; a human applies these rules after
collection (G1).

### 2.4 Two things accepted along with the numbers

**(a) A known undecidable band.** At the pessimistic precision configuration a true effect of
~0.07 nats yields a lower bound of 0.046 → INCONCLUSIVE. At the realistic configuration the same
effect yields 0.054 → RETAIN. A band of genuinely moderate effects will therefore be decided by
which precision the study happens to achieve. This is accepted knowingly, in advance, and is not
grounds for revisiting the threshold after results are seen.

**(b) δ_audio is signed for a comparison that cannot currently be run.** It was proposed
conditionally, to be revisited "once acquisition quality is known." Acquisition quality is now
known: A/V synchronisation is a documented omission (CC-001 §6(a)), so **Δ_audio is not
computable**. δ_audio = 0.05 is accepted so the threshold is fixed in advance should
synchronisation ever be measured — it is **not** an assertion that the comparison will happen.

**Applied.** All five values are now frozen fields in `simulation/config.py`'s
`PreRegisteredConfig` (`delta_gate3`, `delta_attention`, `delta_audio`, `delta_latent`,
`leakage_diagnostic_threshold_nats`), hashed via `config_hash()`, read by no decision-making code
anywhere in the repository (verified by `tests/test_config.py`) — per G1, a human applies §2.3's
rules against these frozen numbers after collection.

---

## 3. Blink positive control criterion — ACCEPTED

**Event F1 ≥ 0.80 AND per-clip count within ±20% of the manual count on at least 8 of 10 clips.**

Event-matching tolerance ±150 ms, as proposed.

**What this validates, narrowly:** blink-count *detection*. It establishes no psychological
interpretation of blinking. Detector validation is not construct validation, and the report will
not blur the two.

**Applied.** `controls/blink_positive.py`'s `BlinkPositiveConfig` already stored exactly these
values as its proposed defaults; nothing numeric changed. Its own comments and docstring are
updated from "proposed, not a decision" to "accepted" (this record), and still never read back by
any function in that module (G1).

---

## 4. §19 rows 19 and 23 — RECLASSIFICATION CONFIRMED

| Row | From | To |
|---|---|---|
| 19 · Modality ablation | DECISION REQUIRED | **RETURNED** |
| 23 · Audio acquisition | DECISION REQUIRED | **RETURNED (conditional)** |

Basis: the client's keep-or-remove decision on Δ_audio is made — **RETAINED** — which discharges
the contingency both rows carried. Row 23 is conditional because the synchronisation condition in
its own text is unmet and is now recorded as a documented omission rather than pending work.

**Resulting counts: 12 EVIDENCED · 6 BUILT-NOT-RUN · 11 RETURNED · 1 DECISION REQUIRED = 30.**
The one remaining DECISION REQUIRED is row 22, sensor swap.

**Applied.** `docs/MATRIX_ROW_MAP.md` rows 19/23 and its own count line; the response `.docx`'s §4
table (both rows), its §4.19/§4.23 status lines, and its §6 numeric summary paragraph — all
re-verified by direct extraction after editing.

---

## 5. Retention and storage — DECIDED

### 5.1 Raw media retention: **90 days, then automatic deletion**

Applies to video, and to audio if any is ever recorded. Deletion is performed by the existing
routine, which writes a **deletion log recording what was removed and when**, so the claim is
verifiable rather than asserted.

Ninety days covers a full analysis cycle including a delayed reproduction run.

### 5.2 Storage location: **split**

- **Derived feature logs** — numeric values and anonymous participant codes, no imagery —
  remain inside the repository directory, untracked. Low risk; no change.
- **Raw media** — any video or audio — lives in a **defined folder outside
  `C:\Dopaland-POC`**, for the full 90-day retention period.

**Reason, recorded so it is not re-litigated:** a 90-day retention window means raw media exists
for 90 days. Inside a git working tree, `git add -f`, `git commit --no-verify`, an unset
`core.hooksPath`, a fresh clone, or GUI staging each bypass the `.gitignore` and pre-commit
guard — and under G4 a repository that has ever held such media is compromised permanently.
Moving raw media outside the tree removes the only mechanism by which a temporary retention
window becomes an irreversible one. The guards remain in place as a second layer.

Both the retention period and the storage path are **configuration parameters under the config
hash**, not literals.

**Applied.** `privacy/retention.py`'s new `RAW_MEDIA_RETENTION_DAYS = 90.0` (a named constant,
deliberately not a change to `RetentionConfig`'s own generic placeholder default, which still
governs the separate, unaddressed derived-logs bucket). `privacy/video_storage_config.py` (new)
mirrors `privacy/audio_storage_config.py`'s existing env-var-only, no-literal-default,
raises-if-unset pattern for the video side. The unified-single-root pattern
`docs/PRIVACY_AND_RETENTION.md` proposes remains unapplied — see §6.

### 5.3 Derived feature log retention: indefinite

Numeric values and anonymous participant codes only — no imagery, no audio. These logs are the
seed of the Track-B dataset and have no expiry that serves a purpose. Recorded as a decision,
not left to the 365-day placeholder in privacy/retention.py, which is to be updated to match.

---

## 6. What this record does NOT sign

**Decision C — session length, and expected ABANDON / NO_ACTION frequency — remains OPEN.**

These are not scope decisions. They are, in the response's own words, *"two numbers from the
harness you built"* — and the controlled software environment does not exist (Decision 27, still
open, ownership unsettled).

They were also the two largest levers in the precision analysis: session length moves the
confidence-interval half-width by roughly 60%, rare-class frequency by roughly 66%. Together
they select a single cell from the computed grid and determine what precision this study can
achieve.

**Supplying a value today would be inventing the input that decides whether the study can decide
anything.** Until the harness exists and a pilot run measures them, planning continues to use the
pessimistic cell. The same applies to the prediction window [Δt_min, Δt_max], which is to be
derived from the harness's own interaction rhythm.

Also unchanged and still open: **row 22 (second camera)**, the unified raw-media-root proposal,
and everything downstream of the harness.

---

## 7. Signature

| Role | Name | Signature | Date |
|---|---|---|---|
| Client — accepting | DOPALAND, by Debanjan Das | Debanjan Das | 2026-09-19 |

**Nothing in this record is in force by appearing in it.** On signature, the items in §2–§5
become the pre-registered, frozen values for this study: set before collection, applied by a
human after it, and not revisable in light of results.

---

## Erratum — added 2026-09-25, after signature

**The capacity note in this record is inaccurate as applied.** It states that proposer and
signer are different parties. They are not: the values were proposed by the vendor (modeller)
and this record was signed by DOPALAND, which is the same solo operation. A solo vendor cannot
supply an independent signer.

This is stated here rather than by amending the text above, which is signed and is not edited
after the fact. The same limitation is disclosed in CC-001 §9.1, and both are recorded in
`docs/CLIENT_FIGURES.md` §10.

**Date discrepancy.** This record dates itself 2026-09-18 in its header and status line, and
2026-09-19 in its signature row. The correct date is 2026-09-19.

Nothing else in this record changes. The values in §2–§5 remain the frozen, pre-registered
values, set before collection and applied by a human after it.
