"""Constants, config loaders, and shared helpers for live evals."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

EVALS_DIR = Path(__file__).parent
PLUGIN_DIR = EVALS_DIR.parent
SKILLS_DIR = PLUGIN_DIR / "skills"

load_dotenv(EVALS_DIR / ".env")

MCP_SERVER_NAME = "monte-carlo"

MCP_URLS = {
    "dev": "https://mcp.dev.getmontecarlo.com/mcp",
    "prod": "https://mcp.getmontecarlo.com/mcp",
}


def get_mcp_server_config(env: str) -> dict:
    """Build the streamable-HTTP MCP server config for the given environment."""
    if env == "prod":
        mcd_id = os.environ.get("MCD_ID")
        mcd_token = os.environ.get("MCD_TOKEN")
        if not mcd_id or not mcd_token:
            print("Error: Set MCD_ID and MCD_TOKEN for prod evals")
            sys.exit(1)
    else:
        mcd_id = os.environ.get("MCD_ID_DEV")
        mcd_token = os.environ.get("MCD_TOKEN_DEV")
        if not mcd_id or not mcd_token:
            print("Error: Set MCD_ID_DEV and MCD_TOKEN_DEV for dev evals")
            sys.exit(1)

    return {
        MCP_SERVER_NAME: {
            "type": "http",
            "url": MCP_URLS[env],
            "headers": {
                "x-mcd-id": mcd_id,
                "x-mcd-token": mcd_token,
            },
        }
    }


def load_skill_content(skill_name: str) -> str:
    """Read the full SKILL.md content for appending to system prompt."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: SKILL.md not found: {skill_md}")
        sys.exit(1)
    return skill_md.read_text()
