"""Per-table session cache backed by temp files.

All state lives under /tmp/mc_safe_change_*. No external dependencies.
Cleans up naturally on reboot.

Workflow 4 gate uses three states:
  absent -> injected (instruction sent, waiting for completion)
  injected -> verified (MC_WORKFLOW4_COMPLETE marker found in transcript)
"""
import json
import os
import time

CACHE_DIR = "/tmp"
W4_PREFIX = "mc_safe_change_w4_"
TURN_PREFIX = "mc_safe_change_turn_"
PENDING_PREFIX = "mc_safe_change_pending_"


def _w4_path(table_name: str) -> str:
    return os.path.join(CACHE_DIR, f"{W4_PREFIX}{table_name}")


def _turn_path(session_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{TURN_PREFIX}{session_id}")


def _pending_path(session_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{PENDING_PREFIX}{session_id}")


# --- Workflow 4 three-state marker ---

def get_workflow4_state(table_name: str) -> str | None:
    """Returns None, 'injected', or 'verified'."""
    path = _w4_path(table_name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data.get("state")
    except (json.JSONDecodeError, OSError):
        return None


def mark_workflow4_injected(table_name: str) -> None:
    path = _w4_path(table_name)
    with open(path, "w") as f:
        json.dump({"state": "injected", "timestamp": time.time()}, f)


def mark_workflow4_verified(table_name: str) -> None:
    path = _w4_path(table_name)
    # Preserve timestamp from injection
    timestamp = time.time()
    try:
        with open(path, "r") as f:
            data = json.load(f)
            timestamp = data.get("timestamp", timestamp)
    except (json.JSONDecodeError, OSError):
        pass
    with open(path, "w") as f:
        json.dump({"state": "verified", "timestamp": timestamp}, f)


def get_marker_age_seconds(table_name: str) -> float:
    path = _w4_path(table_name)
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return time.time() - data.get("timestamp", time.time())
    except (json.JSONDecodeError, OSError):
        return 0.0


# --- Turn-level edit accumulator ---

def get_edited_tables(session_id: str) -> list[str]:
    path = _turn_path(session_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            tables = [line.strip() for line in f if line.strip()]
        return list(dict.fromkeys(tables))  # deduplicate, preserve order
    except OSError:
        return []


def add_edited_table(session_id: str, table_name: str) -> None:
    existing = get_edited_tables(session_id)
    if table_name in existing:
        return
    path = _turn_path(session_id)
    with open(path, "a") as f:
        f.write(table_name + "\n")


def clear_edited_tables(session_id: str) -> None:
    path = _turn_path(session_id)
    if os.path.exists(path):
        os.remove(path)


# --- Pending validation ---

def move_to_pending_validation(session_id: str) -> None:
    tables = get_edited_tables(session_id)
    if tables:
        path = _pending_path(session_id)
        with open(path, "w") as f:
            for t in tables:
                f.write(t + "\n")
    clear_edited_tables(session_id)


def get_pending_validation_tables(session_id: str) -> list[str]:
    path = _pending_path(session_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except OSError:
        return []


def clear_pending_validation(session_id: str) -> None:
    path = _pending_path(session_id)
    if os.path.exists(path):
        os.remove(path)
