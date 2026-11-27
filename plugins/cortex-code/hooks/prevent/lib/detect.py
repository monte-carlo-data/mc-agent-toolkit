"""dbt SQL file detection. Reads dbt_project.yml paths (cached) instead of hardcoding folder names."""
import os

from lib.cache import find_dbt_project_ymls, get_dbt_paths, get_dbt_project_paths

REF_PATTERNS = ["{{ ref(", "{{ source("]
DBT_BLOCK_PATTERNS = ["{% macro", "{% snapshot"]
MAX_SCAN_LINES = 50

GATED_KEYS = ("model-paths", "macro-paths", "snapshot-paths")
EXCLUDED_KEYS = ("seed-paths", "analysis-paths")
MODEL_KEYS = ("model-paths",)
MACRO_KEYS = ("macro-paths",)


def _folder_names(paths: dict, keys) -> set[str]:
    """The folder names a project's paths give under keys: 'my_models' from 'path/my_models'."""
    return {p.rstrip("/").rsplit("/", 1)[-1] for key in keys for p in paths.get(key, [])}


def _in_dirs(parts, dirs: set[str]) -> bool:
    """True if one of parts is named in dirs, ignoring case.

    On a case-insensitive filesystem (macOS, Windows) `MODELS/` is `models/`; on a
    case-sensitive one the match costs at most an extra assessment.
    """
    return not {p.casefold() for p in parts}.isdisjoint(d.casefold() for d in dirs)


def _parts(path: str) -> list[str]:
    return path.replace("\\", "/").split("/")


def _by_folder_names(path: str, keys) -> bool:
    """The rule on main: the nearest project's folder names, anywhere in the path.

    Seed and analysis names match exactly and the others ignore case, so a difference in
    case only adds gating. Without a dbt_project.yml the default names apply.
    """
    paths = get_dbt_paths(path)
    parts = _parts(path)
    if set(parts) & _folder_names(paths, EXCLUDED_KEYS):
        return False
    return _in_dirs(parts, _folder_names(paths, keys))


def _realpath(path: str, fallback: str) -> str:
    """path with symlinks resolved, or fallback if resolving fails (a link chain too deep
    for realpath's recursion, an unreadable link): canonical paths only add matches."""
    try:
        return os.path.realpath(path)
    except (OSError, ValueError, RecursionError):
        return fallback


def _spellings(file_path: str) -> list[str]:
    """file_path as absolute, and with symlinks resolved, so an alias reaches the
    projects above its target."""
    absolute = os.path.abspath(file_path)
    real = _realpath(file_path, absolute)
    return [absolute] if real == absolute else [absolute, real]


def _projects(path: str) -> list[tuple[str, dict]]:
    """Each readable dbt project above path, as (project folder, its paths).

    A project whose file can't be read is skipped: it says nothing about the file, and
    another project may still own it.
    """
    projects = []
    for yml in find_dbt_project_ymls(path):
        try:
            projects.append((os.path.dirname(yml), get_dbt_project_paths(yml)))
        except OSError:
            continue
    return projects


def _roots(project_dir: str, paths: dict, keys) -> list[str]:
    """The folders a project's paths under keys name, resolved against the project like
    dbt does ('../x' and 'src/models' included), plus their symlink targets."""
    roots = []
    for key in keys:
        for p in paths.get(key, []):
            root = os.path.normpath(os.path.join(project_dir, p))
            roots.append(root)
            real = _realpath(root, root)
            if real != root:
                roots.append(real)
    return roots


def _inside(path: str, roots, ignore_case: bool) -> bool:
    for root in roots:
        a, b = (path.casefold(), root.casefold()) if ignore_case else (path, root)
        if a == b or a.startswith(b.rstrip(os.sep) + os.sep):
            return True
    return False


def _project_holds(path: str, project_dir: str, paths: dict, keys) -> bool:
    """True if path is inside one of the project's folders under keys (any case) and not
    inside one of its seed or analysis folders (exact case)."""
    if _inside(path, _roots(project_dir, paths, EXCLUDED_KEYS), ignore_case=False):
        return False
    return _inside(path, _roots(project_dir, paths, keys), ignore_case=True)


