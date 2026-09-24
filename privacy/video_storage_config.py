"""
D0PA1 raw video storage location.

Mirrors `privacy/audio_storage_config.py`'s pattern exactly, for the other
raw-media modality. Until this task, no raw-video storage location had ever
been decided anywhere in this repository -- `docs/PRIVACY_AND_RETENTION.md`
named that gap explicitly and proposed, but did not implement, a UNIFIED
raw-media-root variable covering both modalities.

`D0PA1_Client_SignOff_001.md` §5.2 (2026-09-19) decides the POLICY -- raw
media (video, and audio if any is recorded) lives in a defined folder
OUTSIDE `C:\\Dopaland-POC` for the 90-day retention period (§5.1) -- without
deciding the unification question, which §6 of that same record explicitly
lists as still open. This module therefore implements the video side with
its OWN environment variable, matching audio's already-stricter pattern
(no literal default, raises loudly if unset), rather than pre-empting the
unified-root proposal `docs/PRIVACY_AND_RETENTION.md` describes as
"proposed, not implemented, not decided." If a unified root is decided
later, this module and `audio_storage_config.py` both get superseded
together, not one without the other.

The operator is expected to set `D0PA1_VIDEO_RAW_STORAGE_LOCATION` to a
real directory OUTSIDE this repository before any code that would write
raw video runs. This module does not create, validate, or write to that
directory -- it only resolves and hashes the configuration.
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass

VIDEO_STORAGE_LOCATION_ENV_VAR = "D0PA1_VIDEO_RAW_STORAGE_LOCATION"


@dataclass(frozen=True)
class VideoStorageConfig:
    """No default value for storage_location -- see module docstring. A
    default here would be exactly the literal-path-in-a-committed-file
    pattern this module exists to avoid."""

    storage_location: str

    def config_hash(self):
        """Same short-SHA256-prefix pattern as RetentionConfig/AudioStorageConfig/
        PreRegisteredConfig/every other *Config class in this codebase --
        the ONLY committed trace of which location actually governed a real
        run is this hash, never the literal path itself."""
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


def resolve_video_storage_config():
    """Reads VIDEO_STORAGE_LOCATION_ENV_VAR from the environment. Raises
    RuntimeError, loudly, if it is unset or blank -- there is no fallback
    default anywhere in this module. Does not validate that the path
    exists, is writable, or is genuinely outside the repository -- that
    check belongs to whatever calls this, at the point it actually needs to
    write, not here."""
    value = os.environ.get(VIDEO_STORAGE_LOCATION_ENV_VAR, "").strip()
    if not value:
        raise RuntimeError(
            f"{VIDEO_STORAGE_LOCATION_ENV_VAR} is not set. Raw video storage "
            "location is deliberately never hardcoded in this repository (G4). "
            "Set this environment variable to a real directory OUTSIDE the "
            "repository before running any code that writes raw video, per "
            "D0PA1_Client_SignOff_001.md \u00a75.2."
        )
    return VideoStorageConfig(storage_location=value)
