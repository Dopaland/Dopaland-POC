"""
D1 feature-block separation test (D0PA1 Batch 1, Step 3.4). Verifies the
directional constraint CLAUDE.md's D1 requirement sets:

    PERMITTED    X_core -> E_t          C_t -> E_t
    FORBIDDEN    A_t -> X_core          A_t -> E_t
                 U_t -> X_core          U_t -> E_t

Concretely: features/x_core.py and features/episodes.py must never import
features/attention.py or features/audio.py, directly or transitively, and
must never call anything defined in them -- statically OR at runtime.

Four independent checks, each of which must FAIL LOUDLY on a real
violation (see the bottom of this docstring for how that was proven):

  1. STATIC IMPORT GRAPH -- parses every features/*.py file with `ast`
     (not regex, so a violation can't hide behind unusual formatting or a
     comment that merely LOOKS like an import) and builds the transitive
     features.* dependency graph, including imports nested inside function
     bodies (x_core.py's compute_v_bf/v_es/v_jc import their landmark
     constants from features.geometry INSIDE the function, not at module
     level -- ast.walk() finds these too, a plain top-level scan would
     miss them).

  2. STATIC CALL GRAPH -- collects every top-level name features/attention.py
     and features/audio.py actually DEFINE (function/class/assignment,
     not names they merely import from elsewhere), then checks whether
     any such name is referenced anywhere in features/x_core.py or
     features/episodes.py's AST that is NOT also independently defined or
     imported by that file itself. This second exclusion matters: x_core.py
     and attention.py each define their OWN, independent PERSON_LABEL
     global (see features/x_core.py's and features/attention.py's own
     comments on why) -- a naive name-string match would flag that as a
     violation when it is not one; a symbol only counts as "reaching into"
     attention/audio if the referencing file has no other legitimate
     source for that name.

  3. RUNTIME MONKEYPATCH -- replaces sys.modules['features.attention'] and
     ['features.audio'] with an object that raises on ANY attribute
     access, force-reloads features.x_core and features.episodes fresh
     (catching a module-level "from features.attention import X" the
     moment the reload executes it), then runs the SAME kind of
     computations tests/test_refactor_snapshot.py's golden snapshot
     exercises (reusing its synthetic fixtures, not reinventing them) --
     compute_v_bf/es/jc/pd, NeutralCalibrator, map_to_valence_arousal,
     WindowAccumulator, classify_window_confidence, classify_calibration_
     quality. If anything in that real execution path ever touches the
     poisoned attention/audio module, the proxy raises and names exactly
     which attribute was touched.

  4. COMPATIBILITY-SHIM ISOLATION -- checks 1-3 only walk the features.*
     package graph. stage1_step4_vectors.py, the original Step-4 module,
     now re-exports symbols from features.geometry/x_core/episodes/
     attention side by side (so historical diagnostic scripts --
     stage1_step4_browdiag_session.py, stage1_step9_gate2_capture.py,
     tests/test_refactor_snapshot.py -- keep working against the old flat
     namespace; see its own module docstring, "D0PA1 BATCH 1 STEP 3
     REFACTOR NOTE"). That flattens the block boundary: an import of
     stage1_step4_vectors BY x_core.py or episodes.py would launder an
     attention/audio reference straight past checks 1-3, which never look
     outside features/. This check closes that blind spot generically: it
     discovers, by AST, every repo-root module that imports
     features.attention or features.audio anywhere -- a "cross-block
     shim" by definition, whatever it's named -- then verifies x_core.py
     and episodes.py never import any such module, directly or
     transitively through any other local module. Nested (in-function)
     imports are walked the same way check 1 does.

PROOF THIS TEST CAN ACTUALLY FAIL: a separation test that has never been
observed to fail is worth nothing (same reasoning that required the
pre-commit media-guard hook to be proven, not assumed -- see PROVENANCE.md).
This was verified by temporarily adding
`from features.attention import ATTENTION_ORIENTED_SCORE_THRESHOLD` to
features/x_core.py, confirming check 1 caught it with a clear message
naming the violating edge, then reverting. Check 4 was verified the same
way, separately: temporarily adding `import stage1_step4_vectors` to
features/x_core.py -- a violation invisible to checks 1-3, since
stage1_step4_vectors.py is not a features/* module -- confirmed check 4
caught it with a clear message naming the shim and the import path, then
reverted. See the task's final report for the pasted failure output.
"""

