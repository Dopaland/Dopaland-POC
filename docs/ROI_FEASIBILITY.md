# ROI Feasibility — Can We Do It, and How Much of It Now

**Investigation only. No production code was written, changed, or wired by this task.**
Measurement scripts used to produce the numbers below were run from a scratch path and
were not committed; every number quoted here is either independently re-derived in this
session from data already committed to this repository, or cited directly from
`PITCH_DIAGNOSTIC.md` (already committed, itself a real measurement against archived
footage). Nothing here proposes, applies, or hints at a pass/fail threshold (G1) — every
number is reported for a human to read and act on.

---

## VERDICT (Task 2.4) — read this first

**Horizontal (yaw) region attribution is defensible. Vertical (pitch) region
attribution is not, at any granularity tested — including the coarsest possible
version (a plain top/bottom split).** The required angular separation for every layout
that has a vertical component exceeds what this pipeline's pitch channel can produce
even under maximal, deliberate, directed effort — this is not a noise problem that
more data would average out; the signal does not reach the required magnitude in the
first place. Yaw, by contrast, clears its required separations by roughly 16–24× its
own resting noise floor, confirmed against two independent sets of real archived data.

**The largest honest claim available: a coarse (2- or plausibly 3-way) left/right
region attribution, plus the existing binary "oriented toward the screen" scalar and
its lateral direction.** Both are supported by real data collected in this repository.
Neither is currently validated to the client's own D8 statistical standard — that
validation is a separate, not-yet-run step (see Task 1.2) — but the *underlying
signal*, unlike pitch, is physically capable of carrying the discrimination this
claim requires. One caveat attaches to even this claim: the existing "oriented"
scalar blends yaw and pitch (`max(yaw_frac, pitch_frac)`), so a person looking down —
the single most common real disengagement behaviour — will misleadingly score as
"oriented," inheriting pitch's blind spot into the surviving claim. This is not a new
finding; CLAUDE.md's own "Attention / screen-orientation" section already says so. It
is repeated here because it directly bounds how much weight even the *surviving* claim
can honestly carry.

---

## 1. Inventory (Task 1)

### 1.1 Screen regions, bounding boxes, clicks, keypresses, on-screen actions, task events

**Nothing in this repository defines, stores, or consumes any of these with real
content.** Searched exhaustively (`roi`, `ROI`, `bounding.?box`, `screen_region`,
`click`, `keypress`, `on_screen`, `task_event`, `region_id`, case-insensitive, whole
repository). Every hit falls into one of two categories:

- **Documentation describing the absence** — `docs/D1_DEPENDENCY_MAP.md`,
  `features/context.py`, `features/manifests/context_v1.json`, `features/__init__.py`,
  and CLAUDE.md itself, all stating plainly that ROI/context code does not exist.
- **The canonical schema's declared-but-unpopulated field shapes** —
  `schema/canonical_log_v1.json` / `schema/canonical_log_writer.py` define
  `stimulus_id`, `stimulus_onset`, `roi_or_condition`, `prediction_timestamp`,
  `action_timestamp`, `action_class` as real fields on `canonical_observation`
  records, every one of them typed `["string","null"]` or `["number","null"]` and
  defaulting to `None` in `write_observation()`'s signature. **No code anywhere in
  this repository ever supplies a non-null value for any of these fields.** This is
  the schema's own documented intent — see `schema/canonical_log_v1.json`'s
  `$comment`: *"these fields exist because the client's task harness... will
  eventually populate them — this schema defines the SHAPE those fields must have; it
  does not define the action-class vocabulary itself."*

One false-positive worth naming so it isn't mistaken for a hit: `stage3_demo_ui.py`
has keypress/mouse-click handling, but it is Tkinter window-close chrome (closing the
demo dashboard), unrelated to any task/ROI semantics — confirmed by reading the
surrounding code, not assumed from the grep match.

**Conclusion: Obstacle A (no event source) is total, not partial.** There is no
partially-built ROI ingestion path to extend — the schema has a shape waiting to be
filled, and nothing else.

### 1.2 Full inventory of existing attention-class code

