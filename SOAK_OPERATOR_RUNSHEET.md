# Extended Stability Soak — Operator Runsheet

**You run this, not an agent.** The previous two attempts self-terminated at ~90s because
`cv2.getWindowProperty(...)`-based shutdown logic false-triggers under a backgrounded launch
context. That is **not a defect and must not be "fixed"** — it sits on the validated demo path
(G5). The fix is the launch context: a real interactive terminal on the machine.

**What this closes:** correction #1. The claim was "multi-hour stability"; the evidence is a
41-minute POC-era soak. This run either makes the word literal or it doesn't.

**What this is NOT:** a behavioural test. With a static face in frame it is a **load and leak
test**. Do not let that distinction blur in any later document.

---

## Before you start

**1. Freeze the acceptance rule first.** Fill in the date and your name on
`SOAK_ACCEPTANCE_RULE.md` and save it **outside the repo**, alongside
`GATE2_SCORING_RULE.md` and `ORIENTATION_SCORING_RULE.md`. G1: the rule is set before
collection and applied by a human after it. **If you have not done this, stop here.** A soak
scored against criteria chosen afterwards proves nothing, and is exactly the contamination
Pitfall #2's scoring corollary exists to prevent.

**2. Commit the working tree.** Seven tasks are uncommitted. A soak result that cannot be
attributed to a specific tree state is a number without provenance. Commit first, then record
the hash on the result sheet.

**3. Disable sleep, display sleep and the screensaver.** If the display sleeps, the HighGUI
window can be destroyed and you get the same false trigger — at hour two, which is the most
expensive possible way to learn this.

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
```

Note your prior values first so you can restore them afterwards.

**4. Machine state.**

- On **AC power**, not battery. Power-profile throttling will otherwise show up as FPS drift
  and you will not be able to tell it apart from a real regression.
- Close anything competing for CPU. This is a no-GPU Windows laptop; thermal throttling is a
  genuine confound and worth noting ambient conditions for.
- Confirm no other application holds camera index 0.
- Confirm free disk space for ~180 checkpoint records plus normal session logging.

**5. Set the scene.** An empty scene is not a representative load — no detection work happens.
Place a **printed photograph or a second screen showing a face** in the camera's view, framed
as a subject would be. This gives sustained detection load without three hours of human time.

---

## Launch

Open a **real PowerShell or `cmd` window directly on the machine** — not a backgrounded tool
call, not a remote-driven shell, not an IDE terminal that may be managed by a parent process.

```
cd C:\Dopaland-POC
python stage3_demo_ui.py --soak
```

Leave the window **visible and unminimised**. Do not lock the screen.

**Record the wall-clock start time.**

---

## During the run

**Target: 180 minutes.** The smallest duration that makes "multi-hour" literally true.

Do not touch the machine. Do not run other heavy jobs. If you want to check progress mid-run,
**read the log file** — do not interact with the window, and do not click into it.

---

## After the run

1. Stop it normally. **Record the end time, and whether it ended because you stopped it or
   ended on its own.** Those are different results.
2. The run appends `soak_checkpoint` records every 60 seconds to `logs/`, carrying
   `elapsed_s`, `frames_total`, `fps_median_60s`, `rss_mb`, `detect_rate_60s`.
3. Restore your power settings.
4. **Apply the frozen rule by hand**, reading it from the copy you saved before the run. The
   script logged numbers; it did not score itself, and it must not.

---

## If it self-terminates early again

**Record the elapsed time and stop.** Do not modify the shutdown logic to make the test pass —
that is G2's failure mode wearing a different hat, and it would put a change on the validated
demo path for the convenience of a test harness.

An early clean exit from an interactive launch would be a **new finding**, not a repeat of the
known one, and worth reporting as such.

---

## What to record when you're done

Keep it short, and keep it beside the acceptance rule rather than only in the repo:

- Commit hash of the tree that ran
- Start time, end time, actual duration, and how it ended
- Scene type (printed photo / second screen / other) — and the load-not-behavioural label
- AC power confirmed; anything notable about ambient temperature or competing load
- Date and signature on the acceptance rule copy used
- The five checkpoint series, summarised against each criterion
- **The verdict you applied, and by which criterion** — including PASS, FAIL, or
  INCONCLUSIVE. A soak that degrades is a real result about this system, not a failed test.

**G4:** no video, no images, no raw media are written by this run. Confirm `git status` is
clean of media before committing anything afterwards.