import ast
import importlib
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES_DIR = os.path.join(REPO_ROOT, "features")

for p in (REPO_ROOT, TESTS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

BLOCK_MODULES = ["geometry", "x_core", "episodes", "attention", "audio", "context"]
FORBIDDEN_EDGES = [
    ("x_core", "attention"),
    ("x_core", "audio"),
    ("episodes", "attention"),
    ("episodes", "audio"),
    # Added by the "ACT ON THE ROI FEASIBILITY VERDICT" task: found by audit
    # (docs/ROI_FEASIBILITY.md Task 4.2), not by this test itself -- context.py
    # (C_t) is a BLOCK_MODULES node and its imports were already being parsed,
    # but no FORBIDDEN_EDGES entry named it as a source, so a future
    # `context.py -> attention.py` (or `-> audio.py`) import would have passed
    # unnoticed. C_t -> E_t stays PERMITTED under D1 (CLAUDE.md) -- these two
    # edges forbid only attention-/audio-derived information reaching the core
    # BY WAY OF context, not context reaching episodes at all. See
    # docs/D1_DEPENDENCY_MAP.md Task 2 section for the fail-then-pass proof.
    ("context", "attention"),
    ("context", "audio"),
]


def _parse(module_name):
    path = os.path.join(FEATURES_DIR, module_name + ".py")
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    return ast.parse(source, filename=path)


# ============================================================
# CHECK 1 -- static import graph (transitive, includes nested imports)
# ============================================================

def direct_feature_imports(module_name):
    """features.* module names imported ANYWHERE in module_name's AST
    (module level or nested inside a function/class body)."""
    tree = _parse(module_name)
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "features":
                for alias in node.names:
                    if alias.name in BLOCK_MODULES:
                        deps.add(alias.name)
            elif mod.startswith("features."):
                sub = mod.split(".", 2)[1]
                if sub in BLOCK_MODULES:
                    deps.add(sub)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("features."):
                    sub = alias.name.split(".")[1]
                    if sub in BLOCK_MODULES:
                        deps.add(sub)
    return deps


def transitive_closure(graph, start):
    seen = set()
    stack = list(graph.get(start, ()))
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(graph.get(cur, ()))
    return seen


def check_static_import_graph():
    graph = {name: direct_feature_imports(name) for name in BLOCK_MODULES}
    violations = []
    for src, forbidden in FORBIDDEN_EDGES:
        reachable = transitive_closure(graph, src)
        if forbidden in reachable:
            # Find a concrete path for a useful error message.
            path = _find_path(graph, src, forbidden)
            violations.append(f"{src}.py imports (transitively) {forbidden}.py -- path: {' -> '.join(path)}")
    return violations, graph


def _find_path(graph, start, target):
    from collections import deque
    q = deque([[start]])
    visited = {start}
    while q:
        path = q.popleft()
        node = path[-1]
        if node == target:
            return path
        for nxt in graph.get(node, ()):
            if nxt not in visited:
                visited.add(nxt)
                q.append(path + [nxt])
    return [start, "?", target]


# ============================================================
# CHECK 2 -- static call graph (name-level, shadow-aware)
# ============================================================

def top_level_defined_names(module_name):
    """Names module_name DEFINES itself at module scope (FunctionDef,
    ClassDef, Assign/AnnAssign targets) -- NOT names it merely imports.
    This is deliberately narrower than "every name in scope": a name this
    module imports from a permitted upstream (geometry) is not something
    it "defines", so it correctly stays out of this set."""
    tree = _parse(module_name)
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def all_names_in_scope(module_name):
    """Every name module_name defines OR imports, anywhere (module level
    or nested) -- used to exclude a file's own legitimate bindings from
    being flagged as "reaching into" another module just because the
    other module happens to define a same-spelled symbol."""
    tree = _parse(module_name)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.arg,)):
            names.add(node.arg)
    return names


