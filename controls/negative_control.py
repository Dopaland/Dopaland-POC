"""
D0PA1 control, Part 2.2 -- NEGATIVE CONTROL.

A deliberately meaningless signal: generated to match the real/simulated
signals' sampling rate and autocorrelation structure, while carrying
DEFINITIONALLY ZERO information about any task outcome.

EXACTLY HOW IT IS GENERATED, AND WHY THAT CARRIES NO INFORMATION
------------------------------------------------------------------
An AR(1) process, z_t = ar1_phi * z_{t-1} + eps_t, eps_t ~ N(0,1) -- the
SAME functional form simulation/generator.py's own latent state z_t uses
(A1, serial dependence), so the negative control's autocorrelation
strength (ar1_phi) can be matched to whatever assumption a given analysis
is using for the real/simulated signals. This matters: a plain white-noise
control (phi=0) would have a DIFFERENT, easier-to-distinguish statistical
shape than an autocorrelated real signal, making it too weak a test of
"can this model appear to find structure in nothing." Matching the
autocorrelation is what makes the negative control a fair, hard test.

It carries no information NOT because it is unstructured (it IS
autocorrelated, deliberately), but because its random stream
(np.random.default_rng(seed), used ONLY here) is generated from a SEED
that never derives from, mixes with, or is used anywhere else in the same
analysis's class-label generation, feature generation, or fitting
procedure. There is no causal or numerical path from this control's values
to the outcome being predicted -- it is exactly as informative as
generating it in a separate process on a separate machine and pasting the
numbers in afterward. Any measured "contribution" from this signal in a
downstream fit is BY CONSTRUCTION due to finite-sample noise/overfitting,
never a real effect -- which is exactly what makes it useful as a
negative control.

WHAT THIS CANNOT ESTABLISH: this control tests whether the ANALYSIS
PROCEDURE (feature construction, model fitting, evaluation) can be fooled
into reporting a spurious contribution from pure noise. It says nothing
about sensor/pipeline noise floors under null physical conditions -- that
is controls/null_input.py's job. The two controls are complementary, not
substitutes for each other (see docs/CONTROLS.md).

WIRED IN AUTOMATICALLY, NOT OPTIONAL: simulation/precision.py's
compute_delta() ALWAYS generates and evaluates a negative control alongside
the real candidate signal, for every call, with no flag to disable it --
see that module for how delta_negative_control ends up in every result row
this pipeline produces.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class NegativeControlConfig:
    seed: int
    n_samples: int
    sampling_rate_hz: float = 25.0  # matches CLAUDE.md's CADENCE note: Thread 2 samples at ~20-30/s
    ar1_phi: float = 0.6  # matches simulation/generator.py's own A1 default -- override to match a different analysis's assumed autocorrelation


def generate_negative_control(config: NegativeControlConfig):
    """Returns an (n_samples,) float array. Deterministic given config.seed
    (verified in tests/test_controls.py by generating twice)."""
    rng = np.random.default_rng(config.seed)
    z = 0.0
    values = np.empty(config.n_samples)
    for i in range(config.n_samples):
        eps = rng.normal()
        z = config.ar1_phi * z + eps
        values[i] = z
    return values
