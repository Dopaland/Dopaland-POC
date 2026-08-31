# Signal Completions — Part C (C1–C4)

**Files:** [`features/robust_baseline.py`](../features/robust_baseline.py) (C1) ·
[`features/signal_quality.py`](../features/signal_quality.py) (C2) ·
[`simulation/fps_logger.py`](../simulation/fps_logger.py) (C3) ·
`compute_coverage()` in `features/signal_quality.py` (C4) · wiring in
[`stage1_step4_vectors.py`](../stage1_step4_vectors.py)

**G5 discipline:** every module here is new and additive. Nothing that
computes a validated-path formula or return shape was modified —
`features/x_core.py`, `features/episodes.py`, and `features/geometry.py`
are untouched (confirmed: `git diff` against those three files is empty).
The wiring into `stage1_step4_vectors.py` touches only `capture_thread()`
and `processing_thread()`, which `tests/test_refactor_snapshot.py`'s own
docstring already states are outside its golden-tested surface (they
require a live camera/real MediaPipe detection, not a pure function of
landmark inputs). The golden snapshot was re-run after this work and
**MATCHES** — see the final section below.

---

## C1 — MAD-based robust baseline

`features/robust_baseline.py`: `mad_stats()`, `mad_z_score()`,
`robust_calibration_reference()`, `robust_deviation()`.

- `z = (x_t − median_s) / (1.4826 × MAD_s)`, `1.4826` used exactly.
- Computed **alongside** `NeutralCalibrator`'s existing mean/std
  calibration, never replacing it — both are now logged in the same
  `calibration_complete` record (`reference` = mean/std, `robust_reference`
  = median/MAD, sibling fields) and the same per-sample `record`
  (`vectors_deviation` = mean/std-based, `vectors_robust_z` = MAD-based).
- **MAD == 0 handled explicitly, no division by zero, no silent epsilon**:
  `zero_dispersion` is judged against
  `PRE_REGISTERED_CONFIG.zero_dispersion_epsilon` (Gate 0 A2's single
  hashed source for this exact judgment — reused, not re-invented) — this
  is a *threshold deciding whether to compute z at all*, not an epsilon
  added into a division. When crossed, `mad_z_score()` returns `None`
  (missing), never a finite-but-fabricated number.
- **Why a separate module, not a `NeutralCalibrator` method**:
  `NeutralCalibrator.complete()`'s return shape is captured byte-for-byte
  by the golden snapshot. Adding a field to it would be a real change to
  the validated path (G5), which Part C asked to add *alongside*, not
  *inside*. This module instead reads `NeutralCalibrator.samples` (already
  a public attribute) read-only.
- `tests/test_robust_baseline.py`, 6 checks, all pass — including a
  hand-computed normal case (median/MAD's robustness to a single large
  outlier, verified against mean/std would have been dragged by it), the
  exact-zero case, a **near**-zero (not exactly zero) MAD case shaped like
  V_pd's real dispersion — the failure mode this task exists to prevent —
  and a shorter-than-expected calibration window (`n=0`, `n=1`:
  `insufficient_samples`; `n=2`: computes normally).

---

## C2 — Missingness and confidence on every signal

`features/signal_quality.py`: `classify_signal_missingness()`,
`signal_confidence()`, `signal_quality_record()`.

**Scope, stated plainly:** covers the four X_core vectors — `v_bf`, `v_es`,
`v_jc`, `v_pd` — where `docs/AUDIT_A_COLUMN.md`'s Q2 finding was clearest
and most consequential (these are the validated, Gate-2-scored signals).
**The attention-block pilot signals (V_so/screen-orientation, gaze
direction, blink) are NOT extended by this pass** — see "What is not
covered" below.

- Every sample now carries `record["signal_quality"][sig]` for all four
  signals, always — `{"confidence", "missingness_flag",
  "missingness_reason"}` — never a silent `None` with no explanation.
- `missingness_reason` is drawn from the **same fixed vocabulary** Part B's
  canonical schema defines (`schema.canonical_log_writer.MISSINGNESS_REASONS`)
  — imported, not duplicated, and checked against it at import time
  (`assert _REASONS_THIS_MODULE_EMITS.issubset(...)`, fails loudly if the
  two ever drift). Reasons used: `no_face`, `tracking_lost`,
  `insufficient_samples` (V_pd's own rolling buffer not yet holding ≥2
  samples — a structurally different cause from `tracking_lost`,
  disambiguated rather than conflated), and `quality_gate_rejected` as the
  fallback when the modality *was* detected but a value is still missing
  for an undisambiguated reason.
- `confidence` is derived from the existing, Gate-2-grounded
  `VECTOR_RELIABILITY` static labels (`high`/`medium`/`low` →
  `0.9`/`0.6`/`0.3`) — **not** a new, untested live measurement (G2: no
  tuning without real cross-person data). `v_jc` (`"logged_only"`, no
  reliable directional signal even at max effort) maps to `None` — never a
  fabricated confidence number for a signal with no established
  reliability.
- `tests/test_signal_quality.py`, 8 checks, all pass — including that a
  *present* value is never flagged missing regardless of detection flags,
  each missing-value cause maps to the expected reason, `v_jc`'s
  confidence is never fabricated, and every reason this module can emit is
  a real member of the shared vocabulary.

---

## C3 — Continuous FPS logging as a metric

`simulation/fps_logger.py`: `FPSLogger`.