def referenced_names(module_name):
    tree = _parse(module_name)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def check_static_call_graph():
    violations = []
    for forbidden_mod in ("attention", "audio"):
        forbidden_defined = top_level_defined_names(forbidden_mod)
        if not forbidden_defined:
            continue  # audio.py is empty -- nothing to check
        for src in ("x_core", "episodes"):
            src_own = all_names_in_scope(src)
            src_refs = referenced_names(src)
            leaked = (src_refs & forbidden_defined) - src_own
            if leaked:
                violations.append(
                    f"{src}.py references name(s) {sorted(leaked)} defined in {forbidden_mod}.py, "
                    f"with no other legitimate source for that name in {src}.py"
                )
    return violations


# ============================================================
# CHECK 3 -- runtime monkeypatch (attention/audio raise on any attribute access)
# ============================================================

class _RaiseOnAnyAttribute:
    """Stands in for a features.* module. Any attribute access raises,
    naming exactly which attribute was touched -- this is what makes a
    violation impossible to miss silently."""

    def __init__(self, module_name):
        self._module_name = module_name

    def __getattr__(self, item):
        raise AttributeError(
            f"FEATURE SEPARATION VIOLATION: something touched "
            f"features.{self._module_name}.{item} while {self._module_name} "
            f"was poisoned -- X_core/E_t computation must never reach A_t/U_t."
        )


def check_runtime_isolation():
    """Returns (ok: bool, message: str)."""
    import features.attention as real_attention
    import features.audio as real_audio
    import features.geometry as geometry  # not poisoned -- upstream, permitted
    from collections import deque

    # Build fixtures and do the geometry pre-processing BEFORE poisoning.
    # Importing test_refactor_snapshot transitively imports stage1_step4_vectors,
    # which is an ORCHESTRATOR (not X_core/E_t) and legitimately imports
    # features.attention -- that import must complete against the REAL
    # module, not the poisoned stand-in, or this check would fail for the
    # wrong reason (an orchestrator's permitted import, not an X_core/E_t
    # leak). Only x_core/episodes are reloaded fresh and exercised while
    # attention/audio are poisoned, below.
    import test_refactor_snapshot as snap

    lms = snap.build_synthetic_face_landmarks()
    matrix = snap.build_synthetic_transform_matrix()
    normalized_pts = geometry.pose_normalize(lms, matrix, 640, 480)
    io_dist = geometry.interocular_distance(normalized_pts)
    pose_world_sequence = snap.build_synthetic_pose_world_sequence()
    cal_samples = snap.build_synthetic_calibration_samples()
    win_samples = snap.build_synthetic_window_samples()

    sys.modules["features.attention"] = _RaiseOnAnyAttribute("attention")
    sys.modules["features.audio"] = _RaiseOnAnyAttribute("audio")

    for mod_name in ("features.x_core", "features.episodes"):
        if mod_name in sys.modules:
            del sys.modules[mod_name]

    try:
        x_core = importlib.import_module("features.x_core")
        episodes = importlib.import_module("features.episodes")

        v_bf, bf_components = x_core.compute_v_bf(normalized_pts, io_dist)
        v_es, es_components = x_core.compute_v_es(normalized_pts, io_dist)
        v_jc, jc_components = x_core.compute_v_jc(normalized_pts, io_dist)

        pd_buffer = deque()
        for t, nose, shoulder_mid in pose_world_sequence:
            x_core.compute_v_pd(pd_buffer, nose, shoulder_mid, t)

        calibrator = x_core.NeutralCalibrator()
        for t, composite, covariate, yaw_deg in cal_samples:
            calibrator.add_sample(t, composite, covariate, yaw_deg)
        reference = calibrator.complete(cal_samples[-1][0])
        dev = calibrator.deviation("v_es", -0.20)
        x_core.map_to_valence_arousal(dev, dev, dev, reference)

        window_acc = episodes.WindowAccumulator()
        for t, detected, yaw_deg, composite, covariate in win_samples:
            window_acc.add_sample(t, detected, yaw_deg, composite, covariate)
        window_acc.flush(win_samples[-1][0])

        return True, "computed X_core and E_t end-to-end with attention/audio poisoned -- neither was touched."
    except (AttributeError, ImportError) as e:
        # ImportError covers a module-level "from features.attention import X"
        # in x_core.py/episodes.py itself: Python's import machinery wraps the
        # poisoned __getattr__'s AttributeError into an ImportError at the
        # `from ... import` statement, with a less specific message -- still a
        # clear, loud failure, just from a different exception type.
        return False, f"{type(e).__name__}: {e}"
    finally:
        sys.modules["features.attention"] = real_attention
        sys.modules["features.audio"] = real_audio
        for mod_name in ("features.x_core", "features.episodes"):
            if mod_name in sys.modules:
                del sys.modules[mod_name]
        importlib.import_module("features.x_core")
        importlib.import_module("features.episodes")


