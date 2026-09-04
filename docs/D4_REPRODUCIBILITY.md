# D4 Reproducibility — the Reproduction Command

**THE ACCEPTANCE TEST, as the client stated it:** she runs ONE documented
command on a clean machine and the reported results tables regenerate. A
repository and a README do not satisfy this. This document, plus
[`reproduce.py`](../reproduce.py), [`Makefile`](../Makefile),
[`reproduce.ps1`](../reproduce.ps1), and
[`compare_results.py`](../compare_results.py), is the answer.

---

## 2.1 — the constraint that shapes everything

Reproduction runs from **archived inputs** — never a live camera. Live
capture is non-reproducible by nature (frame timing, exposure, auto-gain,
dropped frames vary every run; no seed reaches any of them). The
reproduction path therefore exercises the **analysis half only** —
`features/`, `analysis/`, `simulation/`, `controls/`, `schema/`.
`reproduce.py` never opens a camera, never calls `cv2.VideoCapture`, and
is confirmed structurally (below) to never import anything that could.

---

## 2.2 — the three consumers are NOT consolidated, and NOT imported

`stage1_step4_vectors.py`'s own loop, `stage3_demo_ui.py`, and
`analyze_video.py` have diverged (different experimental-signal logging,
different attention windowing, a video-time rather than wall-clock
calibration clock in the video path — see `docs/D1_DEPENDENCY_MAP.md`
section 7 for the full account of that divergence). **That divergence is
real, it lives on the capture/UI side, and it is explicitly out of scope
for this task** — G5 for this task specifically forbids modifying any of
the three.

`reproduce.py` is a **new, dedicated entry point** that goes from
archived/synthetic inputs to results using `features/`, `analysis/`, and
`simulation/` directly. **It does not import any of the three consumers**
— confirmed structurally, not just by not having written an import:
`tests/test_reproduce.py`'s `check_reproduce_py_never_imports_the_three_consumers`
parses `reproduce.py`'s own AST and confirms `stage1_step4_vectors`,
`stage3_demo_ui`, and `analyze_video` never appear as an import target.

### Which historical logs came from which consumer

Determined by reading each consumer's own log-writing code (`grep`-
verified, not assumed) — not every file in `logs/` maps cleanly onto one
of the three; three attribution tiers, stated honestly:

