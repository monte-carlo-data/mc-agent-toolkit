"""dbt model file detection. Phase 1: dbt only. Extensible for future SQL frameworks."""
import os

EXCLUDED_DIRS = {"seeds", "analyses", "macros", "snapshots"}
DBT_EXTENSIONS = {".sql", ".yml", ".yaml"}
REF_PATTERNS = ["{{ ref(", "{{ source("]
MAX_SCAN_LINES = 50


def is_dbt_model(file_path: str) -> bool:
    """Check if file_path is a dbt model file.

    Rules:
    - Extension is .sql, .yml, or .yaml
    - Path contains /models/
    - NOT in seeds/, analyses/, macros/, snapshots/
    - For .sql files: contains {{ ref( or {{ source( in first 50 lines
    - For .yml/.yaml files: always True if above conditions met
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in DBT_EXTENSIONS:
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

    # .yml files in models/ are always dbt schema files
    if ext in (".yml", ".yaml"):
        return True

    # .sql files must contain ref() or source() in first 50 lines
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


def extract_table_name(file_path: str) -> str:
    """Extract table name from file path.

    Example: /project/models/staging/client_hub_master.sql -> client_hub_master
    """
    basename = os.path.basename(file_path)
    name, _ = os.path.splitext(basename)
    return name
