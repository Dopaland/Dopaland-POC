# D6 Simulation — Generative Model and Assumptions

**Status: Pass 1 (sections 1-8 below), PLUS a Pass 2 addendum (section 9)
covering what changed and why.** This document describes
`simulation/generator.py` and `simulation/precision.py` in full — every
parameter, every mechanism, and why each choice was made. Per G1, none of
this proposes or decides anything about RETAIN/DROP/INCONCLUSIVE; it
documents a data-generating process and an analysis pipeline whose only
output is a number (a CI width on Δ) for a human to compare against
candidate δ values.

**Read this before reading the numbers in `artefacts/precision_analysis_v1.md`
(Pass 1) or `artefacts/precision_analysis_v2.md` (Pass 2).** The numbers
are downstream of these assumptions. If an assumption here is wrong, the
numbers are wrong in a way this document should make it possible to
predict the direction of. Sections 1-8 are Pass 1, UNCHANGED from their
original form (Pass 1's own artefact and this document's own Pass-1
sections are left exactly as they were, per the "keep v1 unchanged"
principle) -- section 9 is new.

## 1. Why a simulation, and what it can and cannot tell us

This simulation answers one question: **given the study's actual hierarchy
(one subject, a handful of sessions, episodes within sessions, trials
within episodes) and realistic-scale N, how wide is a bootstrap confidence
interval on Δ (a difference in macro-F1 between two models)?**

It **cannot** tell us the real effect size, the real class structure, or
whether V_es/V_pd/attention actually carry predictive information about
real on-screen actions — none of that exists yet (D2, the prediction
target, is blocked; see CLAUDE.md's BLOCKED section). What it **can** tell
us is purely arithmetic: at the N this design can realistically collect,
is the CI on Δ narrow enough that ANY candidate δ could ever be resolved
into RETAIN or DROP, or is it so wide that INCONCLUSIVE is the only
possible verdict regardless of what the real data show? That question does
not require real data to answer — it requires only the study's hierarchy,
a plausible range of effect sizes, and correct arithmetic.

## 2. The hierarchy

```
subject (n=1)
 └── session (n_sessions)
      └── episode (episodes_per_session)
           └── trial (trials_per_episode)
```

`episode` is the resampling and exchangeability unit throughout, per
CLAUDE.md's D0PA1 hard constraint #4 ("resample at episode/session/day
level, never bootstrap frames or individual trials as if independent").
This mirrors `features/episodes.py`'s own `episode_unit` disclosure
(`"rolling_10s_window"`, itself provisional pending D2) — see §7 for how
the simulation's trial/episode timing assumption is anchored to that same
provisional unit, since no other definition exists in this repository.

## 3. Every generator assumption, with parameter value and justification

### A1 — Serial dependence (`ar1_phi`, `ar1_innovation_sigma`)

**Model:** a single continuous latent propensity `z_t` follows an AR(1)
process: `z_t = phi * z_{t-1} + eps_t`, `eps_t ~ N(0, sigma_t^2)`.

**Why AR(1), not a Markov chain on the class sequence directly:** an AR(1)
on a continuous latent state is the simplest model that (a) produces
genuine serial dependence at a controllable strength (`phi`), (b) composes
cleanly with A2/A3 (both act on this same latent state's dynamics, not on
a separate class-transition matrix), and (c) gives a natural, continuous
"observation" target for A6's candidate signal (the signal is a noisy
observation of `z_t`). A Markov chain on the class sequence would conflate
"how predictable is the next class from the last class" with "how much
does the candidate signal carry about the class" — the two questions this
study actually wants to keep separate.

- `ar1_phi = 0.6` — **INVENTED.** Moderate persistence: high enough to
  produce a real autocorrelation structure worth testing episode-level
  resampling against, not so high (`phi` near 1) that the process is
  nearly non-stationary. No real data exists to inform this; it is a
  round, moderate value chosen before any output was inspected.
- `ar1_innovation_sigma = 1.0` — **INVENTED**, sets the scale; the
  candidate-signal generation (A6) rescales by the implied stationary
  standard deviation, so this value's absolute scale does not otherwise
  matter to the results (see A6).
- **Restart per session:** `z` resets to 0 at the start of every session
  (no cross-session persistence of the raw latent path). This is a
  **documented simplification**, not a claim that a real subject's
  underlying state resets between sessions. It was chosen because D0PA1's
  D7 persistent-baseline work is a separate, not-yet-built piece of
  infrastructure — this simulation does not attempt to model
  cross-session state persistence, only within-session serial dependence
  and the across-session A2 learning trend (which is deliberately modeled
  as a SEPARATE mechanism from `z`'s own path, see A2).

### A2 — Learning trend (`gamma_base`, `learning_gain`, `learning_half_life_trials`)

**Model:** the strength of `z_t`'s effect on the class logits, `gamma_t`,
grows across the WHOLE STUDY (cumulative trials, persists across
sessions) via a saturating curve: `gamma_t = gamma_base * (1 +
learning_gain * (1 - exp(-cumulative_trials / learning_half_life_trials)))`.

**Why persistent across sessions, and why saturating:** learning a task's
structure is a plausible candidate for something that persists once
acquired (unlike within-session fatigue, which should reset). A saturating
curve (diminishing returns) is the standard, simple shape for a learning
curve — a subject doesn't get linearly better forever.

- `gamma_base = 1.0` — **INVENTED**, an arbitrary logit-scale unit; only
  relative values (the `learning_gain` multiplier) matter for the shape of
  the effect.
- `learning_gain = 0.5` — **INVENTED.** By full saturation, the
  class-informativeness of `z_t` is 50% higher than at the start. A
  moderate, round value.
- `learning_half_life_trials = 200.0` — **INVENTED.** At the assumed pace
  (§7), this is roughly half a session's worth of trials — i.e., learning
  is assumed to occur on a within-first-session timescale, not something
  that takes many sessions to show up. This is a guess with no empirical
  basis.

### A3 — Fatigue trend (`fatigue_gain`)

**Model:** the AR(1) innovation standard deviation inflates linearly
across a session: `sigma_t = ar1_innovation_sigma * (1 + fatigue_gain *
t_in_session)`, `t_in_session` in `[0, 1]`, and resets at the start of the
next session.

**Why this is a genuinely different mechanism from learning, not a mirror
image of the same knob:** learning (A2) makes the latent state's effect on
behaviour MORE STRUCTURED (higher `gamma_t`, a persistent, cross-session
change). Fatigue (A3) makes the latent state's own path NOISIER (higher
innovation variance, a within-session-only change that resets). A
subject can therefore be simultaneously "better at the task" (A2, growing
across the study) and "noisier by the end of today's session" (A3,
resetting tomorrow) — these are independent, oppositely-directed
mechanisms acting on different parts of the model, not `+x` vs `-x` on the
same term.

