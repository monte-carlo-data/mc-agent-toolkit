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
Only the two shell forms Codex applies itself are gated this way. Any other command that
names `apply_patch` is denied as one Prevent couldn't check when its patch text may change
a dbt file (a `.sql`, `.yml` or `.yaml` path), may be expanded by the shell, or isn't
written out in the command at all; otherwise it is allowed and nothing is tracked.

Bash commands with `git commit` get the pre-commit validation checkpoint.
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
from shell_patch import (
    find_invocation, names_apply_patch, patch_may_expand, reads_unwritten_patch, unchecked_patch_paths,
)


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
    reason = gate_and_remember(
        command, "codex", cwd=raw.get("cwd"), session_id=raw.get("session_id", "unknown"),
        call_id=raw.get("tool_use_id"), make_input=_make_input(raw), evaluate=evaluate_pre_edit,
    )
    if reason:
        _deny(reason)


def _unchecked_problems(command: str, invocation) -> list[str]:
    """Why Prevent couldn't check what the command applies, beyond the recognised call."""
    problems = []
    # Fail closed on a call whose patch the hook can't read. Whether to deny this when the
    # patch may change no dbt file is a product choice; this branch is the place to change it.
    if invocation is None and reads_unwritten_patch(command):
        problems.append("the patch isn't written out in the command")
    if patch_may_expand(command, invocation):
        problems.append("the shell may expand `$` or a backtick in the patch")
    paths = unchecked_patch_paths(command, invocation)
    if paths:
        problems.append(
            f"it applies a patch to {', '.join(paths)} in a form Prevent doesn't check"
        )
    return problems


def _gate_shell(raw: dict, invocation, problems: list[str]) -> None:
    """Gate the recognised call, if any, and deny for `problems`, in one reply. Track the
    call's files once the whole command is allowed."""
    cwd = raw.get("cwd")
    groups: list[list[str]] = []
    if invocation is not None:
        base = resolve_path(invocation.base, cwd) if invocation.base else cwd
        groups = op_groups(parse_operations(invocation.body, "codex"), base)
    reason = gate_patch(groups, _make_input(raw), evaluate_pre_edit)
    if problems:
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

    try:
        invocation = find_invocation(command)
        problems = _unchecked_problems(command, invocation)
    except Exception:
        # safe_run would allow it, and with it any patch the command applies.
        if names_apply_patch(command) and not _prevent_hooks_disabled():
            _deny(_unresolved_reason(["Prevent couldn't read the command"]))
        return
    if _prevent_hooks_disabled():
        problems = []
    if invocation or problems:
        _gate_shell(raw, invocation, problems)
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
