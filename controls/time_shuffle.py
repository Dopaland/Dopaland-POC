"""
D0PA1 control -- TIME-SHUFFLE CONTROL. Matrix row 18 (missed when the
other controls were built).

Shuffles EPISODE ORDER -- never individual frames or trials -- and re-runs
the same with/without comparison controls/leakage.py runs. If ordered and
shuffled performance are comparable, temporal organisation is contributing
little to the with-signal model's apparent performance -- a direct check
on the behavioural-dynamics claim (that WHEN something happens, not just
THAT it happens, carries predictive value).

G1: this control computes and reports numbers. It decides nothing.

1.3 -- DIAGNOSTIC ONLY, NOT A PERMUTATION-TEST P-VALUE. CLAUDE.md's own
D0PA1 hard constraint #4 draws this line explicitly: "time-shift
(diagnostic only, never a p-value)" is listed separately from the
INFERENTIAL permutation procedure, which "must preserve temporal
dependence and has its own exchangeability unit, which need not match the
bootstrap unit." This module implements the FORMER only. It is not, and
must never be read as, the latter -- every function here that returns a
result stamps `"diagnostic_only": True, "not_a_permutation_test_pvalue": True`
directly on the output (not just in a docstring a reader could miss), and
`format_time_shuffle_table()` prints the same warning as a literal line
of the report, not a footnote.

REUSES, not reimplemented: simulation.precision.compute_delta and
bootstrap_ci_on_delta -- run once on the ORDERED records and once on a
SHUFFLED copy, exactly the same machinery controls/leakage.py's four
window variants already use. The negative control is therefore carried
automatically (compute_delta's own unconditional wiring, no flag to
disable) -- not re-implemented or re-verified with new code here.

1.5 -- built and tested against SYNTHETIC data from simulation/generator.py
only. This has NOT been run on real trials, because real trials do not
exist yet (the client's task harness that would produce them is under
separate acceptance review; D2 is BLOCKED per CLAUDE.md). Stated here and
in docs/CONTROLS.md, not implied to be closed.
"""

from dataclasses import asdict, dataclass
import hashlib
import json

import numpy as np

from simulation.precision import compute_delta, bootstrap_ci_on_delta, MACRO_F1_METRIC


@dataclass(frozen=True)
class TimeShuffleConfig:
    shuffle_seed: int = 0
    negative_control_seed: int = 0

    def config_hash(self):
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


# ============================================================
# 1.1 -- shuffle EPISODE ORDER, never trials/frames.
# ============================================================

def _group_episodes(records):
    """Returns [(original_episode_id, trial_list), ...] in the ORIGINAL
    chronological order (each episode's own minimum global_trial_idx),
    trial_list itself sorted by trial_idx_in_episode -- the exact,
    untouched trial-level content of that episode."""
    by_ep = {}
    for r in records:
        by_ep.setdefault(r["episode_id"], []).append(r)
    for ep in by_ep.values():
        ep.sort(key=lambda r: r["trial_idx_in_episode"])
    ordered_ids = sorted(by_ep.keys(), key=lambda eid: min(r["global_trial_idx"] for r in by_ep[eid]))
    return [(eid, by_ep[eid]) for eid in ordered_ids]


def _session_episode_counts(records):
    """[(session_idx, n_episodes_in_that_session), ...] in session order
    -- used to preserve the ORIGINAL session BOUNDARY SIZES under the
    shuffle (same total episode count per session slot); WHICH episode's
    content fills each slot is what gets randomized."""
    session_episodes = {}
    for r in records:
        session_episodes.setdefault(r["session_idx"], set()).add(r["episode_id"])
    ordered_sessions = sorted(session_episodes.keys())
    return [(s, len(session_episodes[s])) for s in ordered_sessions]


