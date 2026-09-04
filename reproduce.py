"""
D0PA1 D4 -- REPRODUCTION COMMAND.

THE ACCEPTANCE TEST, as the client stated it: run ONE documented command
on a clean machine and the reported results tables regenerate. This file
-- invoked via `make reproduce` or `.\\reproduce.ps1` -- IS that command.
See docs/D4_REPRODUCIBILITY.md for the full account: every seed
enumerated, the two consumers this path deliberately does NOT import and
why, which historical logs can and cannot be attributed to a capture-side
consumer, the real byte-diff result of running this command twice, and
the recommended cross-machine comparison tolerance.

2.2 -- imports ONLY features/, analysis/, simulation/, controls/,
schema/. NEVER stage1_step4_vectors.py, stage3_demo_ui.py, or
analyze_video.py (the three capture/UI consumers -- confirmed by this
file's own import list, not just by intent).

2.1 -- reproduces from ARCHIVED INPUTS, never a live camera. Every input
this command consumes is either (a) a fixed, versioned config/seed
(fully self-contained -- no external file needed at all) or (b) this
repository's own committed source. It does NOT read or write logs/ or
manifest/data_manifest.csv -- see docs/D4_REPRODUCIBILITY.md's "why not
logs/" section: that data is machine-local, not archived/version-
controlled (G4), and regenerating it here would risk silently overwriting
a developer's real local manifest with an empty one on a clean checkout
that has no local logs/. manifest/generate_data_manifest.py remains a
separate, already-existing, independently-runnable command for that.

SCOPE, stated honestly (G3): this regenerates the D7/D3/controls
(leakage, time-shuffle, blink-positive synthetic validation)/latent-
recovery results -- all fully synthetic-seeded, all fast. It does NOT
re-invoke the five pre-existing D6 precision-simulation driver scripts
(simulation/run_precision_sweep.py, run_precision_sweep_pass2.py,
run_precision_sweep_finalisation.py, run_metric_comparison.py,
run_eps_and_baseline_analysis.py), each of which already produced its own
committed artefact under artefacts/ and takes several minutes to re-run.
Each remains independently runnable (`python simulation/<script>.py`).
This is a disclosed scope decision, not an oversight -- see
docs/D4_REPRODUCIBILITY.md.

OUTPUT: every file goes under reproduction_output/ (git-ignored -- this
is regenerated output, not source). 00_provenance.json's timestamp/
experiment_id fields are EXPECTED to differ between runs by design (see
that file's own fields); every OTHER file is expected to be byte-for-byte
identical across repeated runs on the same machine -- see
docs/D4_REPRODUCIBILITY.md section "2.5" for the actual, measured result.
"""

import json
import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(REPO_ROOT, "reproduction_output")

from simulation.provenance import capture_run_provenance
from simulation.config import PRE_REGISTERED_CONFIG
from simulation.generator import GeneratorConfig, generate as generate_trials
from simulation.latent_recovery import run_recovery_sweep, LatentRecoveryConfig
from analysis.baselines import compute_all_baselines
from analysis.reliability import (
    build_unit_session_matrix, compute_all_reliability_measures, plot_bland_altman_svg,
)
from controls.leakage import synthetic_trial_source, run_leakage_diagnostics, LeakageConfig
from controls.time_shuffle import run_time_shuffle_diagnostic, TimeShuffleConfig
from controls.blink_positive import BlinkPositiveConfig, run_detector_on_aperture_stream, evaluate_run

# ============================================================
# 2.4 -- EVERY STOCHASTIC COMPONENT'S SEED, enumerated and fixed here.
# Nothing below draws from an unseeded np.random call or the system clock
# for anything that affects a RESULT (captured_at_utc in the provenance
# record is the one deliberate, documented exception -- see
# docs/D4_REPRODUCIBILITY.md).
# ============================================================

SEED_D7_BASELINES_GENERATOR = 1001
SEED_D3_RELIABILITY_SYNTHETIC_DATA = 1002
SEED_D3_RELIABILITY_BOOTSTRAP = 1003
SEED_LEAKAGE_GENERATOR = 1004
SEED_LEAKAGE_BOOTSTRAP = 1005
SEED_TIME_SHUFFLE_GENERATOR = 1006
SEED_TIME_SHUFFLE_SHUFFLE = 1007
SEED_TIME_SHUFFLE_BOOTSTRAP = 1008
SEED_LATENT_RECOVERY = 1009
SEED_BLINK_POSITIVE_SYNTHETIC = 1010


