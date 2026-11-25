#!/usr/bin/env python3
"""PreToolUse hook (Codex adapter) for the Bash and apply_patch tools.

Codex edits files with `apply_patch`, sent two ways:
  - its own `apply_patch` tool (Codex 0.124.0+): `tool_input.command` is the patch.
    Codex sends PostToolUse after a successful patch, and post_edit_hook.py tracks it.
  - a shell command (`tool_name` "Bash") such as `cd <dir> && apply_patch <<'EOF'`.
    No PostToolUse follows a patch Codex applies from the shell, so this hook tracks
    the files itself once the command is allowed.
Every file a patch adds, deletes, updates or moves (both paths) is checked before it
runs, and the patch is denied as a whole when any of them needs an impact assessment.
Only the two shell forms Codex applies itself are gated this way (see shell_patch.py).
Any other shell command that names `apply_patch`, even only as a mention, is denied as
one Prevent couldn't check, whatever it holds; `MC_PREVENT_HOOKS_DISABLED=1` lifts that.

Other Bash commands with `git commit` get the pre-commit validation checkpoint.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.apply_patch import (
    gate_and_remember, gate_patch, link_targets, op_groups, parse_operations, resolve_path,
)
from lib.protocol import (
    HookInput, _prevent_hooks_disabled, evaluate_pre_commit, evaluate_pre_edit, evaluate_post_edit,
)
from shell_patch import find_invocation, names_apply_patch


def _deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def _make_input(raw: dict):
    def make(path: str) -> HookInput:
        return HookInput(
            session_id=raw.get("session_id", "unknown"),
            file_path=path,
            transcript_path=raw.get("transcript_path", ""),
        )
    return make


_UNCHECKED_REASON = (
    "Monte Carlo Prevent: couldn't check this apply_patch command. Prevent only checks "
    "apply_patch written as `apply_patch <<'EOF'` with the patch written out, optionally "
    "after one `cd <dir> &&`, or Codex's apply_patch tool. Retry in one of those forms. "
    "If the command only mentions the name (a search, a file name, a commit message), "
    "reword it so the name isn't spelled out, e.g. `apply_patc[h]` in a search pattern, "
    "or `git commit -F <file>` for a message."
)


def _gate_native(raw: dict, command: str) -> None:
    reason = gate_and_remember(
        command, "codex", cwd=raw.get("cwd"), session_id=raw.get("session_id", "unknown"),
        call_id=raw.get("tool_use_id"), make_input=_make_input(raw), evaluate=evaluate_pre_edit,
    )
    if reason:
        _deny(reason)


def _gate_shell(raw: dict, invocation) -> None:
    """Gate the recognised call, and track its files once it is allowed."""
    cwd = raw.get("cwd")
    base = resolve_path(invocation.base, cwd) if invocation.base else cwd
    groups = op_groups(parse_operations(invocation.body, "codex"), base)
    reason = gate_patch(groups, _make_input(raw), evaluate_pre_edit)
    if reason:
        _deny(reason)
        return
    session_id = raw.get("session_id", "unknown")
    for path in dict.fromkeys(t for files in groups for p in files for t in link_targets(p)):
        evaluate_post_edit(HookInput(session_id=session_id, file_path=path))


@safe_run
def main():
    raw = json.load(sys.stdin)
    command = (raw.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str):
        command = ""

    if raw.get("tool_name") == "apply_patch":
        _gate_native(raw, command)
        return

    if names_apply_patch(command):
        try:
            invocation = find_invocation(command)
        except Exception:
            # safe_run would allow it, and with it any patch the command applies.
            invocation = None
        if invocation is not None:
            _gate_shell(raw, invocation)
            return
        if not _prevent_hooks_disabled():
            _deny(_UNCHECKED_REASON)
            return

    if "git commit" in command:
        inp = HookInput(
            session_id=raw.get("session_id", "unknown"),
            command=command,
            cwd=raw.get("cwd", "."),
        )
        result = evaluate_pre_commit(inp)
        if result.action == "context":
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": result.context,
                }
            }))


if __name__ == "__main__":
    main()
