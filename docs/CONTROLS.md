# D0PA1 Controls — Null-Input, Negative Control, Leakage Harness, Positive Blink Control, Time-Shuffle

**Status:** all five controls built. `controls/negative_control.py` is
fully exercised (it runs automatically inside `simulation/precision.py` —
see §2 — and, through that, inside `controls/leakage.py` and
`controls/time_shuffle.py` too — see §3 and §5).
`controls/leakage.py` (§3) and `controls/time_shuffle.py` (§5) are fully
exercised on synthetic data — **neither has been run on real trials,
because real trials do not exist yet** (stated in each section, not
implied to be closed). `controls/blink_positive.py` (§4) is fully
exercised on synthetic aperture streams against the REAL
`features.attention.BlinkDetector` — **no real clip has been recorded or
processed; that gap is stated explicitly in §4, not implied to be
closed.** `controls/null_input.py`'s camera-loop orchestration has NOT
been run — it requires a live webcam and a human operator sitting still
for the configured duration, which this coding session cannot provide.
Its pure-computation pieces (dispersion, excursion detection, config
hashing) ARE tested (`tests/test_controls.py`). This gap is stated here
explicitly, not implied to be closed (G3).

None of these controls decides anything (G1). All four compute and store
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

These four variants establish **expected DIRECTION**, not magnitude — and
on THIS generator, synthetic data cannot even establish the expected
direction for the `post_action` variant specifically. Stated explicitly,
not left implicit:

**Why synthetic data cannot establish the expected direction here.** In
this generator, `x_signal` at any trial is an observation of the SAME
latent state `z` that drives the action at that trial — the signal
precedes (or at best coincides with) the action, by construction (A6's
mixing: `x_signal_s = effect_size·z_unit_s + noise_s`, and `z_s` is what
produces `class_label_s`). A `post_action`-variant feature, drawn from a
LATER trial, observes `z` only after the causal chain that produced the
action has already run — it carries no channel by which "information
from after the action" could be qualitatively richer than information
from before it, the way a REAL post-action leak (a feature contaminated
by the outcome itself — a motor-response artifact, a next-stimulus cue,
a feature literally computed FROM the recorded action) would be. Shifting
the window forward therefore does not add predictive leverage over the
action being predicted; it only moves further from the causally relevant
moment along the same autocorrelation decay — a forward shift **loses**
information here, it does not gain any. The one real run recorded above
is consistent with exactly that: `valid` (`+0.0000`) outperformed
`post_action` (`-0.0172`), the opposite of what a genuine post-action
leak would look like. **This generator was never built to model a real
post-action contamination channel, so it cannot be used to demonstrate
that a real one would show up as an inflated `post_action` Delta — only
real trials, once collected, can test that direction.**

**What synthetic data DOES conclusively establish**, and is the actual
evidence for this harness working at all: that the underlying detection
mechanism (`compute_delta`'s with/without comparison) responds to leakage
when leakage genuinely exists. A severe, unambiguous leak (a feature that
directly encodes the true class label — something that could only be
known *after* the action) produces a large, clearly-nonzero Delta through
the exact same machinery (`tests/test_leakage.py`'s
`check_injected_severe_leak_produces_large_delta`: `+0.66` vs. a clean
`-0.02` baseline). That is what "the harness detects leakage when leakage
exists" rests on — not the natural `post_action` variant's mild,
direction-ambiguous result on this generator, which this document does
not present as evidence either way.

**This control will be re-run on real trials once they exist, and the
outcome reported either way** — a `post_action` Delta that looks ordinary
on real data is not automatically "no leak" (per the specification's own
investigate-and-report rule: a positive finding gets investigated, not
silently waved through, but neither does an ordinary-looking one get
silently treated as proof of a clean pipeline). Nothing in this harness
decides that question now or later (G1).

### How to run it

```python
from controls.leakage import synthetic_trial_source, run_leakage_diagnostics, format_leakage_table, LeakageConfig
from simulation.generator import GeneratorConfig

source = synthetic_trial_source(GeneratorConfig(seed=1, n_sessions=3, episodes_per_session=200, trials_per_episode=5, effect_size=0.3))
result = run_leakage_diagnostics(source, n_classes=3, n_sessions=3, config=LeakageConfig())
print(format_leakage_table(result))
```

---

## 4. Positive blink control (`controls/blink_positive.py`)

### What it is

Compares `features.attention.BlinkDetector`'s output (reused unmodified,
G5) against a manual, frame-by-frame blink count, over N one-minute
clips. Reports, never decides (G1):

