"""
Stage 1.5, step 7 — consent + opt-out gate (Decision #6), extended for
per-person Gate 2 validation runs with an anonymous participant code.
Further extended (D0PA1 audio acquisition task) with a SEPARATE,
INDEPENDENT audio consent element -- see AUDIO CONSENT below.

Runs BEFORE any capture or calibration: this module never imports or
touches cv2.VideoCapture, mediapipe, sounddevice, pyaudio, or any
camera/microphone/model resource. The only side effect of importing this
file is nothing happening until run_consent_gate() is explicitly called,
and even then, opting out of video still opens no camera and starts no
thread, and never prompts for a participant code; opting out of audio
(independently) still opens no microphone.

Honest framing (CLAUDE.md #10): this is an opt-in wellness/validation
tool. Never "monitoring", never clinical, never a claim of emotion
detection -- "behavioral signals / affective indicators" only.

No name or identity is collected. person_label is an anonymous,
operator-entered participant code (e.g. "P01") -- a join key for
associating this session's records with a validation-study
participant, not an identity field. Along with session_id (already
generated at import time by stage1_step4_vectors, not tied to any
person), the consent log is an audit trail that consent was obtained
for a given session and code, not a record of who gave it.

AUDIO CONSENT (D0PA1 audio acquisition task, Task 2): video and audio
consent are asked as TWO SEPARATE, INDEPENDENT questions -- a person may
consent to video and decline audio (the reverse is moot: without video
consent this module exits before the audio question is ever asked, same
as before this task). "Architecturally unreachable when declined" means
what it means for video: this module never imports an audio library, so
importing it can never open a microphone regardless of any answer; and
audio_consented's caller-side contract is that acquisition code is only
ever IMPORTED (not just called) inside a branch gated on that value being
True -- see audio_acquisition.py's own docstring and
tests/test_consent_audio_gate.py's proof that this holds, the same
"prove the guard fires" discipline as .githooks/pre-commit.

Operating model: one app launch = one person = one consent = one
calibration = one session_id = one person_label. No internal
multi-person loop lives here or anywhere else in this file.
"""

import json
import os
import time
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
CONSENT_LOG_PATH = os.path.join(LOG_DIR, "consent_log.jsonl")

MAX_PERSON_LABEL_LENGTH = 16
INVALID_PERSON_LABEL_CHARS = set("/\\'\"")

CONSENT_TEXT = """
============================================================
 Behavioral Signals Session -- Consent
============================================================

This is an opt-in wellness/validation tool. It is NOT a
monitoring or clinical system. It does not diagnose, predict,
or identify you.

What happens if you continue:
  - Your webcam turns on and tracks facial and postural
    GEOMETRY (positions of points on your face and body) --
    it does not save video or audio.
  - That geometry is used to compute a few behavioral signals
    (e.g. brow tension, eye expression, posture) for this
    session only.
  - Everything is stored LOCALLY on this machine, tagged with
    a random session ID -- no name, no identity, nothing sent
    anywhere.
  - Nothing persists across sessions. Each run starts fresh.

You can stop at any time by closing the window or pressing Q.

Do you consent to continue?
Type "yes" to proceed. Press Enter or type anything else to
exit now without recording anything.
"""

# Asked SEPARATELY from CONSENT_TEXT above, only after video consent is
# already given -- a genuinely independent second question, not a
# sub-clause of the first (Task 2.1). Declining this leaves video capture
# entirely unaffected; only the microphone path is gated on the answer.
AUDIO_CONSENT_TEXT = """
------------------------------------------------------------
 Audio -- a SEPARATE consent question
------------------------------------------------------------

Audio is independent of the video consent you just gave. You
may continue with video only and decline audio.

If you consent to audio:
  - Your microphone turns on and records sound LEVEL and
    TIMING only (loudness, dropouts, timing integrity) -- see
    the session information for what is and is not captured.
  - It does not transcribe speech, does not analyze what was
    said, and does not compute any emotional/psychological
    reading from your voice.

If you decline audio:
  - No microphone is opened, at any point in this session.
  - Video capture (if you consented to it) continues normally.

Do you consent to audio?
Type "yes" to proceed. Press Enter or type anything else to
decline audio only -- video continues either way.
"""


def _sanitize_person_label(raw):
    """Minimal sanity check only -- strip whitespace, reject empty, cap
    length, reject path separators/quotes. This is a free-form
    anonymous participant code (e.g. "P01"), NOT a validated identifier
    format -- do not over-validate beyond making it safe to log."""
    label = raw.strip()
    if not label:
        return None, "Participant code cannot be empty."
    if len(label) > MAX_PERSON_LABEL_LENGTH:
        return None, f"Participant code must be {MAX_PERSON_LABEL_LENGTH} characters or fewer."
    if any(ch in INVALID_PERSON_LABEL_CHARS for ch in label):
        return None, "Participant code cannot contain / \\ ' or \"."
    return label, None


def _prompt_person_label():
    """Only reached after consent is already confirmed -- re-prompting
    here never touches consent state or opt-out behavior."""
    while True:
        raw = input("Participant code (e.g. P01 -- anonymous, not a name): ")
        label, error = _sanitize_person_label(raw)
        if label is not None:
            return label
        print(f"  {error} Try again.")


def _log_consent(session_id, person_label, audio_consented):
    """video_consent is always True here -- this is only ever called after
    video consent already succeeded (declining video exits before this is
    reached, same as before this task). audio_consent is ALWAYS a real
    bool, never omitted: a decline is `false` with an explicit
    audio_consent_reason, never a silently missing field (Task 2.3)."""
    os.makedirs(LOG_DIR, exist_ok=True)
    record = {
        "event": "consent_given",
        "session_id": session_id,
        "person_label": person_label,
        "video_consent": True,
        "audio_consent": audio_consented,
        "audio_consent_reason": None if audio_consented else "declined_by_participant",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "ts_monotonic": time.perf_counter(),
    }
    with open(CONSENT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _ask_audio_consent():
    """Independent second question -- see AUDIO_CONSENT_TEXT and module
    docstring's AUDIO CONSENT section. Never imports an audio library;
    only returns a bool for the caller to act on."""
    print(AUDIO_CONSENT_TEXT)
    response = input("> ").strip().lower()
    return response == "yes"


def run_consent_gate(session_id):
    """Blocking, console-based.

    Returns (video_consented: bool, audio_consented: bool | None, person_label: str | None).
      - Video opt-out (blank / "no" / anything but "yes"): (False, None, None).
        No participant-code prompt, no audio question ever asked, nothing
        logged -- unchanged from before this task.
      - Video opt-in ("yes"): prompts for an anonymous participant code,
        THEN asks the separate, independent audio question
        (_ask_audio_consent), logs one consent_given record carrying BOTH
        video_consent and audio_consent explicitly, returns
        (True, audio_consented, person_label). audio_consented is always
        a real bool in this branch, never None.
    """
    print(CONSENT_TEXT)
    response = input("> ").strip().lower()

    if response != "yes":
        print("\nNo consent given -- exiting. Nothing was recorded.\n")
        return False, None, None

    person_label = _prompt_person_label()
    audio_consented = _ask_audio_consent()
    _log_consent(session_id, person_label, audio_consented)
    audio_note = "audio: consented" if audio_consented else "audio: declined"
    print(f"\nConsent recorded for participant '{person_label}' ({audio_note}). Starting session...\n")
    return True, audio_consented, person_label