**Fully attributable to exactly one of the three (its filename pattern is
constructed only in that one file's own code):**

| Log family | Consumer |
|---|---|
| `session_*.jsonl` (19 files) | `stage1_step4_vectors.py`'s own loop (`processing_thread()` — the only place `f"session_{SESSION_ID}.jsonl"` is constructed) |
| `experimental_signals_log.jsonl` | `stage3_demo_ui.py` (`EXPERIMENTAL_LOG_PATH` — neither of the other two references this file at all) |
| `soak_log.jsonl` | `stage3_demo_ui.py` (`SOAK_LOG_PATH` / `SoakTracker` — confirmed by `docs/AUDIT_A_COLUMN.md`'s own finding that the one real soak log carries `agent_is_stub`, a stage3-specific field) |
| `video_analysis_*.json` (8 files) | `analyze_video.py` (`out_path = ...f"video_analysis_{base_name}.json"` — unique to this file) |

**Partially attributable — rules out one or more of the three, but not
down to exactly one, without per-record inspection this pass did not
attempt (stated as a gap, not guessed past):**

| Log family | What's ruled in/out | Why not fully attributable |
|---|---|---|
| `agent_log.jsonl` | Written via `stage2_personality_agent.py`'s `log_agent_exchange()`, called by BOTH `stage3_demo_ui.py` (via `run_stage2_on_window`) AND `analyze_video.py` (directly). **Never `stage1_step4_vectors.py`'s own loop** (it never imports `stage2_personality_agent` at all). | Individual entries could have come from either of the other two; no distinguishing field was checked for in this pass. |
| `consent_log.jsonl` | Written via `stage1_step7_consent.py`'s `run_consent_gate()`, called by BOTH `stage1_step4_vectors.py`'s own `main()` AND `stage3_demo_ui.py`'s own main. **Never `analyze_video.py`** (offline video analysis needs no live consent gate). | Individual entries could have come from either of the other two. |

**Not produced by any of the three consumers at all** — from other,
separate, purpose-built scripts, confirmed by direct code inspection
(none of these are in scope for "the three consumers" question, stated
here so a reader isn't left guessing where they came from):

| Log family | Actual source |
|---|---|
| `gate2_trials*.jsonl` (3 files) | `stage1_step9_gate2_capture.py` (`TRIALS_PATH`) — a dedicated capture tool; `stage3_demo_ui.py`'s own docstring explicitly disclaims touching it |
| `orientation_trials.jsonl` | `orientation_capture.py` |
| `browdiag_*.jsonl`, `browonly_*.jsonl`, `maxelicit_*.jsonl`, `yawhold_*.jsonl` | Their own dedicated `stage1_step4_{browdiag,browonly,maxelicitation,yawhold}_session.py` diagnostic scripts |
| `calib_repeat_*.json` | `stage1_step8_calibration_repeat_test.py` |
| `validation_*.jsonl` + its manifest | `stage1_step4_validation_session.py` |
| `variant_log.jsonl` | `simulation/variant_log.py` — this project's own Gate 0 tooling, unrelated to the vision-pipeline consumers |

---

## 2.3 — the command

```bash
make reproduce
```

or, on Windows without `make`:

```powershell
.\reproduce.ps1
```

Both call the identical `python reproduce.py` — no separate logic lives
in the Makefile or the PowerShell script. Every run prints, before any
result: `experiment_id`, `git_commit_hash`, `git_dirty`,
`validated_path_source_sha256`, and `config_hash` — and writes them to
`reproduction_output/00_provenance.json`:

```
  experiment_id=reproduce_20260904T043116Z_1ba102b1
  git_commit=c5e881cd102a47512a44be6d2d0e21eea602c5e1  git_dirty=True
  config_hash=2bb10eb548f4bea0
  validated_path_source_sha256=5a1c758b15773c79b17c2f785f7deb7b03a0210a9dae1b1bb6452a2cd1992cba
```

(`git_dirty=True` above is this development checkout mid-session, with
uncommitted new files — a genuinely clean checkout on a tagged commit
reports `git_dirty=False`.)

### Scope, stated honestly (G3)

`reproduce.py` regenerates the **D7 baselines, D3 reliability, leakage
diagnostic, time-shuffle diagnostic, latent-recovery sweep, and
blink-positive synthetic-validation** results — all fully synthetic-
seeded, all fast (the full command completes in well under a minute on
this machine). **It does not re-invoke the five pre-existing D6
precision-simulation driver scripts** (`simulation/run_precision_sweep.py`,
`run_precision_sweep_pass2.py`, `run_precision_sweep_finalisation.py`,
`run_metric_comparison.py`, `run_eps_and_baseline_analysis.py`), each of
which already produced its own committed artefact under `artefacts/` and
takes several minutes to re-run. Each remains independently runnable
(`python simulation/<script>.py`) and is not wired into this fast
command. This is a disclosed scope decision, not an oversight.

---

## 2.4 — every stochastic component, enumerated

Every seed lives as a named `SEED_*` constant at the top of
`reproduce.py` (10 total, confirmed by `tests/test_reproduce.py` to all
be plain ints, never left unset):

| Constant | Feeds |
|---|---|
| `SEED_D7_BASELINES_GENERATOR` | The synthetic 3-session baseline demo's `np.random.default_rng` |
| `SEED_D3_RELIABILITY_SYNTHETIC_DATA` | The synthetic `(25 units × 3 sessions)` reliability matrix's generation |
| `SEED_D3_RELIABILITY_BOOTSTRAP` | `compute_all_reliability_measures`'s unit-level bootstrap |
| `SEED_LEAKAGE_GENERATOR` | `GeneratorConfig.seed` for the leakage diagnostic's synthetic trials, and (unchanged) the negative-control seed derived from it |
| `SEED_LEAKAGE_BOOTSTRAP` | `run_leakage_diagnostics`'s episode-level bootstrap |
| `SEED_TIME_SHUFFLE_GENERATOR` | `GeneratorConfig.seed` for the time-shuffle diagnostic's synthetic trials |
| `SEED_TIME_SHUFFLE_SHUFFLE` | `shuffle_episode_order`'s permutation draw |
| `SEED_TIME_SHUFFLE_BOOTSTRAP` | `run_time_shuffle_diagnostic`'s episode-level bootstrap (same seed for both ordered/shuffled conditions — deliberate, see `controls/time_shuffle.py`) |
| `SEED_LATENT_RECOVERY` | `LatentRecoveryConfig.seed` — feeds both the generator and `add_observation_noise`'s per-cell RNG (derived deterministically from it) |
| `SEED_BLINK_POSITIVE_SYNTHETIC` | The synthetic aperture-stream generator feeding the real, unmodified `BlinkDetector` |

Every function called downstream of these seeds (`simulation.generator.generate`,
`controls.negative_control.generate_negative_control`,
`simulation.precision.fit_multinomial_logreg`/`bootstrap_ci_on_delta`,
`features.robust_baseline.mad_stats`, etc.) is itself fully seed-derived
— none of them reach for `np.random` without an explicit `rng`/`seed`
argument (confirmed by the per-module tests each of these already has,
and by the empirical byte-diff result below, which would show drift if
any hidden unseeded draw existed).

**Nothing was found unseeded.** If a future addition to `reproduce.py`
adds a call path that draws randomness without an explicit seed, that is
a defect against this document's own claim — name it here the moment it
is found, per this task's own standard.

**One non-stochastic but genuinely non-deterministic factor was found and
fixed** (not a "seed" in the RNG sense, but exactly the kind of hidden
non-determinism 2.5 asks to be investigated as a defect, not written off):
matplotlib's SVG backend, by default, embeds (a) a wall-clock creation
timestamp in the SVG's Dublin Core metadata, and (b) per-element `id`
attributes derived from a **random hash salt regenerated every process
run** — neither reflects the plotted data. Fixed in
`analysis/reliability.py`'s `plot_bland_altman_svg()`: `matplotlib.rcParams["svg.hashsalt"]`
pinned to a fixed string, and `metadata={"Date": None}` passed to
`savefig()`. See the 2.5 section below for the actual before/after
byte-diff this fix produced.

---

## 2.5 — same-environment determinism: the ACTUAL result, run twice

**This is the most important finding in this document, reported first as
instructed.**

`reproduce.py` was run twice in this checkout, and every output file
diffed byte-for-byte (`diff -rq`) and checksummed (`sha256sum`):

```
DIFFERS    00_provenance.json
IDENTICAL  01_d7_baselines.json
IDENTICAL  02_d3_reliability.json
IDENTICAL  02_d3_reliability_bland_altman.svg
IDENTICAL  03_leakage_diagnostic.json
IDENTICAL  04_time_shuffle_diagnostic.json
IDENTICAL  05_latent_recovery_sweep.json
IDENTICAL  06_blink_positive_synthetic.json
```

**The one file that differs, and only in the fields expected to differ by
design:**

```diff
2c2
<   "captured_at_utc": "2026-09-04T04:31:17.145770+00:00",
---
>   "captured_at_utc": "2026-09-04T04:31:26.214899+00:00",
4c4
<   "experiment_id": "reproduce_20260904T043116Z_1ba102b1",
---
>   "experiment_id": "reproduce_20260904T043126Z_ce38faa8",
```

`git_commit_hash`, `git_dirty`, `git_dirty_reason`,
`validated_path_source_sha256`, `config_hash`, and `hostname` — every
OTHER field in `00_provenance.json` — were identical across both runs.
`captured_at_utc` and `experiment_id` are, by construction, a wall-clock
timestamp and a timestamp-derived unique id (`simulation/provenance.py`)
— they are supposed to differ every run; that is what makes an
`experiment_id` an identifier at all. **Every actual results table and
the one figure are bit-for-bit identical.**

### This was not true on the first attempt — the real defect, investigated

The first run-twice-and-diff **did** show an unexpected difference, in
`02_d3_reliability_bland_altman.svg` — investigated as a defect per this
task's instruction, not written off:

```diff
9c9
<     <dc:date>2026-09-04T09:59:34.595200</dc:date>
---
>     <dc:date>2026-09-04T10:00:00.450479</dc:date>
42c42
<      <path id="m67fbed3678" d="M 0 1.936492 ...
---
>      <path id="m213a8d658a" d="M 0 1.936492 ...
```

**Root cause, confirmed by inspection, not guessed:** the actual plotted
coordinate data (`d="M 0 1.936492 ..."`, and every `x=`/`y=` value on
every `<use>` element) was **identical** between the two SVGs — only
matplotlib's own internal metadata timestamp and its randomly-salted
element `id` strings differed. This is matplotlib's SVG backend's default
behavior (a fresh random hash salt per process, plus an embedded
creation-time field), not a defect in this codebase's own computation.
Fixed as described in 2.4 above; re-run confirmed byte-identical
afterward (the result quoted at the top of this section is the
POST-FIX run).

A second, structural side effect was also found and fixed during the
same investigation: `git_dirty_reason`'s path COUNT changed between the
two runs (`"1 modified/untracked path(s)"` → `"2 modified/untracked
path(s)"`) — caused by `reproduction_output/` itself being an untracked
directory that `git status` was counting. Added `reproduction_output/`
to `.gitignore`; this stopped the command's own output from perturbing
its own provenance record.

**No BLAS/threading non-determinism was observed** in the fitted-model
outputs (`fit_multinomial_logreg`'s `scipy.optimize.minimize` runs, used
by both the leakage and time-shuffle diagnostics) — both files were
byte-identical across the two runs without any special handling. This is
an empirical, same-machine observation, not a guarantee about a different
machine's BLAS build — see 2.6.

---

## 2.6 — cross-environment tolerance

`compare_results.py --reference <dir> --candidate <dir> [--tolerance T]`
compares two `reproduction_output/` directories: per-field absolute and
relative deviation for every numeric value in the JSON results tables,
and a SHA256 checksum comparison for the SVG figure. It reports; it never
decides (G1) — no exit code or printed line is a pass/fail, and
`00_provenance.json`'s `captured_at_utc`/`experiment_id` are excluded
from the deviation report as EXPECTED differences (reported separately,
never silently dropped).

Proven to actually detect a real deviation, not just pass vacuously
(`tests/test_reproduce.py`): a deliberately-injected `+0.04` perturbation
to one field was correctly flagged with its exact `abs_deviation`/
`rel_deviation`; two structurally-identical result sets correctly report
zero deviations.

**Recommended default: `1e-6` absolute.** This is a **recommendation**,
not a decision — the value is the client's to set. What motivates it:

- The SAME-machine, same-environment result above is bit-identical to
  full float64 precision (deviation `0.0`, not merely "small") —
  `1e-6` is far looser than what this machine actually needs, deliberately.
- The looseness is for what a byte-diff **cannot** distinguish across a
  genuinely different machine: a different NumPy/SciPy build, a
  different BLAS backend (OpenBLAS vs. MKL vs. a different thread count),
  or a different CPU's floating-point unit can each produce a result that
  differs in the last 1-3 bits of a float64 mantissa without indicating
  any real discrepancy in the computation — this is a well-known property
  of floating-point summation/reduction order, not specific to this
  codebase. `1e-6` absolute is comfortably above that noise floor for
  values in the ranges this project's metrics actually take (correlations
  in `[-1,1]`, macro-F1/log-loss deltas typically `< 1`, SEM/RC values at
  whatever scale the signal itself sits at) while still being tight enough
  to catch a REAL discrepancy (an actual algorithm difference, a config
  drift, a stale cached result) rather than laundering one through as
  "cross-platform noise."
- This has NOT been empirically validated against a second, physically
  different machine in this session (none was available) — stated
  honestly: the recommendation is reasoned from general floating-point
  behavior and this project's own value ranges, not measured
  cross-machine. If a second machine becomes available, re-running
  `compare_results.py` against it and inspecting the actual observed
  deviations would be the way to tighten or loosen this number with real
  evidence, and should be done before treating `1e-6` as settled.

---

## 2.7 — archived inputs: what exists, what doesn't, what this command actually consumes

**What `reproduce.py` consumes today: nothing external at all.** Every
input is a fixed, versioned config/seed pair, fully self-contained in
this repository's own committed source — no video file, no logged
feature stream, no path that has to "exist on disk" beyond the checkout
itself. This is deliberate: it is the only thing that can be verified to
work on a genuinely clean checkout with zero additional files, and it is
what the byte-diff in 2.5 actually exercised.

**What `reproduce.py` deliberately does NOT touch: `logs/` and
`manifest/data_manifest.csv`.** `logs/` is git-ignored (G4) — a clean
checkout has none. `manifest/generate_data_manifest.py`'s `generate()`
function hardcodes its output path to overwrite the COMMITTED
`manifest/data_manifest.csv` in place, driven by whatever `logs/`
happens to contain on the machine running it — wiring that into
`reproduce.py`'s automatic run would risk silently overwriting a
developer's real, accurate local manifest with a near-empty one on any
machine that doesn't happen to have the same local logs populated. That
script remains a separate, already-existing, independently-runnable
command (`python manifest/generate_data_manifest.py`) for exactly the
case it's meant for — regenerating the manifest against whatever real
logs a given machine actually has — deliberately NOT folded into the
"run twice, byte-diff, works identically everywhere" verification this
document reports on, because its correct output is machine-dependent by
design (G4), not a bug in it.

**The intended archived inputs for the confirmatory study — stored
video files and a logged feature stream from the client's actual
sessions — do not exist yet.** The client's task harness that would
produce matched-unit, protocol-controlled recordings has not yet been
made available to a session for review — **its acceptance review is
outstanding, not merely undocumented.** No `docs/ROI_HARNESS_ACCEPTANCE.md`
exists today; that document will be created when the review is actually
performed, not before — a citation to a document that doesn't exist yet
is worse than stating the gap plainly here. D2 (action classes, horizon)
remains BLOCKED per CLAUDE.md, for the same underlying reason. **Stated
plainly, not smoothed over:** `reproduce.py` today regenerates the
MACHINERY's results on synthetic/self-contained inputs, not a
confirmatory finding from real archived recordings.

**How the confirmatory inputs would slot in without code changes,
once they exist:** every one of `reproduce.py`'s section runners already
takes its data through a pluggable interface at the module level it
calls into — `controls.leakage.run_leakage_diagnostics` and
`controls.time_shuffle.run_time_shuffle_diagnostic` already accept any
zero-argument `trial_source` callable (`synthetic_trial_source()` is the
only implementation today; a `RealLoggedTrialSource` reading from
`schema/canonical_log_writer.py`'s output would satisfy the identical
contract), and `analysis.baselines`/`analysis.reliability`'s functions
already operate on plain `(session_id, samples)` lists / `(n_units,
n_sessions)` matrices with no assumption about where the values came
from. The day archived real recordings and their logged feature streams
exist, `reproduce.py`'s section runners can be pointed at a real-data
source function in place of the synthetic one, with the surrounding
orchestration (provenance capture, output writing, seed enumeration
discipline) unchanged.
