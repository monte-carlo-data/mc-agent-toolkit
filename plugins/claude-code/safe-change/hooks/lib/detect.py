"""dbt model file detection. Phase 1: dbt only. Extensible for future SQL frameworks."""
import os

EXCLUDED_DIRS = {"seeds", "analyses", "macros", "snapshots"}
DBT_EXTENSIONS = {".sql", ".yml", ".yaml"}
REF_PATTERNS = ["{{ ref(", "{{ source("]
MAX_SCAN_LINES = 50


def is_dbt_model(file_path: str) -> bool:
    """Check if file_path is a dbt model SQL file.

    Rules:
    - Extension is .sql only (yml/yaml schema files are tracked by PostToolUse
      but not gated by PreToolUse — they don't map to a single table)
    - Path contains /models/
    - NOT in seeds/, analyses/, macros/, snapshots/
    - Contains {{ ref( or {{ source( in first 50 lines, OR file doesn't exist
      yet (new model being created)
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext != ".sql":
        return False

    # Normalize path separators
    normalized = file_path.replace("\\", "/")

    if "/models/" not in normalized:
        return False

    # Check excluded directories
    parts = normalized.split("/")
    for part in parts:
        if part in EXCLUDED_DIRS:
            return False

    # If file doesn't exist yet, it's a new model being created — treat as dbt model
    if not os.path.exists(file_path):
        return True

    # Existing .sql files must contain ref() or source() in first 50 lines
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= MAX_SCAN_LINES:
                    break
                for pattern in REF_PATTERNS:
                    if pattern in line:
                        return True
    except (OSError, UnicodeDecodeError):
        return False

    return False


def is_dbt_schema_file(file_path: str) -> bool:
    """Check if file_path is a dbt schema yml file under models/.

    Used by PostToolUse for tracking edits, but not for PreToolUse gating.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".yml", ".yaml"):
        return False

    normalized = file_path.replace("\\", "/")
    if "/models/" not in normalized:
        return False

    parts = normalized.split("/")
    for part in parts:
        if part in EXCLUDED_DIRS:
            return False

    return True


def extract_table_name(file_path: str) -> str:
    """Extract table name from file path.

    Example: /project/models/staging/client_hub_master.sql -> client_hub_master
    """
    basename = os.path.basename(file_path)
    name, _ = os.path.splitext(basename)
    return name
