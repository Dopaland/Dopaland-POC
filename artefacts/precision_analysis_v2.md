# D6 Precision Analysis — v2

**Date:** 2026-08-30
**Status:** Pass 2. Synthetic simulation only — no real subject data exists yet (D2 is blocked).
**Supersedes nothing:** `artefacts/precision_analysis_v1.md` is left UNCHANGED in this
repository. This document is a NEW, separate artefact reporting what changed between
the two passes and why, per this task's explicit instruction.
**Governing guardrails:** G1 (no verdicts anywhere in this document except the verdict
MAP in §5, which is arithmetic applied to hypothetical true Δ values, never a claim
about the real Δ or a recommended δ), G2 (no assumption was adjusted to make a number
look better — see §7 for a case where a correction was found to move a number in the
"wrong" direction and was fixed on methodological grounds, not reverted), G3 (every gap
and every invented number is named).
**Code:** `simulation/generator.py` (extended), `simulation/precision.py` (extended),
`simulation/run_precision_sweep_pass2.py` (new). `docs/D6_SIMULATION.md` §9 documents
every mechanism change in full.

---

## 1. What Pass 1 disclosed, and what this pass fixes

Pass 1 reported a bootstrap CI half-width on Δ of ≈0.019 macro-F1 points at N≈4,050
trials, and explicitly flagged three ways that figure was optimistic:

1. **Bootstrap resampled only the test-set evaluation**, holding a single fixed fitted
   model constant — disclosed as likely *understating* the true CI width.
2. **n_classes=3** was an assumption made because the action space was undefined at the
   time. It is now known: the client's task harness presents three forced-choice
   regions plus ABANDON and NO_ACTION as real classes — five, not three.
3. **Session length (45 minutes) was a single invented number**, flagged as "the single
   most load-bearing invented number in the document."

This pass fixes all three, in the order given, and reports the size of each correction.

---

## 2. 1.1 — Refit per bootstrap replicate: old vs. new, side by side

Both numbers below are computed on the **identical** synthetic dataset config
(n_classes=5, 2 rare classes at frequency 0.05, 3 sessions × 270 episodes × 5 trials,
effect_size=0.3, missingness=0.05) — only the bootstrap method differs, isolating the
effect of the correction itself from the n_classes/session-length changes covered in
§3–§4.

| Method | n_boot | median CI half-width | median Δ_point |
|---|---|---|---|
| **Pass 1 method** — fixed-model, evaluation-only bootstrap | 800 | **0.0113** | 0.0114 |
| **Pass 2 method** — refit per replicate (double bootstrap, see §7) | 50 | **0.0149** | 0.0114 |

**The correction widens the CI by ≈32%** (0.0113 → 0.0149). Δ_point itself is
unaffected (it does not depend on the bootstrap method) — only the reported precision
around it does. This is the expected direction: capturing model-refit uncertainty on
top of test-sampling uncertainty should widen, not narrow, an honest interval. See §7
for a real methodological error found and fixed while building this correction, and why
it matters that the direction is checked, not assumed.

`n_boot` dropped from 800 to 50 because a full refit is far more expensive per replicate
than re-evaluating a fixed model (profiled directly: ≈0.35–0.44s per double-bootstrap
replicate at this N, vs. Pass 1's 800 replicates completing in well under a second
combined). 50 is a deliberately reduced, explicitly reported count — not hidden behind
an unchanged-looking "n_boot" label.

---

## 3. 1.2 — n_classes=3 vs. n_classes=5, and rare-class frequency sensitivity

All rows below use the corrected (refit, double-bootstrap) method, `n_boot=50`, median
over 5 seeds, at the realistic 45-minute/3-session N.

