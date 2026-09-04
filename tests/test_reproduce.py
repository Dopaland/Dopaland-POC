"""
D0PA1 D4 reproduction command validation (runnable directly, no pytest).
Covers: reproduce.py's own AST contains no import of the three capture/UI
consumers (2.2, checked structurally -- not just by not having written
one), every seed constant declared in reproduce.py is actually a plain
int (not accidentally left unset/None), compare_results.py correctly
reports zero deviations on two structurally-identical result sets and
correctly detects a deliberately injected deviation (proof it isn't
vacuous), and that reproduce.py runs end-to-end and produces the expected
output files. This file does NOT itself re-run the full "twice and diff"
byte-identity check (that was run manually once and is reported, with
its real output, in docs/D4_REPRODUCIBILITY.md -- re-running two full
`python reproduce.py` invocations on every test-suite run would be slow
for a suite meant to run in seconds; the mechanism this depends on
(deterministic seeding, no unseeded randomness) IS covered by the
per-module tests each called function already has).
"""

import ast
import json
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

FORBIDDEN_CONSUMER_MODULES = ("stage1_step4_vectors", "stage3_demo_ui", "analyze_video")


def check_reproduce_py_never_imports_the_three_consumers():
    path = os.path.join(REPO_ROOT, "reproduce.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in FORBIDDEN_CONSUMER_MODULES:
                violations.append(mod)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_CONSUMER_MODULES:
                    violations.append(alias.name)
    return len(violations) == 0, {"violations": violations}


def check_all_declared_seeds_are_plain_ints():
    import reproduce
    seed_names = [n for n in dir(reproduce) if n.startswith("SEED_")]
    non_int = {n: getattr(reproduce, n) for n in seed_names if not isinstance(getattr(reproduce, n), int)}
    return len(seed_names) >= 8 and len(non_int) == 0, {"n_seeds_declared": len(seed_names), "seed_names": sorted(seed_names), "non_int": non_int}


def check_compare_results_reports_zero_deviations_on_identical_data():
    from compare_results import compare_directories

    with tempfile.TemporaryDirectory() as tmpdir:
        ref_dir = os.path.join(tmpdir, "ref")
        cand_dir = os.path.join(tmpdir, "cand")
        os.makedirs(ref_dir)
        os.makedirs(cand_dir)
        payload = {"a": 1.0, "b": {"c": 2.5, "d": [1, 2, 3]}}
        for d in (ref_dir, cand_dir):
            with open(os.path.join(d, "result.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f)

        report = compare_directories(ref_dir, cand_dir, tolerance=1e-9)
        comp = report["json_comparisons"][0]
        ok = len(comp["deviations"]) == 0 and len(comp["only_in_reference"]) == 0 and len(comp["only_in_candidate"]) == 0
        return ok, {"comp": comp}


def check_compare_results_detects_injected_deviation():
    from compare_results import compare_directories

    with tempfile.TemporaryDirectory() as tmpdir:
        ref_dir = os.path.join(tmpdir, "ref")
        cand_dir = os.path.join(tmpdir, "cand")
        os.makedirs(ref_dir)
        os.makedirs(cand_dir)
        with open(os.path.join(ref_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump({"delta_point": 0.05, "note": "x"}, f)
        with open(os.path.join(cand_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump({"delta_point": 0.09, "note": "y"}, f)  # both fields deliberately perturbed

        report = compare_directories(ref_dir, cand_dir, tolerance=1e-9)
        comp = report["json_comparisons"][0]
        keys_flagged = {d["key"] for d in comp["deviations"]}
        ok = keys_flagged == {"delta_point", "note"}
        return ok, {"comp": comp}


def check_compare_results_excludes_provenance_run_identity_fields():
    from compare_results import compare_directories

    with tempfile.TemporaryDirectory() as tmpdir:
        ref_dir = os.path.join(tmpdir, "ref")
        cand_dir = os.path.join(tmpdir, "cand")
        os.makedirs(ref_dir)
        os.makedirs(cand_dir)
        with open(os.path.join(ref_dir, "00_provenance.json"), "w", encoding="utf-8") as f:
            json.dump({"experiment_id": "exp_a", "captured_at_utc": "2026-01-01T00:00:00Z", "git_commit_hash": "abc123"}, f)
        with open(os.path.join(cand_dir, "00_provenance.json"), "w", encoding="utf-8") as f:
            json.dump({"experiment_id": "exp_b", "captured_at_utc": "2026-01-02T00:00:00Z", "git_commit_hash": "abc123"}, f)

        report = compare_directories(ref_dir, cand_dir, tolerance=1e-9)
        comp = report["json_comparisons"][0]
        ok = len(comp["deviations"]) == 0 and len(comp["expected_differences"]) == 2
        return ok, {"comp": comp}


def check_reproduce_runs_end_to_end_and_produces_expected_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        env = dict(os.environ)
        result = subprocess.run(
            [sys.executable, "reproduce.py"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=180, env=env,
        )
        ran_ok = result.returncode == 0
        output_dir = os.path.join(REPO_ROOT, "reproduction_output")
        expected_files = {
            "00_provenance.json", "01_d7_baselines.json", "02_d3_reliability.json",
            "02_d3_reliability_bland_altman.svg", "03_leakage_diagnostic.json",
            "04_time_shuffle_diagnostic.json", "05_latent_recovery_sweep.json", "06_blink_positive_synthetic.json",
        }
        actual_files = set(os.listdir(output_dir)) if os.path.isdir(output_dir) else set()
        all_present = expected_files.issubset(actual_files)
        return ran_ok and all_present, {
            "returncode": result.returncode, "all_present": all_present,
            "missing": sorted(expected_files - actual_files),
            "stderr_tail": result.stderr[-500:] if not ran_ok else None,
        }


if __name__ == "__main__":
    checks = [
        ("2.2 STRUCTURAL: reproduce.py never imports the three consumers", check_reproduce_py_never_imports_the_three_consumers),
        ("2.4 SEED ENUMERATION: all declared SEED_* constants are plain ints", check_all_declared_seeds_are_plain_ints),
        ("compare_results.py: zero deviations on identical data", check_compare_results_reports_zero_deviations_on_identical_data),
        ("compare_results.py: detects an injected deviation (proof, not vacuous)", check_compare_results_detects_injected_deviation),
        ("compare_results.py: excludes provenance run-identity fields as EXPECTED differences", check_compare_results_excludes_provenance_run_identity_fields),
        ("reproduce.py runs end-to-end, produces every expected output file", check_reproduce_runs_end_to_end_and_produces_expected_files),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"REPRODUCE VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("REPRODUCE VALIDATION: PASS")
