# D0PA1 — §18 Change Control Record

**CC-002 · Audio-derived terminal interpretation (demonstration and interface only)**

> **STATUS: PROPOSAL PHASE — HELD. Not submitted for signature, not withdrawn, not in force.**
> In force only once signed under §18 (§10 below).
>
> **Origin, stated plainly:** this is a **vendor-originated proposal**, not a client request.
> It is raised through change control precisely because it originates on the vendor side —
> under a pre-registration, a vendor adding capability to a frozen scope is a more serious
> matter than a client asking for it, not a lesser one.

---

## 1. Identification

| Field | Value |
|---|---|
| Change reference | D0PA1-CC-002 |
| Raised by | Vendor (modeller) |
| Origin | Vendor initiative — not requested by the client |
| Frozen document affected | `D0PA1 POC Scope & Acceptance v0.5.1` |
| Related | CC-001 (audio retention); `docs/AUDIO_ACQUISITION.md` scope line |
| Date raised | 2026-09-16 |
| Status | PROPOSAL PHASE — HELD |

---

## 2. What is proposed

A **terminal-output-only** interpretation of captured audio:

```
microphone → local extraction → Claude API → interpretation → DISPLAYED and LOGGED → dead end
```

Nothing derived from audio reaches `X_core`, `E_t`, the predictive model, calibration, the
baseline, or the target. It is a demonstration and interface capability, architecturally
identical in its position to the existing personality read.

---

## 3. Why this is architecturally permissible — the edge analysis, stated explicitly

D1's forbidden edges are:

```
FORBIDDEN:  A_t → X_core    A_t → E_t    U_t → X_core    U_t → E_t
```

The terminal LLM read is **neither `X_core` nor `E_t`**. An audio-derived value reaching a
terminal display therefore traverses no forbidden edge.

The companion rule — *the LLM read is TERMINAL OUTPUT* — constrains where the LLM's **output**
may go: never back into feature extraction, calibration, state estimation, prediction, target
construction or model updating. It places no constraint on the LLM's **input**.

**This analysis is offered for the client's scrutiny, not asserted as settled.** If the client
reads D1's intent more broadly than its literal edge list, that reading governs and this
proposal should be declined on that basis.

---

## 4. What this explicitly does NOT do

| | |
|---|---|
| **No Δ_audio** | The modality ablation is `M_core` vs `M_core + U_t` **at test time**. A terminal display never reaches the model. CC-001's retention purpose remains unmet by this change, and this proposal does not claim otherwise. |
| **No validated signal** | Any interpretation is stamped `validated:false` and described as demonstration output. "An LLM finds this voice tense" is a plausible-sounding output with no validation behind it. |
| **No new model input** | `features/audio.py` remains an empty stub. This code does not live in `features/` at all. |
| **No affect claim** | Nothing here adds to Valence, Arousal, or any vector. The V/A mapping is untouched. |
| **No verdict** | No threshold, no pass/fail, no score (G1). |

**The standing honest-framing precedent applies:** V_bf produced confident numbers and measured
nothing consistent across elicitations. Producing plausible output is not evidence of measuring
anything. This capability must never be presented as a measurement.

---

## 5. What would be built

| Component | Note |
|---|---|
| Local extraction from the captured audio stream | **Definition is the client's — see §7.** No extraction is implemented before that definition is signed. |
| Claude API call carrying the extracted representation | Not raw audio unless §7 selects that option |
| Terminal display + JSONL log, stamped `validated:false` | Same treatment as the existing personality read |
| **Machine-checkable separation guard** | Forbidden edges from this module into `x_core`, `episodes`, the model and the target — extending `tests/test_feature_separation.py`, **each demonstrated failing on a deliberate violation before being relied on**, per this repository's existing standard |
| Independent consent gate | Architecturally unreachable when declined, as with audio acquisition |
| Tests | Extraction, the guard, the consent path, and the `validated:false` stamping |

---

## 6. Privacy and consent — a material change

Audio content leaving the device is a **different posture** from the local capture authorised
under CC-001. The existing consent text, retention policy, and env-var-only storage
configuration were all written for local capture with no content analysis.

Requires, before any implementation:

- Consent language covering transmission of voice-derived content to a third-party API,
  separate from and additional to the audio-capture consent.
- A retention decision for anything transmitted or returned, including whether interpretations
  are stored at all.
- The client's position on the API provider's own data handling, which is the client's to take,
  not the vendor's to assume.

**G4 is unaffected and remains absolute:** no raw audio, and nothing derived from it, enters
git history.

---

## 7. Open decisions — the client's to make

The vendor deliberately does **not** select among these. Whatever is extracted is an audio
feature, and `docs/AUDIO_ACQUISITION.md`'s binding scope line places feature definitions with
the client.

| # | Decision | Options |
|---|---|---|
| 1 | **What is extracted** | (a) non-content acoustic summary — loudness envelope, pitch contour, speech/silence ratio, turn timing; (b) a transcript; (c) both; (d) raw audio to the API |
| 2 | **What the interpretation is asked for** | open-ended description / a named set of dimensions / something narrower |
| 3 | **Whether interpretations are retained**, and for how long | |
| 4 | **Whether option (b) or (d) is acceptable at all**, given they transmit content rather than a summary | |

Option (a) is the smallest privacy footprint and the vendor's suggestion if the client wants
one — offered as a suggestion, not a selection.

---

## 8. What this does not unblock

CC-001's outstanding condition is unchanged: **no clock-synchronisation method between audio
and video exists.** CC-001 §6(a) records it as closed as a documented omission: "Nine attempts
across five sessions did not produce a usable measurement."

The direction of that finding matters. **The video side is solved**: in CC-001 §6(a)'s words,
"Nineteen of nineteen evaluable emissions register cleanly at 19×–72× the detection threshold",
the mechanism being flash duration against the camera's exposure period. **The audio side
fails, and the cause is not characterised**, because "the stimulus and the onset detector
changed together at attempt 6", and "no attempt isolates one from the other". No offset, spread
or drift figure exists. Alignment of any audio-derived value to video or action timestamps
remains impossible until that is measured.

For a terminal display this matters less than it would for a model input — but it must not be
described as resolved.

---

## 9. Cost and schedule impact — to be completed before signature

Per Decision 30, the Rs 45,000 figure was scoped against the webcam POC, not this
pre-registered study, and not against audio work of any kind.

This record states the change carries a cost and schedule consequence and deliberately does not
quantify it here. **Quantify before signature, not after.**

---

## 10. Status and sign-off

**This record is held at proposal phase.** It is not submitted for signature and it is not
withdrawn. It is a vendor-originated idea, recorded so it exists in the change-control trail
rather than in a conversation, and parked until there is a reason to raise it.

Holding it costs nothing. Nothing in the pre-registration depends on it, no §19 row is blocked
by it, and CC-001 is unaffected by its status either way.

**Deliberately not submitted alongside CC-001.** CC-001 authorises work that already exists and
had to be recorded. This is a vendor proposal for new capability. Sending them together would
invite the necessary record to be read as opportunistic, which would not serve either of them.

If it is ever raised for decision, the signature block below applies unchanged, and the privacy
and consent change in §6 is the part that needs answering first.

| Role | Name | Signature | Date |
|---|---|---|---|
| Vendor — proposed | | | |
| Client — accepted / declined | | | |

**Declining this is a perfectly good outcome.** It costs the engagement nothing.

**Nothing in this record is confirmed by appearing in it.**
