# D0PA1 — §18 Change Control Record

**CC-001 · Retention of Δ_audio and authorisation of audio acquisition**

> **STATUS: SIGNED 2026-09-25 — IN FORCE.**
> Signed client-side by DOPALAND under the client's own §18 process (§9 below). It was
> signed **without a cost or schedule figure** (§8), and proposer and signer are the same
> party (§9.1). Both are disclosed, not obscured.

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
| Status | SIGNED 2026-09-25 |

---

## 2. What changed

The sign-off response (§4.23, Decision A) recommended that **Δ_audio be formally
removed** from the POC, on the grounds that no microphone module, no capture path
and no clock-synchronisation method existed, and that the client's §10.9 makes
absent acquisition permanently disqualifying.

The client's decision was the opposite: **Δ_audio is RETAINED, and audio
acquisition is authorised.**

This reverses the vendor's own written recommendation and alters the modality set
of a frozen scope document. (Vendor and client here are the same party; that is recorded
in §9.1.)

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

## 6. What this change does *not* satisfy

The response's own §4.23 set two conditions for retention. Their current state:

**(a) A documented clock-synchronisation method between audio and video, with measured drift —
NOT SATISFIED, AND CLOSED AS A DOCUMENTED OMISSION.**

Nine attempts across five sessions did not produce a usable measurement. The stimulus changed
twice — hand clap with motion detection, then a brief luminance flash, then a 500 ms held flash
with a lengthened click. Two defects were found by code review and corrected before the final
attempt: the video reference timestamp marked the *end* of the flash while the audio reference
marked the *start*, biasing every offset by approximately one flash duration (predicted
−500 ms, observed −502.5 ms); and the diagnostic statistic used to characterise response
strength spanned the full window including pre-stimulus time, so ambient noise could be
reported as the stimulus response.

**Video-side registration was diagnosed and fixed** — a real and durable result. Nineteen of
nineteen evaluable emissions register cleanly at 19×–72× the detection threshold. The mechanism
was flash duration: a ~3-frame flash against a ~33 ms camera exposure period made detection
close to a coin flip, and a 500 ms held flash removed the problem entirely. Emitter operation
is confirmed directly from the diagnostic session onward — flash render and audio callback
timestamps are recorded, not assumed.

**Audio-side registration fails, and the cause is not characterised.** An earlier attribution to
ambient noise rested on the diagnostic statistic since found defective; it does not stand and is
not replaced with another. There is a specific reason the cause cannot be recovered from this
record: **the stimulus and the onset detector changed together at attempt 6** — attempts 1–5
used a hand clap with a percentile-threshold detector, attempts 6–9 a speaker-emitted click with
a rolling-median-plus-MAD detector — and no attempt isolates one from the other.

**Consequence:** Δ_audio cannot be computed. §10.9's condition is not lifted by the acquisition
build alone. A working acquisition pipeline is not a working synchronisation measurement.

This is stated under your §21 request that infeasibility be reported rather than implemented. It
is a legitimate, evidenced outcome: the video half is solved, the audio half is not, and why it
is not is honestly unknown. No further attempts are proposed.

**(b) Recorded microphone availability, audio quality and missingness per session —
INSTRUMENT ONLY.**
The logging exists; no session has been collected under it.

**Consequence, stated plainly:** the acquisition build does not on its own lift
§10.9's disqualification. With (a) unmet — closed as a documented omission, with no work
planned to meet it — **Δ_audio cannot be computed**, and retention buys a capability that
is not usable in this engagement as it stands. A synchronisation measurement in a later
phase, with different equipment, is not ruled out; it is simply not pending. This record
authorises the change; it does not claim the modality is ready.

---

## 7. Consequential matrix reclassification — confirmed and applied (documented here, not requested)

The client's decision resolves two rows that the response recorded as awaiting it. That
reclassification was **confirmed in `D0PA1_Client_SignOff_001.md` §4** and **applied at commit
`00d3a92`** (`docs/MATRIX_ROW_MAP.md` rows 19 and 23 and its count line, plus the response
`.docx`). This record documents the consequence; it does not request it, and signing this record
adds nothing to it (§9.1).

