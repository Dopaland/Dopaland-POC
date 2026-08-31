"""
D0PA1 Gate 0, A5 -- variant log writer.

logs/variant_log.jsonl is the one place a change in method, a tried-and-
abandoned approach, or a deliberate deviation from a documented default gets
recorded, with why (CLAUDE.md "WHAT D0PA1 ADDS": "variant log"). This module
is the SINGLE writer this repository uses for that file.

APPEND-ONLY BY CONSTRUCTION, not by convention: append_variant_log_entry
below is the only function in this repository (confirmed by search -- grep
for `variant_log` across every .py file finds only this module and its
test) that touches VARIANT_LOG_PATH, and it opens the file in "a" (append)
mode exclusively. There is no "w"/"w+"/truncate code path anywhere that can
reach this file. A test that actually calls it twice and checks the file
only grows (tests/test_variant_log.py) backs this up -- "append-only" is
demonstrated, not just asserted in a docstring.
"""

import json
import os
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANT_LOG_PATH = os.path.join(REPO_ROOT, "logs", "variant_log.jsonl")

SCHEMA_VERSION = "1.0"


def append_variant_log_entry(description, what_was_tried, why, retrospective=False, event_ts_utc=None, extra=None, path=None):
    """Appends exactly one JSON line to VARIANT_LOG_PATH. Never truncates,
    never rewrites an existing line.

    description / what_was_tried / why: free text -- this is the schema's
    whole point (CLAUDE.md: "timestamp, description, what was tried, and
    why"), deliberately not a fixed enum, so it can carry any future
    variant without a schema migration.

    retrospective: True for any entry describing work that happened BEFORE
    this call runs (the honest-framing discipline CLAUDE.md applies
    everywhere else, applied here too -- an entry with no such marker
    would misrepresent WHEN it was actually recorded, not just what it
    describes). When True, event_ts_utc should be supplied (the best-
    known real time the work happened, e.g. a commit timestamp); ts_utc
    always records when THIS call actually ran, so the two are never
    conflated.

    extra: optional dict of additional fields (e.g. a commit hash range)
    merged into the entry -- kept separate from the required fields above
    so a caller can't accidentally overwrite them by name collision
    (extra is applied first, required fields always win).

    path: override VARIANT_LOG_PATH -- exists ONLY so tests can point this
    at a throwaway file instead of the real log (tests/test_variant_log.py);
    every real caller should omit it and let the real log get written.
    """
    target_path = path or VARIANT_LOG_PATH
    entry = {}
    if extra:
        entry.update(extra)
    entry.update({
        "schema_version": SCHEMA_VERSION,
        "record_type": "variant_log_entry",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "retrospective": retrospective,
        "event_ts_utc": event_ts_utc,
        "description": description,
        "what_was_tried": what_was_tried,
        "why": why,
    })
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
