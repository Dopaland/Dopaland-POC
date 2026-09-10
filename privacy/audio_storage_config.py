"""
D0PA1 audio acquisition -- raw audio storage location (Task 1.4).

WHY THIS IS NOT JUST privacy/retention.py's PATTERN REUSED: this task's own
instruction was to place raw audio "outside the repository, alongside
wherever raw video already goes." That second half has a false premise --
checked directly against `docs/PRIVACY_AND_RETENTION.md` and `PROVENANCE.md`
before writing this file: **no raw-video storage location has ever been
decided in this repository.** `privacy/retention.py`'s own `storage_location`
default is `logs/` INSIDE this checkout, explicitly labelled a placeholder
"NOT a decision that raw/derived data should live here" and "genuinely
relocating it outside the repository is a separate, not-yet-made decision."
There is no existing "where raw video already goes" to place audio alongside.
This is recorded here rather than silently invented as if settled -- see the
task's own final-report point 8.

Given that, and given this task's own framing that voice is MORE identifying
than facial geometry ("the guardrail under most pressure"), this module goes
one step stricter than `privacy/retention.py`: retention.py's placeholder
path is a Python literal inside a committed file (`os.path.join(REPO_ROOT,
"logs")`). This module's storage location is NEVER a literal in any committed
file, placeholder or otherwise -- it is read from one environment variable at
call time, and only the RESOLVED CONFIG'S HASH (config_hash(), same pattern
every other *Config class in this codebase uses) is ever computed or logged.
If the environment variable is unset, resolve_audio_storage_config() raises
rather than silently falling back to a hardcoded path -- a missing location
is a loud stop, not a guessed default, for exactly the same reason a missing
retention decision must not silently resolve to "keep it in the repo."

The operator is expected to set D0PA1_AUDIO_RAW_STORAGE_LOCATION to a real
directory OUTSIDE this repository (e.g. a sibling directory, or wherever raw
video is eventually decided to live, once that decision actually exists)
before any acquisition code runs. This module does not create, validate
write-access to, or otherwise touch that directory -- it only resolves and
hashes the configuration; `audio_acquisition.py` is what actually writes
there, and only when Task 3.3's own "outside the repo, deleted after
measurement" discipline calls for a raw file at all.
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass

AUDIO_STORAGE_LOCATION_ENV_VAR = "D0PA1_AUDIO_RAW_STORAGE_LOCATION"


@dataclass(frozen=True)
class AudioStorageConfig:
    """No default value for storage_location -- see module docstring. A
    default here would be exactly the literal-path-in-a-committed-file
    pattern this module exists to avoid."""

    storage_location: str

    def config_hash(self):
        """Same short-SHA256-prefix pattern as RetentionConfig/LeakageConfig/
        PreRegisteredConfig/every other *Config class in this codebase --
        the ONLY committed trace of which location actually governed a real
        run is this hash, never the literal path itself."""
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


def resolve_audio_storage_config():
    """Reads AUDIO_STORAGE_LOCATION_ENV_VAR from the environment. Raises
    RuntimeError, loudly, if it is unset or blank -- there is no fallback
    default anywhere in this module (see module docstring on why a fallback
    literal would defeat the point). Does not validate that the path exists,
    is writable, or is genuinely outside the repository -- that check
    belongs to whatever calls this, at the point it actually needs to write,
    not here (this function's only job is resolving + hashing config)."""
    value = os.environ.get(AUDIO_STORAGE_LOCATION_ENV_VAR, "").strip()
    if not value:
        raise RuntimeError(
            f"{AUDIO_STORAGE_LOCATION_ENV_VAR} is not set. Raw audio storage "
            "location is deliberately never hardcoded in this repository (G4 -- "
            "voice is more identifying than facial geometry). Set this "
            "environment variable to a real directory OUTSIDE the repository "
            "before running any audio acquisition code."
        )
    return AudioStorageConfig(storage_location=value)