# ============================================================
# CHECK 4 -- compatibility-shim isolation (repo-wide, not just features/*)
# ============================================================
#
# stage1_step4_vectors.py re-exports features.geometry/x_core/episodes/
# attention symbols side by side for historical diagnostic scripts (see its
# own "D0PA1 BATCH 1 STEP 3 REFACTOR NOTE" docstring). Checks 1-3 above only
# see the features.* package graph, so an import of that shim BY x_core.py
# or episodes.py -- which would launder an attention/audio reference past
# the block boundary -- is invisible to them. This check is deliberately
# NOT hardcoded to that one filename: it discovers cross-block shims by
# definition (any repo-root module whose AST imports features.attention or
# features.audio anywhere) so a future second shim is caught the same way
# without anyone remembering to add it to a list.

def _repo_root_py_modules():
    """module_name -> absolute file path for every top-level .py file in
    the repo root. Excludes features/ and tests/ (walked separately) and
    non-source directories."""
    modules = {}
    for entry in os.listdir(REPO_ROOT):
        full = os.path.join(REPO_ROOT, entry)
        if entry.endswith(".py") and os.path.isfile(full):
            modules[entry[:-3]] = full
    return modules


def _local_module_table():
    """Every locally-resolvable module this repo defines: repo-root
    '<name>' and 'features.<name>', mapped to file path. Building one
    table across both lets the import graph below span block boundaries
    AND the orchestrator layer, instead of stopping at features/'s edge
    the way checks 1-2 deliberately do."""
    table = dict(_repo_root_py_modules())
    for name in BLOCK_MODULES:
        table["features." + name] = os.path.join(FEATURES_DIR, name + ".py")
    return table


def _direct_local_imports(file_path, local_table):
    """Local module names (keys of local_table) imported anywhere in
    file_path's AST -- module level or nested inside a function/class
    body, same walk-not-scan approach as check 1."""
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in local_table:
                deps.add(mod)
            elif mod.startswith("features."):
                sub = "features." + mod.split(".", 2)[1]
                if sub in local_table:
                    deps.add(sub)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in local_table:
                    deps.add(alias.name)
                else:
                    top = alias.name.split(".")[0]
                    if top in local_table:
                        deps.add(top)
    return deps


def discover_cross_block_shims(local_table):
    """Any repo-root module (not inside features/) whose AST imports
    features.attention or features.audio anywhere is, by definition, a
    module that carries forbidden-block content into whatever namespace
    imports it next -- a cross-block shim, regardless of whether it also
    re-exports x_core/episodes symbols alongside them."""
    shims = set()
    for name, path in local_table.items():
        if name.startswith("features."):
            continue
        deps = _direct_local_imports(path, local_table)
        if "features.attention" in deps or "features.audio" in deps:
            shims.add(name)
    return shims


