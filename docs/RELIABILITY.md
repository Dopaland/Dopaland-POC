# Reliability Machinery — What It Computes, and What Data It Needs

**Read this before reading any number this machinery has ever produced.**
The required data does not exist yet. Every number in this document, and
every number `analysis/reliability.py`/`analysis/baselines.py` has ever
produced in this repository, is synthetic (`simulation/generator.py` or a
hand-constructed array with known ground truth) or a structural smoke-test
confirmation with no magnitude reported. **None of it is a reliability
finding for this study.**

---

## What data this machinery requires

Three sessions, on three separate days, under a **fixed protocol** with
**matched, repeatable units** — the same scripted episode or trial type,
presented the same way, measurable in every session. That is what "units =
scripted episodes or trials, measurements = sessions" (2.2) means in
practice: a `(n_units, n_sessions)` matrix where row `i`, column `j` is
"unit `i`'s value in session `j`," and unit `i` in session 1 is *the same
thing* as unit `i` in session 2.

**This has not been collected.** The existing files in `logs/` are POC
captures and diagnostic runs — different schemas, different protocols,
different conditions across files, no matched-unit structure at all. They
are not repeated measurements of anything. Using them as if they were
would produce numbers that *look* like a reliability result and are not
one — CLAUDE.md's G3 ("report gaps honestly") and this task's explicit
Part 3 instruction both forbid that, and it would be a worse outcome than
reporting nothing.

## What the machinery computes, once real data exists

**D7 baselines** (`analysis/baselines.py`, `docs/D7_BASELINES.md`): three
representations of the same recordings — `raw`, `session_z` (within-
session), `persistent_z` (cross-session, temporally leak-safe).

**D3 absolute reliability measures** (`analysis/reliability.py`), per
signal, separately, never blended:
- **SEM** — pooled within-unit standard deviation across sessions.
- **RC** — `1.96 × √2 × SEM`.
- **Bland-Altman limits of agreement** — bias ± `1.96 × SD(diff)`, computed
  per session **pair** (never one blended number across pairs), with an
  SVG plot per pair.
- **Within-unit CV%** — `SEM / |grand_mean| × 100`.

Each carries a bootstrap confidence interval, resampled at the **unit**
level using the exact resampling primitive extracted from
`simulation/precision.py`'s existing episode-level bootstrap
(`precompute_unit_row_groups`/`resample_rows_once`) — not a second,
independently-written resampling loop.

**`compute_icc()`** exists and is correct (Shrout & Fleiss 1979 ICC(2,1)),
but **refuses to run** on a single-unit structure — it raises with:

> *"ICC requires at least 2 distinct repeated-measurement units; got 1
> (...). With a single unit — e.g. one subject's one summary value per
> session, repeated across sessions — there is no between-unit variance
> for an ICC to be a ratio of; the result would be UNINTERPRETABLE, not
> merely imprecise. Use the absolute reliability measures instead
> (compute_sem/compute_rc/compute_bland_altman_*/compute_within_unit_cv in
> this module) — see CLAUDE.md D0PA1 hard constraint #1 and
> docs/RELIABILITY.md."*

**Why this matters for this study specifically**: with one subject, a
single summary value per session across three sessions is three
observations of *one* unit, not multiple units × k measurements. ICC on
that structure is not "imprecise" — it is not computable in any
interpretable sense. If a valid multi-unit design (repeated scripted
episodes) is agreed with the client later, `compute_icc()` is already
correct and ready; until then it fails loudly rather than silently
returning a meaningless number.

## What has been validated, and how

Every number produced by this machinery so far is one of:

1. **Hand-computed correctness checks** (`tests/test_reliability.py`,
   `tests/test_baselines.py`) — small arrays where the right answer can be
   computed by hand and compared exactly.
2. **Synthetic ground-truth recovery** — `simulation/generator.py` with
   `effect_size=0.0`, which makes its `x_signal` output *exactly* i.i.d.
   `N(0,1)` per trial by the generator's own documented construction.
   Averaging `T` such draws per episode gives cells with a *known*
   population variance `1/T`; `compute_sem()` recovered `0.1896` against a
   known target of `1/√30 = 0.1826` (3.8% relative error, one seed, 300
   episodes) — see `tests/test_reliability.py` for the exact check.
3. **A synthetic V_pd-shaped exploration** (heavy-tailed, population std
   ≈ `1.6e-4`, matching the real signal's documented dispersion order of
   magnitude but built from `scipy.stats.t(df=3)`, never real V_pd data)
   — see "V_pd's known shape" below.
4. **A structural smoke test against real logs**
   (`tests/test_reliability_smoke_real_logs.py`) — confirms the full
   pipeline executes end-to-end on real-log-shaped data (arbitrary
   25-sample chunks of real `v_es` values from 3 unrelated real session
   logs, standing in only for *data volume*, never for a matched-unit
   protocol) without crashing or silently producing NaN/inf. **This test
   never prints or asserts on the magnitude of any computed value** — by
   design, so that a passing run cannot be mistaken for a result.

## V_pd's known shape — what the exploration found

The client is already expecting this characteristic to matter: V_pd's real
dispersion runs around `1.6e-4` with a heavy tail, and its MAD runs
roughly 16× smaller than its SD. A synthetic exploration (`t`-distributed,
`df=3`, population std matched to `1.6e-4`, compared against a
matched-std Gaussian with the **same RNG seed for the bootstrap** so any
difference is attributable to the tail shape, not seed luck) found:

- The **point estimates** (SEM, RC, Bland-Altman SD) were not dramatically
  inflated on this particular draw — heavy-tailed SEM came in *slightly
  lower* than the Gaussian control (`1.36e-4` vs `1.59e-4`, a ratio of
  `0.85×`) on this one sample. A single finite sample from a heavy-tailed
  distribution can land close to — or even under — a same-scale Gaussian's
  realized spread; that is expected, not a sign the measure is broken.
- The **bootstrap CI half-width was 41% wider** for the heavy-tailed case
  (`3.02e-5` vs `2.14e-5`) under the identical resampling seed — i.e. the
  *point* estimate looked unremarkable, but *how much that estimate would
  move under resampling* was measurably larger. This is the real,
  reportable signature of a heavy tail: **less stable repeat estimates
  under resampling, even when a single point estimate looks ordinary** —
  consistent with why this codebase already prefers MAD over SD elsewhere
  (`features/robust_baseline.py`, D7's `session_z`/`persistent_z`).
- **CV% behaved exactly as its formula dictates and was highly unstable**
  in both the heavy-tailed and Gaussian cases (hundreds to tens of
  thousands of percent) — because CV is a ratio against a near-zero true
  mean here (V_pd, and this synthetic stand-in, are both zero-centered
  dispersion measures). This is not a bug in `compute_within_unit_cv()` —
  confirmed to match its own formula exactly in both cases
  (`tests/test_reliability.py`'s generator-based check) — it is a real
  property of applying a percentage-of-mean measure to a signal whose true
  mean is near zero. **Reported here, not smoothed over or silently
  special-cased.**

No parameter of any measure was adjusted in response to this exploration
(G2). The behavior is reported as observed.

## What this document is not

This is not a reliability report. It contains no result that bears on
whether any signal in this study is reliable, unreliable, precise, or
imprecise. That question requires the three-session, fixed-protocol,
matched-unit data described above, which does not yet exist.
