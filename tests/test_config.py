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


def check_gate0_a2_fields_sourced_from_config():
    """Gate 0 A2: zero_dispersion_epsilon, camera_index, and
    fps_report_interval_seconds must each be sourced from
    PRE_REGISTERED_CONFIG at their (former) local-constant call sites, not
    duplicated as a second, driftable literal."""
    import controls.null_input as null_input
    import stage1_step4_vectors as s1

    checks = {
        "null_input.ZERO_DISPERSION_EPSILON": (null_input.ZERO_DISPERSION_EPSILON, PRE_REGISTERED_CONFIG.zero_dispersion_epsilon),
        "s1.CAMERA_INDEX": (s1.CAMERA_INDEX, PRE_REGISTERED_CONFIG.camera_index),
        "s1.FPS_REPORT_INTERVAL_SECONDS": (s1.FPS_REPORT_INTERVAL_SECONDS, PRE_REGISTERED_CONFIG.fps_report_interval_seconds),
    }
    ok = all(actual == expected for actual, expected in checks.values())
    return ok, {k: v for k, v in checks.items()}


if __name__ == "__main__":
    failures = []

    ok, detail = check_hash_reproducible_and_sensitive()
    print(f"[1/3] CONFIG_HASH REPRODUCIBLE + SENSITIVE TO CHANGE -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"config_hash did not behave as expected: {detail}")

    ok, detail = check_models_sources_eps_from_config()
    print(f"[2/3] MODELS.PY SOURCES CLIP EPS FROM PRE_REGISTERED_CONFIG -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"simulation.models is not sourcing its epsilon from the pre-registered config: {detail}")

    ok, detail = check_gate0_a2_fields_sourced_from_config()
    print(f"[3/3] GATE 0 A2 FIELDS SOURCED FROM PRE_REGISTERED_CONFIG (not duplicated) -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"a moved Gate 0 A2 field has drifted from its config source: {detail}")

    print()
    if failures:
        print(f"CONFIG VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("CONFIG VALIDATION: PASS")
