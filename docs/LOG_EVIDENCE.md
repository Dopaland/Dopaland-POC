# Log Evidence — Real Output, Not a Description

**Purpose:** answer, from actual emitted records rather than from code
reading or memory, the client's question:

> Do per-frame vectors reach disk, or only the 10-second aggregates?

**Answer: both reach disk, as two separate record types, on two separate
clocks.** Per-frame (`sample`) records are written at detection cadence
(empirically ~30 Hz, see §2). 10-second aggregates (`window_summary`,
`attention_window_summary`) are written once per completed window, computed
FROM the `sample` stream, never as a replacement for it. This document
records the inspection that produced that answer, against one real session
log, so the client can check every number here against the repository
directly.

**Inspected file:** `logs/session_2be7a0e4-981d-4041-b5ae-197f7b3d4e07.jsonl`
(not committed — git-ignored per `.gitignore`'s `logs/*` rule, CLAUDE.md
guardrail G4). A truncated excerpt was produced for emailing; see §5.

**Provenance of the inspected file, stated plainly:** `person_label:
"TEST_THREE_SIGNAL"` — this is a developer integration-test session
(exercising the three orientation/gaze/blink signals added after Gate 2),
**not** one of the four scored Gate 2 participant captures (`P01`–`P04`,
schema version 1.3, already reported in `GATE2_FINDINGS.md`). It was chosen
over a `P0x` file specifically *because* it is the only schema version
(1.6) that carries every current record type — `sample`, `window_summary`,
`attention_window_summary`, and `calibration_complete` — in one file, which
is what best answers the client's schema/cadence question. It is not being
offered as a Gate 2 result. `TEST_THREE_SIGNAL` is an anonymous label, not
a name — see §4 for the privacy check performed on it specifically.

---

## 1. Record types present, and cadence of each

| record_type | count in this session | written when | driven by |
|---|---|---|---|
| `sample` | 1180 | every detection cycle | continuous sampling loop (CADENCE clarification, CLAUDE.md) |
| `window_summary` | 1 | once per completed 10s window, **starting only after calibration completes** | `episodes.WindowAccumulator` (X_core/E_t) |
| `attention_window_summary` | 3 | once per completed 10s window, **from frame 1** (no calibration needed) | `features.attention.AttentionWindowAccumulator` (A_t, its own independent clock) |
| `calibration_complete` | 1 | once, when the 25s neutral-calibration capture ends | `x_core.NeutralCalibrator` |
| **total** | **1185** | | |

Measured directly from the file (not assumed):

- **Sample cadence:** mean inter-sample interval **33.5 ms** → **~29.8
  Hz** (min 28.5 ms, max 170 ms — the one outlier is a single slow cycle,
  not a pattern). Matches CLAUDE.md's "~20–30/s" claim.
- **Session span:** 39.5 s wall-clock (`ts_monotonic` range).
- **Why only 1 `window_summary` but 3 `attention_window_summary` in the
  same 39.5 s session:** `window_summary` cannot start accumulating until
  calibration finishes (it summarizes *calibrated deviation*, which does
  not exist pre-calibration — Decision 38/40). Calibration took 25.0 s in
  this session, leaving 14.5 s of post-calibration time — enough for
  exactly one completed 10 s window (the second window, 10 s–14.5 s in,
  never reached a flush before the session ended). `attention_window_summary`
  needs no calibration and started windowing from t=0, completing windows
  at 0–10.0 s, 10.0–20.1 s, and 20.1–30.1 s (a 4th, 30.1 s–39.5 s, is
  9.4 s — never flushed, same reason). This is the two-independent-clocks
  design (CLAUDE.md D1: `AttentionWindowAccumulator` never touches
  `WindowAccumulator`), not an inconsistency.

## 2. Field list — one `sample` record, in full

```
schema_version, record_type, session_id, person_label, ts_utc, ts_monotonic,
vectors {v_bf, v_es, v_jc, v_pd},
vectors_deviation {v_bf, v_es, v_pd},
vector_components {
  v_bf {convergence_ratio, drop_ratio},
  v_es {aperture, cheek_raise},
  v_jc {inter_lip_dist, lip_corner_dist, masseter_width},
  v_pd {buffer_len}
},
screen_orientation {score, oriented, unvalidated, label},
gaze_direction {score, gaze_reliable, unvalidated, label},
look_away {value, unvalidated, label},
head_pose {yaw_deg, pitch_deg, roll_deg},
quality {face_detected, pose_detected, face_width_px, z_cm,
         min_face_presence_confidence, min_tracking_confidence},
person_id, calibration_status, calibration_neutral_ref, cycle_time_ms,
va_point
```

