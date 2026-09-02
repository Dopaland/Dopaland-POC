# D0PA1 Controls — Null-Input, Negative Control, and Leakage Harness

**Status:** all three controls built. `controls/negative_control.py` is
fully exercised (it runs automatically inside `simulation/precision.py` —
see §2 — and, through that, inside `controls/leakage.py` too — see §3).
`controls/leakage.py` (§3) is fully exercised on synthetic data. `controls/
null_input.py`'s camera-loop orchestration has NOT been run — it requires
a live webcam and a human operator sitting still for the configured
duration, which this coding session cannot provide. Its pure-computation
pieces (dispersion, excursion detection, config hashing) ARE tested
(`tests/test_controls.py`). This gap is stated here explicitly, not
implied to be closed (G3).

None of these controls decides anything (G1). All three compute and store
numbers for a human to read.

---

## 1. Null-input control (`controls/null_input.py`)

### What it is

Runs the FULL, VALIDATED pipeline (`features/geometry.py`,
`features/x_core.py` — imported and used unmodified, G5) against a
person sitting still in front of a blank screen, for a configurable
duration (default 10 minutes, including the same `CALIBRATION_SECONDS`
neutral-calibration phase the real pipeline runs). It logs, per composite
signal (`v_bf`, `v_es`, `v_pd`) and covariate (`v_jc`) — **never blended
together**:

- the observed dispersion of the RAW signal over the whole run: standard
  deviation, MAD (median absolute deviation), and `1.4826 × MAD`, in the
  signal's own units
- an explicit `zero_dispersion` flag (and `zero_dispersion_reason`)
  wherever std or MAD is at or near zero — CLAUDE.md's D0PA1 hard
  constraint #5, applied: **never divide by it, never add a silent
  epsilon**
- the count of confirmed excursion events (see the excursion rule below)
- a false-event rate per minute, computed over the post-calibration
  monitoring window only
- the full canonical JSONL log of the run (`logs/null_input_<session_id>.jsonl`)

### Why this runs before any δ threshold is signed

One of our signals, V_pd (postural volatility), has a neutral dispersion
of roughly 0.0001 (CLAUDE.md's own STATUS section;
`stage1_step8_calibration_repeat_test.py` confirmed this directly). A
near-zero denominator makes every z-score enormous — a δ threshold
expressed on the z-scale may be comparing noise to noise. Switching to a
MAD-based robust estimator does not fix this by itself: the MAD of a
near-constant signal is ALSO near-zero. This control is how we learn what
the dispersion actually is, under conditions where the true answer for
every signal is "nothing is happening," **before** any pre-registered
threshold is signed against these units.

### What it CAN establish