- `fatigue_gain = 0.5` — **INVENTED.** By session end, innovation std is
  50% higher than at session start (variance ~2.25× higher). A moderate,
  round value, symmetric in magnitude to `learning_gain` by design (so
  neither trend is arbitrarily favored) but this symmetry itself is an
  invented convenience, not evidence that the two effects are actually
  matched in a real subject.

### A4 — Class-frequency drift within a session (`class_drift_rate`)

**Model:** a fixed, random, zero-sum per-class direction vector is added
to the base class logits, scaled linearly by `t_in_session`. This shifts
the marginal class frequencies smoothly across a session without changing
the average base rate (zero-sum), and resets each session (uses
`t_in_session`, which restarts at 0 every session). The SAME drift
direction is reused across all sessions within one `generate()` call
(drawn once, not redrawn per session) — an arbitrary but stated choice;
the alternative (a fresh random direction each session) would not
qualitatively change the precision results, only which classes drift
toward or away from each other.

- `class_drift_rate = 0.3` — **INVENTED.** A moderate logit-scale drift
  magnitude. No real data exists on how on-screen action frequencies
  actually drift within a session (that requires D2's controlled task
  environment, which does not exist).

### A5 — Missingness with realistic clustering (`missingness_rate`, `missingness_mean_run_length`)