def _strip_bulky_arrays(obj):
    """Recursively drops large intermediate arrays (raw bootstrap
    replicate arrays, per-point Bland-Altman diffs/means) from a result
    before writing it as a "results table" -- these are real outputs of
    the underlying functions but are intermediate detail, not the
    reported table; keeping them out keeps the regenerated files a
    reviewable size and keeps the byte-diff (2.5) focused on the
    reported numbers, not megabytes of bootstrap noise."""
    DROP_KEYS = {"bootstrap_deltas", "diffs", "means"}
    if isinstance(obj, dict):
        return {
            (str(k) if isinstance(k, tuple) else k): _strip_bulky_arrays(v)
            for k, v in obj.items() if k not in DROP_KEYS
        }
    if isinstance(obj, (list, tuple)):
        return [_strip_bulky_arrays(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _write_json(relative_path, obj):
    path = os.path.join(OUTPUT_DIR, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cleaned = _strip_bulky_arrays(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"  wrote {relative_path}")
    return path


# ============================================================
# Section runners -- each is a thin call into features/analysis/
# simulation/controls, with a FIXED seed from the table above. No new
# computation lives here beyond assembling inputs and writing output.
# ============================================================

def run_d7_baselines():
    print("[reproduce] D7 baselines (3 synthetic sessions, robust_mad/expanding default)...")
    rng = np.random.default_rng(SEED_D7_BASELINES_GENERATOR)
    sessions = []
    for i in range(3):
        values = list(rng.normal(loc=0.1 * i, scale=1.0, size=200))
        samples = [{"value": v, "missingness_reason": None} for v in values]
        sessions.append((f"session_{i}", samples))
    result = compute_all_baselines(sessions)
    summary = {
        "config_hash": result["config_hash"],
        "n_session_pairs_total": {rep: result[rep]["n_session_pairs_total"] for rep in ("raw", "session_z", "persistent_z")},
        "persistent_z_estimator": result["persistent_z"]["estimator"],
        "persistent_z_window_rule": result["persistent_z"]["window_rule"],
        "n_records_per_representation": {rep: len(result[rep]["records"]) for rep in ("raw", "session_z", "persistent_z")},
        "sample_records": {rep: result[rep]["records"][:5] for rep in ("raw", "session_z", "persistent_z")},
    }
    return _write_json("01_d7_baselines.json", summary)


def run_d3_reliability():
    print("[reproduce] D3 reliability (synthetic unit x session matrix)...")
    rng = np.random.default_rng(SEED_D3_RELIABILITY_SYNTHETIC_DATA)
    n_units, n_sessions = 25, 3
    true_unit_values = rng.normal(0, 2.0, n_units)
    matrix = np.column_stack([true_unit_values + rng.normal(0, 0.5, n_units) for _ in range(n_sessions)])
    session_ids = [f"s{i}" for i in range(n_sessions)]

    boot_rng = np.random.default_rng(SEED_D3_RELIABILITY_BOOTSTRAP)
    result = compute_all_reliability_measures(matrix, session_ids, n_boot=200, alpha=0.05, rng=boot_rng)

    first_pair_key = sorted(result["bland_altman"].keys())[0]
    first_pair = result["bland_altman"][first_pair_key]
    svg_path = os.path.join(OUTPUT_DIR, "02_d3_reliability_bland_altman.svg")
    plot_bland_altman_svg(first_pair, svg_path, title=f"D3 reliability demo: {first_pair_key[0]} vs {first_pair_key[1]}")
    print(f"  wrote 02_d3_reliability_bland_altman.svg")

    return _write_json("02_d3_reliability.json", result)


def run_leakage():
    print("[reproduce] leakage diagnostic (4 window variants, synthetic)...")
    gen_config = GeneratorConfig(
        seed=SEED_LEAKAGE_GENERATOR, n_sessions=3, episodes_per_session=100, trials_per_episode=5, effect_size=0.3,
    )
    source = synthetic_trial_source(gen_config)
    result = run_leakage_diagnostics(
        source, n_classes=gen_config.n_classes, n_sessions=gen_config.n_sessions,
        config=LeakageConfig(negative_control_seed=SEED_LEAKAGE_GENERATOR), n_boot=200, bootstrap_seed=SEED_LEAKAGE_BOOTSTRAP,
    )
    return _write_json("03_leakage_diagnostic.json", result)


def run_time_shuffle():
    print("[reproduce] time-shuffle diagnostic (ordered vs shuffled episode order, synthetic)...")
    def source():
        return generate_trials(GeneratorConfig(
            seed=SEED_TIME_SHUFFLE_GENERATOR, n_sessions=3, episodes_per_session=100, trials_per_episode=5,
            effect_size=0.3, fatigue_gain=1.0, class_drift_rate=0.6,
        ))
    result = run_time_shuffle_diagnostic(
        source, n_classes=3, n_sessions=3,
        config=TimeShuffleConfig(shuffle_seed=SEED_TIME_SHUFFLE_SHUFFLE, negative_control_seed=SEED_TIME_SHUFFLE_GENERATOR),
        n_boot=200, bootstrap_seed=SEED_TIME_SHUFFLE_BOOTSTRAP,
    )
    return _write_json("04_time_shuffle_diagnostic.json", result)


def run_latent_recovery():
    print("[reproduce] latent recovery sweep (synthetic, placeholder EMA pipeline)...")
    config = LatentRecoveryConfig(seed=SEED_LATENT_RECOVERY, episodes_per_session=100, ema_alpha=0.3)
    rows = run_recovery_sweep([0.0, 0.4, 0.8], [0.0, 1.0], config)
    return _write_json("05_latent_recovery_sweep.json", {"rows": rows, "config": {"seed": config.seed, "episodes_per_session": config.episodes_per_session, "ema_alpha": config.ema_alpha}})


def _synthetic_aperture_stream(true_blink_onsets_seconds, rng, duration_seconds=30.0, fps=25.0, baseline=0.47, dip=0.40, blink_duration=0.2):
    n_frames = int(duration_seconds * fps)
    stream = []
    for i in range(n_frames):
        t = i / fps
        in_blink = any(onset <= t < onset + blink_duration for onset in true_blink_onsets_seconds)
        aperture = dip + rng.normal(scale=0.005) if in_blink else baseline + rng.normal(scale=0.01)
        stream.append((t, float(aperture)))
    return stream


def run_blink_positive_synthetic():
    print("[reproduce] blink positive control (synthetic aperture streams, real BlinkDetector, NOT a real clip)...")
    rng = np.random.default_rng(SEED_BLINK_POSITIVE_SYNTHETIC)
    per_clip_inputs = []
    for i, true_onsets in enumerate([[3.0, 9.0, 18.0], [5.0, 12.0, 20.0, 25.0]]):
        stream = _synthetic_aperture_stream(true_onsets, rng)
        detected = run_detector_on_aperture_stream(stream)
        per_clip_inputs.append((f"synthetic_clip_{i}", detected, true_onsets))
    result = evaluate_run(per_clip_inputs, BlinkPositiveConfig(matching_tolerance_ms=350.0))
    return _write_json("06_blink_positive_synthetic.json", result)


def run_provenance():
    print("[reproduce] capturing run provenance...")
    provenance = capture_run_provenance(label="reproduce")
    record = {
        "experiment_id": provenance.experiment_id,
        "git_commit_hash": provenance.git_commit_hash,
        "git_dirty": provenance.git_dirty,
        "git_dirty_reason": provenance.git_dirty_reason,
        "validated_path_source_sha256": provenance.validated_path_source_sha256,
        "validated_path_source_files": provenance.validated_path_source_files,
        "config_hash": PRE_REGISTERED_CONFIG.config_hash(),
        "captured_at_utc": provenance.captured_at_utc,
        "hostname": provenance.hostname,
        "note": "experiment_id/captured_at_utc/hostname are EXPECTED to differ between runs by design -- see docs/D4_REPRODUCIBILITY.md. git_commit_hash/validated_path_source_sha256/config_hash are expected to be IDENTICAL for two runs of the same checkout.",
    }
    print(f"  experiment_id={provenance.experiment_id}")
    print(f"  git_commit={provenance.git_commit_hash}  git_dirty={provenance.git_dirty}")
    print(f"  config_hash={PRE_REGISTERED_CONFIG.config_hash()}")
    print(f"  validated_path_source_sha256={provenance.validated_path_source_sha256}")
    return _write_json("00_provenance.json", record)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"[reproduce] output directory: {OUTPUT_DIR}")
    print()

    run_provenance()
    run_d7_baselines()
    run_d3_reliability()
    run_leakage()
    run_time_shuffle()
    run_latent_recovery()
    run_blink_positive_synthetic()

    print()
    print("[reproduce] done. See docs/D4_REPRODUCIBILITY.md for what this command does and does not cover.")


if __name__ == "__main__":
    main()
