# Audio Acquisition — Privacy Guard, Consent, Instrument, Sync Measurement

D0PA1 "AUDIO PART A" task. Authorisation: the client's keep-or-formally-remove
decision on `Δ_audio` (Decision A in `docs/preregistration/D0PA1_Section19_SignOff_Response.docx`)
has been made — **RETAINED**, acquisition authorised. This document is the
record of what that authorisation produced, in the order the task specified:
privacy guard first, then consent, then the acquisition instrument, then the
sync measurement (the actual point of Part A), then the separation guard,
then this document itself.

**Scope line, stated once and binding throughout:** this document and
everything it describes is ACQUISITION and SIGNAL INTEGRITY. No audio
FEATURE is defined or computed anywhere here — no prosody, no
arousal-from-voice, no emotion-from-speech, no valence, no stress. Those
remain the client's to sign off, exactly like every other new-signal
definition in this project (CLAUDE.md's `U_t` AUDIO section).

---

## 1. The privacy guard (Task 1)

### 1.1 What existed before this task

`.githooks/pre-commit` (wired via `git config core.hooksPath .githooks`)
already blocked media by extension (`MEDIA_EXTENSIONS`) AND by magic-byte
content sniffing (`MAGIC_SIGNATURES`), backed by `.gitignore`. Checked
directly before changing anything: audio coverage existed for `.wav .mp3
.m4a .aac .ogg .flac`, with magic-byte signatures for RIFF (WAV/AVI), ID3
(MP3), OggS (OGG), fLaC (FLAC). **No coverage existed for `.opus .wma .aiff
.aif .au .caf .amr .mka .3gp .3g2`, and no magic-byte signatures existed for
WMA/ASF, AIFF/AIFF-C, AU, CAF, or AMR** — confirmed by reading the hook
source directly, not assumed.

### 1.2 What was added

Both `MEDIA_EXTENSIONS` (`.githooks/pre-commit`) and `.gitignore` extended
with the ten missing extensions above. Five new magic-byte signatures added:
WMA/ASF (16-byte header GUID), AIFF, AIFF-C (form type inside a FORM chunk,
matched within the scanned head), AU/SND (`.snd` magic), CAF (`caff`
magic), AMR (`#!AMR` magic). `.3gp`/`.3g2` and `.mka` were already covered by
existing magic bytes (`ftyp`/EBML, shared with MP4/MOV and MKV/WEBM
respectively) — listed in `MEDIA_EXTENSIONS` anyway, belt-and-suspenders, so
the cheaper extension check also catches them.

**Wrong or missing extension**: the magic-byte check runs unconditionally,
never gated on the extension matching first — a file with no extension, or
a deliberately wrong one, is still caught by content alone. Verified
directly (§1.3).

### 1.3 Proof the guard fires

Two layers tested separately, since these extensions are ALSO gitignored —
a plain `git add` never reaches the hook at all for them (confirmed: `git
add` on the new extensions was silently skipped with `.gitignore` advice,
zero files staged). The hook itself was tested by force-staging past
`.gitignore` (`git add -f`):

- **All 8 new extensions**, real magic-byte payloads, real extensions
  (`.opus .wma .aiff .au .caf .amr .mka .3gp`) → commit attempt: **BLOCKED**,
  each flagged by extension (`media file extension (.<ext>)`).
- **Wrong extension**: real WAV (`RIFF`) content saved as `.txt` → **BLOCKED**
  by magic bytes alone (`media magic bytes detected (RIFF container
  (WAV/AVI))`).
- **No extension**: real WAV content, no extension → **BLOCKED** by magic
  bytes alone.
- **New magic-byte signatures tested standalone**: the same six payloads
  (WMA/ASF, AIFF, AIFF-C, AU, CAF, AMR) saved with a neutral `.dat`
  extension (not in `MEDIA_EXTENSIONS`) → **BLOCKED**, each by the new
  magic-byte signature alone, proving those signatures fire independently
  of the extension list.
- Every dummy file was deleted and staging reset (`git reset`) after each
  proof; `--no-verify` was never used anywhere in this task.

### 1.4 Where raw audio lives

**Checked directly before deciding anything: no raw-video storage location
has ever been decided in this repository either.** `privacy/retention.py`'s
own `storage_location` default is `logs/` INSIDE this checkout, explicitly
labelled a placeholder — `docs/PRIVACY_AND_RETENTION.md` states plainly that
"genuinely relocating it outside the repository is a separate, not-yet-made
decision." There is no existing "where raw video already goes" for audio to
be placed alongside — this is recorded here rather than silently assumed
(see the task's own final-report point 8).

Given that, and given audio's elevated identifiability (this task's own
framing), `privacy/audio_storage_config.py` goes one step stricter than
`retention.py`'s pattern: the storage location is **never a literal path in
any committed file** — `resolve_audio_storage_config()` reads
`D0PA1_AUDIO_RAW_STORAGE_LOCATION` from the environment and raises loudly if
unset, with no hardcoded fallback. Only `AudioStorageConfig.config_hash()`
(same short-SHA256-prefix pattern as `RetentionConfig`/`LeakageConfig`/every
other `*Config` class) is ever computed — the literal, resolved path is
never written into a committed file, only its hash. Verified by AST
(`tests/test_audio_storage_config.py`): no default value on the dataclass
field, no path-shaped string literal anywhere in the module's own source.

**Named as an open item, with a proposed (not decided) unified resolution
for both raw video and raw audio**: `docs/PRIVACY_AND_RETENTION.md`'s
"Named open item: raw media of BOTH kinds has no decided, documented home"
section.

---

## 2. Consent (Task 2)

`stage1_step7_consent.py` extended with a **separate, independent** audio
consent question, asked only after video consent is given (declining video
exits before the audio question is ever reached — unchanged from before this
task). `run_consent_gate()` now returns `(video_consented, audio_consented,
person_label)`; four existing call sites (`stage1_step4_vectors.py`,
`stage3_demo_ui.py`, `stage1_step9_gate2_capture.py`,
`orientation_capture.py`) were updated to unpack the new 3-tuple — a
mechanical plumbing fix necessitated by the signature change, touching only
the unpacking line in each file, not any capture/processing logic (G5).
Golden snapshot re-confirmed unchanged after this change.

**"Architecturally unreachable" verified, not just asserted**
(`tests/test_consent_audio_gate.py`, 7 checks):
- The consent module imports no audio library (`sounddevice`, `pyaudio`,
  `wave`, `audioop`, `soundfile`, `simpleaudio`, `portaudio` — checked by
  AST, not string search) — the same standard its pre-existing camera-free
  property meets, now machine-checked for the first time (no prior test
  file asserted the video property either).
- The consent module never imports `audio_acquisition` (the real capture
  module) at all.
- Declining audio logs `audio_consent: false` with an explicit
  `audio_consent_reason: "declined_by_participant"` — never a silently
  missing field (Task 2.3). Declining video logs nothing at all (unchanged
  pre-existing behaviour) and the audio question is never asked.

**The G5 ripple, checked directly this phase (the "ENVIRONMENT AUDIT, SYNC
MEASUREMENT, G5 RIPPLE CHECK" task's Task 3), not merely re-asserted:**
`git show` on the consent commit for all four touched files
(`stage1_step4_vectors.py`, `stage1_step9_gate2_capture.py`,
`orientation_capture.py`, `stage3_demo_ui.py`) shows an **identical
one-line change in every file** — the `run_consent_gate(...)` unpacking
line, plus an explanatory comment — with no other line touched. A repo-wide
search for `audio_consented` confirms it is bound and never read again
anywhere in any of the four files (dead, intentionally-unused plumbing, not
silently feeding into anything downstream). The `_log_consent` diff against
the original baseline import (`1854609`) shows the original five fields
(`event`, `session_id`, `person_label`, `ts_utc`, `ts_monotonic`) are
byte-identical, unmoved, unrenamed — the three new fields (`video_consent`,
`audio_consent`, `audio_consent_reason`) are purely additive.
`tests/test_consent_audio_gate.py` check 4 directly proves the video-decline
path is unchanged: `(False, None, None)`, zero records logged, the exact
pre-existing shape with the new tuple position appended. **Conclusion: the
line was drawn correctly — this was plumbing only, not a behavioural
change to any G5-protected capture/processing logic**, confirmed by direct
diff inspection this phase, not only by the discipline followed while
making the change.

**What was NOT retrofitted, stated plainly (G3):** the EXISTING video
capture loop's per-sample/window-summary record schema
(`stage1_step4_vectors.py`) does not carry an `audio_consent` field — adding
one would touch that file's capture/processing logic, which is G5-protected
and this task did not explicitly ask for it. Audio consent state IS recorded
on: the `consent_log.jsonl` `consent_given` record, and every
`audio_chunk_integrity` record this task's own new module writes (§3). A
future task can decide to wire it into the video sample schema explicitly,
if wanted.

---

## 3. Minimal acquisition (Task 3)

`audio_acquisition.py` (repo root — same placement pattern as
`orientation_capture.py`; `features/audio.py` remains the empty FEATURE
stub, untouched):

- **`AudioAcquisitionThread`** — opens the default input device via
  `sounddevice.InputStream` in callback mode. PortAudio delivers each chunk
  on its own internally-managed thread; nothing here shares a lock or
  buffer with T1/T2 (video capture/processing) — structurally decoupled the
  same way T1 and T2 are decoupled from each other (MANDATORY ARCHITECTURE
  #1), not merely "usually fast enough."
- **`AudioChunkLogger`** — one JSON record per chunk (or per missingness
  event) to `logs/audio_chunk_integrity.jsonl`, its own file, own record
  type (`audio_chunk_integrity`, schema `"1.0"`). `subject_id`/
  `context_id`/`device_id` are required constructor arguments — absent from
  the first record is a hard error, not a default. Every record carries:
  **two independently-sourced timestamps**, each named — `chunk_ts_perf_counter`
  (`time.perf_counter()`, this repository's existing monotonic-clock
  convention) and `chunk_ts_portaudio_adc` (PortAudio's own
  `inputBufferAdcTime`, hardware/driver-timestamped, the more accurate of
  the two for true capture time since it is not subject to Python callback
  scheduling jitter); sample rate, channel count, bit depth, actual
  delivered buffer size; a running dropout count (PortAudio's
  `input_overflow` flag — samples genuinely lost) and overrun count (any
  truthy callback status); and a level measure (`compute_level_stats` —
  peak absolute amplitude, RMS, a `clipping_detected` flag at 99.9% of
  full-scale, the same kind of quality-gate fact as this codebase's existing
  `detect_rate<0.5`/`yaw_variance>ceiling` flags, not a G1 verdict about the
  subject).
- **Missingness** (Task 3.2): its own small, fixed vocabulary —
  `device_unavailable` / `device_disconnected_mid_session` / `stream_error`
  / `buffer_overrun_data_lost` — deliberately NOT reused from
  `schema/canonical_log_v1.json`'s `missingness_reason` enum, whose existing
  values are all video/face-tracking-specific and none honestly describe an
  audio-stream gap (G3: a forced-fit mapping would be worse than an
  honestly-separate vocabulary). A gap is always a row with a reason, never
  an absent row — verified directly.
- **NO CONTENT ANALYSIS** (Task 3.3): `compute_level_stats` is amplitude
  only — peak/RMS/clipping. No transcription, no speech detection, no
  spectral features, nothing that could characterise WHAT was captured, and
  no code path in this module could produce one. Raw audio samples are
  **never written to disk by default** — `write_raw_path=None` is the
  default for every ordinary integrity-logging run; only Task 4's sync
  measurement ever supplies a real path, and `AudioAcquisitionThread.__init__`
  raises if that path resolves inside the repository (a second, independent
  safety net on top of §1's guard).

**A real bug found by testing against the actual device** (not caught by
synthetic-input unit tests alone): `sounddevice`'s `finished_callback`
fires on ANY stream stop, including a deliberate one. An earlier version of
`_on_finished()` logged `device_disconnected_mid_session` unconditionally
there, mislabeling every normal `stop()` call as an unexpected
disconnection. Fixed with an `_intentional_stop` flag set before
`stream.stop()` is called; `_on_finished()` only logs missingness when that
flag is NOT set. Verified against the real device (no spurious missingness
on a normal stop) and covered by two regression tests
(`tests/test_audio_acquisition.py`: intentional stop logs nothing;
an unrequested finish still logs correctly).

**12 pure-computation checks pass** (`tests/test_audio_acquisition.py`) plus
**2 regression checks for the bug above** — level stats (silence/moderate/
clipping/empty), config hashing, required-ID enforcement, complete chunk
records, missingness-never-absent, the fixed missingness vocabulary,
sequence numbering across mixed chunk/missing calls, and the
inside-repo/outside-repo write-path check.

### FPS-impact proof — what was actually measured, and what was not

**Camera use was declined for this session** (the user's explicit choice,
offered because this session's environment turned out to have real camera
AND microphone access — see §5's own note on this discovery). Given that,
the FPS-impact proof does **not** use the real webcam or real
FaceLandmarker/PoseLandmarker detection. It uses a synthetic two-thread
harness that reproduces the EXISTING architecture's TIMING SHAPE: a T1-
equivalent producer at a fixed 30 FPS target (single-slot buffer + lock,
same pattern as MANDATORY ARCHITECTURE #1), and a T2-equivalent consumer
that sleeps **120ms per processed frame** — CLAUDE.md's own real, previously-
measured Gate 1 figure ("Steady-state detection ~120ms/pass"), reused
exactly rather than an easier invented number, so the synthetic T2
reproduces the real pipeline's actual bottleneck duration. This is the same
disclosed-substitution precedent already in this repository's history (V_so's
real end-to-end FPS check used a recorded clip in place of a live webcam).
The AUDIO side is real: the actual `AudioAcquisitionThread`, real
`AudioChunkLogger`, real default microphone.

**Measured** (two independent 8-second runs, steady-state throughput window
only — device-negotiation latency measured and reported separately, not
folded into the fps figure):

| Metric | Before (no audio) | After (real audio thread + real mic) | Delta |
|---|---|---|---|
| T1 (capture-equivalent) fps, run 1 | 29.998 | 29.997 | −0.001 |
| T2 (processing-equivalent) fps, run 1 | 8.374 | 8.374 | −0.000 |
| T1 fps, run 2 | 29.998 | 29.998 | −0.001 |
| T2 fps, run 2 | 8.375 | 8.374 | −0.000 |

Audio device start-up latency (one-time, not an ongoing cost): ~0.24s both
runs. 9 real audio chunks logged per 8-second AFTER window (~1/s at the
1.0s chunk size used), all `missingness_flag: false`, real (very quiet)
room level (`peak_abs` ≈ 3.05e-05, `rms` ≈ 1.46e-05, `clipping_detected:
false`) — genuine captured evidence, not synthetic.

**Conclusion, stated at the precision this measurement actually supports:**
the audio acquisition thread has no measurable effect on either the
capture-equivalent or processing-equivalent throughput of the synthetic
two-thread harness (deltas within measurement noise, both directions, both
runs). This is evidence about THREAD CONTENTION under a timing-realistic
synthetic load, not a measurement of the real webcam pipeline's real FPS
with real detection — that specific number (whether real MediaPipe
detection alongside real audio capture holds ~30 FPS) was not measured this
session and should not be inferred from this table.

---

## 4. The sync measurement (Task 4) — NOT PERFORMED last phase; ATTEMPTED THIS PHASE, still no reliable figure

**"PHYSICAL RUN SESSION" task update.** The Task 0 gate (a 2-second
recording) found the microphone-content block from last phase gone: real,
varying signal (min −0.084, max 0.057, std 0.00247, 1362 distinct values).
Not explained, not investigated — recorded as a fact on the same machine,
one phase apart.

With that resolved, the clap-sync measurement was attempted live, 5 times,
entirely in-memory (confirmed after every attempt: no raw audio or video
sample ever written to disk). **The microphone side worked cleanly and
consistently every time** — real, clap-correlated transient onsets found
via a percentile-based threshold, in every one of the 5 attempts. **The
video side — simple frame-to-frame grayscale-difference motion
detection — did not.** Across 5 threshold adjustments it was either too
sensitive (general movement, not just claps, crossed the threshold: one
run found 19 video "events" against ~8 real claps, and the resulting
9-pair match had a 40ms mean / 281ms std / 828ms range — a spread almost
certainly dominated by false matches pairing a real clap's audio against
an unrelated nearby motion spike, not real sync jitter) or too strict
(0–3 video events, no usable matches).

**No offset, spread, or drift figure is reported.** The one run that DID
produce matched pairs is explicitly not trusted as a result — per Task
4.4's own instruction, a method whose match quality cannot be trusted
tells you nothing, and reporting that 40ms/281ms pair as if it were a
clean measurement would be exactly the kind of fabricated-looking number
this document exists to avoid. This is a genuinely different outcome from
both prior attempts: last phase, neither hardware nor audio content was
available at all; this phase, both were available and a human was
actively cooperating, but the specific visual-event-DETECTION method
chosen (frame-differencing against a mostly-static face-and-background
scene) was not specific enough to isolate individual clap events
reliably. A more visually distinctive event — a light flash rather than
hand-clap motion — would likely resolve this; not attempted this phase.

**Per Task 4.4's own instruction: stated plainly, not simulated, not
estimated from specifications.**

The clap-based sync measurement needs a single physical event (a hand clap)
visible to BOTH sensors simultaneously — the video frame of impact and the
audio transient onset, compared against each other. This session's user was
offered the choice to run it (camera + microphone together, briefly, raw
recordings outside the repo and deleted immediately after) and explicitly
declined the camera (chose "Audio only, skip camera"). Without a video
signal, there is no independent visual event to compare the audio timestamp
against — audio alone cannot supply half of a two-sensor measurement.

**No offset, no uncertainty, and no drift figure is reported, because none
was measured.** This is not the same claim as "sync is impossible" or "sync
is fine" — it is simply not yet measured. `docs/PROJECT_STATE.md`'s
outstanding-items list carries this forward explicitly (§4.2 of this task's
own instruction) as a physical-run item, alongside the other camera/operator-
dependent items already there (null-input control, blink clips).

**What the measurement would need, when it is run:** exactly what Task 4.1–
4.3 specified — repeated hand claps in view of both sensors, the video
frame of impact compared against the audio transient onset (via
`chunk_ts_portaudio_adc`, the more accurate of this module's two
timestamps, per §3 above), enough repetitions to report a distribution
(central value, spread, and whether it drifts over a session) rather than a
single number, reported in milliseconds with its own uncertainty, with no
comparison to any requirement (G1) — a human decides what the number means.
`audio_acquisition.py`'s `write_raw_path` mechanism (raises if the target
resolves inside the repository) is already built and ready for exactly this
use the day it is run.

---

## 5. Separation guard made real (Task 5)

`U_t` (`features/audio.py`) has been trivially compliant as an empty stub.
It is not empty now — `audio_acquisition.py` is real U_t content, at repo
root, outside `features/`.

**5.1 — `FORBIDDEN_EDGES` already covered every core destination for
`features/audio.py` before this task**: `("x_core","audio")`,
`("episodes","audio")` (pre-existing), and `("context","audio")` (added the
prior task, closing the same route-through-context gap found for
`attention`). Re-confirmed fail-then-pass this task (§below) rather than
assumed still-correct.

**A real gap WAS found, by audit, the same way the `context`→`attention`/
`audio` gap was found last task**: `audio_acquisition.py` is a repo-root
module that IS U_t content itself, not a module that imports
`features.audio` and re-exports it — check 4's existing shim-discovery logic
(`discover_cross_block_shims`) only flags a repo-root module as forbidden if
it IMPORTS `features.attention`/`features.audio`, and `audio_acquisition.py`
deliberately imports neither (it needs no feature-block content). This means
none of the four existing checks would have caught `x_core.py` or
`episodes.py` importing `audio_acquisition` directly — a real
`U_t -> X_core`/`U_t -> E_t` violation invisible to the existing machinery.

**Fixed**: `tests/test_feature_separation.py`'s check 4 now also tracks
`DIRECT_UT_MODULES = {"audio_acquisition"}` — repo-root modules that ARE U_t
content by definition, unioned into the same forbidden-target set as
discovered shims, with a distinct violation message ("a U_t (audio) module
in its own right, not merely a re-exporting shim").

**5.2 — proven fail-then-pass**:
- New guard: a temporary `import audio_acquisition` added to
  `features/x_core.py` → check 4 FAILED with `"features.x_core imports
  (transitively) 'audio_acquisition', a U_t (audio) module in its own
  right... path: features.x_core -> audio_acquisition"`. Reverted; suite
  returned to PASS.
- Pre-existing edge re-confirmed: a temporary `import features.audio` added
  to `features/episodes.py` → check 1 FAILED with `"episodes.py imports
  (transitively) audio.py -- path: episodes -> audio"`. Reverted; suite
  returned to PASS.

**5.3** — the full separation suite (all 4 checks) passes with every module
this task added in place. No file this task touched inside `features/`
(`x_core.py`, `episodes.py` were only touched by the two deliberate,
reverted proofs above) — nothing in Tasks 2–4 changed any hardcoded
composite/covariate key list, so no audio field name has entered any record
type X_core/E_t read from. Golden snapshot (`tests/test_refactor_snapshot.py`)
confirmed unchanged throughout.

---

## 6. Change control (Task 6.3)

**This decision reverses the sign-off response's own recommendation.**
`docs/MATRIX_ROW_MAP.md` row 23 / row 19 and the response document's own
Decision A recommend formal removal of `Δ_audio`, pending the client's
decision. That decision has now been made in the opposite direction —
retain, and build acquisition. This is recorded here as a fact, not
characterised: **retaining audio is a substantive scope change against
`D0PA1 POC Scope & Acceptance v0.5.1` (frozen) and the sign-off response's
own proposed direction, and per the client's own §18, requires documented
change control.** This document, CLAUDE.md's update, and
`docs/PROJECT_STATE.md`'s update are the engineering record that the
decision exists and what it produced; they are **not** the change-control
record itself — that distinction still holds (the same one
`docs/preregistration/README.md` draws between a dated commit recording a
change and the client's own sign-off process for it), but it is no longer
quite accurate to call the change-control record "a separate, not-yet-done
step" with nothing behind it. **A draft now exists**, at
`docs/preregistration/D0PA1_Section18_ChangeControl_Audio_DRAFT.md`
(reference CC-001) — proposed by the vendor, **not reviewed, not signed,
not in force**. Its §8 cost-and-schedule impact section is deliberately
left blank pending the vendor, per its own stated discipline (a change
control signed with an empty impact field is how unpriced work becomes
contractual). **The client's own §18 process has still not run** — nothing
in the draft takes effect by existing, and this sentence should not be
read as claiming otherwise.

---

## 7. Environment audit and the sync measurement — attempted, and a new finding (the "ENVIRONMENT AUDIT, SYNC MEASUREMENT, G5 RIPPLE CHECK" task)

### 7.1 The environment claim was stale — tested, not assumed

Every prior session in this engagement stated that "this coding environment
cannot provide" a live webcam or a human operator. This session tested that
claim directly rather than repeating it:

- **Camera**: `cv2.VideoCapture(0)` opens and reads real frames (640×480,
  MSMF backend), ~26.0–26.6 fps in a raw read loop (no CLAHE/detection).
  Indices 1–3 all fail to open — **only one physical camera exists**; the
  simultaneous-two-camera sensor-swap requirement (hard constraint #6) is
  genuinely still unmet, checked specifically rather than swept into the
  general correction.
- **Microphone**: `sounddevice` enumerates a real default input device
  ("Microphone Array (Intel Smart Sound Technology)", 4 input channels),
  opens a stream, and delivers samples at the correct rate and timing
  (~47,800–48,000 samples/sec against a 48,000 target, zero overrun flags).
- **Both simultaneously**: held open together across two repeated 6-second
  trials with neither failing nor either rate measurably degrading (camera
  25.9–26.2 fps with the audio stream running vs. 26.0–26.6 fps alone;
  audio ~47,757–47,835 samples/sec either way) — within ordinary run-to-run
  variance, not a systematic effect.

**This corrects, not merely supplements, the prior session's own framing**
(§3's FPS-impact proof used a synthetic video-timing harness specifically
*because* camera use was believed off-limits that session by the user's own
choice for that session — that choice was reasonable given what was known
then; the environment's actual capability was simply never tested before
this task).

### 7.2 The sync measurement — attempted live, and a new, different blocker found

With the user's real-time cooperation (asked directly, confirmed present,
agreed to clap on cue), two full attempts were made at the clap-based
sync measurement described in §4, entirely in-memory (no raw audio or
video sample ever written to disk at any point in either attempt — video
kept only the immediately-previous grayscale frame for differencing,
discarded on every iteration; audio kept only the in-process numpy buffer
for the script's lifetime):

- **Attempt 1** (60s): video motion detection worked correctly (real,
  non-trivial frame-to-frame variation, sensible percentile spread up to
  ~9.1) — but audio-event detection degenerated (near-zero median/MAD in a
  near-silent recording drove the threshold to ~0, flagging over 500,000
  spurious "events"). Diagnosed as a thresholding bug, not a data problem,
  and fixed (moved to a percentile-based threshold with an absolute floor).
- **Attempt 2** (65s, corrected thresholding): **zero audio events detected,
  and the raw audio amplitude was pinned at the 16-bit quantization floor
  (3.0517578125×10⁻⁵ = exactly 1/32768) for the entire recording** — no
  variation whatsoever, including during the window the user was actively
  clapping.
- **Two further short diagnostics**, run to isolate the cause: (a) the same
  microphone via the WASAPI host API (device index 9, 4-channel, since MME
  might itself be the problem) returned **exact digital zero** across all
  channels, not even the quantization floor; (b) a **completely different
  physical microphone** (`Microphone (Realtek HD Audio Mic input)`, device
  index 13, not the Intel array at all) also returned **exact digital
  zero**, with the user again asked to make a loud noise during the
  5-second window.

**Conclusion: genuine acoustic content does not reach this process, on this
machine, in this session — across two different physical microphones and
two different host APIs (MME, WASAPI), with a human actively present and
cooperating.** This is consistent with an OS-level microphone-privacy
restriction (e.g. Windows' "allow desktop apps to access your microphone"
setting returning a nominally-successful but silent stream rather than an
error, a documented Windows behaviour) rather than any hardware absence —
the API layer reports success at every step (device found, stream opens,
correct sample count and timing delivered), which is exactly why this
was not visible in §3's earlier FPS-impact/integrity work and needed a
live, content-aware test to surface.

**Per Task 2.4's own instruction: stated plainly, and stopped there.** No
attempt was made to force a detection by lowering the threshold further
(that would report noise as a clap — a fabricated result, explicitly
forbidden) or to substitute a workaround (e.g. a screen flash photographed
by the camera) for the specified single-physical-event method.

**No offset, spread, or drift figure is reported. None was measured.**

### 7.3 A correction to §3's own earlier claim

§3's FPS-impact section (prior task) reported a real audio chunk's level as
`peak_abs ≈ 3.05×10⁻⁵, rms ≈ 1.46×10⁻⁵`, described at the time as **"genuine
captured evidence... real (very quiet) room level."** Given §7.2's finding —
that this exact value (3.0517578125×10⁻⁵) is the 16-bit PCM quantization
floor a blocked/silent stream returns via the MME host API, observed
identically this session under conditions (active clapping) that should
have produced a large, obvious departure from it — **that earlier
characterisation is very likely wrong.** The prior session's reading was, in
retrospect, almost certainly this same access-blocked silence artifact, not
genuine ambient room sound. This is recorded here explicitly, the same
discipline `docs/ROI_FEASIBILITY.md`'s own RETRACTION section uses: a
withdrawn characterisation, stated as withdrawn, not silently corrected.
**What is NOT retracted**: the integrity-logging *mechanism* itself
(`AudioChunkLogger`, the record schema, the missingness vocabulary, the
real bug found and fixed in `_on_finished`) — all of that is independent of
whether the amplitude values it logged that session reflected real room
sound or blocked-stream silence, and none of it is affected by this
correction.

### 7.4 What this means for the outstanding-items list

Corrected in `docs/PROJECT_STATE.md`'s "needs a physical run" group and in
`CLAUDE.md`'s D0PA1.3 section: the camera/microphone-hardware-absence
framing was stale for four of the five physical-run items (they need a real
human's TIME as a study subject, not camera hardware, which is a different
and not-yet-resolved obstacle) and remains accurate for the second-camera
requirement (genuinely only one camera exists). The sync measurement
specifically was attempted, with hardware and a human both available, and
hit a new, more specific, non-hardware blocker — audio content access —
which is now the operative open question for that one item, not camera/mic
absence.
