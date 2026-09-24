"""
controls/run_blink_detector.py validation (runnable directly, no pytest).

Every check uses a temporary storage folder OUTSIDE the repository and
synthetic input only -- never a real study clip. One check runs the REAL
analyze_video pipeline (MediaPipe models loaded) end to end on a small
synthetic video written to that temp folder; the rest substitute a stub
analyze function so they run in seconds.

The G1 check is proven by making it fire on a deliberately non-compliant
snippet before trusting its pass on the real runner (D0PA1.4 habit).
"""

import ast
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np

from controls import run_blink_detector as rbd
from privacy.video_storage_config import VIDEO_STORAGE_LOCATION_ENV_VAR
from stage2_personality_agent import AGENT_LOG_PATH

RUNNER_PATH = os.path.join(REPO_ROOT, "controls", "run_blink_detector.py")


@contextlib.contextmanager
def temp_storage():
    """A fresh storage root outside the repo, pointed to by the env var for
    the duration of the block; the previous value is restored after."""
    root = tempfile.mkdtemp(prefix="d0pa1_runner_test_")
    saved = os.environ.get(VIDEO_STORAGE_LOCATION_ENV_VAR)
    os.environ[VIDEO_STORAGE_LOCATION_ENV_VAR] = root
    try:
        yield root
    finally:
        if saved is None:
            os.environ.pop(VIDEO_STORAGE_LOCATION_ENV_VAR, None)
        else:
            os.environ[VIDEO_STORAGE_LOCATION_ENV_VAR] = saved
        shutil.rmtree(root, ignore_errors=True)


def _fake_clip(folder, name):
    path = os.path.join(folder, name)
    with open(path, "wb") as f:
        f.write(b"not a real video -- stub analyze_fn never opens it")
    return path


def _synthetic_stream(seed=0, duration=12.0, fps=30.0, onsets=(4.0, 7.5, 10.0), none_frames=(30, 31, 200)):
    """Known-shape aperture stream in analyze_video's own {"t","aperture"}
    schema: open baseline ~0.47, 0.2s dips to ~0.38, some None frames."""
    rng = np.random.default_rng(seed)
    stream = []
    for i in range(int(duration * fps)):
        t = round(i / fps, 3)
        if i in none_frames:
            stream.append({"t": t, "aperture": None})
            continue
        in_dip = any(o <= t < o + 0.2 for o in onsets)
        a = (0.38 if in_dip else 0.47) + rng.normal(scale=0.003)
        stream.append({"t": t, "aperture": round(float(a), 4)})
    return stream


def _stub_analyze(stream):
    calls = []

    def fn(path):
        calls.append(path)
        return {"status": "ok", "mode": "A_calibrated", "failure_code": None,
                "video_fps_used": 30.0, "video_duration_sec": 12.0, "aperture_stream": stream}
    fn.calls = calls
    return fn


