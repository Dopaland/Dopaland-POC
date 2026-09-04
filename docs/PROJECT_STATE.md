# Project State

The document to open first. Changes often — CLAUDE.md carries the stable package map
and discipline; this file carries what's true right now. Read both.

---

## 1. Current commit and recent work

**HEAD at time of writing:** `bdd2ee4` — "feat: D0PA1 D4 -- reproduction command
(reproduce.py, make/ps1, compare_results.py)"

Last several pieces of work, most recent first (see `git log` for the full history):

1. `bdd2ee4` — D4 reproduction command: `reproduce.py`, `Makefile`, `reproduce.ps1`,
   `compare_results.py`. Regenerates D7/D3/leakage/time-shuffle/latent-recovery/
   blink-positive-synthetic results from fully self-contained seeded inputs. Verified
   bit-identical across two same-machine runs except the two fields expected to differ
   (`captured_at_utc`, `experiment_id`).
2. `c5e881c` — time-shuffle control ("matrix row 18", missed when the other controls
   were built): episode-order shuffle, diagnostic only, never a p-value.
3. `646f560` — positive blink control harness: event matching (precision/recall/F1) +
   per-clip count Bland-Altman, run against synthetic aperture streams through the
   real, unmodified `BlinkDetector`.
4. `fb123c1` (+ `e53486b` sharpening two caveats) — synthetic latent recovery:
   correlation + standardised RMSE, swept over effect size and observation noise.
5. `3fa3c5b` — leakage control harness: four window variants (valid/post_action/
   pre_action/timestamp_shift), synthetic + pluggable trial source.
6. `67ec15e` / `921c317` — D3 reliability (SEM/RC/Bland-Altman/CV + guarded ICC) and D7
   baselines (raw/session_z/persistent_z).
7. `c680951` — Part C signal completions: MAD baseline, per-signal missingness/
   confidence, continuous FPS logging, coverage metric.
8. `a7521b8` / `6e80d05` / `6b774b1` — Part B canonical log schema + writer; Gate 0 B2
   validated-path source hash; Gate 0 A1–A5 (provenance, config, data manifest, variant
   log backfill).

Earlier than this: the D1 feature-block separation refactor (`10a95f0` and the commits
before it), the D6 precision-simulation build-out (generator → models → precision →
three sweep passes → primary-metric comparison → pre-registered clip epsilon), all
predating the Gate 0 work above.

---

## 2. Matrix rows implemented — module and evidence per row