**Model:** a two-state (present/missing) Markov chain, not independent
per-trial dropout. Parameterized by the target STATIONARY missing rate
and the target MEAN RUN LENGTH (in trials) while missing; the two
transition probabilities (`P(present -> missing)`, `P(missing ->
present)`) are solved EXACTLY from those two numbers via the stationary-
distribution identity for a 2-state chain (`simulation/generator.py:_markov_missingness_params`,
verified analytically in `tests/test_generator.py`'s check 5). The
missingness state is drawn from its stationary distribution at the start
of each session (a session need not start "clean").

**Why not IID dropout:** a tracking-loss event (occlusion, the subject
turning away, the model losing lock) lasts for a contiguous run of frames,
not scattered independent instants. Modeling missingness as IID coin
flips at the same overall rate would produce many short, isolated gaps
instead of a few longer runs — understating its true cost to a
window/episode's usable data, because a single-frame gap is easy for a
window to absorb but a multi-second run may invalidate the whole window
(as `features/episodes.py`'s existing `DETECT_RATE_FLOOR` window-validity
gate already treats it).

- `missingness_rate = 0.05` (5%) as the PRIMARY/realistic assumption in
  the sweep, with `0.0` (no missingness, a clean baseline) and `0.15`
  (elevated/adverse) also swept — **INVENTED**, but anchored loosely to
  this repository's own historical soak-test finding that face detection
  is highly reliable in a controlled single-subject setting
  (`PROJECT_STATUS_REPORT.md`'s stability soak: FPS flat, no crashes over
  ~41 minutes) — 5% is a deliberately conservative (i.e., somewhat
  pessimistic relative to that soak) planning assumption, not a measured
  number from this exact setup.
- `missingness_mean_run_length = 5.0` trials — **INVENTED.** No real
  distribution of tracking-loss run lengths exists for this exact pipeline
  under D0PA1 conditions.

### A6 — True effect size (`effect_size`)

**Model:** the candidate signal under test, `x_signal`, is a noisy
observation of the SAME latent state `z_t` that drives the action class:
`x_signal = effect_size * z_unit + sqrt(1 - effect_size^2) * noise`, where
`z_unit = z_t / stationary_std(z)` and `noise ~ N(0,1)` independent of
`z`. This is a correlation-coefficient parameterization: `effect_size` is
intended to equal the population correlation between the observed
candidate signal and the true class-driving state.

**Known calibration approximation (disclosed, not silently absorbed):**
`z_t`'s true variance is NOT constant across a session because A3 fatigue
inflates the AR(1) innovation variance as the session progresses. The
rescaling above uses the STATIONARY variance implied by the BASE
(non-fatigued) innovation sigma, computed once per `generate()` call. This
means `effect_size` is calibrated exactly at the start of a session and is
a mild UNDERESTIMATE of the realized empirical correlation by the end of
a session (verified in `tests/test_generator.py`: at `effect_size=0.2`,
realized `corr(x_signal, z) ≈ 0.28`; at `0.5`, realized `≈ 0.61`; at
`0.8`, realized `≈ 0.87`, using the default `fatigue_gain=0.5`). **Every
result in the sweep reports both the nominal `effect_size` and the
realized empirical correlation** so this gap is visible, not hidden behind
a label.

- `effect_size = 0.0` is included in every sweep as the TRUE NULL: verified
  in `tests/test_generator.py` to produce `|corr(x_signal, z)| <= 0.05`
  (a true null, not a weak-but-nonzero leak).
- The swept range (`0.0` to `0.8`, see `artefacts/precision_analysis_v1.md`)
  is **INVENTED** — there is no real prior on what correlation, if any,
  V_es/V_pd or any other candidate representation has with a real
  subsequent on-screen action, because that comparison has never been run.

## 4. Trial classes and baseline (nuisance) features

The action-class structure (`n_classes = 3` by default) is entirely
**INVENTED** — D2 (which real action classes exist, and their count) is
blocked. Three classes was chosen as a plausible, simple placeholder
(binary would understate the difficulty of a real multi-way classification
target; more than 3-4 would mostly just shrink macro-F1's achievable
ceiling without changing the qualitative precision finding).

The "without" (baseline/nuisance) model's features are: `t_in_session`
(a continuous, deterministic time-within-session feature), a one-hot
encoding of `prev_class_label` (the previous trial's actual class — a
legitimate baseline predictor unrelated to any physiological signal: many
real action sequences have real self-transition structure), and — when
`n_sessions > 1` — a one-hot encoding of `session_idx`. The "with" model
adds `x_signal` (train-mean-imputed on missing trials, with a missingness
indicator dummy column) to that same baseline feature set. **Δ = macro-F1
in this exact head-to-head is a stand-in for the study's real M_core-vs-M0b
comparison** (Gate 3's naming) — it is generic on purpose, so the same
pipeline can later be pointed at real M_core/M0b/attention/latent
comparisons once D2 is answered; it is not itself a claim about what those
specific comparisons will show.

## 5. The classifier (simple model family)

A multinomial (softmax) logistic regression, implemented from scratch
(`simulation/models.py`, numpy + `scipy.optimize.minimize`, L-BFGS-B)
because scikit-learn is not installed in this environment and the
project's scope in any case restricts model families to simple ones. L2
regularization strength is chosen from a small fixed grid (`{0.1, 1.0,
10.0}`) per model, selected on the VALIDATION split (never on test) —
ordinary model selection on freshly generated synthetic data, done
identically regardless of the eventual Δ, not tuning against a real
result (G2 concerns tuning to make an EXISTING result look better; this is
routine model selection on synthetic data generated fresh for this
analysis).

## 6. The precision analysis (Part B)

- **Chronological split, episode-respecting:** episodes are sorted in
  time order and split 60% train / 20% validation / 20% test at EPISODE
  boundaries — no single episode's trials are ever divided across splits,
  since the episode is the exchangeability unit and splitting it would
  leak within-episode correlation across the train/test boundary.
- **Δ = macro-F1(with) − macro-F1(without)** on the test split. `macro_f1`
  is the DEFAULT metric function, passed as a parameter (`metric_fn`) —
  never hardcoded (B5) — so a different primary metric could be substituted
  without touching the analysis code.
- **Bootstrap CI, resampled at an explicit, required unit** (`episode` or
  `session` — `resample_unit` has no default and `'trial'` is refused with
  an explicit error, verified in `tests/test_precision.py`). The bootstrap
  resamples the TEST SET's units (with replacement) using the
  ALREADY-FITTED models' predictions, rather than refitting per
  replicate. **This is a documented computational simplification**: it
  bootstraps the EVALUATION's sampling variability (how much would Δ move
  if we happened to observe a different, equally-plausible draw of test
  episodes), not the full train-then-evaluate procedure's variability
  (which would also capture how much the FITTED MODEL itself would change
  under a different training sample). The full procedure is more
  correct and far more expensive (a full re-fit per bootstrap replicate,
  times every sweep point); the simplification used here is a
  standard, disclosed approximation for a precision/power-style analysis,
  not a hidden shortcut — and if anything, it likely UNDERSTATES the true
  variability (since it holds the fitted model fixed), meaning the true CI
  is probably somewhat WIDER than reported here, not narrower.
- **No verdict anywhere in this pipeline (G1).** `simulation/precision.py`
  computes `delta_point`, `ci_lo`, `ci_hi`, `ci_half_width` and stops. The
  comparison against candidate δ values happens only in
  `artefacts/precision_analysis_v1.md`, stated as arithmetic ("a CI
  half-width of X means a δ of Y can/cannot ever be resolved"), never as a
  recommendation.

## 7. What "realistic N for one subject across three sessions" means here

D2 has not defined a real trial or episode for this study — there is no
real answer to "how long is a trial" or "how many trials fit in a
session" yet. In the absence of that definition, this simulation anchors
its assumption to the **only** unit this repository has already defined,
even provisionally: the existing 10-second rolling window
(`features/episodes.py`'s `WindowAccumulator`, `episode_unit =
"rolling_10s_window"`, itself stamped `PROVISIONAL — blocked on client D2
decision` in `features/manifests/episodes_v1.json`). This is a convenience
anchor, not a claim that a real study episode will turn out to be 10
seconds — it is used here only so this document can give a concrete,
checkable number instead of an unfounded one invented from nothing.

- **1 episode = 1 existing 10-second rolling window.**
- **1 trial = 1 on-screen action opportunity within that window.**
  `trials_per_episode = 5` — **INVENTED**: an action opportunity roughly
  every 2 seconds is a plausible pace for active on-screen interaction,
  but nothing in this repository measures or confirms that pace.
- **Session length = 45 minutes of active recorded task time** —
  **INVENTED.** A single-sitting duration long enough to be practical for
  one subject to complete repeatedly across a 20-working-day window,
  short enough to avoid confounding with the fatigue mechanism (A3)
  becoming implausibly large. At 10s/episode, this gives
  **270 episodes/session** and **1,350 trials/session**.
- **3 sessions** (the study's planned number), with **1** and **2** shown
  for contrast per the task's instruction (B4).

**These four numbers (10s/episode, 5 trials/episode, 45 min/session, 3
sessions) are the load-bearing invented assumptions in this document.** If
the client's real answer to D2 implies a materially different trial rate,
episode duration, or session length, the "achievable N" conclusion in
`artefacts/precision_analysis_v1.md` should be re-derived from the new
numbers — the simulation code (`simulation/generator.py`,
`simulation/precision.py`) does not need to change, only the
`GeneratorConfig` values passed into it.

## 8. Limitations (see also the artefact's own limitations section)

- This is a simulation under stated, largely invented assumptions. No real
  behavioral or action data informs any parameter value here — that data
  does not exist yet (D2 is blocked).
- The classifier is a simple multinomial logistic regression on a
  hand-built, small feature set. A more expressive model family (still
  within scope) could plausibly extract more signal from the same data,
  changing the achievable Δ at a given N — this simulation does not sweep
  over model family, only over N/effect size/missingness.
- The bootstrap approximation (§6) likely understates the true CI width
  somewhat, meaning real achievable precision is probably slightly WORSE
  than reported, not better.
- A1–A6 are independently switchable in `GeneratorConfig`, but this Pass 1
  sweep does not explore every combination of them jointly (see
  `artefacts/precision_analysis_v1.md`'s own scoping note) — interactions
  between, e.g., fatigue and missingness are not separately characterized.

## 9. Pass 2 addendum — what changed and why

Full numeric results live in `artefacts/precision_analysis_v2.md`; this
section documents the MECHANISM changes in `simulation/generator.py` and
`simulation/precision.py` that produced them.

### 9.1 Rare classes (`n_rare_classes`, `rare_class_frequency`)

`GeneratorConfig` gained two fields: `n_rare_classes` (how many of the
LAST `n_classes` indices are "rare") and `rare_class_frequency` (their
shared target marginal probability). The client's task harness presents
THREE REGIONS, FORCED CHOICE, plus ABANDON and NO_ACTION as REAL classes
— `n_classes=5`, `n_rare_classes=2` models this directly.

**Calibration mechanism**: when `n_rare_classes > 0`, `base_logits` is set
to `log(target_probs)` (softmax is invariant to an additive constant, so
this is exact up to that constant) plus a small random jitter
(`scale=0.05`) for per-seed realism, where `target_probs` gives each rare
class exactly `rare_class_frequency` and splits the remainder evenly
across the non-rare "choice" classes. This is an EXACT calibration of the
STARTING marginal frequency — A2 (learning), A3 (fatigue), and A4 (class
drift) still perturb the realized frequency away from this baseline over
the course of a session/study, exactly as they do for the `n_classes=3`,
`n_rare_classes=0` path (unchanged, preserving Pass 1's exact
reproducibility for that configuration — verified in
`tests/test_generator.py`, which still reproduces Pass 1's exact printed
numbers after this change).

**`rare_class_frequency` values used (0.05 and 0.02) are INVENTED.** No
real data exists on how often a subject abandons a trial or takes no
action. These are round, plausible planning numbers, swept specifically
because the task asked for sensitivity to this exact unknown — see
`artefacts/precision_analysis_v2.md` §3 for how large that sensitivity
turned out to be (≈66% swing in CI half-width between the two values).

### 9.2 Session length as a swept parameter, not a second invented number

Pass 1's 45-minute session length was flagged as the single most
load-bearing invented number in the whole document. Pass 2 does not
replace it with a different single guess — `simulation/run_precision_sweep_pass2.py`
computes `episodes_per_session` from a session-length-in-minutes input via
the SAME anchor Pass 1 already used (`episodes_for_minutes(minutes) =
round(minutes * 60 / 10)`, since 1 episode = 1 existing 10-second rolling
window, unchanged from Pass 1 §7) and sweeps 25/35/45 minutes. No new
timing assumption was introduced; the existing one was exposed as a
parameter instead of hidden behind one chosen value.

### 9.3 Refit-per-replicate bootstrap, and the double-bootstrap correction

`simulation/precision.py` gained `bootstrap_ci_on_delta_refit()` and
`run_one_refit()`/`sweep_multi_seed_refit()`, mirroring Pass 1's
`bootstrap_ci_on_delta()`/`run_one()`/`sweep_multi_seed()` but resampling
and REFITTING rather than resampling a fixed model's predictions.

**A real error was found and fixed while building this** (fully accounted
in `artefacts/precision_analysis_v2.md` §7, summarized here): the first
implementation resampled ONLY the training episodes (refitting on each
resample) while holding the test set fixed. This measures a narrower,
DIFFERENT quantity than Pass 1's method (test-resampling variability),
not a superset of it, and on the primary config it produced a CI
*narrower* than Pass 1's (0.0088 vs 0.0113) — the wrong direction given
Pass 1's own disclosed concern. The fix resamples training episodes
(refit) AND test episodes (re-evaluate) INDEPENDENTLY within each
replicate — a proper double bootstrap capturing both sources of
uncertainty together — which produced 0.0149, wider than Pass 1's method,
confirming the fix addressed the actual gap rather than just changing a
number. `DeltaResult` was extended with `train`/`test`/`signal_impute_mean`
fields (populated by `compute_delta` unconditionally, at no extra
computational cost) specifically so the refit bootstrap has access to the
raw records it needs to resample and rebuild feature matrices from.

**Disclosed simplifications, unchanged from the original plan:** L2 and
the signal-imputation mean are fixed at the values chosen once on the
real (non-resampled) train/val split, not re-selected per replicate
(saves ~3x cost per replicate; targets a source of variability
—regularization-strength uncertainty— this correction was not asked to
capture). `n_boot` for the refit variant is 50 (vs Pass 1's 800) and
`n_seeds` is 5 (vs Pass 1's 10), both reduced for tractability and stated
plainly everywhere the resulting numbers are used, per this task's own
instruction to reduce and report rather than silently keep a cheaper
estimator.

### 9.4 Negative control wired into `compute_delta()`

`compute_delta()` gained a `negative_control_seed` parameter (default
`0`, always used — never `None`, never skippable) and now ALWAYS builds a
third comparison: baseline + `controls/negative_control.py`'s
deliberately meaningless AR(1) signal vs. baseline alone. `DeltaResult`,
`run_one()`, `run_one_refit()`, `sweep_multi_seed()`, and
`sweep_multi_seed_refit()` all carry `delta_negative_control` through
unconditionally. See `docs/CONTROLS.md` §2 for the full account and how
"cannot be omitted" was verified (not assumed) via
`tests/test_precision.py`'s `check_negative_control_cannot_be_omitted`.

## 10. Finalisation pass addendum (2026-08-30) — code-level account

Full numeric results and the client-facing writeup live in
`artefacts/precision_analysis_v2.md`'s own addendum section, which this
document's addendum supersedes v2's headline figure. This section
documents the CODE added for that pass:
`simulation/run_precision_sweep_finalisation.py`. No new generative
mechanism was introduced (unlike Pass 2's §9) — this pass reuses
`simulation/generator.py` and `simulation/precision.py` completely
unchanged, run across a wider grid and a larger `n_boot`.

### 10.1 Why a new script rather than editing the Pass 2 driver

`simulation/run_precision_sweep_finalisation.py` imports
`episodes_for_minutes`, `verdict_map`, and several constants directly
from `simulation/run_precision_sweep_pass2.py` rather than duplicating
them, so the two scripts cannot silently drift apart on what "45 minutes"
or "the verdict rule" means. It does not modify
`run_precision_sweep_pass2.py`, `run_precision_sweep.py`, or either
existing artefact's prior content — consistent with the "keep the record"
principle already established for Pass 1 vs Pass 2.

### 10.2 `n_boot` raised to 200, profiled before committing to the number

Before launching the full grid, single-cell timings were measured
directly (not assumed) at `n_boot=20`: ~0.11s/replicate at 25 minutes
(150 episodes), ~0.39–0.41s/replicate at 35/45 minutes (210/270
episodes) — the nonlinearity across session lengths reflects L-BFGS-B
convergence behavior differences, not a bug. Based on this, `n_boot=200`
was judged tractable (~16 minutes for the full 6-cell × 5-seed grid,
confirmed: it actually ran in 975 seconds). No smaller number was
substituted after the fact for speed.

### 10.3 Monte Carlo error is measured across SEEDS, not just within one bootstrap run

The finalisation script computes `ci_half_width_std`/`min`/`max` directly
from each cell's 5 per-seed half-width values (`sweep_multi_seed_refit`'s
existing `per_seed_rows`), rather than adding a new statistic to
`simulation/precision.py` itself. This was a deliberate interpretation
choice, stated explicitly: "Monte Carlo error on the half-width" could
mean either (a) resampling-only noise within one fixed dataset's
bootstrap (which `n_boot` controls), or (b) variability in the resulting
half-width across different synthetic data realizations (seeds), which
`n_boot` does NOT control. This pass measures (b), because it is the
practically relevant question ("how much should one trust this specific
number") and because comparing the SAME cell's spread at `n_boot=50`
(Pass 2) vs `n_boot=200` (this pass) empirically shows raising `n_boot`
alone does not shrink it (`artefacts/precision_analysis_v2.md`'s
addendum, Task 1) — direct evidence that (a) is not the dominant source
of the observed instability, which is exactly what this interpretation
choice was trying to establish.

### 10.4 The joint grid reuses `sweep_multi_seed_refit` unmodified

No change was made to `simulation/precision.py` for this pass — the 3×2
grid is six separate calls to the SAME `sweep_multi_seed_refit` Pass 2
already built, varying `episodes_per_session` (via `episodes_for_minutes`)
and `rare_class_frequency` together instead of one at a time. This is
deliberately the simplest possible extension: the joint grid was a
scheduling change (which configs to run), not a code change to how any
single config is analyzed.

## 11. Primary metric comparison (2026-08-30) — macro-F1 vs. log loss

Full numeric results and the client-facing writeup live in
`artefacts/precision_analysis_v2.md`'s "Addendum 2". This section
documents the CODE changes: `simulation/models.py` (new `neg_log_loss`),
`simulation/precision.py` (refactored to a metric abstraction), and
`simulation/run_metric_comparison.py` (new driver).

### 11.1 Why a comparison of RAW half-widths would be meaningless

A macro-F1 half-width and a log-loss half-width are numbers in different
units with no shared reference point — comparing 0.0209 macro-F1 points
to 0.0166 nats directly would answer nothing and could actively mislead.
The only comparison that means anything is **decidability = |Δ| /
half-width**, a dimensionless signal-to-noise ratio computed per seed (on
the SAME generated data, at the SAME true effect size, for each metric
independently) -- this is the entire reason
`simulation/run_metric_comparison.py`'s `_decidability_stats()` computes
and stores per-seed pairs rather than only aggregated statistics.

### 11.2 `neg_log_loss` (`simulation/models.py`)

`U = -log_loss` -- the SAME "higher is always better, Δ>0 is improvement"
orientation convention `macro_f1`'s Δ already uses, so no caller needs to
flip a sign depending on which metric is active. Takes `proba`, a
`(n_samples, n_classes)` array (the model's FULL predicted distribution,
from the already-existing `predict_proba()` -- no new prediction function
was needed). Clips to `[eps, 1-eps]` then renormalizes each row to sum to
1 (standard practice: clipping only the true-class column and leaving the
rest of the row unclipped would introduce a subtle bias). `eps=1e-15`
(scikit-learn's historical default) is a STATED, not hidden, choice --
`tests/test_precision.py`'s `check_neg_log_loss_clipping` demonstrates
directly that a single trial with an exactly-zero true-class probability
swings the reported value by more than 2x between `eps=1e-6` and
`eps=1e-15`. `macro_f1` itself was NOT touched -- it still takes hard
`y_pred`, exactly as before this pass.

### 11.3 The `Metric` abstraction (`simulation/precision.py`)

Rather than duplicate every fit/bootstrap/sweep function once per metric,
a small frozen dataclass `Metric(name, needs_proba, fn)` was introduced,
with two instances: `MACRO_F1_METRIC` (`needs_proba=False`, uses
`predict()`) and `NEG_LOG_LOSS_METRIC` (`needs_proba=True`, uses
`predict_proba()`). Every function that used to take `metric_fn=macro_f1`
now takes `metric=MACRO_F1_METRIC` -- `_select_l2_and_fit`,
`compute_delta`, `bootstrap_ci_on_delta`, `bootstrap_ci_on_delta_refit`,
`run_one`, `run_one_refit`. `_predict_for_metric(params, X, metric)` is
the one-line dispatch every call site uses instead of calling `predict()`
directly.

**L2 model selection is now metric-aware.** `_select_l2_and_fit` picks the
regularization strength that maximizes WHICHEVER metric is active on the
validation split, not always macro-F1 -- otherwise a log-loss Δ would be
reported on a model tuned for a different objective, biasing the
comparison itself in an uncontrolled way. Each metric gets its own
fairly-tuned "with" and "without" model, matching how either metric would
actually be used in practice.

**Verified, not assumed, that this changed no default behavior**:
`tests/test_precision.py`'s `check_metric_refactor_preserves_default_behavior`
runs the exact config from the pre-existing `check_ci_shrinks_with_n` with
no `metric` argument at all, and confirms the half-width and Δ are
BIT-IDENTICAL to calling with `metric=MACRO_F1_METRIC` explicit -- and,
separately, that every existing test in the file (which never passes
`metric=` anywhere) continues to reproduce its original numbers exactly.

**A pre-existing latent bug was found and fixed while generalizing this**:
`bootstrap_ci_on_delta`'s `n_classes` auto-inference fallback
(`n_classes=None`) computed `max(y_test, pred_with, pred_without) + 1`,
implicitly assuming `pred_with`/`pred_without` were hard integer labels.
Under `NEG_LOG_LOSS_METRIC`, these are `(n_samples, n_classes)` probability
matrices -- `.max()` on one of those returns some probability near 1.0,
not a class count, which would have silently produced `n_classes=1` or
similar nonsense. Fixed by checking `pred_with.ndim` first and using the
array's column count when it is 2-D. This path is not exercised by the
metric-comparison driver (which always passes `n_classes` explicitly) but
would have broken silently for any future caller relying on the fallback
with `NEG_LOG_LOSS_METRIC` -- caught by code inspection while making the
change, not by a failing test, and is recorded here so it is not
mistaken for something that was tested and passed.

### 11.4 `simulation/run_metric_comparison.py` -- two runs, two rigor levels

RUN 1 (`run_grid_comparison`) matches the finalisation pass EXACTLY --
same 3x2 grid, same `n_boot=200`, same 5 seeds -- for both metrics, so
every macro-F1 cell is directly comparable to
`artefacts/d6_finalisation_results.json`'s numbers (and was RE-RUN rather
than read from that file, because per-seed pairs are needed for
decidability and that file only kept aggregates). RUN 2
(`run_effect_size_correspondence`) sweeps `effect_size` at the single
realistic cell only, at deliberately REDUCED rigor (`n_boot=100`, 3
seeds) -- stated as a cost/thoroughness tradeoff, not hidden behind a
same-looking table.

**The structural immunity check (Task 2.4) is a small, separate,
un-scripted verification**, run directly against `bootstrap_ci_on_delta`
(Pass 1's ORIGINAL fixed-model, non-refit bootstrap) at 10 seeds and the
true null: macro-F1 hit an exact `0.000000` half-width on 2 of 10 seeds
(reproducing Pass 1's documented degeneracy); log loss never did (minimum
observed value `0.001213`). This confirms the degeneracy is a structural
property of comparing HARD decisions (two independently-fit models can
produce byte-identical argmax predictions on every trial) that a
CONTINUOUS, full-probability metric like log loss cannot exhibit, rather
than something merely papered over by the refit-bootstrap correction
already in use since the finalisation pass.

### 11.5 A timing anomaly

One grid cell (45min/rare=0.05, macro-F1) took ~12,451s versus 100-650s
for every other cell in the same run, with normal timing immediately
before and after. The result for that cell matches the independently-run
finalisation pass's value for the identical configuration exactly,
indicating a transient system-level slowdown (not investigated further)
rather than a computation error. See
`artefacts/precision_analysis_v2.md`'s Addendum 2 for the full account.

## 12. Clipping epsilon as a pre-registered parameter, and baseline levels (2026-08-30)

Full numeric results and the client-facing writeup live in
`artefacts/precision_analysis_v2.md`'s "Addendum 3". This section
documents the CODE: `simulation/config.py` (new), the one-line change to
`simulation/models.py`, and `simulation/run_eps_and_baseline_analysis.py`
(new driver).

### 12.1 `simulation/config.py` — minimal, not the full Gate 0 system

A single frozen dataclass, `PreRegisteredConfig`, with one field
(`log_loss_clip_eps: float = 1e-15`) and a `config_hash()` method
identical in spirit to `controls/null_input.py`'s `NullInputConfig` (a
short SHA-256 prefix of the config's own JSON representation). The
module docstring states explicitly that this is NOT the Gate 0
provenance system CLAUDE.md's D0PA1 section describes (experiment ID,
pinned dependencies, variant log, canonical log schema, data manifest) --
none of that exists. Adding a field to `PreRegisteredConfig` is reserved
for quantities that change a REPORTED METRIC's value, not ordinary
engineering constants (the L2 grid, split fractions, etc. stay where they
are — they affect model SELECTION, not what a fixed model's score means).

`simulation/models.py`'s `LOG_LOSS_CLIP_EPS` is now `PRE_REGISTERED_CONFIG.
log_loss_clip_eps` rather than a bare literal — a one-line change,
verified (not assumed) to produce the same value via
`tests/test_config.py`'s `check_models_sources_eps_from_config`.

### 12.2 Sensitivity measured on real fitted output, not just the pathological case

`simulation/run_eps_and_baseline_analysis.py`'s `run_eps_sensitivity()`
builds three ad hoc `Metric` instances via
`functools.partial(neg_log_loss, eps=eps_value)` (no change to
`simulation/precision.py` was needed — `Metric.fn` accepts any
`(y_true, proba, n_classes)`-shaped callable, and a `partial` satisfies
that contract) and runs the full refit double-bootstrap
(`sweep_multi_seed_refit`) at the realistic cell for each of
`eps in {1e-6, 1e-12, 1e-15}`, same 5 seeds, `n_boot=200`.

**Result: bit-identical output at all three eps values** (verified by
direct equality comparison on the raw floats in
`artefacts/d6_eps_and_baseline_results.json`, not by comparing
rounded/displayed numbers). This is consistent with, and now confirms
with a real measurement, Addendum 2's own stated expectation that fitted
probabilities in this generator's L2-regularized logistic regression
models rarely approach the clip boundary.

### 12.3 Baseline levels (`simulation/run_eps_and_baseline_analysis.py`)

Three functions, one per reference point:
- `uniform_predictor_log_loss`: closed-form `ln(n_classes)`, computed
  (not assumed) by actually constructing a uniform probability matrix and
  calling `neg_log_loss` on it, so the "exact, zero variance" claim in
  the addendum is a verified property, not an assertion.
- `marginal_predictor_log_loss`: empirical class frequency estimated from
  the TRAIN split only (the same no-leakage discipline
  `build_features`'s signal-imputation mean already uses elsewhere in
  this codebase), applied as a constant prediction to every test trial.
- `m0b_log_loss`: calls `compute_delta(..., metric=NEG_LOG_LOSS_METRIC)`
  and reads `-delta_result.u_without` -- this is DELIBERATE reuse, not a
  parallel re-implementation: "M0b" in this addendum is guaranteed to be
  the exact same fitted model object every other Δ in this study is
  compared against, because it IS that object, not a separately
  maintained stand-in for it.

All three are reported as plain log loss (nats, lower is better) rather
than the oriented `U = -log_loss` convention used everywhere else in this
codebase — a presentation choice for this addendum's baseline table
(reductions and perplexity read more naturally in positive nats), stated
explicitly so it is not mistaken for a change to the oriented-utility
convention used in Δ computations.

### 12.4 Conversion table -- pure arithmetic, no `Metric` or generator code involved

`build_conversion_table()` takes the M0b mean and a list of candidate δ
values and computes relative reduction, perplexity before/after, and the
ratio of δ to each of the two already-known half-widths (Addendum 2's
realistic-cell and worst-cell values, `0.0166` and `0.0246` -- read from
that addendum, not re-derived by a new sweep). No new simulation run
underlies this table; it is a pure function of numbers already
established. The "resolvable" fields are booleans computed as
`ratio > 1.0` -- reported as data, never printed as, or worded like, a
RETAIN/DROP/INCONCLUSIVE verdict (G1).

---

## 13. Synthetic latent recovery (`simulation/latent_recovery.py`)

```
Z_true -> observation generator -> pipeline -> Z_hat
recovery_error = d(Z_true, Z_hat)
```

Reuses `simulation/generator.py` unchanged: `Z_true` is the generator's
own `z` field (the AR(1) latent state, generator-internal, kept exactly
for this purpose — see that module's own docstring), the "observation
generator" is `generate()`'s existing `effect_size`-controlled mixture
plus an added `add_observation_noise()` step (extra i.i.d. Gaussian
corruption applied on top, a genuinely separate axis from `effect_size` —
see that function's own docstring for why the two are not the same knob),
and "pipeline" is `recover_latent_ema()` — a single exponential moving
average, reset per session, carrying forward through missing observations
(no new information, no update). This is the simplest procedure
consistent with the client's own "simple model families" scope
constraint (`simulation/models.py`'s docstring) — not a filter chosen
because it produced a nicer curve (G2).

**`recover_latent_ema()` is a PLACEHOLDER, stated explicitly, not the
study's actual latent model.** The study's real latent model does not
exist yet — this EMA exists solely to give the machinery something
concrete to recover a KNOWN `Z_true` from, so the correlation/RMSE
computation and the sweep code can be validated before any real method is
built. Every number this document reports below is a property of THIS
PLACEHOLDER, run against synthetic data with a known answer — not a
characterization, preview, or lower bound of what the eventual method
will achieve. Do not read the numbers below as evidence about the
eventual method.

### Why this is a PREREQUISITE, not an extra (2.5)

Without it, a near-zero measured latent contribution on real data is
ambiguous between two entirely different explanations: **"the latent
state genuinely adds nothing"** — a real, valuable *negative* result, one
of the outcomes this study is explicitly designed to be able to report —
and **"the recovery implementation is silently broken."** Those two
explanations demand completely different responses, and a bare near-zero
number does not, on its own, tell a reader which one they are looking at.
This module removes that ambiguity in the one place it CAN be removed —
on synthetic data where `Z_true` is known by construction — so that a
later near-zero result on real data can be read as a finding about the
subject, not a question about the code. Skipping this step does not save
work; it just moves the same question to a point where it can no longer
be answered.

### Both metrics, and why neither alone suffices (2.1)

`compute_recovery_metrics()` reports **Pearson correlation** and
**standardised RMSE** (`Z_true`/`Z_hat` each z-scored against their own
mean/std before RMSE) — never blended into one number. Verified directly
(`tests/test_latent_recovery.py`): a pure scale/offset error
(`Z_hat = 50·Z_true`) produces correlation ≈ 1 AND standardised RMSE ≈ 0
— confirming standardising correctly neutralises exactly the failure mode
correlation alone would hide (a systematic scale error still "looks"
perfect under correlation alone; RMSE on the RAW, non-standardised values
would have called that badly wrong, which is why standardising both series
before RMSE is the right choice for a machinery check that separates
scale error from genuine noise).

### The sweep (2.2) — the curve, not a point

`run_recovery_sweep(effect_sizes, extra_noise_stds, config)` runs the full
grid. On one real run (seed 11, 300 episodes/session, 5 trials/episode,
3 sessions, `ema_alpha=0.3`):

```
effect_size extra_noise_std  pearson_r  rmse_std  n_used n_total
----------------------------------------------------------------
       0.00            0.00    -0.0133    1.4236    4500    4500
       0.00            0.50    -0.0129    1.4233    4500    4500
       0.00            1.50    -0.0083    1.4201    4500    4500
       0.20            0.00    +0.2595    1.2170    4500    4500
       0.20            0.50    +0.2320    1.2393    4500    4500
       0.20            1.50    +0.1482    1.3052    4500    4500
       0.40            0.00    +0.4737    1.0260    4500    4500
       0.40            0.50    +0.4336    1.0644    4500    4500
       0.40            1.50    +0.2932    1.1889    4500    4500
       0.60            0.00    +0.6145    0.8781    4500    4500
       0.60            0.50    +0.5754    0.9215    4500    4500
       0.60            1.50    +0.4172    1.0796    4500    4500
       0.80            0.00    +0.7009    0.7734    4500    4500
       0.80            0.50    +0.6680    0.8148    4500    4500
       0.80            1.50    +0.5170    0.9829    4500    4500
```

**Reported, not judged (2.3):** correlation rises with `effect_size` and
falls with `extra_noise_std` at every grid point (confirmed monotonic
both ways on the mean, `tests/test_latent_recovery.py`'s
`run_real_sweep_and_report`) — the curve moves in the direction a working
recovery pipeline should move it. At `effect_size=0.0` (the true null),
correlation sits at ≈0 as it should — the placeholder EMA does not
fabricate structure from noise.

**The best cell on this grid (`effect_size=0.8`, `extra_noise_std=0.0`)
reaches `pearson_r≈0.70`, `rmse_std≈0.77`.** This number characterises
**the placeholder EMA pipeline described above, on synthetic data — and
nothing else.** It is not compared against the proposed success values
(correlation ≥ 0.7, standardised RMSE ≤ 0.5) anywhere in this module or
this document, and it must not be read as a preview of, or a bound on,
what the study's eventual (not-yet-built) latent model would achieve on
the same data. Recording the number and this caveat is the full extent
of what this section does with it — no comparison, no judgment, no
threshold, here or anywhere else in this codebase (G1/2.3).

### What this validates, and what it categorically does not (2.4)

This validates the MACHINERY — correlation/RMSE computation, missing-data
handling, a simple recovery procedure — under KNOWN, STATED assumptions
(the generator's own AR(1)/A1–A6 model). **It establishes nothing about
whether a human latent state is psychologically real.** That distinction
is CONTRACTUAL, not stylistic: a result from this module is never
evidence about the subject, only evidence about whether this code, run
against data with a known answer, gets that known answer approximately
right.