`docs/AUDIT_A_COLUMN.md`'s Q1 finding: FPS was measured and printed every
run, but only written to a **file** as a continuous time series in `--soak`
mode (opt-in, exercised exactly once in this repository's history). This
closes that gap — `FPSLogger` now runs in **every** run, not just soak
mode: `capture_thread()` writes `logs/fps_capture_<session_id>.jsonl` and
`processing_thread()` writes `logs/fps_processing_<session_id>.jsonl`,
each flushing one record every `FPS_REPORT_INTERVAL_SECONDS` (already
Gate-0-A2-sourced from `PRE_REGISTERED_CONFIG`), stamped with
`experiment_id` (from `RunProvenance`, captured once in `main()` — **not**
at module import time; see below), and carrying `frames_captured`,
`frames_processed`, `frames_dropped`, and `drop_reasons`.

**Why provenance capture moved out of module import**: `capture_run_provenance()`
shells out to git twice and measured **~0.5 s** on this machine.
`stage1_step4_vectors.py` is imported by many other scripts/tests
(`tests/test_refactor_snapshot.py`, `controls/null_input.py`,
`analyze_video.py`, `stage3_demo_ui.py`) that never run the live pipeline —
capturing provenance at import time would have added that cost to every
one of them. `RUN_EXPERIMENT_ID` starts `None` at import and is set once,
inside `main()`, only for a real consented run; `capture_thread`/
`processing_thread` are confirmed (by search) to be invoked only via
`main()`, so reading the global from either thread is always safe.

**What "dropped" covers, and what it doesn't, stated honestly:** the
capture thread now counts a real, mechanically detectable drop condition —
`cap.read()` returning `not ok` — under reason `capture_read_failed`.
It does **not** detect a frame silently overwritten in the single-slot
buffer before `processing_thread` ever reads it (a genuine drop under
CLAUDE.md's "stale frames discarded" architecture). Detecting that would
need additional synchronization state (e.g. a per-frame consumed flag) on
top of the existing lock-protected single-slot buffer — a real change to
buffer *behavior*, not just bookkeeping, and out of this task's safe,
additive scope. Stated here as a known limitation, not silently omitted.

- `tests/test_fps_logger.py`, 5 checks, all pass, entirely with synthetic
  timestamps — no camera needed. Covers: no flush on the first call (only
  starts the clock), correct counts/FPS arithmetic after a real interval
  elapses, counters resetting (no carry-over) after each flush, multiple
  drop reasons tallied independently, and real file round-tripping as
  valid JSONL.

---

## C4 — Coverage metric

`compute_coverage()` in `features/signal_quality.py`.

- Per signal, per window **and** per session — never one blended number.
- **Per window**: a `window_coverage` record is written to the session log
  immediately after each `window_summary` it describes (same
  `window_start_monotonic`/`window_end_monotonic`, since both reset on the
  same `window_acc.flush()` call), built from the SAME per-cycle
  `missingness_flag` values C2 already classified — accumulated only once
  calibrated, matching `window_acc`'s own lifecycle exactly.
- **Per session**: a `session_coverage` record is written once at thread
  shutdown, from every cycle's classification across the whole run
  (including the pre-calibration phase, unlike the per-window record).
- `tests/test_signal_quality.py`'s check 8 covers the arithmetic directly,
  including the `n_samples == 0` edge case (`coverage_fraction: None`,
  never a `ZeroDivisionError`).

---

## What is not covered, stated honestly

- **The attention-block pilot signals** (V_so/screen orientation, gaze
  direction, blink) are not extended with the C2/C4 pattern in this pass.
  They are already lower-priority per CLAUDE.md's "PILOT, not POC"
  framing, and already carry a partial, differently-shaped quality signal
  (`gaze_reliable`/`head_pose_only`, an `"unvalidated": true` stamp on
  every record). Extending this exact pattern to them is straightforward
  future work using the same functions, not attempted here.
- **Processing-side frame drops** (buffer overwrite before consumption)
  are not tracked by C3 — see C3's own section above.
- **The live wiring in `capture_thread()`/`processing_thread()` is not
  integration-tested** — consistent with `tests/test_refactor_snapshot.py`'s
  own stated scope ("these require a live camera or real MediaPipe Tasks
  objects... no synthetic fixture can exercise them"). What *was* verified
  without a camera: the module parses (`ast.parse`), imports cleanly and
  quickly (`RUN_EXPERIMENT_ID` stays `None` at import, confirming the
  ~0.5 s provenance capture was NOT paid at import time), the other two
  real consumers of this file (`analyze_video.py`, `stage3_demo_ui.py`,
  `controls/null_input.py` via `tests/test_controls.py`) still import
  without error, and the golden snapshot is unaffected. The pure-
  computation pieces each new module wraps ARE fully unit-tested (see C1–C3
  above) — the same "pure computation tested, camera loop untested, stated
  explicitly" split `docs/CONTROLS.md` already documents for
  `controls/null_input.py`.

---

## Golden snapshot comparison after Part C

```
PASS: snapshot matches golden file exactly.
Golden file SHA256: 4f9c0f1786c18e8dbe5e3048b8b6b6e280cf6c434b9c53b119344746fc31bcff
```

**MATCH** — identical to every prior comparison in this task
(Gate 0 A1–A5, B2, Part B, and now Part C). The validated path was never
touched.