def _run_quiet(*args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = rbd.run(*args, **kwargs)
    return result, buf.getvalue()


# ------------------------------------------------------------------ checks

def check_stubbed_end_to_end_output_well_formed():
    with temp_storage() as root:
        clips = os.path.join(root, "clips")
        os.makedirs(clips)
        clip = _fake_clip(clips, "P01_clip01.mp4")
        stream = _synthetic_stream()
        stub = _stub_analyze(stream)
        manifest_path, _ = _run_quiet(clip, context_id="room_a", _analyze_fn=stub)

        run_dir = os.path.dirname(manifest_path)
        with open(os.path.join(run_dir, "P01_clip01.json"), encoding="utf-8") as f:
            rec = json.load(f)
        with open(manifest_path, encoding="utf-8") as f:
            man = json.load(f)

        prov = rec["provenance"]
        n_none = sum(1 for s in stream if s["aperture"] is None)
        problems = []
        expect = {
            "record_type": rec["record_type"] == rbd.RECORD_TYPE,
            "under detector_output": os.path.basename(os.path.dirname(run_dir)) == rbd.OUTPUT_SUBDIR,
            "clip_filename": rec["clip_filename"] == "P01_clip01.mp4",
            "subject_id": rec["subject_id"] == "P01" and rec["subject_id_source"] == "filename",
            "context_id given": rec["context_id"] == "room_a" and rec["context_id_missingness_reason"] is None,
            "device_id missing-with-reason": rec["device_id"] is None and rec["device_id_missingness_reason"] == "not_provided_to_runner",
            "git commit hash": isinstance(prov.get("git_commit_hash"), str) and len(prov["git_commit_hash"]) == 40,
            "git dirty flag present": "git_dirty" in prov,
            "experiment_id": rec["experiment_id"] == prov["experiment_id"] == man["experiment_id"],
            "validated-path hash": len(prov.get("validated_path_source_sha256", "")) == 64,
            "captured_at_utc": bool(prov.get("captured_at_utc")),
            "config hashes": all(len(v) == 16 for v in rec["config_hashes"].values()) and len(rec["config_hashes"]) == 2,
            "code hashes": set(rec["code_versions"]["code_sha256"]) == set(rbd.CODE_PATH_FILES)
                           and all(len(v) == 64 for v in rec["code_versions"]["code_sha256"].values()),
            "library versions": all(rec["code_versions"].get(k) for k in ("python", "numpy", "opencv", "mediapipe")),
            "missingness frames": rec["missingness"]["frames_total"] == len(stream)
                                  and rec["missingness"]["frames_aperture_none"] == n_none
                                  and rec["missingness"]["frames_aperture_present"] == len(stream) - n_none,
            "missingness fraction": abs(rec["missingness"]["aperture_present_fraction"] - (len(stream) - n_none) / len(stream)) < 1e-12,
            "aperture stream retained with None": rec["aperture_stream"] == stream,
            "detector ran, list output": rec["detector"]["ran"] is True
                                         and isinstance(rec["detector"]["detected_blink_timestamps_seconds"], list),
            "timestamp semantics recorded": "reopen" in rec["detector"]["timestamp_semantics"],
            "manifest names the clip": [c["clip_filename"] for c in man["clips_covered"]] == ["P01_clip01.mp4"],
            "stub called with clip": stub.calls == [clip],
        }
        problems = [k for k, v in expect.items() if not v]
        return not problems, {"failed_fields": problems} if problems else "all provenance/missingness fields present and correct"


def check_real_pipeline_end_to_end_and_agent_log_unchanged():
    """Real analyze_video (MediaPipe loaded) on a small synthetic video with
    no face: every aperture is None, which exercises the whole real path and
    the missingness record. agent_log.jsonl is hashed before and after."""
    import cv2

    def agent_log_state():
        if not os.path.exists(AGENT_LOG_PATH):
            return None
        with open(AGENT_LOG_PATH, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    before = agent_log_state()
    with temp_storage() as root:
        clip = os.path.join(root, "P99_clip99.mp4")
        writer = cv2.VideoWriter(clip, cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (640, 480))
        rng = np.random.default_rng(1)
        for _ in range(60):
            writer.write(rng.integers(90, 110, size=(480, 640, 3), dtype=np.uint8))
        writer.release()

        manifest_path, _ = _run_quiet(clip)
        with open(os.path.join(os.path.dirname(manifest_path), "P99_clip99.json"), encoding="utf-8") as f:
            rec = json.load(f)
    after = agent_log_state()

    m = rec["missingness"]
    ok = (
        m["frames_total"] > 0
        and m["frames_aperture_present"] == 0
        and m["aperture_present_fraction"] == 0.0
        and len(rec["aperture_stream"]) == m["frames_total"]
        and all(s["aperture"] is None for s in rec["aperture_stream"])
        and rec["subject_id"] == "P99"
        and before == after
    )
    return ok, {"analysis": rec["analysis"], "missingness": m, "agent_log_unchanged": before == after}


def check_missing_subject_id_fails_loudly():
    results = {}
    with temp_storage() as root:
        clip = _fake_clip(root, "recording_final.mp4")
        stub = _stub_analyze(_synthetic_stream())
        try:
            _run_quiet(clip, _analyze_fn=stub)
            results["no id"] = "did not raise"
        except rbd.SubjectIdError as e:
            results["no id"] = "raised"
        results["no id: analyze never called"] = stub.calls == []
        results["no id: no output dir created"] = not os.path.exists(os.path.join(root, rbd.OUTPUT_SUBDIR))

        try:
            rbd.resolve_subject_id(os.path.join(root, "P01_clip01.mp4"), "P02")
            results["conflict"] = "did not raise"
        except rbd.SubjectIdError:
            results["conflict"] = "raised"

        try:
            rbd.resolve_subject_id(clip, "  ")
            results["blank arg"] = "did not raise"
        except rbd.SubjectIdError:
            results["blank arg"] = "raised"

        results["explicit arg accepted"] = rbd.resolve_subject_id(clip, "P05") == ("P05", "argument")

        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                rbd.main([clip])
            results["CLI exit"] = "no exit"
        except SystemExit as e:
            results["CLI exit"] = e.code
        results["CLI names the problem"] = "SubjectIdError" in err.getvalue()

    ok = (results["no id"] == "raised" and results["no id: analyze never called"]
          and results["no id: no output dir created"] and results["conflict"] == "raised"
          and results["blank arg"] == "raised" and results["explicit arg accepted"]
          and results["CLI exit"] == 1 and results["CLI names the problem"])
    return ok, results


def check_folder_with_bad_filename_or_shared_id_fails_before_any_clip():
    results = {}
    with temp_storage() as root:
        folder = os.path.join(root, "clips")
        os.makedirs(folder)
        _fake_clip(folder, "P01_clip01.mp4")
        _fake_clip(folder, "zz_unlabelled.mp4")
        stub = _stub_analyze(_synthetic_stream())
        try:
            _run_quiet(folder, _analyze_fn=stub)
            results["bad filename in folder"] = "did not raise"
        except rbd.SubjectIdError:
            results["bad filename in folder"] = "raised"
        try:
            _run_quiet(folder, subject_id_arg="P01", _analyze_fn=stub)
            results["--subject-id on folder"] = "did not raise"
        except rbd.SubjectIdError:
            results["--subject-id on folder"] = "raised"
        results["no clip processed"] = stub.calls == []
    ok = results["bad filename in folder"] == "raised" and results["--subject-id on folder"] == "raised" and results["no clip processed"]
    return ok, results


def check_output_inside_repo_is_refused():
    results = {}
    saved = os.environ.get(VIDEO_STORAGE_LOCATION_ENV_VAR)
    inside = os.path.join(REPO_ROOT, "logs", "__runner_test_should_never_exist__")
    try:
        os.environ[VIDEO_STORAGE_LOCATION_ENV_VAR] = inside
        try:
            rbd.resolve_output_root()
            results["inside repo"] = "did not raise"
        except rbd.OutputLocationError:
            results["inside repo"] = "raised"
        os.environ[VIDEO_STORAGE_LOCATION_ENV_VAR] = REPO_ROOT
        try:
            rbd.resolve_output_root()
            results["repo root itself"] = "did not raise"
        except rbd.OutputLocationError:
            results["repo root itself"] = "raised"
        os.environ.pop(VIDEO_STORAGE_LOCATION_ENV_VAR, None)
        try:
            rbd.resolve_output_root()
            results["env var unset"] = "did not raise"
        except RuntimeError as e:
            results["env var unset"] = "raised" if VIDEO_STORAGE_LOCATION_ENV_VAR in str(e) else f"wrong error: {e}"
    finally:
        if saved is None:
            os.environ.pop(VIDEO_STORAGE_LOCATION_ENV_VAR, None)
        else:
            os.environ[VIDEO_STORAGE_LOCATION_ENV_VAR] = saved
    results["nothing created in repo"] = not os.path.exists(inside)
    ok = all(v == "raised" for k, v in results.items() if k != "nothing created in repo") and results["nothing created in repo"]
    return ok, results


def check_folder_order_is_deterministic():
    with temp_storage() as root:
        folder = os.path.join(root, "clips")
        os.makedirs(folder)
        for name in ("P03_clip03.mp4", "P01_clip01.mp4", "P02_clip02.mp4"):
            _fake_clip(folder, name)
        stub = _stub_analyze(_synthetic_stream())
        manifest_path, _ = _run_quiet(folder, _analyze_fn=stub)
        with open(manifest_path, encoding="utf-8") as f:
            man = json.load(f)
        order = [c["clip_filename"] for c in man["clips_covered"]]
        files = sorted(os.listdir(os.path.dirname(manifest_path)))
    expected = ["P01_clip01.mp4", "P02_clip02.mp4", "P03_clip03.mp4"]
    ok = order == expected and man["n_clips"] == 3 and [os.path.basename(c) for c in stub.calls] == expected \
        and files == ["P01_clip01.json", "P02_clip02.json", "P03_clip03.json", "run_manifest.json"]
    return ok, {"manifest_order": order, "files": files}


def check_console_never_shows_detector_output():
    """Blind-count protection: the detected timestamps (and so their count)
    reach the output file only, never stdout."""
    with temp_storage() as root:
        clip = _fake_clip(root, "P01_clip01.mp4")
        manifest_path, stdout = _run_quiet(clip, _analyze_fn=_stub_analyze(_synthetic_stream()))
        with open(os.path.join(os.path.dirname(manifest_path), "P01_clip01.json"), encoding="utf-8") as f:
            detected = json.load(f)["detector"]["detected_blink_timestamps_seconds"]
    leaked = [t for t in detected if str(t) in stdout]
    mentions = re.findall(r"detected|onset|blinks?\b", stdout, flags=re.IGNORECASE)
    ok = bool(detected) and not leaked and not mentions
    return ok, {"synthetic stream produced detections": bool(detected), "leaked_timestamps": leaked, "suspicious_words": mentions}


# ---- G1: no comparison-to-manual-count and no verdict logic, by AST ----

FORBIDDEN_IDENTIFIER = re.compile(
    r"manual|match_events|evaluate|(^|_)f1($|_)|precision|recall|bland|altman|criterion|verdict|agreement",
    re.IGNORECASE,
)
FORBIDDEN_STRING = re.compile(r"\bPASS(ED)?\b|\bFAIL(ED)?\b|verdict|manual_count", re.IGNORECASE)
ALLOWED_BLINK_POSITIVE_IMPORTS = {"BlinkPositiveConfig", "run_detector_on_aperture_stream"}


def g1_violations(source):
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                docstrings.add(id(node.body[0].value))
    found = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.append(alias.name)
                names.append(alias.asname or "")
            if isinstance(node, ast.ImportFrom) and node.module == "controls.blink_positive":
                for alias in node.names:
                    if alias.name not in ALLOWED_BLINK_POSITIVE_IMPORTS:
                        found.append(f"import of controls.blink_positive.{alias.name}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            if FORBIDDEN_STRING.search(node.value):
                found.append(f"string literal: {node.value!r}")
        for n in names:
            if n and FORBIDDEN_IDENTIFIER.search(n):
                found.append(f"identifier: {n}")
    return found


def check_g1_guard_fires_on_noncompliant_snippet():
    bad = (
        "from controls.blink_positive import load_manual_count, evaluate_run\n"
        "def score(detected, path, config):\n"
        "    manual = load_manual_count(path)\n"
        "    f1 = evaluate_run(detected, manual)['event_f1']\n"
        "    return 'PASS' if f1 >= config.criterion_event_f1 else 'FAIL'\n"
    )
    found = g1_violations(bad)
    return len(found) >= 5, found


def check_runner_has_no_comparison_or_verdict_logic():
    with open(RUNNER_PATH, encoding="utf-8") as f:
        found = g1_violations(f.read())
    return not found, found or "no manual-count, metric, criterion or verdict logic in the runner"


if __name__ == "__main__":
    checks = [
        ("stubbed end-to-end: well-formed output with full provenance", check_stubbed_end_to_end_output_well_formed),
        ("REAL analyze_video end-to-end on synthetic video; agent_log.jsonl unchanged", check_real_pipeline_end_to_end_and_agent_log_unchanged),
        ("missing/conflicting subject_id fails loudly, before any work", check_missing_subject_id_fails_loudly),
        ("folder: bad filename or shared --subject-id fails before any clip", check_folder_with_bad_filename_or_shared_id_fails_before_any_clip),
        ("output inside the repository is refused (enforced, not defaulted)", check_output_inside_repo_is_refused),
        ("folder processing order is deterministic and named in the manifest", check_folder_order_is_deterministic),
        ("console never shows detector output", check_console_never_shows_detector_output),
        ("G1 guard FIRES on a deliberately non-compliant snippet", check_g1_guard_fires_on_noncompliant_snippet),
        ("G1: runner has no comparison-to-manual-count and no verdict logic", check_runner_has_no_comparison_or_verdict_logic),
    ]
    failures = []
    for i, (label, fn) in enumerate(checks, 1):
        ok, detail = fn()
        print(f"[{i}/{len(checks)}] {label} -- {'PASS' if ok else 'FAIL'}: {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")
    print()
    if failures:
        print(f"BLINK DETECTOR RUNNER VALIDATION: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("BLINK DETECTOR RUNNER VALIDATION: PASS")