def shuffle_episode_order(records, rng):
    """Permutes the ORDER episodes occur in -- their own trial-level
    content (x_signal, class_label, z, missing) is NEVER touched, only
    the POSITION each episode's trials occupy in the stream. Episodes may
    move across the ORIGINAL session boundaries (session slot SIZES are
    preserved; WHICH episode fills a given slot is randomized) --
    deliberate: session dummy features (build_features' one-hot session
    encoding) are exactly the kind of temporal-organisation feature this
    control is meant to test, same as t_in_session.

    RECOMPUTED after the shuffle (position-dependent, not content-
    dependent): global_trial_idx, episode_id (new sequential ids so
    simulation.precision.chronological_split's `sorted(episode_ids)`
    reflects the SHUFFLED order, not the stale original one), session_idx,
    t_in_session, prev_class_label (a running value across the WHOLE
    shuffled stream, never reset per session -- matching
    simulation.generator.generate()'s own prev_class, which is
    initialized once before the session loop and never reset at a
    session boundary).

    NEVER touched: x_signal, missing, class_label, z,
    trial_idx_in_episode (recomputed but represents the same within-
    episode relative position, since trial_list is already sorted by it)."""
    grouped = _group_episodes(records)
    n_episodes = len(grouped)
    perm = rng.permutation(n_episodes)
    shuffled_grouped = [grouped[i] for i in perm]

    session_counts = _session_episode_counts(records)
    if sum(c for _, c in session_counts) != n_episodes:
        raise ValueError("episode count mismatch while partitioning into session-sized chunks -- input malformed")

    session_chunks = []
    cursor = 0
    for session_idx, n_eps in session_counts:
        session_chunks.append((session_idx, shuffled_grouped[cursor:cursor + n_eps]))
        cursor += n_eps

    out = []
    global_trial_idx = 0
    new_episode_id = 0
    running_prev_class = shuffled_grouped[0][1][0]["prev_class_label"]  # seed value, same spirit as generate()'s own arbitrary initial draw

    for session_idx, chunk in session_chunks:
        session_trials_total = sum(len(trial_list) for _, trial_list in chunk)
        trial_in_session = 0
        for _orig_episode_id, trial_list in chunk:
            for trial_idx_in_episode, orig_r in enumerate(trial_list):
                new_r = dict(orig_r)
                new_r["session_idx"] = session_idx
                new_r["episode_id"] = new_episode_id
                new_r["trial_idx_in_episode"] = trial_idx_in_episode
                new_r["global_trial_idx"] = global_trial_idx
                new_r["t_in_session"] = trial_in_session / max(1, session_trials_total - 1)
                new_r["prev_class_label"] = running_prev_class
                out.append(new_r)
                running_prev_class = orig_r["class_label"]
                trial_in_session += 1
                global_trial_idx += 1
            new_episode_id += 1
    return out


# ============================================================
# 1.2/1.4 -- the diagnostic itself: ordered vs shuffled, side by side,
# CI on the Delta difference, negative control carried automatically.
# ============================================================

