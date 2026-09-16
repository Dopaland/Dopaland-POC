# A/V Sync Measurement — Operator Runsheet

**This is a measurement, not a test.** There is no pass/fail and no acceptance rule to freeze.
The deliverable is a number with its uncertainty — or an honest statement that it failed again.
That is why this runsheet is one page and the soak's was not.

**What it closes:** one of exactly two NOT TRACEABLE items. It is also what unblocks Δ_audio
and §10.9, which CC-001 depends on.

**Prior attempts:** five, across two sessions. Audio-side detection worked every time; video-side
motion detection never produced a trustworthy match. The stimulus has changed — a light flash
instead of clap motion — not the rigour.

---

## Setup

1. **Camera pointed at a static scene** illuminated by the laptop display — a wall, a sheet of
   paper, anything that will brighten visibly when the screen flashes white. No face needed;
   this measures the two streams, not detection.
2. **Room lighting low enough that the flash produces a clear luminance step.** Bright ambient
   light is the one thing that can defeat a global-luminance detector.
3. **Speakers on**, at a normal level. Mic unobstructed.
4. **Quiet room.** No talking, no music, nothing moving in frame for the whole run.
5. AC power, competing CPU load closed.

## Run

```
cd C:\Dopaland-POC
python av_sync_flash.py
```

A real interactive terminal, same as the soak. ≥ 10 minutes, ≥ 20 flash events, roughly one
every 30 seconds.

**Leave the room or sit still and silent.** Movement in frame doesn't break this the way it
broke the clap method, but a quiet static scene is what the detectors were built against.

**Photosensitivity note:** one flash per ~30 seconds, well outside the 3–60 Hz range. If anyone
in the room is photosensitive, don't run it with them present.

## After

The script writes per-event records and a run summary to `logs/`. It computes and stores; it
reaches no verdict (G1).

**What a usable result looks like:**

- A median offset, with IQR and MAD across **≥ 20 matched events**
- A Theil–Sen drift slope across the run
- The frame-period quantisation floor (~33 ms at 30 FPS) stated **alongside** the spread

**The floor is the part that matters.** Video onset resolution is bounded by the frame period,
so any spread below ~33 ms is not resolvable by this method and must not be reported as though
it were. That is precisely what made the earlier 40 / 281 / 828 ms figures untrustworthy — and
withholding them was the right call.

**If it fails again:** report that attempt six failed and why. A documented failure is a real
result here; a noisy number presented as a measurement is not. Attempt three is the template.

## Then

Record the figure — or the failure — against CC-001 §6(a) and CC-001-A, which is where the
outstanding condition lives.

**G4:** no audio and no video content is written to disk. Onsets, energies and timestamps only.
Confirm `git status` is clean of media afterwards.
