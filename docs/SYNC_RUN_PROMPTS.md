# A/V Sync Run — agent prompts either side of the run

**You launch the run yourself.** The script renders a full-screen flash and needs a real
display session, same constraint as the soak. The agent does the pre-flight before and the
parsing after.

---

# PART A — Pre-flight (paste now)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`, the
D0PA1 vendor project. G1–G5 bind this task.

`av_sync_flash.py` was built but has never been run against hardware. Five previous sync
attempts failed on the video side. **This is a pre-flight check only — do not run the
measurement itself; the operator does that in an interactive terminal.**

Check and report:

1. `av_sync_flash.py` imports cleanly and its dependencies are installed.
2. `tests/test_av_sync_flash.py` passes — all 11 tests.
3. **`K_v` and `K_a` live in the hashed configuration, not hardcoded in a detection function.**
   Print where they are read from and their current values.
4. **The video detector reads the raw frame, pre-CLAHE.** Confirm by reading the code path,
   not by trusting a comment. This is the single most likely repeat of the previous failures.
5. **No threshold, pass/fail, verdict or "acceptable sync" logic anywhere in the module** (G1).
6. **No disk-write path for audio or video content** (G4) — onsets, energies and timestamps only.
7. The emitter's schedule: confirm the interval and how many events a 10-minute run produces.

Report each as pass/fail with the evidence you actually checked. **Change nothing.** If
anything is wrong, say so and stop — do not fix it in this task.

---

# YOU RUN THIS

Lights off, laptop facing the wall, speakers unmuted. Real PowerShell or `cmd` on the machine.

**Smoke test first — 2 minutes.** Cheap insurance against a sixth failed 10-minute attempt:

```
cd C:\Dopaland-POC
python av_sync_flash.py
```

Let it emit two or three flashes, then stop it. Confirm the log shows events detected and
paired on both sides. If it does, run it properly: **≥ 10 minutes, ≥ 20 flashes**, then leave
it alone.

---

# PART B — Parse the log (paste after the run)

---

**Read `CLAUDE.md` in full before doing anything else.** You are in `C:\Dopaland-POC`.
G1–G5 bind this task.

The A/V sync measurement has been run. Parse the per-event records and run summary in `logs/`
and report:

- **Median offset** (video onset − audio onset)
- **Spread**: IQR and MAD across matched events
- **Drift**: Theil–Sen slope of per-event offset against elapsed time
- **Matched event count**, and **every unpaired emission with its missingness reason** —
  unpaired events are reported, never dropped
- **The frame-period quantisation floor** (~33 ms at 30 FPS), stated alongside the spread

**The floor is the part that decides whether this is usable.** Video onset resolution is
bounded by the frame period, so a spread below ~33 ms is not resolvable by this method and
must not be presented as though it were. That is exactly what made the earlier
40 / 281 / 828 ms figures untrustworthy.

**This is a measurement, not a test.** There is no pass/fail to apply and none exists (G1).
Report the numbers and their uncertainty.

**If the measurement failed again** — too few matched events, or a spread that the floor makes
meaningless — say attempt six failed and why. A documented failure is a real result here; a
noisy number presented as a measurement is not.

Then state, without editing any document yet, what this means for **CC-001 §6(a)** and
**CC-001-A**, which is where the outstanding condition lives.

**Do not commit.**
