#!/usr/bin/env python3
"""PreToolUse/Bash hook (Codex adapter): unified handler for all Bash tool calls.

Codex routes apply_patch, git commit, and other commands through the Bash tool.
This hook dispatches to the appropriate shared logic:
  - apply_patch → pre_edit gate + post_edit tracking
  - git commit  → pre_commit validation checkpoint
  - everything else → noop
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, HookOutput, evaluate_pre_edit, evaluate_post_edit, evaluate_pre_commit

_UPDATE_FILE_RE = re.compile(r"\*\*\*\s+Update File:\s+(.+)")


def _extract_patch_files(command: str) -> list[str]:
    """Extract file paths from an apply_patch command."""
    return _UPDATE_FILE_RE.findall(command)


@safe_run
def main():
    raw = json.load(sys.stdin)
    session_id = raw.get("session_id", "unknown")
    command = raw.get("tool_input", {}).get("command", "")
    cwd = raw.get("cwd", ".")
    transcript_path = raw.get("transcript_path", "")

    # --- apply_patch: pre_edit gate + post_edit tracking ---
    # Codex may prefix with "cd <dir> &&" before apply_patch
    if "apply_patch" in command:
        files = _extract_patch_files(command)
        for file_path in files:
            # Resolve relative paths against cwd
            if not os.path.isabs(file_path):
                file_path = os.path.join(cwd, file_path)

            # Run pre_edit check — deny if impact assessment hasn't run
            inp = HookInput(
                session_id=session_id,
                file_path=file_path,
                transcript_path=transcript_path,
            )
            result = evaluate_pre_edit(inp)
            if result.action == "deny":
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": result.reason,
                    }
                }))
                return

            # Track the edit (post_edit) — since Codex won't send PostToolUse
            evaluate_post_edit(inp)
        return

    # --- git commit: pre_commit validation checkpoint ---
    if "git commit" in command:
        inp = HookInput(
            session_id=session_id,
            command=command,
            cwd=cwd,
        )
        result = evaluate_pre_commit(inp)
        if result.action == "context":
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": result.context,
                }
            }))
        return


if __name__ == "__main__":
    main()
