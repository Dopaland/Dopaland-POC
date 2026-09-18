# A/V Sync — attempt 8, and the last one

The diagnostic run (session `0e6b2a1a`) settled two things: **the emitter is not at fault**
(all 20 emissions physically confirmed), and **a large, cleanly detectable step does occur** on
this hardware in this room — in about half the emissions, by 8–24× the threshold gap.

So the failure is neither emitter nor physics nor threshold. It is **intermittent
registration**, and the diagnostic data points at three mechanical fixes.

**Stopping condition, declared before the run:** if this attempt does not produce **≥ 20
matched events**, stop and record A/V synchronisation as a documented omission under the
client's §21. Do not run a ninth.

**Three parts.** Part A the agent builds, Part B you run, Part C the agent parses.

---

# PART A — Three changes to the stimulus and the reference (paste now)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

Session `0e6b2a1a` (the `--diagnose` run) established:

- All 20 emissions physically occurred — `window_visible_flag: 1.0` and an
  `audio_first_callback_ts` present for every one. **The emitter is ruled out.**
- Video luminance response is **bimodal**: 8 of 19 emissions show almost no step
  (0.03–0.7× the threshold gap), 9 show 8–24×. No single `k` separates those populations.
- Audio misses correlate with an elevated ambient baseline and MAD at that moment.
- Flash render completes **69–159 ms** after the scheduled timestamp; the audio output
  callback fires **61–91 ms** after it.

Make these three changes. **Do not change `k_v` or `k_a`, and do not touch either detector's
logic** (G2) — the detectors are not what this run is testing.

## Change 1 — lengthen the flash

The flash is currently ~3 frames. Against a ~33 ms camera exposure period, whether the flash
lands inside a captured exposure is close to a coin flip — which is the most plausible
mechanical explanation for the bimodality above.

**Make the flash ~500 ms**, held white, then cleared. Put the duration in the versioned
configuration, not hardcoded.

**Onset precision is unaffected by this.** The measurement is the *first* frame crossing
threshold; a longer flash only guarantees the crossing happens. Say so in a comment so nobody
later "optimises" it back down.

## Change 2 — lengthen and raise the click

Same reasoning on the audio side: misses track a raised ambient noise floor, so a brief quiet
click has margin only when the room happens to be quiet.

**Lengthen the click and raise its amplitude**, both in the versioned configuration. Keep it a
sharp-onset sound — the onset is what is measured, so do not replace it with something that
ramps up gradually.

## Change 3 — pair against confirmed emission timestamps, not scheduled ones

This is the substantive one.

Pairing currently uses the **scheduled** emission timestamp as the reference. The diagnostic
shows flash render lags scheduling by 69–159 ms and the audio callback by 61–91 ms — so up to
~100 ms of pure **emitter jitter** is currently inside every computed offset, against a 33 ms
resolution floor.

**Use the confirmed timestamps as the reference**: video onset relative to
`flash_render_completed_ts`, audio onset relative to `audio_first_callback_ts`. The measured
offset then reflects capture and detection latency only, which is what the measurement is
actually for.

This requires the confirmation timestamps in ordinary runs, not only under `--diagnose`.
Promote that emitter confirmation to the normal path. Keep `--diagnose`'s extra trace logging
as it is.

**Record this change explicitly in the run output** — any offset from this run is measured
against a different reference than sessions `04d5cb0f` and `0e6b2a1a`, and must never be
compared with them as though it were the same quantity.

## On the pairing window — do not change it

An earlier reading suggested widening the ±500 ms window, citing the last run's 512 ms offset
IQR. **That IQR came from 3 matched events and establishes nothing.** Leave the window at
±500 ms. With Change 3 removing emitter jitter, the offset should tighten rather than spread;
if events still fall outside the window after that, *then* there is real evidence to act on.

## Constraints

- **G1:** no threshold, pass/fail or verdict anywhere. Computes and stores.
- **G2:** `k_v`, `k_a` and both detectors unchanged.
- **G4:** scalars and timestamps only — no frames, no audio samples.
- New config values are versioned and hashed like the rest. **Note in your report that
  `config_hash` will change**, which is correct and expected — this is a different stimulus.
- Tests for the new durations and the new pairing reference, against synthetic input.

Report what you built, the tests, the new `config_hash`, and anything you could not do.
**Do not commit.**

---

# PART B — Run it (you)

Lights off, laptop facing the wall, speakers unmuted, real interactive terminal.

```
cd C:\Dopaland-POC
python av_sync_flash.py --diagnose --subject-id P01
```

Keep `--diagnose` on — if this attempt fails too, the traces are what make the omission write-up
honest rather than a shrug.

**Run it long enough for ≥ 25 emissions** so 20 matched events is achievable with some misses.
At ~30 s spacing that is roughly 13 minutes.

Quiet room matters more this time than last: the audio misses tracked ambient noise directly.

---

# PART C — Parse (paste after)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`.
G1–G5 bind this task.

Attempt 8 has been run, with a lengthened flash, a lengthened and louder click, and pairing
against confirmed emission timestamps rather than scheduled ones.

Report:

1. **Matched event count.** The pre-declared stopping condition is **≥ 20**.
2. **Did the bimodality resolve?** Give the distribution of video excess-over-baseline ratios
   as before. If the population that showed almost no step has gone, say so; if it persists,
   say that too — that would mean the flash duration was not the mechanism.
3. **Audio the same**, and whether misses still track an elevated baseline.
4. **If ≥ 20 matched:** median offset, IQR, MAD, Theil–Sen drift, and the **33 ms frame-period
   floor stated alongside the spread**. State explicitly that this offset is measured against
   confirmed emission timestamps and is **not comparable** to sessions `04d5cb0f` or
   `0e6b2a1a`.
5. **Every unpaired emission with its reason.** None dropped.

**Do not retune anything** regardless of outcome (G2).

## If fewer than 20 matched

The stopping condition fires. Do not propose a ninth attempt. Instead draft — as a proposal for
human review, not an edit — the text recording A/V synchronisation as a **documented omission**
for CC-001 §6(a) and CC-001-A, covering:

- Eight attempts across four sessions; the stimulus changed twice (clap → flash → long flash).
- The emitter is confirmed working; registration is intermittent for reasons identified but not
  resolved.
- What that means concretely: **Δ_audio cannot be computed**, and §10.9's condition is not
  lifted by the acquisition build alone.
- That this is offered under the client's §21 request for infeasibility to be stated rather
  than implemented, and is a legitimate result rather than a failure.

**Do not commit. Do not edit CC-001.**
