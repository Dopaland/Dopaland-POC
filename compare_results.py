"""
D0PA1 D4, 2.6 -- CROSS-ENVIRONMENT COMPARISON SCRIPT.

Compares a reproduction_output/ directory against a REFERENCE
reproduction_output/ directory (e.g. one generated on a different
machine/OS, or committed as a reference snapshot), reporting per-value
absolute and relative deviation for numeric results, plus a checksum
comparison for artefacts expected to match EXACTLY (SVG figures).

G1: this script REPORTS deviations. It does not decide whether a
deviation is acceptable -- `--tolerance` is a plain parameter with a
RECOMMENDED default (see docs/D4_REPRODUCIBILITY.md section 2.6 for what
was actually observed and why that value is recommended, not decided);
no comparison anywhere in this file causes it to exit non-zero or print
a pass/fail verdict based on the tolerance. It prints every deviation
found and its magnitude; a human reads the output and judges it.

USAGE:
    python compare_results.py --reference <dir> --candidate <dir> [--tolerance 1e-9]

Both directories are expected to be reproduce.py output
(reproduction_output/ from two different runs/machines).
"""

import argparse
import hashlib
import json
import os
import sys

# 2.6's recommendation -- see docs/D4_REPRODUCIBILITY.md for what was
# actually observed (same-machine runs are bit-identical to the seeded
# results; this default is for CROSS-machine/CROSS-BLAS/CROSS-numpy-version
# comparison, where floating-point summation order can differ in the
# last few bits without indicating any real discrepancy). Stated as a
# recommendation, not a decision -- the value is the client's to set.
RECOMMENDED_TOLERANCE = 1e-6

# 00_provenance.json's run-identity fields are EXPECTED to differ between
# any two runs by design (see reproduce.py's own module docstring) --
# excluded from the numeric/exact comparison below, reported separately
# as "expected to differ", never silently skipped without saying so.
PROVENANCE_EXPECTED_TO_DIFFER = {"captured_at_utc", "experiment_id"}

