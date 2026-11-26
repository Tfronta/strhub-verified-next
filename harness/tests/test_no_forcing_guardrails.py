"""Architectural guardrails enforcing the Non-Forcing Principle across the automatic engine.

These checks run in CI (`verify.yml` -> `Harness tests`) BEFORE any repository is
evaluated. They make it structurally impossible to introduce:
  1. Tool-specific or author-specific heuristics/conditionals (`if slug == "hipstr"`, etc.)
     in any automatic evaluation or assisted-remediation module.
  2. Imports of legacy hand-crafted `preparations/` modules from automatic workflows.
  3. Writable mounts of `/app` (the upstream repository checkout at runtime must stay `:ro`).
  4. More than a single deterministic assisted retry (`MAX_ASSISTED_ATTEMPTS == 1`).
"""
from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"

#: Modules that execute on automatic / URL-submitted trials (Track 1 + Track 2).
#: None of these may branch on a tool's name, repository owner, or hand-written recipe.
AUTOMATIC_MODULES = (
    "harness/propose_manifest.py",
    "harness/documented_install.py",
    "harness/source_install.py",
    "harness/procedure.py",
    "harness/fidelity.py",
    "harness/verdict.py",
    "harness/assisted_remediation.py",
    "harness/engine/runner.py",
    "harness/engine/stages.py",
)

#: Known STR tool names / slugs that must NEVER appear in executable code of
#: automatic modules (docstrings and comments are excluded via AST inspection).
FORBIDDEN_TOOL_TOKENS = frozenset({
    "hipstr",
    "straglr",
    "nanorepeat",
    "repeathmm",
    "longtr",
    "expansionhunter",
    "expansionhunterdenovo",
    "strspy",
    "straitrazor",
    "str8rzr",
    "fdstools",
    "lobstr",
    "lusstr",
    "mpsproto",
    "stretch",
    "strique",
    "strkit",
    "strling",
    "strsearch",
    "toastr",
    "trgt",
    "trtools",
    "vamos",
    "mahi-mahi",
    "mahi_mahi",
    "gangstr",
    "tandem-genotypes",
    "popstr",
    "ensembletr",
})


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                ids.add(id(node.body[0].value))
    return ids


def test_no_tool_specific_identifiers_in_automatic_engine_ast():
    violations: list[str] = []
    for rel in AUTOMATIC_MODULES:
        path = ROOT / rel
        assert path.is_file(), f"Expected automatic engine module is missing: {rel}"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        doc_ids = _docstring_node_ids(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
                lowered = node.value.lower()
                for token in FORBIDDEN_TOOL_TOKENS:
                    if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered):
                        violations.append(f"{rel}:{node.lineno} contains tool-specific literal '{token}' in {node.value!r}")
            elif isinstance(node, ast.Name):
                lowered = node.id.lower()
                for token in FORBIDDEN_TOOL_TOKENS:
                    norm = token.replace("-", "_")
                    if norm in lowered:
                        violations.append(f"{rel}:{node.lineno} contains tool-specific identifier '{node.id}'")
    assert not violations, (
        "Tool-specific heuristics are strictly prohibited in automatic/assisted modules:\n  - "
        + "\n  - ".join(violations)
    )


def test_no_legacy_preparations_imported_in_automatic_engine():
    # Note: `fidelity.py` is the shared boundary validator that also verifies
    # standalone `strhub-prepared-environment/1` manual runs when `environment.source == "prepared"`,
    # whereas its `literal_profiles()` and every automatic discovery/remediation/runner module
    # must NEVER import `preparation` or `preparations`.
    non_manual_modules = tuple(m for m in AUTOMATIC_MODULES if m != "harness/fidelity.py")
    violations: list[str] = []
    for rel in non_manual_modules:
        path = ROOT / rel
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("preparation", "preparations") or alias.name.startswith("preparations."):
                        violations.append(f"{rel}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in ("preparation", "preparations") or mod.startswith("preparations."):
                    violations.append(f"{rel}:{node.lineno} imports from {mod}")
    assert not violations, (
        "Automatic/assisted engine modules must never import hand-written preparations:\n  - "
        + "\n  - ".join(violations)
    )

    import sys
    if str(HARNESS) not in sys.path:
        sys.path.insert(0, str(HARNESS))
    import fidelity
    literal_names = {m.__name__ for m in fidelity.literal_profiles()}
    assert literal_names == {"source_install", "documented_install"}, (
        f"fidelity.literal_profiles() must never include manual preparations: {literal_names}"
    )


def test_upstream_checkout_mount_is_always_read_only_and_bounded():
    import sys
    sys.path.insert(0, str(HARNESS))
    import assisted_remediation

    assert assisted_remediation.MAX_ASSISTED_ATTEMPTS == 1, (
        "Assisted remediation must execute at most 1 deterministic pass per workflow run."
    )

    for rel in ("harness/engine/stages.py", "harness/assisted_remediation.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        # Every :/app mount must explicitly carry :ro
        mounts = re.findall(r":/app(?::[a-z]+)?", text)
        assert mounts, f"Expected explicit :/app:ro mount in {rel}"
        bad = [m for m in mounts if m != ":/app:ro"]
        assert not bad, f"Writable /app mount detected in {rel}: {bad}"
