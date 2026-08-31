"""
D0PA1 Gate 0, A5 -- variant log writer validation (runnable directly, no
pytest). Writes to a throwaway temp file (never the real
logs/variant_log.jsonl) so this test can never pollute the real provenance
record. Covers: the file only ever grows (append-only, demonstrated by
actually appending twice and checking), every written line is valid JSON
carrying the required fields, and the retrospective/event_ts_utc vs
ts_utc distinction is preserved.
"""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from simulation.variant_log import append_variant_log_entry


def check_append_only_growth():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "variant_log.jsonl")
        append_variant_log_entry("first change", "tried X", "because Y", path=path)
        size_after_1 = os.path.getsize(path)
        with open(path, encoding="utf-8") as f:
            lines_after_1 = f.readlines()

        append_variant_log_entry("second change", "tried Z", "because W", path=path)
        size_after_2 = os.path.getsize(path)
        with open(path, encoding="utf-8") as f:
            lines_after_2 = f.readlines()

        grew = size_after_2 > size_after_1
        first_line_unchanged = lines_after_1[0] == lines_after_2[0]
        two_lines_now = len(lines_after_2) == 2
        ok = grew and first_line_unchanged and two_lines_now
        return ok, {
            "size_after_1": size_after_1, "size_after_2": size_after_2,
            "first_line_unchanged": first_line_unchanged, "n_lines_after_2": len(lines_after_2),
        }


def check_required_fields_and_retrospective_distinction():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "variant_log.jsonl")
        entry = append_variant_log_entry(
            "backfilled description", "tried A", "because B",
            retrospective=True, event_ts_utc="2026-01-01T00:00:00+00:00", path=path,
        )
        with open(path, encoding="utf-8") as f:
            line = f.readline()
        parsed = json.loads(line)

        required = ["schema_version", "record_type", "ts_utc", "retrospective", "event_ts_utc", "description", "what_was_tried", "why"]
        has_all_fields = all(k in parsed for k in required)
        retrospective_flagged = parsed["retrospective"] is True
        event_ts_differs_from_write_ts = parsed["event_ts_utc"] != parsed["ts_utc"]
        matches_return_value = parsed == entry

        ok = has_all_fields and retrospective_flagged and event_ts_differs_from_write_ts and matches_return_value
        return ok, {"parsed": parsed}


if __name__ == "__main__":
    failures = []

    ok, detail = check_append_only_growth()
    print(f"[1/2] APPEND-ONLY: FILE ONLY GROWS, EARLIER LINES NEVER REWRITTEN -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"append-only growth check failed: {detail}")

    ok, detail = check_required_fields_and_retrospective_distinction()
    print(f"[2/2] REQUIRED FIELDS + RETROSPECTIVE/EVENT_TS DISTINCTION -- {'PASS' if ok else 'FAIL'}: {detail}")
    if not ok:
        failures.append(f"required-fields/retrospective check failed: {detail}")

    print()
    if failures:
        print(f"VARIANT LOG VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("VARIANT LOG VALIDATION: PASS")