All of it lives in `features/attention.py` (the A_t block), imported by three
consumers (`stage1_step4_vectors.py`, `stage3_demo_ui.py`, `orientation_capture.py`)
that call it identically but log/display it differently (see §4's caveat on this).

| Item | What it computes | Output | Record type / file | Validated? |
|---|---|---|---|---|
| `compute_v_so` | Screen-orientation score: `0.7×pose_score + 0.3×gaze_score` (or pose-only if gaze implausible); pose_score from `max(yaw_frac, pitch_frac)` against a 20° threshold on each axis | `orientation_score` (float 0–1), `components` dict incl. `oriented` (bool), `head_pose_only` (bool) | `record["screen_orientation"]` in `sample` records; aggregated into `attention_window_summary` via `AttentionWindowAccumulator.flush()` | **No.** Stamped `"unvalidated": true` on every record. Yaw component behaves correctly on real data (§2.2); pitch component does not (§2.2, §2.4). |
| `_gaze_centering_score` | Secondary/bonus input to `compute_v_so` — how centred the iris sits between eye corners, averaged across both eyes | `(score, reliable)` tuple, never surfaced independently | Consumed internally by `compute_v_so` only | Unvalidated (same status as V_so overall) |
| `compute_gaze_direction` | Coarse **LEFT / RIGHT / CENTER / UNKNOWN** label from the signed difference between the two eyes' iris-centring ratios | `(label, reliable, raw_shift)` | `record["gaze_direction"]` in `sample` records (stage3/orientation_capture consumers only); `logs/experimental_signals_log.jsonl` | **No.** Explicitly experimental, `"unvalidated": true`. Never up/down by design — same pitch-unreliable reasoning as V_so, deliberately never attempted. |
| `BlinkDetector` | Blinks/minute via a relative-threshold state machine over V_es's own aperture value | rate_per_min, diagnostic fields | `logs/experimental_signals_log.jsonl` | **Partially** — the positive blink control (`controls/blink_positive.py`) validates detection against synthetic ground truth; no real clip exists (see `docs/MATRIX_ROW_MAP.md` row 15). Not ROI-relevant on its own but is attention-class and lives in the same module. |
| `AttentionWindowAccumulator` | Windows `compute_v_so`'s per-sample output into 10s avg/peak/variance + `oriented_rate`, `gaze_reliable_rate`, `look_away_rate` — its own independent clock, never touching `WindowAccumulator`/`NeutralCalibrator` | `attention_window_summary` record | Own record type, own file position within `logs/session_*.jsonl` | Unvalidated (inherits V_so's status) |
| `orientation_capture.py` | A dedicated **directed-capture study tool** — 6 fixed segments (`look_at_screen`, `look_left`, `look_right`, `look_down`, `look_up`, `look_away_and_back`), each ~10s, using the real `AttentionWindowAccumulator` unmodified, plus (schema 1.1) per-segment raw yaw/pitch/roll avg/min/max/variance | `orientation_trial` record | `logs/orientation_trials.jsonl` | This *is* the validation study tool — dumb capture, no scoring in-tool, same discipline as Gate 2's capture tool. It has produced 18 real records (3 sessions × 6 segments) to date, all under schema 1.0 (pre-dating the raw-pitch field — see §2.2). |

No dwell, persistence, switching, or head-gaze-coherence code exists anywhere — those
are the exact ROI-dependent derivatives that cannot exist without Obstacle A. Nothing
was found under any name.

### 1.3 Where A_t lives and what the separation test does for it

`features/attention.py` is a single, flat block-module file — one of the five named
blocks the D1 architecture defines
(`geometry`/`x_core`/`episodes`/`attention`/`audio`/`context`). ROI, dwell,
persistence, switching, and head-gaze coherence are all named explicitly, by CLAUDE.md
itself, as belonging inside this one file (*"attention.py A_t -- attention (ROI,
orientation, dwell, persistence, switching, head-gaze coherence, and ANY downstream
attention derivative)"*).

**The machinery to hold this work is already in place; nothing new needs
scaffolding.** Concretely, from reading `tests/test_feature_separation.py` directly:

