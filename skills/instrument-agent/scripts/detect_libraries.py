#!/usr/bin/env python3
"""
Detect runtime classification, dependency surface, and any existing Monte
Carlo OpenTelemetry setup in a Python codebase.

The script is intentionally a thin discovery layer. It walks dependency
manifests (requirements.txt, pyproject.toml, Pipfile), serverless deployment
markers, and existing `mc.setup()` calls — then emits a JSON document the
skill consumes. The script does **not** classify AI libraries or pick
instrumentor packages; that is the LLM's job, working from `dependencies[]`
plus the live PyPI list from `fetch_sdk_docs.py`.

Usage:
    python3 detect_libraries.py [TARGET_PATH]

TARGET_PATH defaults to the current working directory. Output is JSON
on stdout. Exit code is 0 on success and 1 on hard errors (missing or
unreadable target path).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB per-file cap

SKIP_DIRS = {
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".git",
    "dist",
    "build",
    "target",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
}

SERVERLESS_FILES = {
    "serverless.yml",
    "serverless.yaml",
    "template.yaml",
    "template.yml",
    "vercel.json",
    "netlify.toml",
    "wrangler.toml",
    "zappa_settings.json",
    "modal.toml",
}

SERVERLESS_DEPS = {
    "aws-lambda-powertools",
    "mangum",
    "chalice",
    "zappa",
    "aws-cdk-lib",
    "aws-sam-cli",
    "modal",
    "sst",
}

SERVERLESS_CODE_PATTERNS = [
    re.compile(r"def\s+lambda_handler\s*\("),
    re.compile(r"from\s+chalice\s+import\s+Chalice"),
    re.compile(r"from\s+mangum\s+import\s+Mangum"),
    re.compile(r"app\s*=\s*Chalice\s*\("),
]

# Existing-setup detection requires BOTH an import of montecarlo_opentelemetry
# AND an actual setup() call in the same file. Matching on imports alone
# false-positives any file that uses the SDK's decorators (e.g. handler.py
# importing `montecarlo_opentelemetry as mc` to use `@mc.trace_with_workflow`)
# but doesn't actually call setup().
EXISTING_SETUP_IMPORT_PATTERNS = [
    "import montecarlo_opentelemetry",
    "from montecarlo_opentelemetry",
]
EXISTING_SETUP_FALLBACK_CALL_PATTERN = re.compile(
    r"\b(?:mc|montecarlo_opentelemetry)\.setup\s*\("
)


# ---------------------------------------------------------------------------
# TOML loader (stdlib tomllib in 3.11+, fall back to tomli, else None)
# ---------------------------------------------------------------------------


def _load_toml_module():
    try:
        import tomllib  # type: ignore[import-not-found]

        return tomllib
    except ImportError:
        pass
    try:
        import tomli  # type: ignore[import-not-found]

        return tomli
    except ImportError:
        return None


_TOML = _load_toml_module()


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def _is_within(path: Path, root: Path) -> bool:
    """True if `path` (resolved) is inside `root` (resolved)."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    try:
        resolved.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_read_text(path: Path) -> str | None:
    """Read a file as UTF-8 text, skipping if too large or unreadable."""
    try:
        size = path.stat().st_size
    except OSError as exc:
        print(f"warning: cannot stat {path}: {exc}", file=sys.stderr)
        return None
    if size > MAX_FILE_BYTES:
        print(
            f"warning: skipping {path} ({size} bytes exceeds {MAX_FILE_BYTES})",
            file=sys.stderr,
        )
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"warning: cannot read {path}: {exc}", file=sys.stderr)
        return None


def _walk_files(root: Path) -> Iterable[Path]:
    """Yield files under root, skipping noise dirs and out-of-tree symlinks."""
    root_resolved = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Filter directories in-place so os.walk doesn't descend into them.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        # Drop any dir that resolves outside the target tree (symlink escape).
        kept: list[str] = []
        for d in dirnames:
            full = Path(dirpath) / d
            if _is_within(full, root_resolved):
                kept.append(d)
        dirnames[:] = kept

        for name in filenames:
            full = Path(dirpath) / name
            if full.is_symlink() and not _is_within(full, root_resolved):
                continue
            yield full