- **Event precision / recall / F1** — `match_events()` pairs each
  manually-counted blink against the nearest detected blink within a
  CONFIGURABLE tolerance (`BlinkPositiveConfig.matching_tolerance_ms`,
  default 150ms), greedily by smallest time difference (not index order,
  and not "first found") so two nearby manual events competing for one
  detected event resolve to whichever is genuinely closer. An unmatched
  manual event is a false negative (a real blink the detector missed); an
  unmatched detected event is a false positive (the detector saw a blink
  that wasn't there).
- **Per-clip count agreement, Bland-Altman** — `compute_count_agreement()`
  reuses `analysis.reliability.compute_bland_altman_pair` DIRECTLY (a
  `(n_clips, 2)` matrix, columns `[detected_count, manual_count]`) — not
  a second implementation of bias/limits-of-agreement math. Confirmed
  identical output to calling that function directly
  (`tests/test_blink_positive.py`'s
  `check_count_agreement_reuses_reliability_bland_altman`).

### G1, precisely — where the proposed criterion values live and why nothing reads them

`BlinkPositiveConfig` holds `matching_tolerance_ms` (a genuine algorithm
parameter — `match_events()` actually uses it) AND three PROPOSED
criterion values from this task's own instruction — `criterion_event_f1`
(0.80), `criterion_count_tolerance_fraction` (0.20),
`criterion_count_min_clips_fraction` (0.80, "at least 8 of 10 clips") —
stored and hashed so they travel with every report, but **never read back
by any function in this file to make a comparison.** Verified
structurally, not just by not having written the comparison:
`tests/test_blink_positive.py`'s `check_criterion_values_never_compared_in_code`
parses `controls/blink_positive.py`'s own AST and confirms none of the
three criterion field names ever appears as either side of a `Compare`
node anywhere in the file. `format_blink_report()` prints the computed
`precision`/`recall`/`f1`/Bland-Altman numbers and the `config_hash` —
never the criterion values next to a checkmark or a verdict. A human
reads the config's stored criterion alongside the report and makes the
comparison themselves.

### The manual-count entry format — fillable without touching code

`write_manual_count_template(clip_id, path)` writes a plain CSV with a
commented instruction header (what to do, one blink timestamp per line,
where to put your initials) and `load_manual_count(path)` reads it back,
skipping comment lines. No code editing, no JSON schema, no special
tooling — a reviewer opens the file in any text editor or spreadsheet
program.

### Synthetic validation, against the REAL detector (3.3)

`tests/test_blink_positive.py` builds a synthetic per-frame aperture
stream (baseline ~0.47 with noise, dipping to ~0.40 for ~200ms at KNOWN
blink onset times — shaped to match `features/attention.py`'s own
documented real-aperture evidence, not invented from scratch) and runs it
through the **real, unmodified** `BlinkDetector`:

- **Clean synthetic case**: 5 known onsets, detector recovers all 5,
  `precision=1.0 recall=1.0 f1=1.0`.
- **Deliberately degraded case** (half the real detections dropped, two
  spurious detections added far from any real blink): F1 drops from
  `1.0` to `0.615` — confirming the metrics actually MOVE in the expected
  direction under a worse detector, not merely that they compute without
  crashing.
- **Full multi-clip run**: three synthetic clips through
  `evaluate_run()`, producing a pooled precision/recall/F1 (TP/FP/FN
  summed across clips before taking one set of ratios — never a
  mean-of-per-clip-ratios, which would weight a 1-blink clip the same as
  a 30-blink one) and a count-agreement Bland-Altman result.

**Confirmed by construction that `run_detector_on_aperture_stream()`
records the REOPEN-confirmation timestamp, not the closure onset** (see
that function's own docstring) — a real methodological choice, stated
explicitly rather than left for a reader to discover, since it affects
how a ~150ms tolerance should be interpreted against a real ~150-300ms
blink duration.

### THE CLIPS DO NOT EXIST YET — stated as plainly as the task requires

**No real clip has been recorded. No real clip has been processed by this
harness. No placeholder result for a real clip exists anywhere in this
repository.** Every number `controls/blink_positive.py` or
`tests/test_blink_positive.py` has ever produced is either a hand-
constructed example (event-matching/metric correctness) or the synthetic
aperture stream described above. `tests/test_blink_positive.py`'s
`check_no_placeholder_real_clip_artefacts_committed` checks this
repository's own tracked file list for anything shaped like a real clip
manifest or manual-count file and finds none.

### 3.4 — scope limit, stated explicitly

**This validates blink-count DETECTION only.** It establishes no
psychological interpretation of blinking — not fatigue, not attention,
not affect, not anything else CLAUDE.md's honest-framing rules already
forbid claiming from a geometric signal. A detector that reliably counts
blinks the way a human would is a DETECTION-validation result. **Detector
validation is not construct validation.** Nothing in this control, or in
any report it produces, should be read as evidence about what blinking
*means* for this subject.

### How to run it

```python
from controls.blink_positive import (
    BlinkPositiveConfig, build_clip_manifest, write_manual_count_template,
    load_manual_count, run_detector_on_aperture_stream, evaluate_run, format_blink_report,
)

# 1. Build the manifest and manual-count templates for N real clips (once recorded):
manifest = build_clip_manifest([f"clip_{i:02d}" for i in range(10)])
for entry in manifest:
    write_manual_count_template(entry.clip_id, f"manual_counts/{entry.clip_id}.csv")
    # -> a human fills this in by hand, one blink timestamp per line.

# 2. Once a clip is recorded and its aperture stream extracted:
detected = run_detector_on_aperture_stream(aperture_stream)  # [(t, aperture_or_None), ...]
manual = load_manual_count(f"manual_counts/{entry.clip_id}.csv")["blink_timestamps_seconds"]

# 3. Evaluate across all clips and print the report (no verdict):
result = evaluate_run([(cid, detected, manual) for cid, detected, manual in per_clip_data], BlinkPositiveConfig())
print(format_blink_report(result))
```

---

## 5. Time-shuffle control (`controls/time_shuffle.py`)

**Matrix row 18** — missed when the other three controls were built,
added here.

### What it is

Shuffles **episode order** — never individual frames or trials — and
re-runs the exact same with/without comparison `controls/leakage.py`'s
four window variants run (`compute_delta`/`bootstrap_ci_on_delta`,
reused, not reimplemented). If ordered and shuffled performance are
comparable, temporal organisation (WHEN something happened, not just
THAT it happened) is contributing little to the with-signal model's
apparent performance — a direct check on the behavioural-dynamics claim.

`shuffle_episode_order()` permutes which episode's content fills which
chronological slot, preserving each ORIGINAL session's episode count (a
slot can move across session boundaries — deliberate, since session
dummy features are exactly the kind of temporal-organisation feature this
control tests) while leaving every trial's own observed content
(`x_signal`, `class_label`, `z`, `missing`) completely untouched.
Position-dependent fields (`global_trial_idx`, `episode_id`,
`session_idx`, `t_in_session`, `prev_class_label`) are recomputed for
internal self-consistency after the shuffle — verified directly
(`tests/test_time_shuffle.py`): the multiset of trial content is
byte-identical before and after, session slot sizes are preserved,
`prev_class_label` always equals whatever trial's `class_label` now
immediately precedes it in the shuffled order, and the same seed produces
the identical shuffle twice while a different seed produces a genuinely
different one.

### A representative run (synthetic, seed 21, strong drift/fatigue)

```
condition      u_with  u_without  delta_point      ci_lo      ci_hi  delta_negctrl n_test_trials
------------------------------------------------------------------------------------------------
ordered        0.3989     0.3101      +0.0888    +0.0472    +0.1294        -0.0004           600
shuffled       0.4168     0.3112      +0.1056    +0.0501    +0.1675        -0.0001           600

DIFFERENCE (ordered - shuffled): delta_point_diff=-0.0168  CI=[-0.0936, +0.0479]
```

Reported, not judged (G1): on this synthetic draw the difference's CI
spans zero. That is a number for a human to read, not a claim this
document is making about whether temporal organisation matters — see
1.3 immediately below for why no p-value-shaped interpretation may ever
be attached to it.

### 1.3 — DIAGNOSTIC ONLY, not a permutation-test p-value

CLAUDE.md's own D0PA1 hard constraint #4 draws this line explicitly:
*"time-shift (diagnostic only, never a p-value)"* is listed separately
from the INFERENTIAL permutation procedure, which *"must preserve
temporal dependence and has its own exchangeability unit, which need not
match the bootstrap unit."* `controls/time_shuffle.py` implements the
FORMER only. This is not a stylistic caveat left to a docstring a reader
could miss: every result dict carries `"diagnostic_only": True,
"not_a_permutation_test_pvalue": True` as literal fields (checked
directly, `tests/test_time_shuffle.py`), and `format_time_shuffle_table()`
prints the same warning as the first four lines of the report, before any
number appears.

### 1.4 — negative control, verified the same unaware-caller way

Both conditions (`ordered` and `shuffled`) run through `compute_delta()`,
which always builds the negative control unconditionally — carried
through automatically here for the same reason it is in
`controls/leakage.py`. Verified directly: `run_time_shuffle_diagnostic(source,
3, 3, n_boot=100)` — no mention of negative controls anywhere in the call —
still returns `delta_negative_control` populated for both conditions.

### 1.5 — synthetic only, stated plainly

Built and tested exclusively against `simulation/generator.py`. **This
control has not been run on real trials, because real trials do not
exist yet** — the client's task harness that would produce them is under
separate acceptance review, and D2 (action classes, horizon) is BLOCKED
per CLAUDE.md. Same pluggable `trial_source` contract as
`controls/leakage.py` (a zero-argument callable) — a future real-trial
source can be substituted without any change to this module.

### How to run it

```python
from controls.time_shuffle import run_time_shuffle_diagnostic, format_time_shuffle_table, TimeShuffleConfig
from simulation.generator import GeneratorConfig, generate

def source():
    return generate(GeneratorConfig(seed=1, n_sessions=3, episodes_per_session=200, trials_per_episode=5, effect_size=0.4))

result = run_time_shuffle_diagnostic(source, n_classes=3, n_sessions=3, config=TimeShuffleConfig())
print(format_time_shuffle_table(result))
```