- `BLOCK_MODULES` already includes `"attention"` — any new function added inside
  `features/attention.py` is automatically part of the module the static import
  graph (check 1), static call graph (check 2), and runtime monkeypatch (check 3)
  all already parse and poison.
- `FORBIDDEN_EDGES` already includes `("x_core","attention")` and
  `("episodes","attention")` — a new ROI/dwell function added inside `attention.py`
  is automatically covered by the exact same forbidden-edge check that already
  protects V_so, gaze, and blink. No new edge needs adding for attention-internal
  growth.
- Check 4 (`check_shim_isolation`) discovers cross-block shims *by definition* (any
  repo-root module whose AST imports `features.attention`) — a new ROI consumer
  written as, say, a new root-level analysis script would be caught by this exact
  mechanism the moment it imported `features.attention`, with zero changes needed.

**What is *not* already covered, and would need new scaffolding, is anything that
lands in `features/context.py` instead of `features/attention.py`** — see Task 4
below; this is the one genuine gap, and it is a pre-existing, already-documented one
(`features/context.py`'s own docstring names it), not something ROI work introduces.

### 1.4 The clock

Every `sample` record (`stage1_step4_vectors.py`) carries two timestamps:
`ts_utc` (`datetime.now(timezone.utc).isoformat()`, wall-clock, ISO-8601) and
`ts_monotonic` (`cycle_start`, sourced from `time.perf_counter()`) — captured at the
same instant, every processing cycle. `window_summary`/`attention_window_summary`
records carry `window_start_monotonic`/`window_end_monotonic`, also `perf_counter()`-
sourced, no wall-clock companion at the window level (only at sample level).
Resolution: `time.perf_counter()`'s resolution is sub-millisecond on Windows; the
practical resolution of the signal itself is the ~30–33ms inter-frame interval
(`docs/LOG_EVIDENCE.md`: measured mean inter-sample interval 33.5ms, ~29.8Hz), not the
clock's own precision.

**The canonical schema already contains the exact mechanism needed to align this
pipeline's monotonic clock with an externally-arriving event log's own clock** —
`schema/canonical_log_writer.py`'s `CanonicalLogWriter.open_session()`. It captures
`wall_clock_utc` (`datetime.now`) and `monotonic_reference` (`time.perf_counter()`) at
the same instant, once per session, specifically so *"every later monotonic timestamp
in the session is interpretable as real time"* (the schema doc's own words). This is
the **exact integration point**: a harness delivering its own event log, each event
carrying its own wall-clock time, can be reconciled with this pipeline's
`ts_monotonic`/`window_start_monotonic` values by converting both sides through their
own wall-clock anchor into a shared wall-clock frame, then re-expressing the offset in
whichever clock the join needs. `action_timestamp`/`stimulus_onset` are the fields
already declared, on `canonical_observation`, to hold exactly this — monotonic,
cross-checked for per-field monotonicity within a session — waiting for a value.

**This mechanism has never been exercised with two independent clock domains.**
Gate 0's `RunProvenance`/`capture_run_provenance` and the canonical schema both exist
and are tested in isolation (`docs/MATRIX_ROW_MAP.md` rows 27/28); neither has ever
been called against a second, genuinely separate process's clock. The design is
sound and already built; the empirical question ("how much do two independent
Windows-process monotonic clocks actually drift over a session") is untested and
cannot be tested until a second real clock (the harness's) exists.

---

## 2. The resolution measurement (Task 2)

### 2.1 Required angular separation, computed

**Assumptions, stated explicitly:**
- Screen: 14-inch diagonal, 16:9 laptop panel → **30.0cm × 17.0cm** (exact 16:9 math
  on a 14in diagonal gives 30.5cm × 17.2cm; rounded for a clean number, immaterial to
  the conclusion at this precision).
- Viewing distance: **55cm**, a standard mid-point of common laptop-ergonomics
  guidance (~50–70cm).
- Eye assumed level with screen centre for the horizontal (yaw) calculation, and the
  vertical (pitch) calculation is the *differential* between region centres only — it
  does not depend on where the whole screen sits relative to eye height, only on how
  far apart two region centres are, angularly, from each other.
- Angles computed as `atan(offset_cm / distance_cm)`, i.e. the true angle subtended at
  the eye, not a small-angle linear approximation (though at these distances the two
  agree to within a few hundredths of a degree).

**Arithmetic, and the result** (script run this session, not committed; the inputs
above fully reproduce it):

| Layout | Cell size | Adjacent horizontal (yaw) separation | Adjacent vertical (pitch) separation | Axis stressed |
|---|---|---|---|---|
| Halves (1×2, left/right) | 15.0 × 17.0cm | **15.53°** | 0° (single row) | Yaw only |
| Quadrants (2×2) | 15.0 × 8.5cm | **15.53°** | **8.84°** | Both |
| 3×3 grid | 10.0 × 5.7cm | **10.30°** (both adjacent pairs) | **5.88°** (both adjacent pairs) | Both |

A plain top/bottom halves split (not in the client's named layouts, but worth
computing since it isolates the pitch axis at its coarsest possible granularity) would
require the same **8.84°** as the quadrant layout's vertical component, since both
split the same 17cm height into two equal rows.

### 2.2 What this system actually delivers, measured

**No suitable archived webcam footage exists on this machine right now for a fresh,
independent frame-by-frame re-measurement — checked directly, not assumed.** Three
candidate video files were found locally (`C:\Users\Abcom\Downloads\*.mp4`, dated
mid-July 2026) and systematically sampled (10 evenly-spaced frames each, run through
the real, unmodified `FaceLandmarker`): **0/10, 0/10, and 1/9 sampled frames had a
detected face.** Their resolution (1896×950, ~25fps, 5–66 minutes long) and near-total
absence of any detectable face confirm these are screen recordings (a `ScreenRec`
installer is present on this machine), not webcam footage of a person — unrelated to
this question. The two clips `PITCH_DIAGNOSTIC.md` previously analysed frame-by-frame
(`test_clip.mp4`, `directed_clip.mp4`) no longer exist anywhere on this machine or in
this repository (confirmed: zero `.mp4`/`.mov`/`.avi` files anywhere under
`C:\Dopaland-POC`, consistent with G4 — raw media is never committed). **Per this
task's own instruction, this sub-task stops there rather than recording a number
against unsuitable footage.** What would be needed to re-run it fresh: 1–2 minutes of
real webcam footage of a seated subject performing a directed "look at screen / look
down / look up" sequence — exactly what `orientation_capture.py` is built to produce,
and exactly the physical-run item already listed as outstanding in
`docs/PROJECT_STATE.md`.

**What *is* available, and was used instead, is real archived measurement data
already committed to this repository** — not raw video, but the actual numeric output
of processing real footage, which is what the noise-floor/range questions need
either way:

**Yaw noise floor** (head held still, `look_at_screen` segments, 3 real capture
sessions, `logs/orientation_trials.jsonl`, re-extracted this session):

| Session | `yaw_variance_deg2` | std (deg) |
|---|---|---|
| ddbc2c0f | 0.5408 | 0.735 |
| 1fd37ee4 | 0.1503 | 0.388 |
| ad539d4a | 0.6622 | 0.814 |

Pooled (mean variance 0.4511 deg²): **std ≈ 0.65°.** This is a real number from real,
held-still footage — three independent sessions, consistent range 0.39–0.81°.

**Yaw usable range**: `PITCH_DIAGNOSTIC.md`'s own frame-by-frame scan of
`test_clip.mp4` (real footage, 816 detected frames) found `|yaw|` ranging **16.1°–
78.4°** (mean 36.3°) during natural head movement — real, large, easily-detected
excursions. Corroborating this from `orientation_trials.jsonl`: `look_left`/
`look_right` segments (3 sessions) show `oriented_rate` collapsing to **0.11–0.69**
(from 1.00 at rest) — the same tool, on the same real subjects, robustly registers
real yaw excursions as a behavioural change, not just as a quiet noise increase.

**The pitch finding — reproduced, from two independent real-data sources:**

1. **`PITCH_DIAGNOSTIC.md`'s frame-by-frame video scan** (real footage,
   `directed_clip.mp4`, already committed, not re-run by this session but its
   numbers are the actual measured output of real data): during the clip's directed
   "look down" phase, pitch stayed **0–5°, never exceeding ~4.4°**, across the whole
   ~10s window — while the *same pitch channel*, in the *same clip*, registered
   **15–18°** incidentally elsewhere (a settling motion, not a commanded look-down).
2. **This session's fresh extraction of `orientation_trials.jsonl`** (3 real
   sessions, never previously tabulated this way): `look_down`'s `oriented_rate` is
   **1.00, 1.00, 1.00** — indistinguishable from `look_at_screen`'s own 0.789–0.934
   average orientation score. `look_up`: **0.93, 0.86, 1.00** — same pattern, slightly
   less extreme. Every one of 6 real directed vertical-look attempts, across 3
   different real sessions, reads as "still oriented at the screen." Zero exceptions.

**Both sources agree, independently: the pitch finding reproduces.** A real,
deliberate, sustained "look down" command produces a system readout that is not
reliably distinguishable from sitting still and looking at the screen.

### 2.3 Required separation vs. measured signal, as a ratio

`ratio = required separation ÷ measured value`. For yaw, the denominator is the real
resting noise floor (§2.2) — a large ratio is favourable (the required gap dwarfs the
noise). **For pitch, no archived resting-noise-floor figure exists** (the schema that
would log it, `raw_head_pose_deg`, was added to `orientation_capture.py` after the 18
existing real records were captured — every one of them predates it). The denominator
used for pitch instead is the **best-case achieved deflection under active, deliberate
effort** (~4.4°, §2.2) — an upper bound on what the channel can contribute at all. A
ratio **above** 1 here is *unfavourable*: it means the required separation exceeds
even the most generous real signal available, which likely understates the true
noise-floor ratio (resting variation is presumably smaller than actively-attempted
deflection, so the real noise-floor ratio would be worse, not better).

| Layout | Axis | Required | Measured | Ratio | Reads as |
|---|---|---|---|---|---|
| Halves | Yaw | 15.53° | 0.65° (noise floor) | **≈24×** | Comfortably resolvable |
| Quadrants | Yaw | 15.53° | 0.65° (noise floor) | **≈24×** | Comfortably resolvable |
| Quadrants | Pitch | 8.84° | ≤4.4° (best-case deflection) | **≈2.0×** *(required exceeds achievable)* | Not resolvable — required separation is double what pitch can produce at best |
| 3×3 grid | Yaw | 10.30° | 0.65° (noise floor) | **≈16×** | Comfortably resolvable |
| 3×3 grid | Pitch | 5.88° | ≤4.4° (best-case deflection) | **≈1.3×** *(required exceeds achievable)* | Not resolvable — required separation exceeds achievable even at the finest grid's smallest gap |
| Top/bottom halves | Pitch | 8.84° | ≤4.4° (best-case deflection) | **≈2.0×** | Not resolvable — fails even at the coarsest possible vertical split |

Yaw and pitch give opposite answers, as expected. Pitch does not merely fail the
*hardest* layout — it fails the *easiest possible* vertical layout too, because the
achievable deflection (≤4.4°) never reaches even half of what a single top/bottom
split requires (8.84°).

### 2.4 The verdict, and the largest honest claim

See the top of this document for the full verdict. In summary form against each named
layout:

- **Halves (left/right)** — resolvable. Yaw only; comfortably clears its bar.
- **Quadrants (2×2)** — not resolvable as a 4-way attribution. The horizontal half of
  the discrimination is fine; the vertical half fails outright.
- **3×3 grid** — not resolvable as a 9-way attribution, for the same reason: its
  vertical component fails even more severely relative to its own (smaller) required
  gap than the quadrant layout's does.
- **A bare top/bottom split** — not resolvable, at any granularity. This is the
  coarsest possible vertical layout and it still fails by a factor of 2.

**What survives:** a coarse horizontal attribution (defensibly 2-way; plausibly 3-way
— `orientation_trials.jsonl`'s three real, qualitatively distinct readings for
`look_at_screen`/`look_left`/`look_right` are suggestive of a usable 3-way split,
though this has not been directly tested at 3-way resolution, only observed as three
separately-commanded 2-way comparisons). The existing binary "oriented toward screen"
scalar (V_so) and its lateral gaze-direction label are both already built and both
supported by real yaw-driven data. **Neither is validated to the client's own D8
statistical standard** (primary statistic, null distribution, minimum effect, N —
all proposed in the sign-off response's §4.14, none run — see
`docs/MATRIX_ROW_MAP.md` row 14); this document establishes physical *capability*, not
statistical *validation*. Head-gaze coherence as a scalar (rather than per-ROI) is
plausible on the same yaw-driven grounds, but no code computes it today (§1.2) — it
would need to be built, and Task 3 covers what of that is buildable now.

**The caveat that bounds even the surviving claim:** `compute_v_so`'s `oriented`
boolean is `max(yaw_frac, pitch_frac) < threshold` — a single scalar blending both
axes. Because pitch essentially never registers, **a person looking down will read as
"oriented"** regardless of how far down they are actually looking, for exactly the
reason established above. This is not a new finding — CLAUDE.md's own
"Attention / screen-orientation" section already states it — but it directly caps how
much the surviving claim can be trusted for its single most likely real use (detecting
disengagement, whose most common form is looking down at a phone or lap).

---

## 3. What could be built now (Task 3)

Assuming Obstacle A resolves later and Task 2's verdict constrains what is honest to
compute, against a pluggable synthetic event source — the same pattern
`controls/leakage.py`'s `synthetic_trial_source()` already establishes in this
codebase.

| Item | What it is | Depends on | How it would be tested now |
|---|---|---|---|
| **Event-log reader / adapter interface** | A function `real_event_source() -> list[trial-like-record]` matching the exact shape `controls/leakage.py`'s `trial_source` contract already expects, plus a mapping into the canonical schema's already-declared `stimulus_id`/`roi_or_condition`/`action_timestamp`/`action_class` fields | The canonical schema (already built) for the *target* shape; nothing for the *source* shape, since that is the harness's own format, unknown until delivered | A hand-built synthetic fixture file standing in for "whatever the harness delivers," exercised through the adapter, asserting the output validates against `schema/canonical_log_v1.json` |
| **Timestamp join between an external stream and our own records** | A pure function taking two wall-clock-anchored monotonic streams (ours + the harness's) and returning aligned pairs, using each side's own `CanonicalLogWriter.open_session()`-style wall-clock/monotonic anchor pair | Nothing external — `time.perf_counter()`/`datetime.now(timezone.utc)` semantics are already fully understood and testable | Two synthetic streams with a known, deliberately-injected clock offset and drift rate; assert the join recovers the known offset within a stated tolerance |
| **ROI dwell / switching / persistence, computed from *supplied* region assignments** | Given a stream of `(timestamp, roi_id)` tuples — real or synthetic, source-agnostic — compute per-ROI dwell time, switch count, and time-since-last-switch. This is pure aggregation, structurally identical to `episodes.WindowAccumulator`/`attention.AttentionWindowAccumulator`'s existing windowing pattern | Nothing about *our own* gaze-to-ROI attribution accuracy — it aggregates whatever `roi_id` stream it is given, synthetic or real | A synthetic `roi_id` stream with known, hand-constructed dwell/switch patterns; assert the aggregator recovers the known statistics exactly, the same style `tests/test_baselines.py`'s mutation-test pattern already uses |
| **D8's statistic** (oriented-rate difference, salient vs. non-salient episodes) | Pure aggregation math over `(episode_label, oriented_rate)` pairs — the difference statistic, the block-permutation null, the percentile-bootstrap interval, per §4.14 of the response | `simulation/precision.py`'s existing episode-level bootstrap machinery (directly reusable, not reimplemented) | Synthetic episode labels + synthetic oriented-rate values with a known injected effect, mirroring `tests/test_leakage.py`'s injected-severe-leak proof pattern |
| **A_t block placement for any of the above** | Literally: add the functions to `features/attention.py`. No new module, no new scaffolding — see Task 1.3 | Nothing beyond what already exists | The separation test already covers it automatically the moment the code lands inside `attention.py` (Task 1.3) — no new test infrastructure needed for *this* part |
| **A synthetic ROI-attribution-noise generator** | Extend `simulation/generator.py`'s existing A1–A6 generative model with an "A7"-style mechanism: a true `roi_id` per trial, observed through a configurable attribution-noise parameter (directly analogous to A6's `effect_size` for the candidate signal) | `simulation/generator.py`'s existing structure — this is additive, same shape as every prior extension to that generator | The generator's own existing test pattern (`tests/test_generator.py`) — verify the true-null case (attribution noise = 1) produces chance-level accuracy, and effect_size=0-equivalent produces perfect recovery |
| **ROI-dependent controls, on the synthetic source** | `controls/leakage.py` already accepts any `trial_source`; a synthetic ROI-labelled source (built above) can be plugged in with zero changes to the harness itself | The leakage harness (already built) + the synthetic generator extension above | Already covered by `tests/test_leakage.py`'s existing pluggable-source proof (`check_data_source_is_genuinely_pluggable`) — this would be a second instance of a pattern already demonstrated, not a new capability |

**Constrained by Task 2's verdict, stated plainly:** the dwell/switching/persistence
aggregation math above is honest to build and test against *any* supplied `roi_id`
stream. It would **not** be honest to wire it to this system's own attempted
gaze-to-ROI attribution beyond a coarse left/right (or plausibly 3-way) label — doing
so for a quadrant- or grid-level attribution would silently launder Obstacle B's
physics problem into what reads as a built, tested feature. The aggregation layer and
the attribution layer are separable, and should stay built separably.

### Genuinely cannot be built until real events exist

- **The real harness-format adapter** — its wire format is unknown; nothing to build
  against.
- **Real gaze-to-ROI attribution accuracy, at any resolution** — needs real recorded
  sessions with simultaneous ground-truth ROI and gaze; this is exactly Obstacle A +
  Obstacle B's physical-run dependency, not a code gap.
- **D8's actual minimum-effect size and required trial count** — per the response's
  own §4.14, these are to be *derived from the D6 simulation*, not asserted; deriving
  them needs the harness's real session-length/class-balance numbers (Decision C in
  the response), which do not exist yet.
