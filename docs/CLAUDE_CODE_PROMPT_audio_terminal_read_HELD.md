# Claude Code prompt — audio terminal read

# ⛔ HELD. DO NOT RUN UNTIL CC-002 IS SIGNED.

This prompt is written now so nothing waits on drafting later. **It must not be pasted until
two things are true:**

1. **CC-002 is signed by the client** (`D0PA1_Section18_ChangeControl_AudioTerminalRead_CC002_DRAFT.md`, §10).
2. **§7's four open decisions are answered**, and the answers are filled into the bracketed
   slots below. In particular, decision 1 — *what is extracted* — determines what this code
   does. **Running this with the brackets unfilled would have the vendor inventing an audio
   feature definition, which is the exact thing CC-002 exists to prevent.**

If CC-002 is declined, delete this file. Nothing else in the engagement depends on it.

---

> Paste everything below the line once the two conditions above are met.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. Guardrails G1–G5 bind this task.

**Authorisation:** this work is authorised by change control record CC-002, signed
[DATE], which permits an audio-derived **terminal-output-only** interpretation. Read
`docs/preregistration/D0PA1_Section18_ChangeControl_AudioTerminalRead_CC002_DRAFT.md`
before writing any code. If anything below contradicts that record, **the record wins — stop
and report the contradiction.**

## The architecture, and the one line that must never be crossed

```
microphone → local extraction → Claude API → interpretation → DISPLAYED and LOGGED → dead end
```

**Nothing derived from audio may reach `X_core`, `E_t`, the predictive model, calibration, the
persistent baseline, or the target.** This is not a style preference; it is what makes the
change permissible at all. A guard that proves it is part of this task, not an optional extra.

## Do not touch

- `features/x_core.py`, `features/episodes.py`, `features/geometry.py`, the two-thread capture
  architecture (G5).
- **`features/audio.py` stays an empty stub.** That module is reserved for a `U_t` *model-path*
  feature, which this is not. Do not put anything in `features/` for this task.
- The V/A mapping. Valence stays `z_es`, Arousal stays `z_pd`.

## Build

**1. `audio_terminal_read.py` at the repo root** — beside `audio_acquisition.py`, deliberately
outside `features/`.

**2. Local extraction: [FILL FROM CC-002 §7 DECISION 1].**
Read from the existing capture path in `audio_acquisition.py`. Do not add a second capture
thread; do not change the existing one.

**3. Claude API call.** Send only what decision 1 authorises — nothing more. Read the API key
from the environment; **never commit a literal** (follow `privacy/audio_storage_config.py`'s
existing env-var-only pattern). The request asks for: **[FILL FROM CC-002 §7 DECISION 2]**.

**4. Output.** Terminal display plus a JSONL record. **Every record and every displayed string
is stamped `validated:false`** and labelled as demonstration output. It is never called a
measurement, a reading, a score, or an emotion. Retention: **[FILL FROM CC-002 §7 DECISION 3]**.

**5. Consent gate.** An independent consent, additional to the audio-capture consent, covering
transmission to a third-party API. **Architecturally unreachable when declined** — same
construction as `stage1_step7_consent.py`'s audio gate, not a runtime `if` that can be bypassed.

**6. The separation guard — the load-bearing deliverable.**
Extend `tests/test_feature_separation.py` with forbidden edges from `audio_terminal_read` into
`x_core`, `episodes`, the model path and the target. Cover the static import graph, the call
graph, and a runtime check with the module monkeypatched to raise on any attribute access.
**Demonstrate every new check failing on a deliberate violation before relying on it** — that
is this repository's existing standard and the reason its separation claims are credible.

## Hard constraints

- **G1.** No threshold, no pass/fail, no score, no verdict anywhere in this module. It computes
  and stores and displays. It never decides what anything means.
- **G4.** No raw audio, and nothing derived from it, is ever committed. Check `.githooks/pre-commit`
  coverage still holds for anything this writes.
- **G3.** If any part of this cannot be done as specified, report it. Do not substitute.
- The API key never appears in a log, an error message, or a committed file.

## Tests

Extraction against synthetic input with known properties; the consent-declined path (proving
unreachability, not just that a branch returns early); the `validated:false` stamping on every
output path; and the new separation checks, each demonstrated failing first.

## Verification

1. Golden snapshot still `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8`.
   This change adds no computed value to any existing path, so **any change means you touched
   something you should not have** — stop and report.
2. `tests/test_feature_separation.py` — all checks pass, including the new ones, and each new
   one was shown failing on a deliberate violation.
3. Full test suite passing.
4. `git status` — no media, no audio, no `.env`, no credential.
5. `features/audio.py` still an empty stub — confirm by reading it.

**Do not commit.** Report the diff, the verification output, the failing-first demonstrations
for each new guard check, and anything you could not do — plainly, without substituting an
approach.