def run_time_shuffle_diagnostic(
    trial_source, n_classes, n_sessions, config=None,
    resample_unit="episode", n_boot=1000, alpha=0.05,
    train_frac=0.6, val_frac=0.2, metric=MACRO_F1_METRIC, bootstrap_seed=0,
):
    """trial_source: zero-argument callable returning a trial-record list
    shaped like simulation.generator.generate()'s output -- same pluggable
    contract controls/leakage.py's run_leakage_diagnostics uses (1.5: only
    a synthetic implementation exists today; real trials do not exist).

    Runs compute_delta/bootstrap_ci_on_delta on the ORDERED records, then
    on shuffle_episode_order()'s output, using the IDENTICAL bootstrap
    seed for both (so the two bootstrap draws are directly comparable --
    same convention controls/leakage.py's four variants already use). The
    CI on the DIFFERENCE is built from the two conditions' own
    bootstrap_deltas arrays (already returned by bootstrap_ci_on_delta --
    no new resampling code), paired by replicate index."""
    if config is None:
        config = TimeShuffleConfig()

    base_records = trial_source()

    ordered_delta = compute_delta(
        base_records, n_classes, n_sessions, train_frac, val_frac, metric,
        negative_control_seed=config.negative_control_seed,
    )
    ordered_rng = np.random.default_rng(bootstrap_seed)
    ordered_ci = bootstrap_ci_on_delta(ordered_delta, resample_unit, n_boot, alpha, ordered_rng, metric, n_classes)

    shuffle_rng = np.random.default_rng(config.shuffle_seed)
    shuffled_records = shuffle_episode_order(base_records, shuffle_rng)
    shuffled_delta = compute_delta(
        shuffled_records, n_classes, n_sessions, train_frac, val_frac, metric,
        negative_control_seed=config.negative_control_seed,
    )
    shuffled_rng = np.random.default_rng(bootstrap_seed)  # SAME seed as ordered's bootstrap -- comparable draws
    shuffled_ci = bootstrap_ci_on_delta(shuffled_delta, resample_unit, n_boot, alpha, shuffled_rng, metric, n_classes)

    diff_bootstrap = ordered_ci["bootstrap_deltas"] - shuffled_ci["bootstrap_deltas"]
    diff_lo = float(np.percentile(diff_bootstrap, 100 * (alpha / 2)))
    diff_hi = float(np.percentile(diff_bootstrap, 100 * (1 - alpha / 2)))

    return {
        "diagnostic_only": True,
        "not_a_permutation_test_pvalue": True,
        "ordered": {
            "delta_point": ordered_delta.delta_point, "u_with": ordered_delta.u_with, "u_without": ordered_delta.u_without,
            "ci_lo": ordered_ci["ci_lo"], "ci_hi": ordered_ci["ci_hi"],
            "delta_negative_control": ordered_delta.delta_negative_control,
            "n_test_trials": ordered_delta.n_test_trials,
        },
        "shuffled": {
            "delta_point": shuffled_delta.delta_point, "u_with": shuffled_delta.u_with, "u_without": shuffled_delta.u_without,
            "ci_lo": shuffled_ci["ci_lo"], "ci_hi": shuffled_ci["ci_hi"],
            "delta_negative_control": shuffled_delta.delta_negative_control,
            "n_test_trials": shuffled_delta.n_test_trials,
        },
        "difference": {
            "delta_point_diff": ordered_delta.delta_point - shuffled_delta.delta_point,
            "ci_lo": diff_lo, "ci_hi": diff_hi,
            "ci_half_width": (diff_hi - diff_lo) / 2.0,
            "note": "CI on (ordered_delta - shuffled_delta), from the two conditions' independent bootstrap_deltas arrays paired by replicate index -- NOT a joint/paired bootstrap over the same resampled units (ordered and shuffled test splits contain different episode content by construction).",
        },
        "resample_unit": resample_unit,
        "n_boot": n_boot,
        "alpha": alpha,
        "metric": metric.name,
        "config_hash": config.config_hash(),
    }


def format_time_shuffle_table(result):
    """No verdict, no highlighting -- and the diagnostic-only warning is a
    literal PRINTED LINE of the report, not a footnote a reader could miss
    (1.3)."""
    lines = []
    lines.append("=" * 78)
    lines.append("DIAGNOSTIC ONLY -- NOT A PERMUTATION-TEST P-VALUE.")
    lines.append("The inferential permutation procedure has its own pre-specified")
    lines.append("exchangeability unit and is defined separately (CLAUDE.md D0PA1")
    lines.append("hard constraint #4). This is a diagnostic, not a hypothesis test.")
    lines.append("=" * 78)
    lines.append("")
    header = f"{'condition':10s} {'u_with':>10s} {'u_without':>10s} {'delta_point':>12s} {'ci_lo':>10s} {'ci_hi':>10s} {'delta_negctrl':>14s} {'n_test_trials':>13s}"
    lines.append(header)
    lines.append("-" * len(header))
    for cond in ("ordered", "shuffled"):
        r = result[cond]
        lines.append(
            f"{cond:10s} {r['u_with']:>10.4f} {r['u_without']:>10.4f} {r['delta_point']:>+12.4f} "
            f"{r['ci_lo']:>+10.4f} {r['ci_hi']:>+10.4f} {r['delta_negative_control']:>+14.4f} {r['n_test_trials']:>13d}"
        )
    diff = result["difference"]
    lines.append("")
    lines.append(f"DIFFERENCE (ordered - shuffled): delta_point_diff={diff['delta_point_diff']:+.4f}  CI=[{diff['ci_lo']:+.4f}, {diff['ci_hi']:+.4f}]")
    lines.append(f"config_hash={result['config_hash']}  metric={result['metric']}  n_boot={result['n_boot']}  alpha={result['alpha']}  resample_unit={result['resample_unit']}")
    return "\n".join(lines)