- **Real clock-drift measurement between two independent processes** — cannot be
  measured without a second real running system; the join *mechanism* (above) is
  buildable, its real-world accuracy is not testable until then.
- **The leakage/time-shuffle controls' real-data run** — already listed as
  outstanding in `docs/PROJECT_STATE.md`; ROI data does not change this, it only adds
  a new *kind* of trial these same controls could eventually run against.

---

## 4. The separation risk (Task 4)

### 4.1 Every plausible entry route for ROI/gaze-derived information into C_t or E_t

**(a) Direct import.** `features/context.py` (C_t) is currently empty, but nothing
prevents a future implementation from `import`ing `features.attention` directly — the
exact "legal-looking back door" `features/context.py`'s own docstring and
`docs/D1_DEPENDENCY_MAP.md` already name, because `C_t -> E_t` is a *permitted*
direction.

**(b) Shared field name.** If `episodes.WindowAccumulator` (or any future E_t
component) were ever generalised from its current hardcoded composite/covariate key
lists to accept a caller-supplied dict of "extra features," a context-supplied field
that happens to share a name with an attention-block output (`gaze_score`,
`orientation_score`, etc.) could enter E_t without any import at all — purely by
sitting under a familiar-looking key in a dict built elsewhere.

**(c) A record read from a shared log.** Sample records already interleave
attention-block fields (`screen_orientation`, `gaze_direction`, `look_away`) alongside
X_core fields (`vectors`, `vectors_deviation`) in the *same* JSON object, in the *same*
`logs/session_*.jsonl` file (confirmed directly, `docs/LOG_EVIDENCE.md`'s field list).
A future C_t/E_t component that reads "the sample record" generically from this file
— rather than specifically the X_core-relevant sub-fields — could pick up
attention-block content purely because it lives in the same on-disk object, with no
Python-level import anywhere in the chain.

**(d) A join key.** `session_id` and a timestamp are the natural keys for joining any
two record types from the same session. A future E_t-building step that joins "context
for this window" by `session_id` + nearest/overlapping timestamp could inadvertently
match an `attention_window_summary` record — which shares both keys with every other
record type in the same session — under a generic "whatever's relevant to this window"
join, without ever importing `features.attention`.

### 4.2 Would the existing separation test catch each route?

| Route | Caught today? | Why / why not |
|---|---|---|
| (a) Direct import | **Not caught today.** `BLOCK_MODULES` already includes `"context"` (its imports are parsed), but `FORBIDDEN_EDGES` has no entry naming `context` as a source — only `x_core` and `episodes` are checked as sources. Even if `context.py` imported `attention.py` directly today, no forbidden-edge check would fire, because the only way the current check could catch it is transitively *through* `episodes.py` — and `episodes.py` does not import `context.py` (nothing does; C_t → E_t is a design relationship, not yet a real import anywhere). | **What would be needed** (described, not written): extend `FORBIDDEN_EDGES` with `("context","attention")` and `("context","audio")` as direct entries. `check_static_import_graph` already builds a graph node for `context` and already supports arbitrary `(src, forbidden)` pairs — this needs no new function, only two new tuples, so the fix is trivial once someone decides to make it. It is *not yet made* — stated as a real, currently-open gap, not a defect that was somehow already closed. |
| (b) Shared field name | **Not caught by anything.** No existing check inspects JSON/dict *key names* in logged output at all — checks 1–4 all operate on Python import/call graphs, never on the shape of a dict a function returns. | **What would be needed**: a test asserting `WindowAccumulator.flush()`'s (and any future E_t component's) output keys are drawn from an explicit, fixed, enumerated set — never dynamically extended from a caller-supplied dict — i.e., a guard on the *discipline* (hardcoded key lists) that already exists today, turned into an explicit, checked invariant rather than an implicit property of the current code. |
| (c) Record read from a shared log | **Not caught by anything.** This is a runtime, file-format data-flow risk, invisible to any static Python-level analysis — none of the four checks read a `.jsonl` file or reason about record types at all. | **What would be needed**: extend the check-3 philosophy (poison a module, prove real code never touches it) from in-process poisoning to log-schema poisoning — a fixture log file containing *only* attention-block record types (`attention_window_summary`, samples with only attention fields populated) fed to whatever future C_t/E_t log-reading code exists, asserting it returns nothing usable (raises, or returns an empty/filtered result) rather than silently accepting attention-typed content. |
| (d) Join key | **Not caught by anything**, for the same reason as (c) — a data-flow risk outside any existing check's scope. | **What would be needed**: once real join logic exists, a test that constructs a log containing *only* `attention_window_summary` records for a given `session_id`/time range and asserts a "join context for this window" function returns empty rather than silently substituting the attention record under a generic key. |

**Summary**: routes (b), (c), and (d) share a common shape — every one of them is a
*data-flow* risk (through a dict, a file, or a join), not an *import-graph* risk, and
none of the four existing checks look at data flow at all; all four were built,
correctly, to answer "did forbidden code get imported or called," not "did a
forbidden-shaped value arrive some other way." Route (a) is closer to being caught —
the graph-based machinery already exists and already handles `context` as a node —
but the specific forbidden-edge entries that would make it fire have not been added,
because `context.py` has never had content to trigger the need. **None of this is
urgent while `features/context.py` stays empty** (confirmed, again, this session: zero
functions, classes, or constants in the file). It becomes urgent the day someone
starts filling C_t in — which is exactly what `features/context.py`'s own docstring
already says, and this task's own findings do not change that timing, only sharpen
what the guard would need to check when the day comes.
