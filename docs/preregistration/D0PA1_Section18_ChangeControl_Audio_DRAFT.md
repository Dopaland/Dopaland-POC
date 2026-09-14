# D0PA1 — §18 Change Control Record

**CC-001 · Retention of Δ_audio and authorisation of audio acquisition**

> **STATUS: DRAFT — PROPOSED, NOT IN FORCE.**
> Nothing in this record takes effect by appearing in it. It is in force only
> once signed under the client's own §18 process (§9 below).

---

## 1. Identification

| Field | Value |
|---|---|
| Change reference | D0PA1-CC-001 |
| Raised by | Vendor (modeller) |
| Frozen document affected | `D0PA1 POC Scope & Acceptance v0.5.1` |
| Addendum rows affected | Clarifications v0.7 — §19 rows 19 and 23; Decision A |
| Vendor documents affected | `D0PA1_Section19_SignOff_Response.docx` §4.19, §4.23; `docs/MATRIX_ROW_MAP.md` |
| Date raised | 2026-09-13 |
| Status | PROPOSED |

---

## 2. What changed

The sign-off response (§4.23, Decision A) recommended that **Δ_audio be formally
removed** from the POC, on the grounds that no microphone module, no capture path
and no clock-synchronisation method existed, and that the client's §10.9 makes
absent acquisition permanently disqualifying.

The client's decision was the opposite: **Δ_audio is RETAINED, and audio
acquisition is authorised.**

This reverses the vendor's own written recommendation and alters the modality set
of a frozen scope document.

---

## 3. Why this requires change control rather than a note

Scope v0.5.1 is frozen. A decision that reverses a frozen document's disposition
of an entire modality is a substantive scope change whether or not anyone regards
the added work as small.

The specific risk §18 exists to prevent is exactly the one present here: the
engineering record (`docs/AUDIO_ACQUISITION.md`, `CLAUDE.md`, `docs/PROJECT_STATE.md`)
already documents the decision and everything built under it. If that were left to
stand as the whole record, the scope change would have taken effect **by drift** —
the same failure mode the response's own §4.23 argued against when it insisted the
keep-or-remove question be decided deliberately rather than by silence.

The engineering documents record that the change exists and what it produced.
**They are not the change-control record. This is.**

---

## 4. What has been built under this authorisation — complete list

| Component | Location |
|---|---|
| Acquisition thread (`AudioAcquisitionThread`, sounddevice callback-based, structurally decoupled from the T1/T2 video threads) | `audio_acquisition.py` |
| Per-chunk integrity logging — availability, chunk continuity, missingness; **no content analysis** | `audio_acquisition.py` |
| Independent audio consent, architecturally unreachable when declined | `stage1_step7_consent.py` |
| Env-var-only storage configuration; no committed path literal | `privacy/audio_storage_config.py` |
| Pre-commit privacy guard extended — 10 additional container extensions, 5 additional magic-byte signatures, each demonstrated firing on a real payload | `.githooks/pre-commit`, `.gitignore` |
| Feature-separation guard extended to cover `audio_acquisition.py` as direct `U_t` content | `tests/test_feature_separation.py` |
| Tests | `test_audio_acquisition`, `test_audio_storage_config`, `test_consent_audio_gate` |

---

## 5. What has explicitly NOT been built, and will not be without a separate instruction

- **No audio feature of any kind exists or is planned.** `features/audio.py`
  remains an empty stub.
- No prosody, no arousal-from-voice, no emotion-from-speech, no valence, no
  stress, no speaker state.
- Audio feature definitions remain **the client's to sign off**, under the same
  rule as every other new signal in this project.
- **G5 is preserved:** this change adds provenance, consent and integrity
  infrastructure. It adds **no new affect signal**.
- **D1 is preserved:** `U_t → X_core` and `U_t → E_t` remain forbidden and
  machine-checked. Acquisition is a `U_t`-class module and is covered by the
  separation guard as such.

---

## 6. What this change does *not* yet satisfy

The response's own §4.23 set two conditions for retention. Their current state:

**(a) A documented clock-synchronisation method between audio and video, with
measured drift — NOT SATISFIED.**
Five attempts across two sessions. Audio-side transient detection succeeded every
time; video-side motion detection never produced a trustworthy match — too
sensitive gave false matches from ordinary motion, too strict gave 0–3 events. One
run's noisy figures were deliberately not reported as a result. **No offset, spread
or drift figure exists.** A redesigned light-flash attempt is specified and not yet
run (see CC-001-A).

**(b) Recorded microphone availability, audio quality and missingness per session —
INSTRUMENT ONLY.**
The logging exists; no session has been collected under it.

**Consequence, stated plainly:** the acquisition build does not on its own lift
§10.9's disqualification. Until (a) is satisfied, **Δ_audio cannot be computed**,
and retention buys a capability that is not yet usable. This record authorises the
change; it does not claim the modality is ready.

---

## 7. Consequential matrix reclassification — proposed, requires client confirmation

The client's decision resolves two rows that the response recorded as awaiting it.
The vendor proposes, the client confirms; these are **not applied** until signed.

| Row | Current | Proposed | Basis |
|---|---|---|---|
| 19 · Modality ablation | DECISION REQUIRED | RETURNED | Contingency on Decision A is discharged. `δ_audio = 0.05` proposed on the same reasoning as the other components, to be revisited once acquisition quality is known — an unmeasured modality's achievable contribution cannot be sensibly bounded in advance. |
| 23 · Audio acquisition | DECISION REQUIRED | RETURNED *(conditional)* | Acquisition is built and has been exercised against a real microphone. The sync measurement under §6(a) is outstanding and blocking. Not EVIDENCED, because the condition the row's own text sets is unmet. |

**Resulting §19 counts if confirmed:**
12 EVIDENCED · 6 BUILT, NOT YET RUN ON REAL DATA · **11** RETURNED · **1** DECISION
REQUIRED (row 22, sensor swap) — 30 rows, none unassigned.

---

## 8. Cost and schedule impact — to be completed before signature

Per Decision 30, the original Rs 45,000 figure was scoped against the webcam POC,
not against this pre-registered study, and not against audio acquisition at all.

This record states that the change carries a schedule and cost consequence. It
deliberately **does not quantify it here.** Quantify it before signature, not after
— a change control signed with an empty impact field is how unpriced work becomes
contractual.

---

## 9. Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| Vendor — proposed | | | |
| Client — accepted | Gargi | | |

**Nothing in this record is confirmed by appearing in it.**

---

## Appendix — CC-001-A: the outstanding sync measurement

Raised here so that the unmet condition in §6(a) has a named owner and a defined
completion test rather than sitting as a general gap.

- **Blocking:** Δ_audio computation; row 23 reaching EVIDENCED; §10.9 clearance.
- **Blocked on:** nothing but machine time and one physical run.
- **Method:** specified separately in the closure pack (`D0PA1_PENDING_CLOSURE_PACK.md`,
  Part D). The detection rule is pre-registered **before** the run, per G1.
- **Completion test:** a reported offset with a stated spread across ≥ 20 matched
  events and a drift estimate across the run, or an explicit statement that the
  measurement failed again and why. A noisy number reported as a result is worse
  than a documented failure.
