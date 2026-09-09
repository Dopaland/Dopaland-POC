"""
ROI aggregation layer validation (runnable directly, no pytest) --
"ACT ON THE ROI FEASIBILITY VERDICT" task, Task 3.4. Covers the six
scenarios that task named as a minimum, plus two additional correctness
checks (switching's documented gap semantics; JSON-serializability of a
flushed summary, since these summaries are meant to be logged).

Everything here exercises features.attention.ROIWindowAccumulator against
a hand-built synthetic (timestamp, roi_id) stream -- this file is the
"synthetic supplier for testing" Task 3.3 asked for. synthetic_roi_source()
below mirrors controls/leakage.py's synthetic_trial_source() shape: a
factory that returns a zero-argument callable yielding the stream, so a
future real source could be substituted with no change to how a caller
drives ROIWindowAccumulator. No camera-derived supplier and no harness
adapter exist here or anywhere in this repository, deliberately (Task
3.3's own instruction) -- the harness's real event format is unknown.
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from features.attention import ROIWindowAccumulator


def synthetic_roi_source(assignments):
    """Pluggable-supplier shape, mirroring controls/leakage.py's
    synthetic_trial_source(): a zero-argument callable returning the
    stream. `assignments` is a fixed list of (timestamp, roi_id) tuples,
    roi_id possibly None (an explicit "unassigned" sample)."""
    return lambda: list(assignments)


def _drive(accumulator, source, flush_at):
    """Feeds every (ts, roi_id) from source() into accumulator, then
    flushes at flush_at. Returns the summary."""
    for ts, roi_id in source():
        accumulator.add_sample(ts, roi_id)
    return accumulator.flush(flush_at)


def check_clean_single_region_window():
    """One roi_id, sampled steadily, no gaps -- the simplest case.
    Expect: full coverage, one roi_id in dwell equal to the whole window,
    zero switches, one persistence run covering the whole window (both
    censored, since it starts at window_start and runs to flush time)."""
    source = synthetic_roi_source([(0.0, "A"), (1.0, "A"), (2.0, "A"), (3.0, "A")])
    acc = ROIWindowAccumulator()
    summary = _drive(acc, source, flush_at=4.0)

    ok = (
        summary["dwell"] == {"A": 4.0}
        and summary["coverage"]["assigned_fraction"] == 1.0
        and summary["switching"]["count"] == 0
        and summary["persistence"]["A"]["n_runs"] == 1
        and summary["persistence"]["A"]["runs"][0]["duration"] == 4.0
        and summary["persistence"]["A"]["runs"][0]["left_censored"] is True
        and summary["persistence"]["A"]["runs"][0]["right_censored"] is True
    )
    return ok, {"dwell": summary["dwell"], "coverage": summary["coverage"], "switching": summary["switching"]}


def check_rapid_alternation():
    """Alternating A/B every second -- stresses switching + persistence.
    5 samples (A,B,A,B,A), 4 inter-sample intervals of 1s each, plus a
    final 1s tail on the last sample -> A: intervals at [0,1),[2,3),[4,5)
    = 3s; B: intervals at [1,2),[3,4) = 2s. 4 switches (A->B->A->B->A).
    5 separate one-length runs (no two consecutive samples share a
    roi_id), first run left-censored, last run right-censored."""
    source = synthetic_roi_source([
        (0.0, "A"), (1.0, "B"), (2.0, "A"), (3.0, "B"), (4.0, "A"),
    ])
    acc = ROIWindowAccumulator()
    summary = _drive(acc, source, flush_at=5.0)

    ok = (
        summary["dwell"] == {"A": 3.0, "B": 2.0}
        and summary["switching"]["count"] == 4
        and summary["persistence"]["A"]["n_runs"] == 3
        and summary["persistence"]["B"]["n_runs"] == 2
        and summary["persistence"]["A"]["runs"][0]["left_censored"] is True
        and summary["persistence"]["A"]["runs"][-1]["right_censored"] is True
        and summary["coverage"]["assigned_fraction"] == 1.0
    )
    return ok, {"dwell": summary["dwell"], "switching": summary["switching"], "n_runs_A": summary["persistence"]["A"]["n_runs"]}


def check_window_with_gaps():
    """A, then an explicit unassigned gap, then A again, then B.
    Verifies: (1) dwell excludes gap time entirely, (2) coverage < 1.0,
    (3) switching counts A->B as ONE switch even though a gap sits
    between the two A samples and the B sample (documented [A,None,A]=0,
    [A,None,B]=1 semantics -- exercised here as A,None,A,None,B)."""
    source = synthetic_roi_source([
        (0.0, "A"), (1.0, None), (2.0, "A"), (3.0, None), (4.0, "B"),
    ])
    acc = ROIWindowAccumulator()
    summary = _drive(acc, source, flush_at=5.0)

    # intervals: [0,1)=A, [1,2)=None, [2,3)=A, [3,4)=None, [4,5)=B
    ok = (
        summary["dwell"] == {"A": 2.0, "B": 1.0}
        and summary["coverage"]["assigned_duration"] == 3.0
        and summary["coverage"]["assigned_fraction"] == 3.0 / 5.0
        and summary["switching"]["count"] == 1  # A -> A (no-op) -> B: one real switch
        and summary["persistence"]["A"]["n_runs"] == 2  # gap breaks the run into two
        and summary["persistence"]["B"]["n_runs"] == 1
    )
    return ok, {"dwell": summary["dwell"], "coverage": summary["coverage"], "switching": summary["switching"]}


def check_window_with_no_assignments_all_none():
    """Samples arrive, but every one is roi_id=None -- the stream is
    reporting, it just never assigns anything. Expect: empty dwell,
    empty persistence, zero coverage (not None -- window_duration > 0
    and assigned_duration == 0 are both known facts here)."""
    source = synthetic_roi_source([(0.0, None), (1.0, None), (2.0, None)])
    acc = ROIWindowAccumulator()
    summary = _drive(acc, source, flush_at=3.0)

    ok = (
        summary["dwell"] == {}
        and summary["persistence"] == {}
        and summary["coverage"]["assigned_fraction"] == 0.0
        and summary["switching"]["count"] == 0
        and summary["n_samples"] == 3
    )
    return ok, {"dwell": summary["dwell"], "coverage": summary["coverage"], "n_samples": summary["n_samples"]}


def check_window_with_no_assignments_never_started():
    """The other reading of 'no assignments at all': add_sample() is
    NEVER called this window. should_flush() must stay False (same
    guard WindowAccumulator/AttentionWindowAccumulator already use), and
    a forced flush() with window_start=None must not divide by zero or
    fabricate a coverage number -- it must report coverage as None,
    distinctly from the all-None-samples case above (0.0)."""
    acc = ROIWindowAccumulator()
    never_flushes = not acc.should_flush(now=100.0)
    summary = acc.flush(now=100.0)  # forced anyway, to check it doesn't crash or lie
    ok = (
        never_flushes
        and summary["n_samples"] == 0
        and summary["dwell"] == {}
        and summary["coverage"]["assigned_fraction"] is None
    )
    return ok, {"never_flushes": never_flushes, "coverage": summary["coverage"]}


def check_single_assignment_spanning_whole_window():
    """Exactly one sample for the entire window. Its interval must
    extend all the way to flush time, and the resulting single run must
    be marked BOTH left- and right-censored (this window genuinely
    cannot see before its own start or after its own end)."""
    source = synthetic_roi_source([(0.0, "A")])
    acc = ROIWindowAccumulator()
    summary = _drive(acc, source, flush_at=10.0)

    run = summary["persistence"]["A"]["runs"][0]
    ok = (
        summary["dwell"] == {"A": 10.0}
        and summary["coverage"]["assigned_fraction"] == 1.0
        and summary["switching"]["count"] == 0
        and run["duration"] == 10.0
        and run["left_censored"] is True
        and run["right_censored"] is True
    )
    return ok, {"dwell": summary["dwell"], "run": run}


def check_run_crossing_a_window_boundary():
    """A single continuous roi_id=A assignment that in reality spans two
    consecutive windows. Drives ONE accumulator instance through two
    flush() calls (the same reuse pattern a real processing loop would
    use) and confirms the boundary-crossing behaviour this task's own
    docstring commits to: NO state carries across flush() (tumbling,
    same as WindowAccumulator/AttentionWindowAccumulator); the A run in
    window 1 is right-censored (still open at flush); the A run in
    window 2 is left-censored (open at window start) -- together they
    are the two honestly-partial halves of what was really one
    continuous assignment, never silently reported as a single 20s run
    or silently dropped at the boundary."""
    acc = ROIWindowAccumulator()

    # Window 1: A starts at t=0, still ongoing when window 1 flushes at t=10.
    window1 = _drive(acc, synthetic_roi_source([(0.0, "A"), (3.0, "A")]), flush_at=10.0)
    run1 = window1["persistence"]["A"]["runs"][-1]

    # Window 2 (same accumulator, reused after flush -- state was reset):
    # A continues, then switches to B partway through.
    window2 = _drive(acc, synthetic_roi_source([(10.0, "A"), (15.0, "B")]), flush_at=20.0)
    run2_a = [r for r in window2["persistence"]["A"]["runs"]][0]
    run2_b = [r for r in window2["persistence"]["B"]["runs"]][0]

    ok = (
        window1["dwell"] == {"A": 10.0}
        and run1["right_censored"] is True
        and run1["left_censored"] is True  # A was also the window's very first sample
        and window2["dwell"] == {"A": 5.0, "B": 5.0}
        and run2_a["left_censored"] is True    # window 2 cannot see A's true start
        and run2_a["right_censored"] is False  # but DOES see A end (switch to B) -- known
        and run2_b["left_censored"] is False   # B's start is a known, observed transition
        and run2_b["right_censored"] is True   # B is still open when window 2 flushes
    )
    return ok, {
        "window1_dwell": window1["dwell"], "run1": run1,
        "window2_dwell": window2["dwell"], "run2_a": run2_a, "run2_b": run2_b,
    }


def check_switching_gap_semantics_directly():
    """Isolated correctness check for the documented switching rule,
    beyond what the gap-window scenario above already exercises:
    [A, None, A] -> 0 switches (same ROI resumed after a gap, not a
    switch); [A, None, B] -> 1 switch (a real change, counted even
    though nothing was reported during the gap itself)."""
    same_after_gap = synthetic_roi_source([(0.0, "A"), (1.0, None), (2.0, "A")])
    diff_after_gap = synthetic_roi_source([(0.0, "A"), (1.0, None), (2.0, "B")])

    s1 = _drive(ROIWindowAccumulator(), same_after_gap, flush_at=3.0)
    s2 = _drive(ROIWindowAccumulator(), diff_after_gap, flush_at=3.0)

    ok = s1["switching"]["count"] == 0 and s2["switching"]["count"] == 1
    return ok, {"same_after_gap_switches": s1["switching"]["count"], "diff_after_gap_switches": s2["switching"]["count"]}


def check_summary_is_json_serializable():
    """These summaries are meant to be logged (JSONL, same as every
    other window_summary/attention_window_summary record in this
    codebase) -- confirm json.dumps never trips on a numpy scalar or
    other non-native type, same discipline WindowAccumulator/
    AttentionWindowAccumulator already apply via explicit float(...)
    casts."""
    source = synthetic_roi_source([(0.0, "A"), (1.0, "B"), (2.0, "A"), (3.0, None)])
    summary = _drive(ROIWindowAccumulator(), source, flush_at=4.0)
    try:
        json.dumps(summary)
        ok = True
        detail = "json.dumps succeeded"
    except TypeError as e:
        ok = False
        detail = f"json.dumps failed: {e}"
    return ok, detail


def run_all():
    checks = [
        ("CLEAN SINGLE-REGION WINDOW", check_clean_single_region_window),
        ("RAPID ALTERNATION", check_rapid_alternation),
        ("WINDOW WITH GAPS", check_window_with_gaps),
        ("NO ASSIGNMENTS AT ALL (samples present, all None)", check_window_with_no_assignments_all_none),
        ("NO ASSIGNMENTS AT ALL (add_sample never called)", check_window_with_no_assignments_never_started),
        ("SINGLE ASSIGNMENT SPANNING WHOLE WINDOW", check_single_assignment_spanning_whole_window),
        ("RUN CROSSING A WINDOW BOUNDARY", check_run_crossing_a_window_boundary),
        ("SWITCHING GAP SEMANTICS ([A,None,A]=0, [A,None,B]=1)", check_switching_gap_semantics_directly),
        ("SUMMARY IS JSON-SERIALIZABLE", check_summary_is_json_serializable),
    ]

    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"ROI AGGREGATION VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("ROI AGGREGATION VALIDATION: PASS")


if __name__ == "__main__":
    run_all()