| Item | Module(s) | Document evidencing it |
|---|---|---|
| Gate 0 A1 (run provenance) | `simulation/provenance.py` | `docs/GATE0_PROVENANCE.md` §A1 |
| Gate 0 A2 (config + hash, constant audit) | `simulation/config.py` | `docs/GATE0_PROVENANCE.md` §A2 |
| Gate 0 A3 (pinned deps) | `requirements.txt`, `models/MODEL_MANIFEST.md` | `docs/GATE0_PROVENANCE.md` §A3 |
| Gate 0 A4 (data manifest) | `manifest/generate_data_manifest.py` → `manifest/data_manifest.csv` | `docs/GATE0_PROVENANCE.md` §A4 |
| Gate 0 A5 (variant log) | `simulation/variant_log.py` → `logs/variant_log.jsonl` | `docs/GATE0_PROVENANCE.md` §A5 |
| Gate 0 B2 (validated-path source hash) | `simulation/provenance.py` (`validated_path_source_sha256`) | `docs/GATE0_PROVENANCE.md` §B2 |
| Part B (canonical log schema) | `schema/canonical_log_v1.json`, `schema/canonical_log_writer.py` | `docs/CANONICAL_LOG_SCHEMA.md` |
| Part C1 (MAD robust baseline) | `features/robust_baseline.py` | `docs/SIGNAL_COMPLETIONS.md` §C1 |
| Part C2 (missingness + confidence) | `features/signal_quality.py` | `docs/SIGNAL_COMPLETIONS.md` §C2 |
| Part C3 (continuous FPS metric) | `simulation/fps_logger.py` | `docs/SIGNAL_COMPLETIONS.md` §C3 |
| Part C4 (coverage metric) | `features/signal_quality.py:compute_coverage` | `docs/SIGNAL_COMPLETIONS.md` §C4 |
| D1 (feature-block separation) | `features/{geometry,x_core,episodes,attention,audio,context}.py` | `docs/D1_DEPENDENCY_MAP.md` |
| D3 (absolute reliability measures) | `analysis/reliability.py` | `docs/RELIABILITY.md`, `docs/D7_BASELINES.md` |
| D4 (reproduction command) | `reproduce.py`, `Makefile`, `reproduce.ps1`, `compare_results.py` | `docs/D4_REPRODUCIBILITY.md` |
| D6 (precision simulation, Pass 1/2/finalisation/metric comparison/clip-eps) | `simulation/{generator,models,precision}.py` + 5 `run_*.py` drivers | `docs/D6_SIMULATION.md`, `artefacts/precision_analysis_v1.md`, `artefacts/precision_analysis_v2.md` |
| D6 (synthetic latent recovery) | `simulation/latent_recovery.py` | `docs/D6_SIMULATION.md` §13 |
| D7 (three baseline representations) | `analysis/baselines.py` | `docs/D7_BASELINES.md` |
| Null-input control | `controls/null_input.py` | `docs/CONTROLS.md` §1 |
| Negative control | `controls/negative_control.py` | `docs/CONTROLS.md` §2 |
| Leakage harness | `controls/leakage.py` | `docs/CONTROLS.md` §3 |
| Positive blink control | `controls/blink_positive.py` | `docs/CONTROLS.md` §4 |
| Time-shuffle control ("matrix row 18") | `controls/time_shuffle.py` | `docs/CONTROLS.md` §5 |

---

## 3. Open items — not code

### Client decisions outstanding
- **D2** (prediction target: action classes, horizon, tie/rapid-succession handling) —
  BLOCKED. Everything downstream of a real action label (real `A_t`/ROI features, the
  leakage/time-shuffle controls on real data, `CanonicalLogWriter`'s stimulus/action
  fields) waits on this.
- **`U_t` audio** — keep-or-formally-remove decision, not yet made. `features/audio.py`
  stays an intentionally empty stub either way until decided.
- **Second-camera sensor swap** — pending hardware and an FPS feasibility test; the
  opportunity is permanently lost once real collection starts without it (must happen
  *during* collection, not after).
- **The client's task harness acceptance review** — `docs/D4_REPRODUCIBILITY.md`
  formerly cited a `docs/ROI_HARNESS_ACCEPTANCE.md` that did not exist; corrected
  (see that file) to state plainly that the review is outstanding — the harness
  package has not yet been made available to a session — and that the document will
  be created when the review is actually performed, not before.

### Physical runs outstanding
- **Null-input control** — needs a live webcam + a human operator sitting still for
  ~10 minutes. Has never been run (`controls/null_input.py`'s pure-computation pieces
  are unit-tested; the camera loop itself is not exercised).
- **Blink positive-control clips** — needs N real one-minute recorded clips + a manual
  frame-by-frame blink count per clip. Zero clips exist; `controls/blink_positive.py`
  has only ever seen synthetic aperture streams.
- **Extended stability soak** — the only soak on record is the POC-era 41-minute run
  (`logs/soak_log.jsonl`). No longer or repeated soak exists; 41 minutes is a modest
  window for a *definitive* no-leak claim on its own (`docs/AUDIT_A_COLUMN.md` Q4).
- **The harness acceptance check** — D2's task harness (whatever produces ROIs and
  logged on-screen actions) is under separate review and does not exist in this repo;
  nothing here can be pointed at real trial data until it lands.
- **Three real sessions, fixed protocol, matched repeatable units** — required before
  D3/D7's reliability/baseline numbers mean anything about this study (as opposed to
  about synthetic data). Not collected.

---

## 4. Known limitations, gathered in one place

