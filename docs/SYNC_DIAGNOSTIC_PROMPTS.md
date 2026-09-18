# A/V Sync — diagnostic run (attempt 7 is not another blind attempt)

Six measurement attempts have produced no figure. This run does not try to measure the offset.
It answers **why the detectors miss**, by recording what the signals actually do around each
emission.

**Three parts.** Part A the agent builds, Part B you run, Part C the agent parses.

---

# PART A — Add a diagnostic mode (paste now)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

Six A/V sync attempts have failed. The last one (session `04d5cb0f`) logged 20 emissions on a
clean ~30 s cadence with only 2 matched events, 18 video misses, 13 audio misses — **including
nine consecutive emissions, idx 2–10, with nothing detected on either channel.**

That pattern exposes a gap in the instrument: **the log records that an emission was
*scheduled*, not that it physically happened.** A flash that never rendered and a flash that
rendered but wasn't detected are currently indistinguishable. Close that gap.

## Build: a `--diagnose` flag on `av_sync_flash.py`

**Use the existing emitter, the existing detectors and the existing config.** The point is to
diagnose the real instrument, so a separate reimplementation would be worthless. `--diagnose`
adds logging; it changes no detection logic and no defaults.

For each emission, record:

**1. Emission confirmation — the ambiguity to kill.**
- The scheduled emission timestamp (already logged).
- Evidence the **flash actually rendered**: the timestamp at which the draw/blit call
  completed, and any window visibility or focus state obtainable from the display layer.
- Evidence the **audio actually played**: confirmation the output callback consumed the
  buffer, with its timestamp.

**2. Signal traces, ±1 second around each emission.**
- Per-frame mean luminance (raw grayscale, **pre-CLAHE**) with frame timestamps.
- Per-hop audio short-time energy with timestamps.

**3. The threshold context at that moment — the most diagnostic numbers in the run.**
- The rolling baseline median and robust MAD for each channel.
- The computed threshold (`baseline + k × MAD`) for each.
- **The maximum value each signal actually reached in the window, and its ratio to the
  threshold.** A ratio near 1 means a tuning problem. A ratio near zero means no step exists.
  These two diagnoses have completely different consequences, and nothing in six attempts has
  distinguished them.
- Whether the onset fired.

## Hard constraints

- **Do not change `k_v` or `k_a`.** Do not change any default. Do not "improve" either
  detector. This run must observe the instrument as it currently stands, or it diagnoses
  nothing (G2).
- **G1:** no threshold, pass/fail or verdict. It records numbers.
- **G4:** luminance values, energy values and timestamps only. **No frames, no audio samples,
  no images** — a ±1 s trace of scalars is fine; a ±1 s buffer of content is not.
- Without `--diagnose`, behaviour is byte-identical to today.
- Add tests for the new logging path against synthetic input.

Report what you built, the tests, and anything you could not do. **Do not commit.**

---

# PART B — Run it (you)

Same setup as before — lights off, laptop facing the wall, speakers unmuted, real interactive
terminal.

```
cd C:\Dopaland-POC
python av_sync_flash.py --diagnose
```

**Five minutes, ~10 emissions is enough.** This is a diagnostic, not a measurement; you are
not trying to accumulate matched events.

If you can, **note roughly how far the laptop sits from the wall** — if the step turns out to
be small, distance is the first thing worth varying.

---

# PART C — Read the traces (paste after)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`.
G1–G5 bind this task.

Parse the diagnostic log and answer these, in order. **Report what the data shows; do not fix
anything.**

**1. Did every emission physically happen?** For each, did the flash render and the audio play?
If any emission was scheduled but not emitted, that alone explains the corresponding misses —
and would recast the idx 2–10 blackout in the previous session.

**2. For each emission where the flash did render: is there a luminance step at all?**
Report the maximum luminance reached, the baseline median and MAD, the threshold, and the
**ratio of max to threshold.** Give the distribution across emissions, not just an average.

**3. Same for audio energy.**

**4. Which of these three is it?**
- *Emitter* — emissions not physically occurring.
- *Threshold* — a real step exists but doesn't cross `k × MAD`. Say by what factor it falls
  short.
- *Physics* — no meaningful step exists in the captured signal at all.

Name the one the data supports. If the data supports more than one, say so rather than picking.

## What must not happen next

**Do not retune `k_v` or `k_a` in this task, and do not propose a value fitted to these
traces.** Tuning a threshold against the only data you have is the exact failure V_bf stands
as proof of (G2).

If the diagnostic shows a real step that falls short of the threshold, the legitimate path is:
a revised `k` justified from the observed signal structure, **frozen before** a fresh
measurement run, whose new data is the reported result. State the reasoning; propose nothing
as final.

## Then, one paragraph on CC-001

Say what this means for **CC-001 §6(a)** and **CC-001-A** — including, if the answer to (4) is
*physics*, that the honest outcome may be to record A/V synchronisation as **not measurable
with the available equipment**, under the client's own §21 request that infeasibility be stated
rather than implemented. That would be a legitimate result, not a failure — it would join the
other documented impossibilities and stop a seventh, eighth and ninth attempt.

**Do not commit. Do not edit CC-001.**
