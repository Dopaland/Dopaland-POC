# D6 Simulation — Generative Model and Assumptions

**Status: Pass 1.** This document describes `simulation/generator.py` and
`simulation/precision.py` in full — every parameter, every mechanism, and
why each choice was made. Per G1, none of this proposes or decides
anything about RETAIN/DROP/INCONCLUSIVE; it documents a data-generating
process and an analysis pipeline whose only output is a number (a CI width
on Δ) for a human to compare against candidate δ values.

**Read this before reading the numbers in `artefacts/precision_analysis_v1.md`.**
The numbers are downstream of these assumptions. If an assumption here is
wrong, the numbers are wrong in a way this document should make it possible
to predict the direction of.

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
