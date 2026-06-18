"""dbt SQL file detection. Reads dbt_project.yml paths (cached) instead of hardcoding folder names."""
import os

from lib.cache import get_dbt_paths

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


def is_dbt_model(file_path: str) -> bool:
    """Check if file_path is a dbt SQL file that could affect data.

    Gates any .sql file in a dbt project (models, macros, snapshots) since
    macros are inlined into models at compile time and can have equal or
    greater blast radius than a single model change.

    Reads folder names from dbt_project.yml (cached per mtime) so projects
    with custom paths like 'transformations/' instead of 'models/' are handled.

    Rules:
    - Extension is .sql
    - NOT in seed or analysis directories
    - IS in a model, macro, or snapshot directory
    - Contains dbt patterns in first 50 lines, OR file doesn't exist yet
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext != ".sql":
        return False

    normalized = file_path.replace("\\", "/")
    parts = set(normalized.split("/"))

    # Check excluded directories (seeds, analyses)
    excluded = _get_excluded_dirs(file_path)
    if parts & excluded:
        return False

    # Must be inside a gated directory (models, macros, snapshots)
    gated = _get_gated_dirs(file_path)
    if not (parts & gated):
        return False

    # If file doesn't exist yet, it's a new file being created — treat as dbt SQL
    if not os.path.exists(file_path):
        return True

    # Existing .sql files must contain dbt patterns in first 50 lines
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= MAX_SCAN_LINES:
                    break
                for pattern in REF_PATTERNS:
                    if pattern in line:
                        return True
                for pattern in DBT_BLOCK_PATTERNS:
                    if pattern in line:
                        return True
    except (OSError, UnicodeDecodeError):
        return False

    return False


def is_dbt_schema_file(file_path: str) -> bool:
    """Check if file_path is a dbt schema yml file under a model directory.

    Used by PostToolUse for tracking edits, but not for PreToolUse gating.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".yml", ".yaml"):
        return False

    normalized = file_path.replace("\\", "/")
    parts = set(normalized.split("/"))

    excluded = _get_excluded_dirs(file_path)
    if parts & excluded:
        return False

    paths = get_dbt_paths(file_path)
    model_dirs = {p.rstrip("/").rsplit("/", 1)[-1] for p in paths.get("model-paths", [])}
    return bool(parts & model_dirs)


def is_macro_file(file_path: str) -> bool:
    """Check if file_path is under a macro directory."""
    normalized = file_path.replace("\\", "/")
    parts = set(normalized.split("/"))
    macro_dirs = _get_macro_dirs(file_path)
    return bool(parts & macro_dirs)


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
