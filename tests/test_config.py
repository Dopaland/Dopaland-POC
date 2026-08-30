"""
D0PA1 minimal pre-registered config validation (runnable directly, no
pytest). Covers: config_hash is reproducible for identical values and
sensitive to a changed value (same contract as controls/null_input.py's
NullInputConfig.config_hash, tested the same way in tests/test_controls.py),
and that simulation.models sources its clip epsilon from this config
rather than a disconnected literal.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.config import PreRegisteredConfig, PRE_REGISTERED_CONFIG


def check_hash_reproducible_and_sensitive():
    c1 = PreRegisteredConfig(log_loss_clip_eps=1e-15)
    c2 = PreRegisteredConfig(log_loss_clip_eps=1e-15)
    c3 = PreRegisteredConfig(log_loss_clip_eps=1e-12)
    same = c1.config_hash() == c2.config_hash()
    different = c1.config_hash() != c3.config_hash()
    return same and different, (c1.config_hash(), c2.config_hash(), c3.config_hash())


def check_models_sources_eps_from_config():
    from simulation.models import LOG_LOSS_CLIP_EPS
    ok = LOG_LOSS_CLIP_EPS == PRE_REGISTERED_CONFIG.log_loss_clip_eps
    return ok, {"models.LOG_LOSS_CLIP_EPS": LOG_LOSS_CLIP_EPS, "config.log_loss_clip_eps": PRE_REGISTERED_CONFIG.log_loss_clip_eps}


if __name__ == "__main__":
    failures = []

    ok, detail = check_hash_reproducible_and_sensitive()
    print(f"[1/2] CONFIG_HASH REPRODUCIBLE + SENSITIVE TO CHANGE -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"config_hash did not behave as expected: {detail}")

    ok, detail = check_models_sources_eps_from_config()
    print(f"[2/2] MODELS.PY SOURCES CLIP EPS FROM PRE_REGISTERED_CONFIG -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"simulation.models is not sourcing its epsilon from the pre-registered config: {detail}")

    print()
    if failures:
        print(f"CONFIG VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("CONFIG VALIDATION: PASS")
