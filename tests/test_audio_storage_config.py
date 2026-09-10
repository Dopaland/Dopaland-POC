"""
Audio raw-storage config validation (Task 1.4). Covers: no fallback default
(raises loudly when the environment variable is unset), correct resolution
when set, config_hash() stability/uniqueness, and -- the actual point of this
module -- confirms no literal storage-path string is hardcoded anywhere in
privacy/audio_storage_config.py's own source.
"""

import ast
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from privacy.audio_storage_config import (
    AUDIO_STORAGE_LOCATION_ENV_VAR, AudioStorageConfig, resolve_audio_storage_config,
)


def check_raises_when_env_var_unset():
    saved = os.environ.pop(AUDIO_STORAGE_LOCATION_ENV_VAR, None)
    try:
        try:
            resolve_audio_storage_config()
            return False, "did not raise with the env var unset"
        except RuntimeError as e:
            return AUDIO_STORAGE_LOCATION_ENV_VAR in str(e), f"raised correctly: {e}"
    finally:
        if saved is not None:
            os.environ[AUDIO_STORAGE_LOCATION_ENV_VAR] = saved


def check_raises_when_env_var_blank():
    saved = os.environ.get(AUDIO_STORAGE_LOCATION_ENV_VAR)
    os.environ[AUDIO_STORAGE_LOCATION_ENV_VAR] = "   "
    try:
        resolve_audio_storage_config()
        return False, "did not raise with the env var set to whitespace-only"
    except RuntimeError as e:
        return True, f"raised correctly: {e}"
    finally:
        if saved is None:
            os.environ.pop(AUDIO_STORAGE_LOCATION_ENV_VAR, None)
        else:
            os.environ[AUDIO_STORAGE_LOCATION_ENV_VAR] = saved


def check_resolves_and_hashes_when_set():
    saved = os.environ.get(AUDIO_STORAGE_LOCATION_ENV_VAR)
    fake_path = os.path.join("D:", "not_a_real_repo_sibling", "d0pa1_raw_audio")
    os.environ[AUDIO_STORAGE_LOCATION_ENV_VAR] = fake_path
    try:
        cfg = resolve_audio_storage_config()
        h = cfg.config_hash()
        ok = (
            cfg.storage_location == fake_path
            and isinstance(h, str)
            and len(h) == 16
        )
        return ok, {"storage_location": cfg.storage_location, "hash": h}
    finally:
        if saved is None:
            os.environ.pop(AUDIO_STORAGE_LOCATION_ENV_VAR, None)
        else:
            os.environ[AUDIO_STORAGE_LOCATION_ENV_VAR] = saved


def check_hash_changes_with_location():
    a = AudioStorageConfig(storage_location="X:\\one\\place").config_hash()
    b = AudioStorageConfig(storage_location="X:\\a\\different\\place").config_hash()
    return a != b, {"hash_a": a, "hash_b": b}


def check_no_literal_path_in_committed_source():
    """The actual point of this module (see its own docstring): confirm, by
    AST, that privacy/audio_storage_config.py never assigns a filesystem-path-
    shaped string literal as a default anywhere. Specifically: AudioStorageConfig
    must have NO default for storage_location (an AST check that its
    dataclass field has no `=` default), and no top-level string constant in
    the file should look like an absolute path (contains a path separator
    AND is not the env-var name itself)."""
    path = os.path.join(REPO_ROOT, "privacy", "audio_storage_config.py")
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=path)

    # No default value on the dataclass field.
    field_has_default = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AudioStorageConfig":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and getattr(item.target, "id", None) == "storage_location":
                    field_has_default = item.value is not None

    # No string literal anywhere in the file that looks like a real path
    # (contains a path separator) other than inside the docstrings/comments
    # (AST string constants exclude comments already; docstrings are Str/
    # Constant nodes too, so explicitly skip the module/class/function
    # docstrings by excluding the first Expr-Constant-str in each body).
    suspicious = []
    docstring_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                docstring_nodes.add(id(node.body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstring_nodes:
            val = node.value
            if ("/" in val or "\\" in val) and val != AUDIO_STORAGE_LOCATION_ENV_VAR:
                suspicious.append(val)

    ok = (field_has_default is False) and not suspicious
    return ok, {"field_has_default": field_has_default, "suspicious_literals": suspicious}


def run_all():
    checks = [
        ("RAISES WHEN ENV VAR UNSET", check_raises_when_env_var_unset),
        ("RAISES WHEN ENV VAR BLANK", check_raises_when_env_var_blank),
        ("RESOLVES AND HASHES WHEN SET", check_resolves_and_hashes_when_set),
        ("HASH CHANGES WITH LOCATION", check_hash_changes_with_location),
        ("NO LITERAL PATH IN COMMITTED SOURCE", check_no_literal_path_in_committed_source),
    ]
    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    print()
    if failures:
        print(f"AUDIO STORAGE CONFIG VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("AUDIO STORAGE CONFIG VALIDATION: PASS")


if __name__ == "__main__":
    run_all()
