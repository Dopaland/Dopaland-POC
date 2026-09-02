# D7 — Three Baseline Representations

**File:** [`analysis/baselines.py`](../analysis/baselines.py) ·
**Tests:** [`tests/test_baselines.py`](../tests/test_baselines.py) (10 checks, all pass)

## What this computes

Three representations of the same recordings, per CLAUDE.md's D7 requirement:

- **`raw`** — the value as given, no standardisation. Passthrough.
- **`session_z`** — `z = (x_t − median_s) / (1.4826 × MAD_s)`, computed
  **within** the sample's own session only. Reuses
  [`features/robust_baseline.py`](../features/robust_baseline.py)'s
  `mad_stats()`/`mad_z_score()` directly — the MAD math is not
  reimplemented anywhere in this file.
- **`persistent_z`** — `z = (x_t − B_person,t) / S_person,t`, where
  `B_person,t` and `S_person,t` are computed **exclusively** from sessions
  strictly before session `t`.

## The temporal rule (1.1–1.3)

`B_person,t` and `S_person,t` are both estimated from the same expanding
(default) window of strictly-prior sessions — `_select_prior_pool()` slices
`sessions_in_order[:t_idx]`, never `[:t_idx+1]`. This is the **one place**
the invariant is enforced, and it applies identically to the baseline and
the scale — the scale is not treated as a special case that could leak
while the baseline stays clean.

**Selectable, config-hashed parameters** (`simulation/config.py`'s
`PreRegisteredConfig`):

| Field | Values | Default |
|---|---|---|
| `baseline_estimator` | `historical_sd` (mean/std) · `robust_mad` (median/1.4826×MAD) | `robust_mad` |
| `baseline_window_rule` | `expanding` (all strictly-prior sessions, "pooled within-person") · `rolling` (last N strictly-prior sessions) · `preceding_session_only` (exactly the one most recent prior session) | `expanding` |
| `baseline_rolling_window_sessions` | integer ≥ 1 (only consulted when `window_rule == "rolling"`) | `3` |

Stated explicitly, per the task's instruction: **`robust_mad` + `expanding`
is a default, not the only option.** Any of the six estimator×window-rule
combinations runs correctly (`tests/test_baselines.py` check 6 confirms
invalid values are rejected, not silently coerced).

### The leakage test — the evidence, not just the invariant

`tests/test_baselines.py` check 1 (`check_leakage_test_bit_identical`)
builds three sessions, computes `persistent_z`'s baseline/scale for the
3rd session against the real dataset, then again against a dataset that is
**identical except the 3rd session's own raw values are replaced with
`99999.0` repeated** — a mutation that would visibly drag a median/MAD
computed from itself. Result:

```
center_original = 0.008013792940586562   center_mutated = 0.008013792940586562
scale_original  = 0.9256868475497263     scale_mutated  = 0.9256868475497263
```

**Bit-identical**, not approximately equal.

Check 2 proves this test is not vacuous: a locally-defined *deliberately
leaky* selector (`sessions_in_order[:t_idx+1]`, including the session's own
data) run through the exact same original-vs-mutated comparison produces:

```
leaky_center_original = 0.35703808890977085   leaky_center_mutated = 0.7426621859908957
leaky_scale_original  = 0.9914601934321821    leaky_scale_mutated  = 1.7882634646052455
```

Visibly different — confirming the test structure actually catches a real
leak, not just that the committed implementation happens to pass it.

## Session 1 (1.4)

The first session in `sessions_in_order` has no strictly-prior session by
construction. Every sample in it is emitted — **never dropped** — with
`value: None`, `missingness_flag: True`, `missingness_reason:
"no_prior_history"` (a new value added to the shared fixed vocabulary,
`schema/canonical_log_v1.json` bumped to v2 — see that file's own
changelog note). There is no fallback to a within-session estimate
anywhere in `compute_persistent_z()`. Verified directly (`tests/test_baselines.py`
check 3): all 20 of 20 rows present, all missing, all correctly reasoned.

## MAD == 0 (1.5)

Reuses the SAME `zero_dispersion` handling as everywhere else in this
codebase — a scale below `PRE_REGISTERED_CONFIG.zero_dispersion_epsilon`
(the single pre-registered threshold Gate 0 A2 centralized) is reported
missing with reason `zero_dispersion`, never divided into and never
smoothed with a silent epsilon. Verified with prior sessions holding an
identical value (`MAD == 0` exactly) — check 4.

## Session-pair count (1.6)

Every representation's output carries `n_session_pairs_total`:
`raw` and `session_z` are always `0` (neither ever looks outside its own
session, by construction — verified directly, not just claimed: check 8
confirms `session_z`'s output for a session is byte-identical whether or
not another session's data is even present in the input). `persistent_z`
carries the real total — the count of `(evaluated_session, prior_session)`
pairs actually pooled across the whole computation. For 5 sessions under
`expanding`: `0+1+2+3+4 = 10`; under `preceding_session_only`: `4` (every
session but the first contributes exactly one pair). A downstream reader
comparing all three side by side sees this difference on every record, not
as a footnote.

## What was reused vs. written new

- **Reused directly**: `features.robust_baseline.mad_stats`/`mad_z_score`
  (session_z, and persistent_z's `robust_mad` estimator) —
  `PRE_REGISTERED_CONFIG.zero_dispersion_epsilon` (the zero-dispersion
  threshold, same source as everywhere else) — `schema.canonical_log_writer.MISSINGNESS_REASONS`
  (the fixed vocabulary, extended by one value with a stated reason).
- **Written new**: the cross-session temporal windowing
  (`_select_prior_pool`), the `historical_sd` estimator (no prior home in
  this codebase), and `PreRegisteredConfig`'s three new baseline fields.