# ---------------------------------------------------------------------------
# Dependency parsing
# ---------------------------------------------------------------------------

# PEP 508 / requirements line — captures the project name only.
# Allowed name characters per PEP 508: letters, digits, ., -, _
_REQ_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
_EGG_RE = re.compile(r"[#&]egg=([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalize_dep(name: str) -> str:
    return name.strip().lower()


def _parse_requirements_line(line: str) -> str | None:
    """Extract a package name from a single requirements.txt line, or None."""
    raw = line.strip()
    if not raw:
        return None
    # Strip inline comments — preserve URLs that contain '#egg=' first.
    if "#egg=" not in raw and "#" in raw:
        raw = raw.split("#", 1)[0].strip()
    if not raw:
        return None

    lowered = raw.lower()

    # Skip include directives and pip flags.
    if (
        lowered.startswith("-r ")
        or lowered.startswith("--requirement ")
        or lowered.startswith("-c ")
        or lowered.startswith("--constraint ")
        or lowered.startswith("--index-url")
        or lowered.startswith("--extra-index-url")
        or lowered.startswith("--find-links")
        or lowered.startswith("--no-")
        or lowered.startswith("--pre")
        or lowered.startswith("--trusted-host")
    ):
        return None

    # Editable / VCS / URL specs — name comes from #egg=<name>.
    # Note: bare "-e ./local_pkg" without #egg= yields no package name and is skipped.
    if (
        lowered.startswith("-e ")
        or lowered.startswith("--editable ")
        or lowered.startswith("git+")
        or lowered.startswith("hg+")
        or lowered.startswith("svn+")
        or lowered.startswith("bzr+")
        or lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("file://")
    ):
        m = _EGG_RE.search(raw)
        return _normalize_dep(m.group(1)) if m else None

    # Drop any "[extras]" segment, then match the leading package name.
    bracket = raw.find("[")
    if bracket > 0:
        candidate = raw[:bracket]
    else:
        candidate = raw
    m = _REQ_NAME_RE.match(candidate)
    return _normalize_dep(m.group(1)) if m else None


def _parse_requirements_file(path: Path) -> list[str]:
    text = _safe_read_text(path)
    if text is None:
        return []
    deps: list[str] = []
    try:
        for line in text.splitlines():
            name = _parse_requirements_line(line)
            if name:
                deps.append(name)
    except Exception as exc:  # noqa: BLE001 — tolerate any parse glitch
        print(f"warning: failed to parse {path}: {exc}", file=sys.stderr)
    return deps


def _pep508_name(spec: str) -> str | None:
    """Pull the project name from a PEP 508 requirement string."""
    candidate = spec.strip()
    if not candidate:
        return None
    bracket = candidate.find("[")
    if bracket > 0:
        candidate = candidate[:bracket]
    m = _REQ_NAME_RE.match(candidate)
    return _normalize_dep(m.group(1)) if m else None


def _parse_pyproject(path: Path) -> list[str]:
    if _TOML is None:
        print(
            f"warning: skipping {path} — no TOML parser available "
            "(install tomli or use Python 3.11+)",
            file=sys.stderr,
        )
        return []
    text = _safe_read_text(path)
    if text is None:
        return []
    try:
        data = _TOML.loads(text)
    except Exception as exc:  # noqa: BLE001
        print(f"warning: failed to parse {path}: {exc}", file=sys.stderr)
        return []

    deps: list[str] = []

    # PEP 621: [project] dependencies + optional-dependencies.
    project = data.get("project") if isinstance(data, dict) else None
    if isinstance(project, dict):
        for spec in project.get("dependencies", []) or []:
            if isinstance(spec, str):
                name = _pep508_name(spec)
                if name:
                    deps.append(name)
        opt = project.get("optional-dependencies") or {}
        if isinstance(opt, dict):
            for group in opt.values():
                if not isinstance(group, list):
                    continue
                for spec in group:
                    if isinstance(spec, str):
                        name = _pep508_name(spec)
                        if name:
                            deps.append(name)

    # Poetry: [tool.poetry.dependencies] + [tool.poetry.group.<g>.dependencies]
    tool = data.get("tool") if isinstance(data, dict) else None
    poetry = tool.get("poetry") if isinstance(tool, dict) else None
    if isinstance(poetry, dict):
        poetry_deps = poetry.get("dependencies") or {}
        if isinstance(poetry_deps, dict):
            for name in poetry_deps.keys():
                if isinstance(name, str) and name.lower() != "python":
                    deps.append(_normalize_dep(name))
        groups = poetry.get("group") or {}
        if isinstance(groups, dict):
            for group in groups.values():
                if not isinstance(group, dict):
                    continue
                gdeps = group.get("dependencies") or {}
                if isinstance(gdeps, dict):
                    for name in gdeps.keys():
                        if isinstance(name, str) and name.lower() != "python":
                            deps.append(_normalize_dep(name))

    return deps


def _parse_pipfile(path: Path) -> list[str]:
    if _TOML is None:
        print(
            f"warning: skipping {path} — no TOML parser available "
            "(install tomli or use Python 3.11+)",
            file=sys.stderr,
        )
        return []
    text = _safe_read_text(path)
    if text is None:
        return []
    try:
        data = _TOML.loads(text)
    except Exception as exc:  # noqa: BLE001
        print(f"warning: failed to parse {path}: {exc}", file=sys.stderr)
        return []

    deps: list[str] = []
    for section in ("packages", "dev-packages"):
        section_data = data.get(section) if isinstance(data, dict) else None
        if isinstance(section_data, dict):
            for name in section_data.keys():
                if isinstance(name, str):
                    deps.append(_normalize_dep(name))
    return deps


def _scan_tree(target: Path) -> dict:
    """Walk *target* once and bucket files by role.

    Returns a dict with:
    - ``dep_files``: paths to dependency manifests (requirements*.txt,
      pyproject.toml, Pipfile).
    - ``serverless_files``: paths whose filename matches SERVERLESS_FILES.
    - ``py_files``: paths to ``*.py`` source files.
    - ``py_contents``: ``{path: text}`` — eagerly read content of each Python
      file (None values are omitted; callers treat a missing key as unreadable).
    """
    dep_files: list[Path] = []
    serverless_files: list[Path] = []
    py_files: list[Path] = []
    py_contents: dict[Path, str] = {}

    serverless_names_lower = {n.lower() for n in SERVERLESS_FILES}

    for path in _walk_files(target):
        name = path.name
        lower = name.lower()
        suffix = path.suffix.lower()

        if lower == "requirements.txt" or (
            lower.startswith("requirements") and lower.endswith(".txt")
        ):
            dep_files.append(path)
        elif lower == "pyproject.toml":
            dep_files.append(path)
        elif lower == "pipfile":
            dep_files.append(path)

        if lower in serverless_names_lower:
            serverless_files.append(path)

        if suffix == ".py":
            py_files.append(path)
            text = _safe_read_text(path)
            if text is not None:
                py_contents[path] = text

    return {
        "dep_files": dep_files,
        "serverless_files": serverless_files,
        "py_files": py_files,
        "py_contents": py_contents,
    }


def _collect_dependencies(scan: dict) -> set[str]:
    """Collect normalized dep names from pre-scanned manifest files."""
    found: set[str] = set()
    for path in scan["dep_files"]:
        lower = path.name.lower()
        if lower == "requirements.txt" or (
            lower.startswith("requirements") and lower.endswith(".txt")
        ):
            found.update(_parse_requirements_file(path))
        elif lower == "pyproject.toml":
            found.update(_parse_pyproject(path))
        elif lower == "pipfile":
            found.update(_parse_pipfile(path))
    return found


# ---------------------------------------------------------------------------
# Runtime detection
# ---------------------------------------------------------------------------


def _detect_serverless(scan: dict, deps: set[str]) -> list[str]:
    """Return the list of serverless signals observed."""
    signals: list[str] = []

    # File-level markers — check anywhere in the walked tree; this catches
    # monorepo subprojects too.
    seen_files: set[str] = set()
    for path in scan["serverless_files"]:
        if path.name not in seen_files:
            signals.append(path.name)
            seen_files.add(path.name)

    # Dependency markers.
    for dep in sorted(deps):
        if dep in SERVERLESS_DEPS:
            signals.append(dep)

    # Code patterns — only meaningful tokens, not which file they came from.
    code_signals: set[str] = set()
    code_signal_labels = {
        SERVERLESS_CODE_PATTERNS[0]: "lambda_handler",
        SERVERLESS_CODE_PATTERNS[1]: "chalice_import",
        SERVERLESS_CODE_PATTERNS[2]: "mangum_import",
        SERVERLESS_CODE_PATTERNS[3]: "chalice_app",
    }
    py_contents = scan["py_contents"]
    for path in scan["py_files"]:
        text = py_contents.get(path)
        if text is None:
            continue
        for pattern, label in code_signal_labels.items():
            if label in code_signals:
                continue
            if pattern.search(text):
                code_signals.add(label)
        if len(code_signals) == len(code_signal_labels):
            break
    signals.extend(sorted(code_signals))

    return signals


# ---------------------------------------------------------------------------
# Existing setup detection
# ---------------------------------------------------------------------------


def _has_existing_setup_call(text: str) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        has_import = any(pat in text for pat in EXISTING_SETUP_IMPORT_PATTERNS)
        return has_import and bool(EXISTING_SETUP_FALLBACK_CALL_PATTERN.search(text))

    module_aliases: set[str] = set()
    setup_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "montecarlo_opentelemetry":
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module != "montecarlo_opentelemetry":
                continue
            for alias in node.names:
                if alias.name == "setup":
                    setup_names.add(alias.asname or alias.name)
                elif alias.name == "*":
                    setup_names.add("setup")

    if not module_aliases and not setup_names:
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "setup"
            and isinstance(func.value, ast.Name)
            and func.value.id in module_aliases
        ):
            return True
        if isinstance(func, ast.Name) and func.id in setup_names:
            return True

    return False