| Configuration | median CI half-width | median Δ_point | negative-control median Δ |
|---|---|---|---|
| n_classes=3 (Pass 1's structure, for comparison) | 0.0177 | 0.0214 | 0.0000 |
| **n_classes=5, rare_class_frequency=0.05** (primary) | **0.0149** | 0.0114 | 0.0015 |
| n_classes=5, rare_class_frequency=0.02 (secondary) | 0.0248 | 0.0248 | 0.0003 |

**Two assumed rare-class frequencies, stated as assumptions, not measurements:**
0.05 ("moderately rare" — e.g. abandoning or declining to act roughly 1 trial in 20) and
0.02 ("very rare" — roughly 1 in 50). Neither is derived from real data; D2's real
action-class frequencies do not exist yet.

**Sensitivity is large and in the expected direction:** halving the rare-class
frequency (0.05→0.02) *widens* the CI by ≈66% (0.0149→0.0248). Macro-F1 weights every
class equally, so a rarer class contributes disproportionately more finite-sample
variance to the metric — exactly the mechanism the task asked this pass to check for.
**Which of these two frequencies is closer to reality is unknown** — this table exists
so a human with a real estimate of ABANDON/NO_ACTION frequency can read off the
corresponding precision, not to suggest either number is correct.

---

## 4. 1.3 — Session length as an explicit swept parameter

At n_classes=5, rare_class_frequency=0.05 (primary), 3 sessions, refit bootstrap,
`n_boot=50`, median over 5 seeds:

| Session length | Episodes/session | Total trials (3 sessions) | median CI half-width |
|---|---|---|---|
| 25 minutes | 150 | 2,250 | 0.0237 |
| 35 minutes | 210 | 3,150 | 0.0163 |
| 45 minutes | 270 | 4,050 | 0.0149 |

Session length is no longer a single invented number standing in for "the answer" — it
is a parameter a human can read off once the real session length is known. The anchor
(10 seconds/episode, 5 trials/episode, ≈2s/trial) is UNCHANGED from Pass 1
(`docs/D6_SIMULATION.md` §7) — only the number of sessions' worth of minutes is now
swept rather than fixed at one guess.

---

## 5. 1.4 — Verdict map (arithmetic only — no recommendation)

Built from the corrected, primary CI half-width: **0.0149** (n_classes=5,
rare_class_frequency=0.05, 45-minute sessions — §3's primary row). Models the observed
CI as `[true_Δ − half_width, true_Δ + half_width]`, applying the pre-registered rule
exactly as stated in this task's prompt:

```
RETAIN        lower bound of CI on Δ  >  δ
DROP          upper bound of CI on Δ  <  δ
INCONCLUSIVE  CI spans δ
```

| True Δ | Verdict at δ=0.03 | Verdict at δ=0.05 |
|---|---|---|
| 0.00 | DROP | DROP |
| 0.01 | DROP | DROP |
| 0.02 | **INCONCLUSIVE** | DROP |
| 0.03 | **INCONCLUSIVE** | DROP |
| 0.04 | **INCONCLUSIVE** | **INCONCLUSIVE** |
| 0.05 | RETAIN | **INCONCLUSIVE** |
| 0.06 | RETAIN | **INCONCLUSIVE** |
| 0.07 | RETAIN | RETAIN |
| 0.08 | RETAIN | RETAIN |
| 0.09 | RETAIN | RETAIN |

**For δ=0.03:** the forced-INCONCLUSIVE range is true Δ ∈ **(0.0151, 0.0449)**
(δ ± half_width). The DROP range is true Δ ∈ **[0, 0.0151]**. RETAIN is reachable for
true Δ ≥ 0.0449.

**For δ=0.05:** the forced-INCONCLUSIVE range is true Δ ∈ **(0.0351, 0.0649)**. The DROP
range is true Δ ∈ **[0, 0.0351]**. RETAIN is reachable for true Δ ≥ 0.0649.

This table states arithmetic only. It does not say which δ is preferable, and it does
not say what the real Δ will be — both remain for a human to determine.

---

## 6. Negative control — reported automatically, alongside every row above

D0PA1 Part 2.2's negative control (`controls/negative_control.py`) is now wired into
`simulation/precision.py`'s `compute_delta()` unconditionally — every row in §2–§4
carries its own negative-control Δ, computed on an independently-seeded, deliberately
meaningless AR(1) signal that shares no random state with anything else in the analysis
(see `docs/CONTROLS.md` §2 for the full account and how the "cannot be omitted" claim
was verified, not assumed).

Observed negative-control medians across §3's three rows: **0.0000, 0.0015, 0.0003** —
all far below either candidate δ (0.03, 0.05) and consistent with ordinary
finite-sample noise. Reported, not decided upon: nothing here triggers an automatic
exclusion (per the task's own instruction that occasional apparent significance from a
negative control across many tests is expected, not automatically disqualifying).

---

## 7. A methodological error found and fixed during this pass — reported in full

An earlier version of the Pass 2 refit bootstrap resampled ONLY the training episodes
(refitting on each resample) while holding the test set FIXED. Run on the primary
config, it produced a half-width of **0.0088** — *narrower* than Pass 1's fixed-model
method (0.0113), the opposite of the disclosed direction. Investigating rather than
reporting this: resampling only training data and evaluating on an unchanged test set
measures a DIFFERENT, narrower quantity ("how much would Δ move if we had different
training history, holding the actual observed test outcomes fixed") than Pass 1's
method measures ("how much would Δ move under a different draw of test episodes") — it
is not a strict superset of Pass 1's uncertainty, it is a different, non-comparable one.
**The fix:** resample training episodes (refit) AND test episodes (re-evaluate)
independently within every replicate — a double bootstrap capturing both sources of
variability together. Re-run, this produced 0.0149 — wider than Pass 1's method, the
expected direction. This full account, including the incorrect intermediate number, is
recorded here and in `docs/D6_SIMULATION.md` §9 rather than quietly replaced (G2/G3):
the corrected code was NOT chosen because 0.0149 "looked more right" after the fact —
it was chosen because the single-resample version was independently identified as
measuring the wrong quantity, and the fix was verified to move the number in the
theoretically-expected direction before being adopted.

---

## 8. Assumptions — carried over, changed, and newly introduced

**Carried over from Pass 1, unchanged:**
- A1–A6 generative mechanisms and their parameter values (AR(1) φ=0.6, learning/fatigue
  gains, class-drift rate, missingness rate/run-length) — see `docs/D6_SIMULATION.md` §3.
- The realistic-N anchor's per-episode/per-trial timing (10s/episode, 5 trials/episode,
  ≈2s/trial) — only the number of session-minutes is now swept, not this anchor itself.
- The simple multinomial logistic regression model family and its L2 grid `{0.1, 1.0, 10.0}`.
- The 60/20/20 chronological, episode-respecting train/val/test split.
- `effect_size=0.3` as the moderate, clearly-nonzero anchor used for the N-curve and
  session-length sweeps (matches Pass 1's own N-curve anchor).

**Changed in Pass 2:**
- **Bootstrap methodology**: fixed-model evaluation-only → refit-per-replicate double
  bootstrap (§2, §7). `n_boot` reduced from 800 to 50 for the refit variant (cost).
  `n_seeds` reduced from Pass 1's 10 to 5 (cost) — stated plainly: results in this
  document carry more Monte Carlo noise per number than Pass 1's did.
- **n_classes**: 3 → 5 as the PRIMARY configuration (3 retained only for comparison, §3).
- **Session length**: a single fixed 45-minute guess → an explicit swept parameter
  (25/35/45 minutes, §4).

**Newly introduced in Pass 2 (INVENTED, no real basis yet):**
- `n_rare_classes=2` and the identity of ABANDON/NO_ACTION as the two rare classes —
  this structural fact comes from the client's task-harness specification (not
  invented), but its REALIZATION in the generator (how rare classes are calibrated to
  a target marginal frequency, `simulation/generator.py`'s new base_logits branch) is
  new mechanism, documented in `docs/D6_SIMULATION.md` §9.
- `rare_class_frequency ∈ {0.05, 0.02}` — both INVENTED; no real frequency data exists
  for how often a subject abandons a trial or takes no action.
- The double-bootstrap's own simplifications: L2 and the signal-imputation mean are
  fixed at the values chosen once on real (non-resampled) data, not re-selected per
  replicate (cost-saving, disclosed in `simulation/precision.py`'s own comments).
- The negative control's AR(1) φ=0.6 (matched to the generator's own A1 default) and
  `sampling_rate_hz=25.0` (matched to CLAUDE.md's CADENCE note) — both INVENTED choices
  for how to construct a "fair" nuisance signal, not measurements.

---

## 9. Limitations (in addition to Pass 1's, which still apply)

- **5 seeds, not 10**: every median reported in this document is noisier than the
  corresponding Pass 1 number. Where §3/§4's numbers look non-monotonic in a way that
  seems surprising, seed noise at n=5 is a plausible explanation before any mechanism
  is invoked to explain it.
- **50 bootstrap replicates, not 800**: the refit CI bounds themselves are noisier
  estimates than Pass 1's fixed-model bounds. The verdict map in §5 inherits this
  extra noise — a different run with a different seed set would shift the exact
  boundary values (though not, based on §2's replication, the qualitative picture).
  Please note: given time constraints only ONE double-bootstrap configuration (§2) was
  used to validate the direction of the fix; the full grid (§3, §4) was run once each
  at n_boot=50, not independently re-validated at a larger n_boot.
- **The double bootstrap still fixes L2 and the imputation mean** (§8) — a further,
  smaller source of real-world variability (regularization-strength uncertainty) that
  this pass's numbers still do not capture.
- **Rare-class frequency is a pure guess** (§3) — the ≈66% swing in CI half-width
  between the two assumed frequencies means this single unknown number matters more to
  the achievable precision than most of the other assumptions in this document
  combined. If the client can supply even a rough real estimate, re-running §3's sweep
  at that value would sharpen this analysis considerably more than any other single
  action available right now.

---

## Addendum (2026-08-30) — bootstrap precision and the joint grid

**This addendum supersedes this document's own headline figure (0.0149 macro-F1
points, §2/§4) for PLANNING purposes.** The reason: §2's number was computed at
`n_boot=50` (Monte Carlo noise not yet quantified) and at a single factor combination
(45-minute sessions, rare-class frequency 0.05) while the OTHER factor was held at its
own most favourable value. Neither condition holds for the real study, which will
combine whatever the real session length and real rare-class frequency turn out to be
— the number below is what actually governs planning until those two real values are
known. **v1 and v2's own sections above are left completely unchanged** — this
addendum is new content appended below them, not a correction overwriting what was
already reported.

### Headline: the achievable precision is worse than v2 reported, and highly variable

At the worst combination of assumptions this simulation tested (25-minute sessions,
rare-class frequency 0.02), the mean bootstrap CI half-width across 5 seeds is
**0.0339** macro-F1 points — individual seeds ranged as high as **0.0444**. This is
**larger than the smaller candidate δ (0.03) by itself**. At this combination, a δ of
0.03 has **no true effect size for which DROP is even reachable** — every non-negative
true Δ from 0 up to roughly 0.064 resolves to INCONCLUSIVE, and only Δ ≥ 0.064 permits
RETAIN. This is not a bad result to report — it is exactly the kind of finding this
simulation exists to surface before, not after, a δ is signed.

### Task 1 — stabilising the estimate

**Replicate count and cost.** Raised from Pass 2's `n_boot=50` to `n_boot=200` (a 4x
increase) for every figure in this addendum. The full 6-cell joint grid (Task 2) at
`n_boot=200`, 5 seeds, ran in **975 seconds (≈16.3 minutes)** wall-clock — well within
budget, so 200 was used as planned rather than reduced further for speed.

**Monte Carlo spread, and what it actually shows.** At the original Pass 2 cell
(45-minute sessions, rare-class frequency 0.05), raising `n_boot` from 50 to 200 gave:

| n_boot | mean | std | min | max | range (max−min) |
|---|---|---|---|---|---|
| 50 (Pass 2) | 0.0179 | *(not computed in Pass 2)* | 0.0098 | 0.0321 | 0.0223 |
| 200 (this addendum) | 0.0209 | 0.0118 | 0.0126 | 0.0433 | 0.0307 |

**The spread did NOT shrink when `n_boot` quadrupled — if anything the observed range
widened.** This is the key methodological finding of Task 1: the instability in the
reported half-width is **not primarily bootstrap resampling noise** (which more
replicates would fix) — it is **variability across which synthetic data realization
(seed) is drawn**, which a larger `n_boot` cannot address at all, because `n_boot`
only controls how precisely the CI is estimated FOR one fixed dataset, not how much
that CI would differ across different, equally-plausible datasets. Practically: the
answer to "is this a 0.0149 ± 0.004 or 0.0149 ± 0.0005 situation" is neither — it is
closer to **a genuinely wide underlying distribution (std comparable to or larger than
the mean itself in several cells, see the full grid below)**, and no amount of
additional bootstrap replicates within one run will narrow it. Only more independent
seeds (more simulated "alternate realities" for this one subject) characterize that
distribution better — `n_boot` and `n_seeds` answer different questions, and this
addendum's finding is that the SEED dimension, not the bootstrap dimension, is where
the real uncertainty lives.

### Task 2 — the joint grid

Full 3×2 grid, `n_classes=5`, refit-per-replicate double bootstrap, `n_boot=200`,
5 seeds (seeds 1–5, the same set Pass 2 used):

| Session length | Rare-class freq | N (trials) | mean half-width | std | min | max |
|---|---|---|---|---|---|---|
| 25 min | 0.02 | 2,250 | **0.0339** | 0.0090 | 0.0190 | 0.0444 |
| 25 min | 0.05 | 2,250 | 0.0266 | 0.0068 | 0.0189 | 0.0388 |
| 35 min | 0.02 | 3,150 | 0.0321 | 0.0126 | 0.0128 | 0.0467 |
| 35 min | 0.05 | 3,150 | 0.0227 | 0.0108 | 0.0134 | 0.0416 |
| 45 min | 0.02 | 4,050 | 0.0256 | 0.0112 | 0.0134 | 0.0442 |
| 45 min | 0.05 | 4,050 | 0.0209 | 0.0118 | 0.0126 | 0.0433 |

Every row above has its own genuinely large std relative to its mean (roughly 30–55%
relative standard deviation throughout) — this is not specific to the worst cell, it
is a property of the whole grid at this seed count.

### Worst cell, named explicitly

**25-minute sessions × rare-class frequency 0.02 — mean half-width 0.0339** (std
0.0090, individual seeds up to 0.0444). This matches the pre-stated expectation
exactly: both factors independently make precision worse (shorter sessions = less
data; rarer classes = more macro-F1 variance from the minority classes), and they
compound rather than cancel. **The ranking across all six cells matched expectation in
both dimensions with no surprises**: within each rare-class frequency, half-width
decreases monotonically as session length increases (25>35>45 min); within each
session length, `rare_freq=0.02` gives a wider half-width than `rare_freq=0.05` at
every one of the three session lengths. The only non-obvious observation was the SIZE
of the per-seed spread (above), not the direction of any ranking.

### Task 3 — verdict map at the worst cell, beside Pass 2's original map

Both tables apply the identical arithmetic rule (`RETAIN`: CI lower bound > δ; `DROP`:
CI upper bound < δ; `INCONCLUSIVE`: CI spans δ) to a range of hypothetical true Δ
values. Neither table states or implies which δ, or which planning assumption, should
be adopted (G1).

**Optimistic (Pass 2's original map): 45 min / rare=0.05, half-width = 0.0149**

| True Δ | δ=0.03 | δ=0.05 |
|---|---|---|
| 0.00–0.01 | DROP | DROP |
| 0.02–0.04 | INCONCLUSIVE | DROP (0.02–0.03), INCONCLUSIVE (0.04) |
| 0.05–0.06 | RETAIN | INCONCLUSIVE |
| ≥0.07 | RETAIN | RETAIN |

- δ=0.03: forced-INCONCLUSIVE for true Δ ∈ (0.0151, 0.0449); DROP for Δ ∈ [0, 0.0151];
  RETAIN reachable for Δ ≥ 0.0449.
- δ=0.05: forced-INCONCLUSIVE for true Δ ∈ (0.0351, 0.0649); DROP for Δ ∈ [0, 0.0351];
  RETAIN reachable for Δ ≥ 0.0649.

**Pessimistic (this addendum): 25 min / rare=0.02 (worst cell), half-width = 0.0339**

| True Δ | δ=0.03 | δ=0.05 |
|---|---|---|
| 0.00–0.06 | INCONCLUSIVE (no Δ in this range gives DROP) | DROP (0.00–0.01), INCONCLUSIVE (0.02–0.06) |
| 0.07–0.08 | RETAIN | INCONCLUSIVE |
| ≥0.09 | RETAIN | RETAIN |

- δ=0.03: forced-INCONCLUSIVE for true Δ ∈ (−0.0039, 0.0639) — since Δ is
  non-negative in this study, **every non-negative true Δ below 0.0639 is
  INCONCLUSIVE and DROP IS NOT REACHABLE AT ALL** for any plausible non-negative
  effect size at this δ. RETAIN reachable only for Δ ≥ 0.0639.
- δ=0.05: forced-INCONCLUSIVE for true Δ ∈ (0.0161, 0.0839); DROP for Δ ∈ [0, 0.0161];
  RETAIN reachable for Δ ≥ 0.0839.

**Side-by-side reading of the arithmetic** (stated, not recommended): the pessimistic
map's INCONCLUSIVE zone is roughly **2.3× wider** than the optimistic map's for both δ
values, and for δ=0.03 specifically, the pessimistic map removes DROP as a reachable
outcome entirely for any non-negative effect below the RETAIN boundary. Which of the
two planning assumptions (optimistic or pessimistic) is closer to the real study is
not something this simulation can determine — that depends on the real session length
and the real ABANDON/NO_ACTION frequency, neither of which is known yet.

### New assumptions introduced in this addendum

- `n_boot=200` for all figures in this addendum (Task 1.1) — a specific, stated choice,
  not defaulted.
- 5 seeds (1–5), the same set Pass 2 used — chosen for direct comparability with Pass
  2's own numbers, not re-derived independently.
- No new generative assumptions were introduced — this addendum runs the SAME
  generator and analysis code as Pass 2 (`simulation/generator.py`,
  `simulation/precision.py`, unmodified) across a wider grid and a larger `n_boot`. See
  `docs/D6_SIMULATION.md` section 10 for the code-level account.

### Limitations specific to this addendum

- **Only 5 seeds** underlie every mean/std/min/max above. With `n=5`, the std and
  range are themselves noisy estimates of the true seed-to-seed variability — the
  qualitative finding ("the spread is large and n_boot doesn't fix it") is robust, but
  the exact std values would likely shift with more seeds.
- The worst cell was identified by comparing MEAN half-width across the 6 cells;
  ranking by median would not change which cell is worst here (25min/rare=0.02's
  median, 0.0384, is also the highest of the six), but is worth stating since mean and
  median diverge noticeably within some cells (evidence of the same seed-driven
  skew noted above).
- This addendum does not re-examine whether more seeds (rather than more `n_boot`)
  would itself stabilise the headline figure — that would be the natural next
  question this finding raises, and is not answered here.
