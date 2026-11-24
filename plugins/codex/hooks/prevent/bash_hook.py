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
A shell command whose call can't be resolved (the folder it runs in, or the patch it
reads, is unknown), or that names `apply_patch` and holds patch text no recognised call
reads, is denied when that patch may change a dbt file: Prevent couldn't check it. So is
one that names `apply_patch` and that the scan can't read at all.

Bash commands with `git commit` get the pre-commit validation checkpoint.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.apply_patch import (
    gate_and_remember, gate_patch, link_targets, op_groups, op_paths, parse_operations, resolve_path,
)
from lib.protocol import (
    HookInput, _prevent_hooks_disabled, evaluate_pre_commit, evaluate_pre_edit, evaluate_post_edit,
)
from lib.detect import may_be_dbt_file
from shell_patch import find_invocations, names_apply_patch, unchecked_patch_paths


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


def _gate_shell(raw: dict, invocations, unchecked: list[str]) -> None:
    """Gate the calls found in a shell command, and deny patch text none of them gates
    (`unchecked`, its paths that may be dbt files)."""
    cwd = raw.get("cwd")
    groups: list[list[str]] = []
    problems: list[str] = []
    unknown_base_paths: set[str] = set()
    for inv in invocations:
        if inv.body is None:
            problem = "the patch isn't written out in the command"
        else:
            ops = parse_operations(inv.body, "codex")
            if inv.base is not None:
                groups += op_groups(ops, resolve_path(inv.base, cwd) if inv.base else cwd)
                continue
            paths = op_paths(ops)
            if not any(may_be_dbt_file(p) for p in paths):
                continue
            unknown_base_paths.update(paths)
            problem = "the directory it runs in can't be known before it runs"
        if problem not in problems:
            problems.append(problem)
    # A call found without a known base leaves its body unchecked too; it already has a reason.
    unrecognised = [p for p in unchecked if p not in unknown_base_paths]
    if unrecognised:
        problems.append(
            f"Prevent doesn't recognise how apply_patch is called for {', '.join(unrecognised)}"
        )

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

    try:
        invocations = find_invocations(command)
        # Patch text no recognised call gates (`env apply_patch`, a script's heredoc, a pipe)
        # is checked by path alone, and denied in the same reply as the calls' own gate.
        unchecked = unchecked_patch_paths(command, invocations)
    except Exception:
        # safe_run would allow it, and with it any patch the command applies.
        if names_apply_patch(command) and not _prevent_hooks_disabled():
            _deny(_unresolved_reason(["Prevent couldn't read the command"]))
        return
    if invocations or unchecked:
        _gate_shell(raw, invocations, unchecked)
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
