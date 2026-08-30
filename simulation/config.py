"""
D0PA1 minimal pre-registered configuration (D6, Addendum 3).

THIS IS NOT THE FULL GATE 0 CONFIGURATION INFRASTRUCTURE. CLAUDE.md's
"WHAT D0PA1 ADDS" section describes a much larger provenance system --
experiment ID, pinned dependency versions, a variant log, a canonical
versioned log schema, a data manifest. NONE of that exists here. This
file exists for exactly one reason: the log-loss clip epsilon is a
quantity that materially changes the primary metric's VALUE (Addendum 2:
a single trial with an exact-zero true-class probability swung U by more
than 2x between eps=1e-6 and eps=1e-15), which makes it exactly the kind
of decision a pre-registered study must fix in advance, visibly, and
verifiably -- not a bare literal sitting in model code where it could be
edited after seeing a result with no audit trail.

Calling this "the config system" would overstate what exists (G3). It is
the minimal versioned home for ONE pre-registered parameter. The fuller
Gate 0 work remains OUTSTANDING.
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
