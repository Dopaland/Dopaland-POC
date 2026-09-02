"""
================================================================
 PIPELINE SMOKE TEST ONLY -- NOT A RELIABILITY RESULT FOR THIS STUDY.
================================================================

D0PA1 Part 3, explicit instruction: "DO run it on existing logs ONLY as a
smoke test that it executes end to end, and label any such output
UNAMBIGUOUSLY as a pipeline smoke test. DO NOT produce, commit or report
anything that could be read as a reliability RESULT for this study."

The logs used below (arbitrary real session_*.jsonl files already in
logs/) are POC captures and diagnostic runs under DIFFERING conditions,
schemas, and protocols -- they are NOT repeated measurements of matched
units across three fixed-protocol sessions on three separate days (that
data has not been collected -- see docs/RELIABILITY.md). The "sessions"
and "units" this file constructs from them are an ARBITRARY CHUNKING for
the sole purpose of feeding a realistic data VOLUME/SHAPE through
analysis/baselines.py and analysis/reliability.py end-to-end and
confirming nothing crashes.

THIS FILE DELIBERATELY DOES NOT:
  - print any SEM/RC/CV/Bland-Altman/ICC NUMBER to the console
  - write any such number to a file
  - assert anything about the MAGNITUDE of any computed value
It asserts ONLY structural properties: the pipeline ran, produced the
right SHAPE of output, and every computed value is a finite float or an
explicitly-reasoned missing value -- i.e. that it didn't crash and didn't
silently produce NaN/inf. If you are looking for what these functions
compute and how to validate them, see tests/test_baselines.py and
tests/test_reliability.py (synthetic, with real numbers reported there,
where reporting numbers is appropriate).
"""

import glob
import json
import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from analysis.baselines import compute_all_baselines
from analysis.reliability import build_unit_session_matrix, compute_all_reliability_measures

CHUNK_SIZE = 25  # arbitrary -- purely to create multiple "units" per pseudo-session, not a real episode boundary


def _load_v_es_chunks_as_pseudo_session(path, max_samples=2000):
    """Reads real v_es values from one real session log, in order, and
    chunks them into CHUNK_SIZE-sample groups -- an ARBITRARY, NOT
    protocol-meaningful grouping used only to exercise the pipeline's
    'multiple units per session' shape. Returns list of
    {"value": float|None, "missingness_reason": str|None} per chunk (mean
    of the chunk's non-missing values, or missing if the whole chunk had
    none)."""
    values = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("record_type") != "sample":
                continue
            values.append(rec.get("vectors", {}).get("v_es"))
            if len(values) >= max_samples:
                break

    chunks = []
    for i in range(0, len(values) - CHUNK_SIZE + 1, CHUNK_SIZE):
        window = values[i:i + CHUNK_SIZE]
        present = [v for v in window if v is not None]
        if present:
            chunks.append({"value": float(np.mean(present)), "missingness_reason": None})
        else:
            chunks.append({"value": None, "missingness_reason": "no_face"})
    return chunks


def _find_real_session_logs(n_needed=3):
    logs_dir = os.path.join(REPO_ROOT, "logs")
    candidates = sorted(glob.glob(os.path.join(logs_dir, "session_*.jsonl")))
    usable = []
    for path in candidates:
        chunks = _load_v_es_chunks_as_pseudo_session(path)
        if len(chunks) >= 5:  # need enough chunks to be a non-trivial "session"
            usable.append((os.path.basename(path), chunks))
        if len(usable) >= n_needed:
            break
    return usable


def check_pipeline_executes_end_to_end_on_real_log_shapes():
    """Structural-only assertions -- see module docstring for what this
    deliberately does NOT check or print."""
    sessions = _find_real_session_logs(n_needed=3)
    if len(sessions) < 3:
        return False, f"could not find 3 usable real session logs with >= 5 chunks each (found {len(sessions)}) -- cannot run the smoke test"

    sessions_in_order = [(sid, chunks) for sid, chunks in sessions]

    # --- D7 baselines: must execute without raising ---
    baselines_result = compute_all_baselines(sessions_in_order)
    baselines_ran = set(baselines_result.keys()) == {"raw", "session_z", "persistent_z", "config_hash"}

    # --- D3 reliability: build a (unit, session) matrix by pairing chunk
    # index across the (arbitrarily chunked) pseudo-sessions, then run
    # the full measure set end to end. ---
    rows = []
    for session_id, chunks in sessions_in_order:
        for unit_idx, entry in enumerate(chunks):
            rows.append({"unit_id": unit_idx, "session_id": session_id, "value": entry["value"]})
    matrix, unit_ids, session_ids = build_unit_session_matrix(rows)

    rng = np.random.default_rng(0)
    reliability_result = compute_all_reliability_measures(matrix, session_ids, n_boot=100, alpha=0.05, rng=rng)
    reliability_ran = set(reliability_result.keys()) >= {"sem", "rc", "cv", "bland_altman"}

    # Structural-only checks: every point value computed is either a
    # finite float or accompanied by an explicit reason -- no silent
    # NaN/inf anywhere in the output.
    def _finite_or_reasoned(value, reason):
        return (value is None and reason is not None) or (value is not None and np.isfinite(value))

    sem_ok = _finite_or_reasoned(reliability_result["sem"]["sem"], reliability_result["sem"]["missingness_reason"])
    cv_ok = _finite_or_reasoned(reliability_result["cv"]["cv_percent"], reliability_result["cv"].get("missingness_reason"))
    ba_ok = all(
        _finite_or_reasoned(ba["bias"], ba.get("missingness_reason"))
        for ba in reliability_result["bland_altman"].values()
    )

    ok = baselines_ran and reliability_ran and sem_ok and cv_ok and ba_ok
    return ok, (
        f"executed end-to-end on {len(sessions_in_order)} real log(s), "
        f"{matrix.shape[0]} pseudo-units x {matrix.shape[1]} pseudo-sessions -- "
        f"baselines_ran={baselines_ran} reliability_ran={reliability_ran} "
        f"no_silent_nan_or_inf={sem_ok and cv_ok and ba_ok} "
        "(no computed VALUE is printed here -- see module docstring)"
    )


if __name__ == "__main__":
    print(__doc__)
    ok, detail = check_pipeline_executes_end_to_end_on_real_log_shapes()
    print(f"[1/1] PIPELINE SMOKE TEST (real log SHAPES, arbitrary chunking, NOT a reliability result) -- {'PASS' if ok else 'FAIL'}: {detail}")
    print()
    if not ok:
        print("SMOKE TEST: FAIL")
        sys.exit(1)
    print("SMOKE TEST: PASS -- pipeline executes end to end on real-log-shaped data. This is NOT a finding.")
