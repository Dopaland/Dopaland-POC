# Claude Code prompt — per-frame aperture export, and the ambiguity field

> Paste everything below the rule.

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

Your own pre-flight established that the blink positive control cannot be run as designed: there
is no route from an archived video file to a per-frame aperture stream. `analyze_video.py`
computes `es_components["aperture"]` on every frame and discards it, keeping only the
10-second-averaged `v_es` composite — and a 10-second average cannot recover 200–500 ms blink
events even in principle.

Two changes close that. Both are small. **Do not build anything else.**

---

## Change 1 — stop discarding the per-frame aperture

In `analyze_video.py`, retain the per-frame `(timestamp, aperture)` pair that is already being
computed, and write it out as its own stream.

**This is a retention change, not a computation change.** You are not computing anything new,
not changing any existing output, and not touching how `v_es` is composed. If you find yourself
altering a formula, stop — you have misread the task.

Requirements:

- Output format must be directly consumable by `run_detector_on_aperture_stream` — the same
  `(timestamp_seconds, aperture_or_None)` shape `stage3_demo_ui.py`'s experimental log already
  produces. Match that existing schema rather than inventing a second one.
- `None` on no-detect frames, preserved as `None`. **Do not interpolate, do not forward-fill,
  do not drop the row.** A missing frame is information (G3), and the detector's own handling of
  gaps is part of what this control tests.
- Timestamps relative to the start of the video file, in seconds.
- Works in **both Mode A and Mode B**. Mode B output stays stamped `validated:false` throughout,
  as everything in that mode is.
- Written alongside the existing analysis outputs. Do not replace or restructure any of them.

## Change 2 — an ambiguity field in the manual count template

`write_manual_count_template` / `load_manual_count` define a CSV of `blink_timestamp_seconds`
values. The frozen counting rule requires ambiguous cases to be logged separately and **counted
as neither** blinks nor non-blinks — and there is nowhere to put them.

Add that, minimally. A second optional column flagging a row as ambiguous, or a separate
`# ambiguous_timestamp_seconds` block — your call, but keep it hand-fillable in a text editor
without tooling, which is the point of the current format.

**Ambiguous entries must never enter the blink count** in either direction. `load_manual_count`
returns them separately so the count of ambiguities can be reported alongside the result.

---

## Constraints

- **G5:** `features/x_core.py`, `features/episodes.py`, `features/geometry.py` and the two-thread
  capture architecture are untouched. `analyze_video.py` is not on that list, but the change
  above is still additive only.
- **G1:** no threshold, no pass/fail, no verdict anywhere. The blink criterion is frozen and
  signed; code still does not apply it.
- **G4:** the aperture stream is numeric — timestamps and floats. No frames, no images.
- The **golden snapshot must not change.** This alters no computed value, so if it moves, stop
  and report — you changed something you should not have.

## Tests

- The aperture stream round-trips into `run_detector_on_aperture_stream` without reshaping.
- `None` frames survive as `None` through write and read.
- Mode A and Mode B both produce the stream; Mode B stays `validated:false`.
- Ambiguous manual entries load separately and are excluded from the count.

## Verification

1. Golden snapshot `f7fa0575fba2959b9c21e88314e2fef645e8aa66fe11443102288db9dc1792b8` — unchanged.
2. `tests/test_feature_separation.py` — all checks pass.
3. Full test suite passing.
4. `git status` — no media, audio, `.env` or credential (G4).
5. **Demonstrate the end-to-end route works**: any short video file → analysis → aperture stream
   → `run_detector_on_aperture_stream` → detected onsets. It does not matter whether the onsets
   are correct; what matters is that the path exists and runs. Report the command used.

**Do not commit.** Report what you changed, the tests, the end-to-end demonstration, and anything
you could not do — plainly, without substituting an approach.
