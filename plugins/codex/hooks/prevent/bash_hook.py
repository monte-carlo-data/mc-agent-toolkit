#!/usr/bin/env python3
"""PreToolUse hook (Codex adapter) for the Bash and apply_patch tools.

Codex edits files with `apply_patch`, sent two ways:
  - its own `apply_patch` tool (Codex 0.124.0+): `tool_input.command` is the patch.
    Codex sends PostToolUse after a successful patch, and post_edit_hook.py tracks it.
  - a shell command (`tool_name` "Bash") such as `cd <dir> && apply_patch <<'EOF'`.
    No PostToolUse follows a patch Codex applies from the shell, so this hook tracks
    the files itself once the whole command is allowed.
Every file a patch adds, deletes, updates or moves (both paths) is checked before it
runs, and the patch is denied as a whole when any of them needs an impact assessment.

Bash commands with `git commit` get the pre-commit validation checkpoint.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.apply_patch import (
    gate_patch, link_targets, op_groups, op_paths, parse_operations, remember_existing_models, resolve_path,
)
from lib.protocol import (
    HookInput, _prevent_hooks_disabled, evaluate_pre_commit, evaluate_pre_edit, evaluate_post_edit,
)
from shell_patch import find_invocations

# The only extensions the gate or edit tracking acts on; a patch touching none of them
# needs no check, wherever it runs.
_DBT_EXTENSIONS = (".sql", ".yml", ".yaml")


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


def _unresolved_reason(problems: list[str]) -> str:
    return (
        f"Monte Carlo Prevent: couldn't check this apply_patch command: {'; '.join(problems)}. "
        "It may change dbt models, which need a change impact assessment first. Retry with "
        "the apply_patch tool, or with the patch written out as `apply_patch <<'EOF'` "
        "(optionally after one `cd <dir> &&`)."
    )


def _gate_native(raw: dict, command: str) -> None:
    groups = op_groups(parse_operations(command, "codex"), raw.get("cwd"))
    reason = gate_patch(groups, _make_input(raw), evaluate_pre_edit)
    if reason:
        _deny(reason)
        return
    remember_existing_models(raw.get("session_id", "unknown"), raw.get("tool_use_id"),
                             [p for files in groups for p in files])


def _gate_shell(raw: dict, invocations) -> None:
    cwd = raw.get("cwd")
    groups: list[list[str]] = []
    problems: list[str] = []
    for inv in invocations:
        if inv.body is None:
            problem = "the patch isn't written out in the command"
        else:
            ops = parse_operations(inv.body, "codex")
            if inv.base is not None:
                groups += op_groups(ops, resolve_path(inv.base, cwd) if inv.base else cwd)
                continue
            if not any(p.lower().endswith(_DBT_EXTENSIONS) for p in op_paths(ops)):
                continue
            problem = "the directory it runs in can't be known before it runs"
        if problem not in problems:
            problems.append(problem)

    reason = gate_patch(groups, _make_input(raw), evaluate_pre_edit)
    if problems and not _prevent_hooks_disabled():
        reason = "\n\n".join(filter(None, [_unresolved_reason(problems), reason]))
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

    invocations = find_invocations(command)
    if invocations:
        _gate_shell(raw, invocations)
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
