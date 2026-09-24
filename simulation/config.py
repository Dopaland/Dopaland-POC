"""
D0PA1 pre-registered configuration (D6 Addendum 3; generalised, Gate 0 A2).

Originally the minimal versioned home for exactly one pre-registered
parameter (log_loss_clip_eps). Gate 0's A2 step generalises this into the
real provenance layer CLAUDE.md's "WHAT D0PA1 ADDS" section describes --
but generalising the CONTAINER does not mean every hardcoded constant in
the repository belongs inside it. Every field added here still has to meet
the same bar the original docstring set: a quantity whose VALUE materially
changes what a downstream metric or record reports, fixed in advance rather
than tunable after seeing a result (G2). See docs/GATE0_PROVENANCE.md
section A2 for the full audit of which hardcoded constants were moved here
and which were deliberately left in place (most of them -- anything
load-bearing inside the validated path, G5, stays exactly where it is;
moving a constant's *definition* is itself a change to a G5-protected file,
independent of whether its numeric value stays the same).

Companion to simulation/provenance.py's RunProvenance: THIS file answers
"which pre-registered parameter values are in force" (fixed once, reused
across many runs); RunProvenance answers "which code, exactly, produced
this run's data" (captured fresh every run). Different lifetimes, kept in
separate objects on purpose -- see provenance.py's own module docstring.
"""

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PreRegisteredConfig:
    """Every field here is a quantity whose VALUE changes what a
    downstream metric reports, and must therefore be fixed before data
    collection, not tuned afterward (G2). Add a field here ONLY when a
    parameter meets that bar -- this is not a place to collect ordinary
    engineering constants (L2 grid, split fractions, etc. stay where they
    are; they affect model SELECTION machinery, not the reported primary
    metric's value on a fixed model, and are not what this task's
    guardrail is about)."""

    # scikit-learn's historical default. Demonstrated sensitivity: a
    # single trial with an exact-zero true-class probability swings U by
    # more than 2x between eps=1e-6 and eps=1e-15 (Addendum 2). See
    # docs/D6_SIMULATION.md section 12 for the full justification and the
    # measurement on REAL fitted output (not just this pathological case).
    log_loss_clip_eps: float = 1e-15

    # Numerical-safety floor below which a dispersion estimate (std or
    # 1.4826*MAD) is treated as zero_dispersion rather than divided into --
    # CLAUDE.md D0PA1 hard constraint #5: "MAD == 0 must be handled
    # explicitly -- emit missing with reason zero_dispersion. Do not divide
    # by zero, do not add a silent epsilon." This IS that floor, made a
    # single hashed, pre-registered value instead of a bare literal, so the
    # zero_dispersion classification any signal's missingness_reason relies
    # on is auditable rather than buried in whichever module happens to
    # compute it. Was previously a local module constant in
    # controls/null_input.py (same value, 1e-9) -- moved here, not
    # duplicated (see docs/GATE0_PROVENANCE.md A2).
    zero_dispersion_epsilon: float = 1e-9

    # Camera device index. Pure I/O device selection -- affects WHICH
    # physical sensor produced a run's data (provenance-relevant), never
    # what a formula computes from whatever that sensor returns. Was
    # previously a local module constant in stage1_step4_vectors.py (same
    # value, 0) -- moved here, not duplicated.
    camera_index: int = 0

    # How often the capture/processing threads print a console FPS report.
    # Purely a reporting cadence -- never read by any formula, calibration,
    # or windowing code -- moved here for the same single-source-of-truth
    # reason as camera_index, not because it meets the "changes a reported
    # metric's value" bar on its own.
    fps_report_interval_seconds: float = 3.0

    # D7 (analysis/baselines.py): which ESTIMATOR persistent_z's cross-
    # session baseline/scale use -- "historical_sd" (mean/std) or
    # "robust_mad" (median/1.4826*MAD, reusing features/robust_baseline.py's
    # mad_stats()). Directly changes persistent_z's VALUE for every sample
    # in the study -- exactly the kind of decision this config exists to
    # pin in advance (G2). See analysis/baselines.py's BASELINE_ESTIMATORS
    # for the full validated set; this field is NOT validated here (see
    # that module's own docstring on why validation lives with the
    # consumer, not the config object). Default is robust_mad -- stated as
    # a default, not the only option (this task's explicit instruction).
    baseline_estimator: str = "robust_mad"

    # D7: which WINDOW of strictly-prior sessions persistent_z pools before
    # applying baseline_estimator -- "expanding" (all strictly-prior
    # sessions, aka "pooled within-person"), "rolling" (the last
    # baseline_rolling_window_sessions strictly-prior sessions), or
    # "preceding_session_only" (exactly the single most recent strictly-
    # prior session). Default is expanding -- again, a default, not the
    # only option. See analysis/baselines.py's BASELINE_WINDOW_RULES.
    baseline_window_rule: str = "expanding"

    # Only consulted when baseline_window_rule == "rolling" -- how many
    # strictly-prior sessions to pool. Kept as its own field (rather than
    # overloading a generic "window size" that would be meaningless for
    # "expanding"/"preceding_session_only") so its value is still hashed
    # and inspectable even when the active window_rule ignores it.
    baseline_rolling_window_sessions: int = 3

    # ACCEPTED by the client, `docs/preregistration/D0PA1_Client_SignOff_001.md`
    # §2 (2026-09-19) -- the four component decision thresholds and the
    # leakage diagnostic threshold, all in NATS (the study's primary metric
    # is negative multiclass log loss; converting a nats-derived threshold
    # to macro-F1 is explicitly forbidden by the sign-off response §4.7 --
    # see that sign-off record's own §1 for the conversion-error this
    # correction fixed in both the response document and
    # docs/MATRIX_ROW_MAP.md row 9).
    #
    # G1: these are read by NO decision logic anywhere in this repository.
    # `simulation.precision.compute_delta`/`bootstrap_ci_on_delta` and
    # `controls.leakage` compute and return delta_point/CI numbers only; a
    # human applies the RETAIN/DROP/INCONCLUSIVE rule and the leakage
    # gross-error check against these frozen values AFTER collection, per
    # the sign-off record's own §2.3 decision-rule block. Grep this
    # repository for `delta_gate3`/`delta_attention`/`delta_audio`/
    # `delta_latent`/`leakage_diagnostic_threshold_nats` outside this
    # dataclass's own definition and config_hash(): there is no such
    # reference -- these fields exist for provenance (so a run's
    # config_hash captures which frozen thresholds were in force), not for
    # any code path to compare against.
    #
    # Coincide by argument, not by default (sign-off record §2.2): each
    # component clears the same 20%-of-baseline-structure bar because each
    # carries a comparable build/validation/failure-mode cost.
    delta_gate3: float = 0.05
    delta_attention: float = 0.05
    delta_audio: float = 0.05  # accepted conditionally -- see §2.4(b): Delta_audio
                                # is not currently computable (A/V sync is a
                                # documented omission, CC-001 §6(a)); this value is
                                # fixed in advance should synchronisation ever be
                                # measured, not an assertion that it will be.
    delta_latent: float = 0.05  # exploratory status unchanged by acceptance
    leakage_diagnostic_threshold_nats: float = 0.10  # = 2 x delta_gate3

    def config_hash(self):
        """Same pattern as controls/null_input.py's NullInputConfig --
        a short, stable hash of the config's own JSON representation,
        meant to be recorded alongside every result this config
        influenced, so a reader can verify which pre-registered values
        produced a given number."""
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


# The single, canonical instance every consumer imports -- there is
# exactly one pre-registered configuration in force at a time, not a
# per-caller default that could silently drift between call sites.
PRE_REGISTERED_CONFIG = PreRegisteredConfig()