# D0PA1 audio acquisition task, Task 5.1 -- a gap found by audit, the same
# way the context->attention/audio FORBIDDEN_EDGES gap was found: audio
# acquisition (Task 3) added audio_acquisition.py, a REPO-ROOT module that
# IS U_t content itself (real microphone capture) rather than a features/
# module. discover_cross_block_shims() above only flags a repo-root module
# as forbidden if it IMPORTS features.attention/features.audio -- but
# audio_acquisition.py deliberately does NOT import features.audio (it
# needs no feature-block content, only sounddevice/numpy), so that
# detection-by-re-export logic would never flag it, even though x_core.py
# or episodes.py importing it directly would be exactly the U_t -> X_core /
# U_t -> E_t violation D1 forbids. Named here explicitly, and unioned into
# the forbidden-target set below, rather than only ever checked for
# RE-EXPORTING U_t content -- some modules simply ARE U_t content.
DIRECT_UT_MODULES = {"audio_acquisition"}


def check_shim_isolation():
    local_table = _local_module_table()
    shims = discover_cross_block_shims(local_table)
    direct_ut = DIRECT_UT_MODULES & set(local_table)
    forbidden_targets = shims | direct_ut
    graph = {name: _direct_local_imports(path, local_table) for name, path in local_table.items()}
    violations = []
    for src in ("features.x_core", "features.episodes"):
        reachable = transitive_closure(graph, src)
        for target in sorted(reachable & forbidden_targets):
            path = _find_path(graph, src, target)
            if target in shims:
                reason = "a cross-block compatibility shim that re-exports features.attention/features.audio symbols"
            else:
                reason = "a U_t (audio) module in its own right, not merely a re-exporting shim"
            violations.append(f"{src} imports (transitively) '{target}', {reason} -- path: {' -> '.join(path)}")
    return violations, sorted(shims), sorted(direct_ut)


# ============================================================
# MAIN
# ============================================================

def run_all():
    failures = []

    static_import_violations, graph = check_static_import_graph()
    print("[1/4] STATIC IMPORT GRAPH")
    for name in BLOCK_MODULES:
        print(f"      {name}.py direct features.* imports: {sorted(graph[name]) or '(none)'}")
    if static_import_violations:
        print("      FAIL:")
        for v in static_import_violations:
            print(f"        - {v}")
        failures.extend(static_import_violations)
    else:
        print("      PASS -- x_core.py and episodes.py never import attention.py or audio.py, transitively.")

    static_call_violations = check_static_call_graph()
    print("[2/4] STATIC CALL GRAPH")
    if static_call_violations:
        print("      FAIL:")
        for v in static_call_violations:
            print(f"        - {v}")
        failures.extend(static_call_violations)
    else:
        print("      PASS -- no symbol defined in attention.py/audio.py is referenced by x_core.py/episodes.py.")

    runtime_ok, runtime_message = check_runtime_isolation()
    print("[3/4] RUNTIME MONKEYPATCH (attention/audio raise on any attribute access)")
    if runtime_ok:
        print(f"      PASS -- {runtime_message}")
    else:
        print(f"      FAIL: {runtime_message}")
        failures.append(runtime_message)

    shim_violations, shims_found, direct_ut_found = check_shim_isolation()
    print("[4/4] COMPATIBILITY-SHIM ISOLATION (repo-root modules re-exporting across blocks)")
    print(f"      cross-block shim module(s) discovered: {shims_found or '(none)'}")
    print(f"      direct U_t module(s) present in this repo: {direct_ut_found or '(none)'}")
    if shim_violations:
        print("      FAIL:")
        for v in shim_violations:
            print(f"        - {v}")
        failures.extend(shim_violations)
    else:
        print("      PASS -- x_core.py and episodes.py never import a cross-block shim module.")

    return failures


if __name__ == "__main__":
    failures = run_all()
    print()
    if failures:
        print(f"FEATURE SEPARATION TEST: FAIL ({len(failures)} violation(s))")
        sys.exit(1)
    print("FEATURE SEPARATION TEST: PASS")