def _detect_existing_setup(scan: dict, target: Path) -> dict:
    files: list[str] = []
    target_resolved = target.resolve()
    py_contents = scan["py_contents"]
    for path in scan["py_files"]:
        text = py_contents.get(path)
        if text is None:
            continue
        if not _has_existing_setup_call(text):
            continue
        try:
            rel = path.resolve().relative_to(target_resolved)
            files.append(str(rel))
        except ValueError:
            files.append(str(path))
    files.sort()
    return {"found": bool(files), "files": files}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def detect(target: Path) -> dict:
    scan = _scan_tree(target)
    deps = _collect_dependencies(scan)

    serverless_signals = _detect_serverless(scan, deps)
    if serverless_signals:
        runtime = "serverless"
    elif scan["dep_files"]:
        runtime = "long_running"
    else:
        runtime = "unknown"

    existing_setup = _detect_existing_setup(scan, target)

    return {
        "dependencies": sorted(deps),
        "runtime": runtime,
        "serverless_signals": serverless_signals,
        "existing_setup": existing_setup,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Detect runtime style, Python dependencies, and any existing "
            "Monte Carlo OpenTelemetry setup in a codebase. AI-library "
            "matching is the LLM's job; this script just emits the raw "
            "discovery surface."
        )
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Path to the codebase to scan (defaults to the current directory).",
    )
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(
            json.dumps({"error": f"Target path does not exist: {target}"}, indent=2)
        )
        sys.exit(1)
    if not target.is_dir():
        print(
            json.dumps({"error": f"Target path is not a directory: {target}"}, indent=2)
        )
        sys.exit(1)
    if not os.access(target, os.R_OK):
        print(
            json.dumps({"error": f"Target path is not readable: {target}"}, indent=2)
        )
        sys.exit(1)

    try:
        result = detect(target)
    except OSError as exc:
        print(json.dumps({"error": f"Filesystem error: {exc}"}, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