| Row | Before | After (confirmed) | Basis |
|---|---|---|---|
| 19 · Modality ablation | DECISION REQUIRED | RETURNED | Contingency on Decision A is discharged. `δ_audio = 0.05` nats (accepted, conditional, in `SignOff_001` §2) is set on the same reasoning as the other components, to be revisited once acquisition quality is known — an unmeasured modality's achievable contribution cannot be sensibly bounded in advance. |
| 23 · Audio acquisition | DECISION REQUIRED | RETURNED *(conditional)* | Acquisition is built and has been exercised against a real microphone. The sync measurement under §6(a) is now closed as a documented omission, not outstanding work — the condition remains unmet, and no further attempt is proposed. Not EVIDENCED, because the condition the row's own text sets is unmet. |

**Resulting §19 counts, as recorded in `docs/MATRIX_ROW_MAP.md`:**
12 EVIDENCED · 6 BUILT, NOT YET RUN ON REAL DATA · **11** RETURNED · **1** DECISION
REQUIRED (row 22, sensor swap) — 30 rows, none unassigned.

---

## 8. Cost and schedule impact

Per Decision 30, the original Rs 45,000 figure was scoped against the webcam POC,
not against this pre-registered study, and not against audio acquisition at all.

**This record was signed on 2026-09-25 without a cost or schedule figure, by the
signatory's decision.** The change carries a cost and schedule consequence, and that
consequence remains **unquantified and open**. Nothing in this record prices the work,
and the signature is not to be read as agreement to any figure, including the Rs 45,000
above. Signing with this field unquantified is the risk this section previously warned
against, and it is recorded here as a known and accepted gap rather than left implicit.

---

## 9. Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| Vendor — proposed | | | |
| Client — accepting | DOPALAND, by Debanjan Das | Debanjan Das | 2026-09-25 |

### 9.1 Signing capacity — a disclosed limitation

**Proposer and signer are the same party.** This record is raised by the vendor (modeller) and
accepted client-side by DOPALAND, which is the same solo operation. The governing documents
assume those are different parties, and here they are not.

This is recorded rather than obscured. A solo vendor cannot supply an independent signer, and
the honest response is to state the constraint — the same basis on which the held-out blinding
limitation is recorded.

**No precedent is claimed for this.** `D0PA1_Client_SignOff_001.md` was also signed client-side
by the same party, but its capacity note states that proposer and signer are different parties.
That statement is inaccurate as applied. It is recorded as a correction rather than relied on
here.

**What this signature does and does not carry:**

- It **authorises** the audio acquisition work described in §4, which was built under a client
  decision and until now had no change-control record. Leaving it unsigned would mean the build
  stands on no authorising document at all — the drift §18 exists to prevent.
- It **adds nothing to the status of §19 rows 19 and 23.** Their reclassification was recorded
  in `D0PA1_Client_SignOff_001.md` §4 and applied in `docs/MATRIX_ROW_MAP.md` at commit
  `00d3a92`. This record neither confirms nor reopens them; they stand or fall on that record.
- It does **not** assert that Δ_audio is computable. §6(a) stands: synchronisation is a
  documented omission, and §10.9's condition is not lifted.

**Nothing in this record is confirmed by appearing in it.**

---

## Appendix — CC-001-A: the sync measurement, closed as a documented omission

**Closed.** Nine attempts across five sessions; see §6(a). The completion test is defined in
`docs/D0PA1_PENDING_CLOSURE_PACK.md` §D.5, and in this appendix as first committed (`e724167`).
Its measurement branch — in summary, a reported offset with a stated spread across ≥ 20 matched
events plus a drift estimate — was not met: the best attempt produced 6 matched events of 20,
the final attempt 2 of 20.

The alternative outcome this appendix allowed for — "an explicit statement that the
measurement failed again and why" — is what was delivered, with the qualification that the *why* is
established only for the video half. This item is closed and requires no further work.