**Composites vs. uncomposited components — both are present, every
sample.** `vectors` carries the composited vector value itself (e.g.
`v_bf = -drop_ratio`); `vector_components` carries the raw, uncomposited
pieces that formula combines (e.g. `v_bf`'s `convergence_ratio` and
`drop_ratio` separately). Neither is a subset of the other — a
per-sample record is never composite-only.

Older sessions in this repository (schema 1.0–1.5) carry a subset of
these fields — `screen_orientation`/`gaze_direction`/`look_away` were
added at 1.5/1.6 (the attention-signal work, post-Gate-2); `vectors`,
`vector_components`, `head_pose`, and `quality` go back to 1.0. The full
per-version field history is in `stage1_step4_vectors.py`'s
`SCHEMA_VERSION` comment block, checkable directly.

## 3. Field list — one `window_summary` record, in full

```
schema_version, record_type, session_id, person_label,
window_start_monotonic, window_end_monotonic, window_seconds,
n_samples, n_detected, detection_rate,
yaw_mean_deg, yaw_variance_deg2,
window_quality {low_confidence, reasons},
composite {v_bf, v_es, v_pd -- each {avg, peak, variance, n}},
covariates {v_jc, v_bf_convergence_ratio, v_es_cheek_raise -- each {avg, peak, variance, n}}
```

(`attention_window_summary` is a structurally separate record type — own
`screen_orientation`/`gaze_direction`/`look_away_rate` blocks, own
`unvalidated` stamp — never merged into `window_summary`'s schema; see
CLAUDE.md's ATTENTION SIGNAL section and D1's block-separation rule.)

A `window_summary` is a **derived aggregate of the `sample` stream**
(avg/peak/variance over the samples that fell in its window,
`n = n_samples` in the composite/covariate sub-blocks matching the
window's own `n_samples`) — it is not written from an independent
measurement. Confirmed directly: this session's single `window_summary`
has `n_samples: 303`, and exactly 303 `sample` records fall in its
`[window_start_monotonic, window_end_monotonic]` range.

## 4. Privacy check performed on this file (§2.2 of the task)

Checked programmatically against **all 1185 records** in the file (not a
sample of them):

- **No name, no face data, no image or video content.** Every record's
  keys and values were walked recursively; no key name matching
  name/email/image/photo/video/face_id/encoding/embedding/address/phone
  was found anywhere in the file. The longest string value in the entire
  file is 134 characters (a descriptive `label` string, e.g. "screen
  orientation (geometric) — NOT attention/engagement"), which rules out
  an embedded base64 image/frame blob (those run to tens of thousands of
  characters minimum).
- **Anonymous participant code only.** All 1185 records carry
  `person_label: "TEST_THREE_SIGNAL"` (the 1180 `sample` records) or the
  same value where the field applies to the other record types — a single
  fixed string, not a name, not derived from Face-ID (Face-ID is out of
  scope per CLAUDE.md).
- **The participant-identity field (`person_id`) is null throughout.**
  Present in 1180/1185 records (the `sample` records; the three
  aggregate/calibration record types don't carry this field at all —
  they identify the person via `person_label` only). Of those 1180,
  **0 have a non-null `person_id`** — checked by iterating every record,
  not sampled.

All three hold. This file was nominated for the client on that basis.

## 5. Excerpt for emailing

The full file is 2,895,560 bytes / 1185 records — too large and, per G4,
not something to commit. A truncated excerpt preserving the full field
structure was produced instead:

**Location (NOT tracked by git, local to this machine):**
`C:\Users\Abcom\AppData\Local\Temp\claude\C--Dopaland-POC\dc96b8e6-ac10-4f66-b877-40f4725433af\scratchpad\session_2be7a0e4_EXCERPT_for_client.jsonl`
(57,053 bytes, 29 JSON lines)

Contents: all 8 pre-calibration `sample` records at the very start of the
session (so the client can see `calibration_status: "calibrating"` and
null `vectors_deviation`/`va_point` in that state), all 5 non-`sample`
records in the file (`calibration_complete`, the one `window_summary`, all
three `attention_window_summary` records — none omitted, there are few
enough to include in full), the first 8 `sample` records after calibration
completes, and 4 `sample` records from the temporal midpoint of the
session — a real, non-cherry-picked span rather than only the first N
rows. Each omitted stretch is marked with an explicit `_excerpt_note`
line so the gap is visible, not silent.

This excerpt file is for emailing to the client directly — it is not part
of this repository and was not committed.