- **V_pd's near-zero dispersion.** Neutral std ≈ 0.0001–0.0002. Any z-score built on
  this denominator is enormous for even tiny movement — this is *why* the null-input
  control and the `zero_dispersion` handling (hard constraint #5) exist. Never treat a
  large V_pd z as evidence of a large real effect without checking dispersion first.
- **CV% is uninformative for a near-zero-mean signal.** `compute_within_unit_cv` was
  confirmed, on a synthetic V_pd-shaped exploration, to swing from hundreds to tens of
  thousands of percent — a real property of dividing by a near-zero grand mean, not a
  bug (`docs/RELIABILITY.md`, "V_pd's known shape").
- **Precision (bootstrap CI half-width) varies by roughly a factor of three across
  synthetic subject realisations (seeds) at a fixed sample size** — the per-seed
  min/max spread in `artefacts/precision_analysis_v2.md`'s joint grid (Task 2) runs
  as wide as ~0.013 to ~0.047 in the worst cells. More `n_boot` does not shrink this;
  only more independent seeds would characterise it better. Any single-seed precision
  number quoted from this simulation should be read as one draw from a wide
  distribution, not a stable estimate.
- **Pitch (head tilt up/down) is structurally unrecoverable** from this single-camera
  landmark pipeline — confirmed empirically (a maximal, verified chin-to-chest look-down
  still read ~0.1° pitch), root-caused as face foreshortening degrading the underlying
  landmark data, not a fixable bug in `yaw_pitch_roll_from_matrix`. `V_so`'s pitch
  contribution and any UI surfacing of it must stay flagged accordingly; only yaw is
  shown in the demo's experimental strip.
- **The three capture/UI consumers have diverged.** `stage1_step4_vectors.py`'s own
  loop, `stage3_demo_ui.py`, and `analyze_video.py` all call the identical `features.x_core`
  functions (so the validated math cannot diverge) but differ in what they do around it:
  v_jc z-scoring (stage3 only), V_so usage (full vs. yaw-only), gaze/blink tracking
  (stage3 only), and `analyze_video.py`'s video-time rather than wall-clock calibration
  clock. See `docs/D1_DEPENDENCY_MAP.md` §7 for the full account. None of this is a D0PA1
  defect — it predates D0PA1 — but a future session must not assume the three consumers
  behave identically outside the shared core.
- **Much of the historical `logs/` data is weakly identified.** Per
  `manifest/data_manifest.csv` (Gate 0 A4): 36 of 50 files carry no recoverable
  `subject_id`, and 14 of 50 have no real acquisition timestamp (falling back to file
  mtime, explicitly marked weak/non-evidentiary). This is expected for data predating
  Gate 0, not a defect in the manifest generator — but it means historical `logs/` files
  cannot be treated as reliably attributable without checking the manifest's `notes`
  column first.

---

## 5. What a future session must NOT do

- **Do not tune anything against existing data** (G2) — not a formula, not a threshold,
  not a config default, regardless of how a result looks. V_bf's Gate-2 failure is the
  standing proof of what tuning against n=1 costs.
- **Do not implement a verdict** (G1) — no `if metric > X: return PASS`, no RETAIN/
  DROP/INCONCLUSIVE branch, anywhere in this codebase's own logic. Every control and
  every analysis module computes and stores numbers; a human applies the pre-registered
  rule afterward.
- **Do not modify the validated path** (G5) without an explicit ask —
  `features/x_core.py`, `features/episodes.py`, `features/geometry.py`, and
  `stage1_step4_vectors.py`'s capture/processing logic. Re-run
  `tests/test_refactor_snapshot.py` after any change anywhere near these and report the
  SHA256 match/mismatch explicitly.
- **Do not present a harness or control as validated when it has only been run on
  synthetic input.** `controls/leakage.py`, `controls/time_shuffle.py`,
  `controls/blink_positive.py`, and `reproduce.py`'s confirmatory scope are all in this
  category today (see §3's "Physical runs outstanding" above) — state the synthetic-only
  status every time one of these is discussed, not just the first time.
