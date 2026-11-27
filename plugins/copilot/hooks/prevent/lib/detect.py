"""dbt SQL file detection. Reads dbt_project.yml paths (cached) instead of hardcoding folder names."""
import os

from lib.cache import find_dbt_project_dir, get_dbt_paths

REF_PATTERNS = ["{{ ref(", "{{ source("]
DBT_BLOCK_PATTERNS = ["{% macro", "{% snapshot"]
MAX_SCAN_LINES = 50


def _get_gated_dirs(file_path: str) -> set[str]:
    """Return directory names that should be gated (models, macros, snapshots)."""
    paths = get_dbt_paths(file_path)
    gated = set()
    for key in ("model-paths", "macro-paths", "snapshot-paths"):
        for p in paths.get(key, []):
            # Take last component: 'models' from 'models', 'my_models' from 'path/my_models'
            gated.add(p.rstrip("/").rsplit("/", 1)[-1])
    return gated


def _get_excluded_dirs(file_path: str) -> set[str]:
    """Return directory names that should be excluded from gating (seeds, analyses)."""
    paths = get_dbt_paths(file_path)
    excluded = set()
    for key in ("seed-paths", "analysis-paths"):
        for p in paths.get(key, []):
            excluded.add(p.rstrip("/").rsplit("/", 1)[-1])
    return excluded


def _get_macro_dirs(file_path: str) -> set[str]:
    """Return directory names configured as macro paths."""
    paths = get_dbt_paths(file_path)
    return {p.rstrip("/").rsplit("/", 1)[-1] for p in paths.get("macro-paths", [])}


def _folder_parts(file_path: str) -> list[str]:
    """The components of file_path that can name a dbt folder.

    With a dbt_project.yml above the file, only those below the project folder count: a
    folder above the project named `seeds` or `Macros` says nothing about the file. Without
    one, every component counts.
    """
    project_dir = find_dbt_project_dir(file_path)
    if project_dir:
        file_path = os.path.relpath(file_path, project_dir)
    return file_path.replace("\\", "/").split("/")


def _in_dirs(parts: list[str], dirs: set[str]) -> bool:
    """True if one of parts (from _folder_parts) is named in dirs, ignoring case.

    On a case-insensitive filesystem (macOS, Windows) `MODELS/` is `models/`; on a
    case-sensitive one the match costs at most an extra assessment.
    """
    return not {p.casefold() for p in parts}.isdisjoint(d.casefold() for d in dirs)


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
    - NOT in seed or analysis directories (exact folder name)
    - IS in a model, macro, or snapshot directory (folder name in any case)
    - Folders count only below the dbt_project.yml folder, when there is one
    - Contains dbt patterns in first 50 lines, OR file doesn't exist yet

    When content is given (for example a staged blob), it is scanned instead of
    the file on disk, and whether the file exists doesn't matter.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in MODEL_EXTENSIONS:
        return False

    parts = _folder_parts(file_path)

    # Check excluded directories (seeds, analyses)
    if set(parts) & _get_excluded_dirs(file_path):
        return False

    # Must be inside a gated directory (models, macros, snapshots). Exclusions match
    # exactly and gated folders ignore case, so a difference in case only adds gating.
    if not _in_dirs(parts, _get_gated_dirs(file_path)):
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

    parts = _folder_parts(file_path)

    if set(parts) & _get_excluded_dirs(file_path):
        return False

    paths = get_dbt_paths(file_path)
    model_dirs = {p.rstrip("/").rsplit("/", 1)[-1] for p in paths.get("model-paths", [])}
    return _in_dirs(parts, model_dirs)


def is_macro_file(file_path: str) -> bool:
    """Check if file_path is under a macro directory, matched like the gated ones."""
    return _in_dirs(_folder_parts(file_path), _get_macro_dirs(file_path))


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
