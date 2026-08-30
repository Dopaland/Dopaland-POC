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