- The sensor/pipeline noise floor for each signal, under a genuinely null
  physical condition, over a duration long enough (10 minutes vs. the
  real pipeline's 25-second calibration window) to characterize it with
  more statistical power than the calibration phase alone provides.
- A concrete, per-signal false-event rate: if the excursion rule
  (`|z| >= 2.0` sustained `>= 1.0s`, both parameterized — see below) were
  applied to a truly resting person, how often would it fire anyway,
  purely from sensor/tracking noise?
- Whether any signal's dispersion is so close to zero that a z-scored
  threshold on it is likely to be dominated by noise rather than by any
  real behavioral variation (the `zero_dispersion` flag).

### What it CANNOT establish

- Whether a real signal exists during real task performance. A clean
  null-input run does not imply the signal will behave well under a real
  cognitive/behavioral load — that is what real study data (and the
  negative control's complementary check on the ANALYSIS PROCEDURE, not
  the sensor) are for.
- Anything about a different subject, different lighting, different
  camera, or a different day. This is a single run, under the conditions
  stated by its own log — it characterizes that run, not "the pipeline in
  general." Repeat it if conditions change materially.
- Anything about D2's real action-class structure — null-input has
  nothing to do with class prediction; it is purely about signal
  dispersion and false-event rate.

### The excursion rule — parameterized, not hardcoded

```
excursion_z_threshold:            2.0    (default)
excursion_min_duration_seconds:   1.0    (default)
```

Both live in `NullInputConfig` and are hashed into every log
(`config_hash()`, SHA-256, first 16 hex chars) — the rule that produced a
given false-event-rate number is always inspectable and reproducible from
the log alone. A missing/None z-reading (no face detected, or the signal
is `zero_dispersion` and cannot be z-scored at all) ends any in-progress
excursion timer immediately (documented design choice in
`ExcursionDetector`'s own docstring) — this control is deliberately
conservative: it can undercount an excursion that happens to straddle a
brief tracking gap, but it can never manufacture one from a gap, which is
the safer error direction for a control whose whole purpose is
establishing a trustworthy rate.

### How to run it

```bash
python controls/null_input.py --subject-id P01 --duration-minutes 10
```

Requires a live webcam. `--subject-id` is required and must be an
anonymous participant code (e.g. `P01`), never a name (CLAUDE.md's
anonymous-`person_label` convention, applied here as `subject_id` per
D0PA1 hard constraint #7). Operator instructions (what to do, how long,
what invalidates the run) print automatically at start — see
`print_operator_instructions()` in the script, reproduced in full below
for reference without needing to run it first:

> **WHAT TO DO:** sit in front of the camera as you normally would for a
> real session; display a BLANK SCREEN for the entire run; sit as still
> and relaxed as you can — this is meant to capture "nothing is
> happening," not a posed-still performance; do not talk, check your
> phone, or get up.
>
> **HOW LONG:** the configured duration (10 minutes by default), including
> a 25-second neutral-calibration phase at the very start — keep sitting
> still through that phase too, it is part of the run.
>
> **WHAT WOULD INVALIDATE THIS RUN:** leaving the frame or a second person
> entering it; talking, eating, or checking a phone; deliberately holding
> a fixed expression (a documented blind spot of the calibration's own
> contamination check — see `features/x_core.py`'s
> `classify_calibration_quality` docstring); a real interruption; poor or
> changing lighting mid-run.
>
> Ctrl+C stops early — a partial run is still logged with its actual
> duration, never silently discarded.

### Output schema

Record types in the JSONL log (schema_version `"1.0"`):
`null_input_run_start` (config + config_hash, once), `null_input_sample`
(per-cycle, all four signals' raw composite/covariate values + detection
flags), `null_input_calibration_complete` (the real `NeutralCalibrator`
reference, unmodified), `null_input_summary` (the final per-signal
dispersion/excursion report — the terminal record, written once at the
end even on an early Ctrl+C stop).

---

## 2. Negative control (`controls/negative_control.py`)

### What it is

A deliberately meaningless signal: an AR(1) process (`z_t = ar1_phi *
z_{t-1} + eps_t`) — the SAME functional form `simulation/generator.py`'s
own latent state uses for its serial-dependence assumption (A1) — so the
control's autocorrelation strength can be matched to whatever assumption
a given analysis is using for the real/simulated signals. Matching the
autocorrelation matters: a plain white-noise control would have an
easier-to-distinguish statistical shape than a real autocorrelated
signal, making it a weaker test of "can this model be fooled into finding
structure in nothing."

### Exactly why it carries no information

It is not "meaningless" because it lacks structure (it IS autocorrelated,
deliberately) — it is meaningless because its random stream
(`np.random.default_rng(seed)`, used ONLY inside
`generate_negative_control`) never derives from, mixes with, or is used
anywhere else in the same analysis's class-label generation, feature
construction, or model fitting. There is no causal or numerical path from
its values to the outcome being predicted. Generating it in a fully
separate process and pasting the numbers in afterward would produce an
identical guarantee. Any measured "contribution" from it in a downstream
fit is, by construction, finite-sample noise or overfitting — never a
real effect.

### Wired into the analysis path automatically — how this was verified, not assumed

`simulation/precision.py`'s `compute_delta()` — the single function every
sweep, every report, and every future analysis in this codebase calls to
compute a Δ — **always** builds a third comparison (baseline +
negative-control vs. baseline alone) alongside the real candidate
signal's with/without comparison, and returns `delta_negative_control` in
its `DeltaResult`. There is no parameter to disable this. `run_one()` and
`run_one_refit()` (the two functions every sweep in this repository is
built from) both carry `delta_negative_control` through to their result
dictionaries unconditionally.

This was **verified directly**, not assumed from having written the code:
`tests/test_precision.py`'s `check_negative_control_cannot_be_omitted`
calls `compute_delta()` the way a caller who has never heard of the
negative control would call it — positional/required arguments only, no
mention of negative controls anywhere in the call — and asserts
`delta_negative_control` still comes back populated; it repeats the same
check through `run_one()`. Both pass. Additionally,
`tests/test_controls.py` verifies the negative-control generator itself
is (a) reproducible given a seed and (b) carries no measurable
correlation with an unrelated random outcome sequence, confirming the
"carries no information" claim empirically rather than by construction
alone.

### What it CAN establish

Whether the ANALYSIS PROCEDURE itself — feature construction, model
fitting, evaluation, the whole pipeline in `simulation/precision.py` — can
be fooled into reporting a spurious contribution from pure noise, on a
given draw of data. A large `delta_negative_control` on a specific run is
a signal that THAT run's result should be looked at carefully before
trusting `delta_point` from the same run.

### What it CANNOT establish

Anything about sensor or pipeline noise under physically null conditions
— that is the null-input control's job (§1). The two controls are
complementary: null-input tests "does the SENSOR see something when
nothing is happening," negative control tests "does the ANALYSIS see
something when nothing is there by construction." Neither substitutes for
the other.

### Handling a "positive" negative control — reported, never an automatic kill rule

Per the task's own instruction: a negative control demonstrating
contribution beyond the pre-specified null distribution means the
affected analysis should be **investigated** before the real signal
result is interpreted — but this is explicitly **not** an automatic kill
rule, because across many tests a negative control will occasionally
reach apparent significance by chance alone (the same multiple-comparisons
reality that makes any single test's p<0.05 unsurprising in a large
enough batch). `simulation/precision.py`'s sweep aggregation
(`sweep_multi_seed` / `sweep_multi_seed_refit`) reports
`delta_negative_control_median` and `delta_negative_control_max_abs`
across seeds for exactly this reason: a human can see the typical
magnitude and the worst case across repeated draws, and judge whether a
given run's negative control result looks like ordinary sampling noise or
something worth investigating. Nothing in this codebase makes that
judgment automatically.

### Parameters and where they live

`NegativeControlConfig` (`controls/negative_control.py`): `seed` (no
default — every caller must supply one, though `compute_delta` supplies
one automatically derived from the analysis's own generator seed so a
human calling `run_one`/`run_one_refit` never has to think about it),
`n_samples`, `sampling_rate_hz` (default 25.0, matching CLAUDE.md's CADENCE
note that Thread 2 samples at ~20-30/s), `ar1_phi` (default 0.6, matching
`simulation/generator.py`'s own A1 default).

### How to run it standalone

```python
from controls.negative_control import NegativeControlConfig, generate_negative_control
values = generate_negative_control(NegativeControlConfig(seed=1, n_samples=1000))
```

In normal use it does not need to be run standalone — it runs
automatically inside every `simulation/precision.py` analysis (see
above).

---

## 3. Leakage harness (`controls/leakage.py`)

### What it is

Four window variants, run over the SAME trial stream and reported side by
side in one table (`format_leakage_table`):

| Variant | Construction |
|---|---|
| `valid` | trial `t`'s feature comes from trial `t − valid_lag_trials` (default 3) — strictly before the action |
| `post_action` | trial `t`'s feature comes from trial `t + valid_lag_trials` — the SAME magnitude offset as `valid`, but forward: deliberately includes post-action information |
| `pre_action` | trial `t`'s feature comes from trial `t − pre_action_starved_lag_trials` (default 15, must exceed `valid_lag_trials` by construction — `LeakageConfig.__post_init__` enforces this) — deliberately starved, further back than `valid` |
| `timestamp_shift` | `valid`'s own alignment, offset by an additional `~timestamp_shift_seconds` (default 2.0s) worth of trials, converted via `sampling_rate_hz` (default 25.0, matching `controls/negative_control.py`'s own default) |

Only the **feature** moves between variants — `class_label`,
`prev_class_label`, `episode_id`, `session_idx`, `t_in_session` are
identical across all four (verified directly,
`tests/test_leakage.py`'s `check_only_x_signal_and_missing_change_between_variants`).
A lag never crosses a session boundary (the generator's own `z` resets
per session — pulling a "prior" value from a different session would not
be a leakage test, it would be nonsense); a trial whose source index falls
outside its own session's range gets `x_signal=None`, handled by
`simulation/precision.py`'s existing missing-value convention
(mean-imputed + indicator dummy on the train split) — not a new one
invented here.

### Why it reuses `compute_delta`/`bootstrap_ci_on_delta` directly, not a new fit/eval loop

Structurally, each variant IS `compute_delta`'s existing "with signal vs.
without signal" comparison — only which trial's `x_signal` gets used as
"with" changes. Calling `compute_delta()` on four differently-windowed
copies of the same record list gets the episode-level resampling (1.2)
and the negative control (1.4) for free, with zero new fit/eval code.

### Pluggable data source (1.1)

`run_leakage_diagnostics(trial_source, ...)` takes any zero-argument
callable returning a trial-record list shaped like
`simulation.generator.generate()`'s output. `synthetic_trial_source()` is
the only implementation today, wrapping that generator — real action data
does not exist yet (the client's task harness that would produce it is
under separate acceptance review; D2 is BLOCKED per CLAUDE.md). A future
source reading from `schema/canonical_log_writer.py`'s output would
implement the identical interface and could be substituted for
`trial_source` with **zero changes** to the window-construction logic or
`run_leakage_diagnostics` itself — proven, not just asserted:
`tests/test_leakage.py`'s `check_data_source_is_genuinely_pluggable` runs
the full harness against a hand-built fake source that never touches
`simulation.generator` at all.

### G1 — diagnostics, never a verdict (1.3)

Every variant returns a `delta_point`, a bootstrap CI, and
`delta_negative_control` — numbers, with their own sign and magnitude
already carrying the "direction and magnitude" this task's instruction
asks to be reported. Nothing in `controls/leakage.py` compares one
variant's Delta against another's, labels a variant "clean" or "leaky",
or branches on a computed value. `format_leakage_table()` prints every
row identically — no highlighting, no pass/fail column.

### The negative control, verified the same way as `simulation/precision.py`'s

`tests/test_leakage.py`'s `check_negative_control_carried_automatically`
calls `run_leakage_diagnostics()` exactly the way `tests/test_precision.py`'s
own check calls `compute_delta()` — no mention of the negative control
anywhere in the call — and confirms `delta_negative_control` comes back
populated for **all four** variants, not just one. On a small synthetic
draw it can compute to exactly `0.0` (the same hard-decision/macro-F1
discreteness `simulation/precision.py`'s own module docstring already
documents — both models collapsing to the majority class on every test
trial); on a larger draw it is non-zero and, because the same
`negative_control_seed` and the same "without" baseline are shared across
all four variants by construction, identical across all four — confirmed
directly, not assumed.

### 1.5 — the task-conditional caveat, stated plainly

These four variants establish **expected DIRECTION**, not magnitude.
Because this generator's latent state `z` is a stationary AR(1) process,
`Corr(z_t, z_{t+k})` depends only on `|k|` — a `valid` feature at lag `k`
and a `post_action` feature at lag `k` (forward) carry, in this synthetic
model, the **same theoretical correlation strength** with the trial being
predicted. **Where post-action information is not known to carry
target-relevant signal for a given real task, the post-action window may
not dramatically outperform `valid` — and that alone does not mean the
windowing (or this harness) is broken.** A severe, unambiguous leak (a
feature that directly encodes the true class label — something that could
only be known *after* the action) is confirmed to produce a large,
clearly-nonzero Delta through the exact same `compute_delta` machinery
(`tests/test_leakage.py`'s `check_injected_severe_leak_produces_large_delta`:
`+0.66` vs. a clean `-0.02` baseline) — proving the underlying detection
mechanism genuinely responds to a real leak when one exists. Whether the
milder, naturally-symmetric `post_action` variant's Delta on any given
real dataset should be read as "no leak" or "a leak too weak to show up
in this particular window construction" is a human judgment this harness
deliberately does not make.

### How to run it

```python
from controls.leakage import synthetic_trial_source, run_leakage_diagnostics, format_leakage_table, LeakageConfig
from simulation.generator import GeneratorConfig

source = synthetic_trial_source(GeneratorConfig(seed=1, n_sessions=3, episodes_per_session=200, trials_per_episode=5, effect_size=0.3))
result = run_leakage_diagnostics(source, n_classes=3, n_sessions=3, config=LeakageConfig())
print(format_leakage_table(result))
```