def _counts(file_path: str, keys) -> bool:
    """True if main's folder-name rule or any project above the file counts it under keys.

    Gating is never narrower than main's rule. The exact check adds the files that rule
    misses: a project inside another one's model folder, a seeds or Macros folder above a
    project, configured paths with several segments.
    """
    # The written path first, before anything that resolves symlinks.
    if _by_folder_names(file_path, keys):
        return True
    spellings = _spellings(file_path)
    for path in spellings:
        if path != file_path and _by_folder_names(path, keys):
            return True
    for path in spellings:
        for project_dir, paths in _projects(path):
            if _project_holds(path, project_dir, paths, keys):
                return True
    return False


def _has_dbt_patterns(lines) -> bool:
    """True if any of the first MAX_SCAN_LINES lines holds a dbt ref/source or block."""
    for i, line in enumerate(lines):
        if i >= MAX_SCAN_LINES:
            break
        for pattern in REF_PATTERNS:
            if pattern in line:
                return True
        for pattern in DBT_BLOCK_PATTERNS:
            if pattern in line:
                return True
    return False


MODEL_EXTENSIONS = (".sql",)
SCHEMA_EXTENSIONS = (".yml", ".yaml")


def may_be_dbt_file(path: str) -> bool:
    """Path-only check, for when the file can't be classified: any extension dbt gating acts on.

    Normalised first, since a patch tool writes `models/orders.sql` for `models/orders.sql/`.
    """
    return os.path.normpath(path).lower().endswith(MODEL_EXTENSIONS + SCHEMA_EXTENSIONS)


def is_dbt_model(file_path: str, content: str | None = None) -> bool:
    """Check if file_path is a dbt SQL file that could affect data.

    Gates any .sql file in a dbt project (models, macros, snapshots) since
    macros are inlined into models at compile time and can have equal or
    greater blast radius than a single model change.

    Reads folder names from dbt_project.yml (cached per mtime) so projects
    with custom paths like 'transformations/' instead of 'models/' are handled.

    Rules:
    - Extension is .sql
    - Counted by either rule, for the path as written or with symlinks resolved:
      - main's: a folder in the path is named like one of the nearest project's
        model, macro, or snapshot folders (any case) and none like its seed or
        analysis folders (exact)
      - exact: some dbt_project.yml above the file configures a model, macro, or
        snapshot folder holding it (any case), and no seed or analysis folder of
        that same project holds it (exact)
    - Contains dbt patterns in first 50 lines, OR file doesn't exist yet

    When content is given (for example a staged blob), it is scanned instead of
    the file on disk, and whether the file exists doesn't matter.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in MODEL_EXTENSIONS:
        return False

    if not _counts(file_path, GATED_KEYS):
        return False

    if content is not None:
        return _has_dbt_patterns(content.splitlines())

    # If file doesn't exist yet, it's a new file being created — treat as dbt SQL
    if not os.path.exists(file_path):
        return True

    # Existing .sql files must contain dbt patterns in first 50 lines
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return _has_dbt_patterns(f)
    except (OSError, UnicodeDecodeError):
        return False


def is_dbt_schema_file(file_path: str) -> bool:
    """Check if file_path is a dbt schema yml file under a model directory.

    Used by PostToolUse for tracking edits, but not for PreToolUse gating.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SCHEMA_EXTENSIONS:
        return False

    return _counts(file_path, MODEL_KEYS)


def is_macro_file(file_path: str) -> bool:
    """Check if file_path should be named as a macro.

    Main's rule names it first: a folder in the written path named exactly (same case)
    like one of the nearest project's macro folders. The exact check can only veto
    that, never add a macro name main wouldn't give, so a model never drops out of the
    commit-time table list. When some project's configured model, macro, or snapshot folder holds the
    file, it stays a macro only if a macro folder holds it and no model or snapshot
    folder of any project does: dbt builds models/macros/x.sql as a model.
    """
    if not set(_parts(file_path)) & _folder_names(get_dbt_paths(file_path), MACRO_KEYS):
        return False
    held = set()
    for path in _spellings(file_path):
        for project_dir, paths in _projects(path):
            for key in GATED_KEYS:
                if _inside(path, _roots(project_dir, paths, (key,)), ignore_case=True):
                    held.add(key)
    if held:
        return "macro-paths" in held and not held & {"model-paths", "snapshot-paths"}
    return True


def extract_table_name(file_path: str) -> str:
    """Extract table or macro name from file path.

    Example: /project/models/staging/client_hub_master.sql -> client_hub_master
    Example: /project/macros/filters/internal_accounts.sql -> macro:internal_accounts
    """
    basename = os.path.basename(file_path)
    name, _ = os.path.splitext(basename)
    if is_macro_file(file_path):
        return f"macro:{name}"
    return name
