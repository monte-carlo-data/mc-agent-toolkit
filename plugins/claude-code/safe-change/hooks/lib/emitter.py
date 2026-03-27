"""Event assembly and non-blocking emission to Monte Carlo.

Assembles change events from local cache state and sends them via a daemon
thread POST. Never blocks the hook, never throws to the caller.
"""
import json
import os
import subprocess
import threading
import urllib.request
from datetime import datetime, timezone

MC_CHANGE_EVENTS_URL = os.environ.get(
    "MC_CHANGE_EVENTS_URL",
    "https://integrations.getmontecarlo.com/plugin/change-events",
)


def _get_git_identity():
    """Read git user.email and user.name via subprocess."""
    try:
        email = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        name = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return {"git_email": email, "git_name": name}
    except Exception:
        return {"git_email": "", "git_name": ""}