# Files expected to match EXACTLY (checksum, not tolerance) -- currently
# only the SVG figure(s); JSON results tables get the numeric tolerance
# comparison instead, since JSON key ordering/float repr can legitimately
# vary in ways a plain byte-diff would flag even when every VALUE matches
# to full precision.
EXACT_MATCH_EXTENSIONS = (".svg",)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _flatten(obj, prefix=""):
    """Yields (dotted_path, value) for every leaf (non-dict, non-list)
    value in a nested JSON structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def compare_json_files(reference_path, candidate_path, tolerance, basename):
    with open(reference_path, encoding="utf-8") as f:
        ref = json.load(f)
    with open(candidate_path, encoding="utf-8") as f:
        cand = json.load(f)

    ref_flat = dict(_flatten(ref))
    cand_flat = dict(_flatten(cand))

    is_provenance = basename == "00_provenance.json"

    deviations = []
    expected_differences = []
    only_in_reference = sorted(set(ref_flat) - set(cand_flat))
    only_in_candidate = sorted(set(cand_flat) - set(ref_flat))

    for key in sorted(set(ref_flat) & set(cand_flat)):
        field_name = key.split(".")[-1].split("[")[0]
        if is_provenance and field_name in PROVENANCE_EXPECTED_TO_DIFFER:
            if ref_flat[key] != cand_flat[key]:
                expected_differences.append({"key": key, "reference": ref_flat[key], "candidate": cand_flat[key]})
            continue

        rv, cv = ref_flat[key], cand_flat[key]
        if isinstance(rv, (int, float)) and isinstance(cv, (int, float)) and not isinstance(rv, bool) and not isinstance(cv, bool):
            abs_dev = abs(cv - rv)
            rel_dev = abs_dev / abs(rv) if rv != 0 else (0.0 if cv == 0 else float("inf"))
            if abs_dev > tolerance:
                deviations.append({"key": key, "reference": rv, "candidate": cv, "abs_deviation": abs_dev, "rel_deviation": rel_dev})
        else:
            if rv != cv:
                deviations.append({"key": key, "reference": rv, "candidate": cv, "abs_deviation": None, "rel_deviation": None})

    return {
        "basename": basename,
        "n_fields_compared": len(set(ref_flat) & set(cand_flat)),
        "deviations": deviations,
        "expected_differences": expected_differences,
        "only_in_reference": only_in_reference,
        "only_in_candidate": only_in_candidate,
    }


def compare_directories(reference_dir, candidate_dir, tolerance):
    ref_files = sorted(f for f in os.listdir(reference_dir) if os.path.isfile(os.path.join(reference_dir, f)))
    cand_files = sorted(f for f in os.listdir(candidate_dir) if os.path.isfile(os.path.join(candidate_dir, f)))

    report = {
        "reference_dir": reference_dir,
        "candidate_dir": candidate_dir,
        "tolerance": tolerance,
        "only_in_reference_dir": sorted(set(ref_files) - set(cand_files)),
        "only_in_candidate_dir": sorted(set(cand_files) - set(ref_files)),
        "json_comparisons": [],
        "exact_match_comparisons": [],
    }

    for basename in sorted(set(ref_files) & set(cand_files)):
        ref_path = os.path.join(reference_dir, basename)
        cand_path = os.path.join(candidate_dir, basename)
        ext = os.path.splitext(basename)[1]

        if ext == ".json":
            report["json_comparisons"].append(compare_json_files(ref_path, cand_path, tolerance, basename))
        elif ext in EXACT_MATCH_EXTENSIONS:
            ref_hash = sha256_of(ref_path)
            cand_hash = sha256_of(cand_path)
            report["exact_match_comparisons"].append({
                "basename": basename, "reference_sha256": ref_hash, "candidate_sha256": cand_hash,
                "identical": ref_hash == cand_hash,
            })

    return report


def print_report(report):
    print(f"Reference:  {report['reference_dir']}")
    print(f"Candidate:  {report['candidate_dir']}")
    print(f"Tolerance:  {report['tolerance']} (absolute; see docs/D4_REPRODUCIBILITY.md 2.6 for the recommendation this defaults to)")
    print()

    if report["only_in_reference_dir"]:
        print(f"FILES ONLY IN REFERENCE: {report['only_in_reference_dir']}")
    if report["only_in_candidate_dir"]:
        print(f"FILES ONLY IN CANDIDATE: {report['only_in_candidate_dir']}")

    total_deviations = 0
    for comp in report["json_comparisons"]:
        print(f"--- {comp['basename']} ({comp['n_fields_compared']} fields compared) ---")
        if comp["expected_differences"]:
            print(f"  {len(comp['expected_differences'])} field(s) differ but are EXPECTED to (run-identity fields, by design):")
            for d in comp["expected_differences"]:
                print(f"    {d['key']}: reference={d['reference']!r} candidate={d['candidate']!r}")
        if comp["only_in_reference"]:
            print(f"  fields only in reference: {comp['only_in_reference']}")
        if comp["only_in_candidate"]:
            print(f"  fields only in candidate: {comp['only_in_candidate']}")
        if comp["deviations"]:
            total_deviations += len(comp["deviations"])
            print(f"  {len(comp['deviations'])} field(s) exceed tolerance {report['tolerance']}:")
            for d in comp["deviations"]:
                if d["abs_deviation"] is not None:
                    print(f"    {d['key']}: reference={d['reference']!r} candidate={d['candidate']!r} abs_dev={d['abs_deviation']:.6g} rel_dev={d['rel_deviation']:.6g}")
                else:
                    print(f"    {d['key']}: reference={d['reference']!r} candidate={d['candidate']!r} (non-numeric mismatch)")
        else:
            print(f"  all numeric/text fields within tolerance.")
        print()

    for comp in report["exact_match_comparisons"]:
        status = "IDENTICAL" if comp["identical"] else "DIFFERS"
        print(f"--- {comp['basename']} (exact-match checksum) --- {status}")
        if not comp["identical"]:
            print(f"    reference_sha256={comp['reference_sha256']}")
            print(f"    candidate_sha256={comp['candidate_sha256']}")
        print()

    n_exact_mismatches = sum(1 for c in report["exact_match_comparisons"] if not c["identical"])
    print(f"SUMMARY: {total_deviations} field(s) exceeded tolerance across {len(report['json_comparisons'])} JSON file(s); "
          f"{n_exact_mismatches} of {len(report['exact_match_comparisons'])} exact-match file(s) differ. "
          "This is a report, not a verdict -- no pass/fail is computed here (G1).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, help="Reference reproduction_output/ directory")
    parser.add_argument("--candidate", required=True, help="Candidate reproduction_output/ directory to compare against the reference")
    parser.add_argument("--tolerance", type=float, default=RECOMMENDED_TOLERANCE, help=f"Absolute tolerance for numeric fields (default: {RECOMMENDED_TOLERANCE}, a recommendation -- see docs/D4_REPRODUCIBILITY.md 2.6)")
    args = parser.parse_args()

    report = compare_directories(args.reference, args.candidate, args.tolerance)
    print_report(report)


if __name__ == "__main__":
    main()
