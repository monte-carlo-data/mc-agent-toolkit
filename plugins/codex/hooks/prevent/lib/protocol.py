"""Platform-agnostic hook decision logic.

All business logic for the prevent hooks lives here.
Platform adapters (Claude Code, Cursor) call these functions
and translate the result to their platform's JSON format.
"""
import hashlib
import json
import os
import re
import subprocess
from typing import NamedTuple

from lib.cache import (
    add_bayes_offered_tables,
    add_edited_table,
    claim_commit_checkpoint,
    cleanup_stale_cache,
    clear_head_snapshot,
    clear_monitor_gap,
    get_bayes_offered_tables,
    get_edited_tables,
    get_head_snapshot,
    get_impact_check_age_seconds,
    get_impact_check_state,
    get_pending_validation_tables,
    has_monitor_gap,
    has_verified_impact_check,
    is_valid_session_id,
    mark_impact_check_injected,
    mark_impact_check_verified,
    mark_monitor_gap,
    move_to_pending_validation,
    remove_edited_tables,
    save_head_snapshot,
)
from lib.commit_command import parse_commit_command
from lib.detect import extract_table_name, is_dbt_model, is_dbt_schema_file


# --- Data types ---

class HookInput:
    """Platform-agnostic hook input."""

    __slots__ = ("session_id", "file_path", "command", "transcript_path",
                 "cwd", "tool_name", "stop_hook_active", "validate_command",
                 "transcript_format")

    def __init__(
        self,
        session_id: str,
        file_path: str | None = None,
        command: str | None = None,
        transcript_path: str | None = None,
        cwd: str | None = None,
        tool_name: str | None = None,
        stop_hook_active: bool = False,
        validate_command: str = "/mc-validate",
        transcript_format: str = "raw",
    ):
        self.session_id = session_id
        self.file_path = file_path
        self.command = command
        self.transcript_path = transcript_path
        self.cwd = cwd
        self.tool_name = tool_name
        self.stop_hook_active = stop_hook_active
        self.validate_command = validate_command
        # Transcript layout this adapter produced: "raw" (line-scannable text,
        # the default for Claude Code/Cursor/Copilot/Codex) or "messages_jsonl"
        # (Cortex `.history.jsonl`, where only assistant text blocks are scanned).
        self.transcript_format = transcript_format


class HookOutput:
    """Platform-agnostic hook decision."""

    __slots__ = ("action", "reason", "context")

    def __init__(
        self,
        action: str = "noop",
        reason: str | None = None,
        context: str | None = None,
    ):
        self.action = action      # "deny", "context", "block", "noop"
        self.reason = reason
        self.context = context


# --- Shared helpers ---

GRACE_PERIOD_SECONDS = 120


def _compile_marker_patterns(table_name: str):
    """Compile the impact-check and monitor-gap regexes for a table.

    Matches the table name with an optional MCON-style prefix (e.g.
    "analytics:prod.client_hub") so markers work even if the model emits a fully
    qualified name instead of just "client_hub".
    """
    esc = re.escape(table_name)
    return (
        re.compile(rf"MC_IMPACT_CHECK_COMPLETE:\s+(?:\S+\.)?{esc}\b"),
        re.compile(rf"MC_MONITOR_GAP:\s+(?:\S+\.)?{esc}\b"),
    )


def _match_markers_in_lines(lines, table_name: str) -> dict:
    """Run the marker regexes over an iterable of text lines/blocks."""
    ic_pattern, mg_pattern = _compile_marker_patterns(table_name)
    found = {"impact_check": False, "monitor_gap": False}
    for line in lines:
        if ic_pattern.search(line):
            found["impact_check"] = True
        if mg_pattern.search(line):
            found["monitor_gap"] = True
    return found


def scan_transcript_for_markers(transcript_path: str, table_name: str) -> dict:
    """Scan a plain-text / JSONL transcript line-by-line for prevent markers.

    Used by Claude Code, Cursor, Copilot, and Codex, whose transcripts can be
    scanned as raw text. Cortex uses scan_history_jsonl_for_markers instead.
    """
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            return _match_markers_in_lines(f, table_name)
    except (OSError, UnicodeDecodeError):
        return {"impact_check": False, "monitor_gap": False}


def _iter_assistant_text(content) -> list[str]:
    """Return text from assistant content blocks of type 'text'.

    Defensive against shape drift: tolerates a plain string, a list of blocks,
    or malformed entries (which are skipped).
    """
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    texts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                texts.append(text)
    return texts


def scan_history_jsonl_for_markers(history_path: str, table_name: str) -> dict:
    """Scan a Cortex `<id>.history.jsonl` transcript for prevent markers.

    Only assistant-authored text blocks are scanned. Cortex persists hook output
    — including this gate's own deny reason — back into the transcript as a
    tool_result delivered under role "user". Scanning only assistant text ensures
    nothing but the model's own emitted marker can unlock the gate.

    Each line is an Anthropic Messages-style object:
        {"role": "assistant", "content": [{"type": "text", "text": "..."}, ...]}
    Malformed (non-JSON) lines are skipped, and undecodable bytes are replaced
    (errors="replace") so a stray non-UTF-8 byte doesn't abort the whole scan and
    miss a genuine marker. Worst case the scan finds no marker and the gate stays
    denied (fail closed) rather than raising into the adapter's safe_run (which
    would exit 0 and let the edit through).
    """
    found = {"impact_check": False, "monitor_gap": False}
    ic_pattern, mg_pattern = _compile_marker_patterns(table_name)
    try:
        with open(history_path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(msg, dict) or msg.get("role") != "assistant":
                    continue
                for text in _iter_assistant_text(msg.get("content")):
                    if ic_pattern.search(text):
                        found["impact_check"] = True
                    if mg_pattern.search(text):
                        found["monitor_gap"] = True
    except (OSError, UnicodeDecodeError):
        pass
    return found


def _scan_markers(inp: "HookInput", table_name: str) -> dict:
    """Dispatch to the right transcript scanner for the harness's format.

    Adapters that store messages in an Anthropic Messages-style `.history.jsonl`
    (Cortex) set inp.transcript_format == "messages_jsonl" and point
    transcript_path at that sibling file. "raw" (the default) uses the raw-line
    scan. An unrecognized format (e.g. a future adapter's typo) deliberately
    returns no markers so the gate stays denied — failing CLOSED rather than
    silently scanning with the wrong reader (which would drop the assistant-text
    protection) or raising (which fails OPEN, since the adapter's safe_run exits 0).
    """
    no_markers = {"impact_check": False, "monitor_gap": False}
    path = inp.transcript_path or ""
    if not path:
        return no_markers
    if inp.transcript_format == "messages_jsonl":
        return scan_history_jsonl_for_markers(path, table_name)
    if inp.transcript_format == "raw":
        return scan_transcript_for_markers(path, table_name)
    return no_markers  # unknown format → fail closed


_GIT_TIMEOUT_SECONDS = 10


def _git(args: list[str], cwd: str, text: bool = True, input=None):
    """Run git in cwd. Return stdout, or None if git fails or can't run."""
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=text, cwd=cwd, input=input,
            timeout=_GIT_TIMEOUT_SECONDS,
            **({"encoding": "utf-8", "errors": "surrogateescape"} if text else {}),
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _git_toplevel(cwd: str) -> str | None:
    """Root of the work tree containing cwd (git resolves symlinks), or None."""
    out = _git(["rev-parse", "--show-toplevel"], cwd)
    if not out or not out.strip():
        return None
    return out.strip()


def _get_staged_model_tables(cwd: str) -> list[str]:
    """Get table names from staged dbt SQL files using the detect library.

    git prints staged paths relative to the repository root, so they are joined
    to the root, not to cwd (which may be a subdirectory).
    """
    toplevel = _git_toplevel(cwd)
    if toplevel is None:
        return []
    out = _git(["diff", "--cached", "--name-only"], toplevel)
    if out is None:
        return []
    tables = []
    for line in out.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        full_path = os.path.join(toplevel, line)
        if is_dbt_model(full_path):
            tables.append(extract_table_name(full_path))
    return tables


class StagedModel(NamedTuple):
    """A dbt model in the git index: repo-relative path, staged blob ID, table name.

    A staged deletion has an all-zero blob ID.
    """
    path: str
    blob: str
    table: str


def _parse_raw_diff(out: str):
    """Yield (status, path, old_blob, new_blob) from `git diff --raw -z --no-abbrev`.

    Each record is ":<mode> <mode> <old> <new> <status>" then one path, or two
    (source, destination) for renames and copies.
    """
    fields = out.split("\0")
    i = 0
    while i < len(fields):
        meta = fields[i]
        if not meta.startswith(":"):
            i += 1
            continue
        parts = meta[1:].split()
        if len(parts) < 5:
            return
        old_blob, new_blob, status = parts[2], parts[3], parts[4][:1]
        if status in ("R", "C"):
            if i + 2 >= len(fields):
                return
            path = fields[i + 2]
            i += 3
        else:
            if i + 1 >= len(fields):
                return
            path = fields[i + 1]
            i += 2
        yield status, path, old_blob, new_blob


def _read_staged_models(cwd: str) -> tuple[str, list[StagedModel]] | None:
    """Return (toplevel, staged dbt models) for the repo containing cwd.

    Each file is classified from its staged blob, not the work tree, so the
    answer matches what `git commit` records. A staged deletion is classified
    from the blob being deleted. Returns None if cwd isn't in a git work tree or
    git fails.
    """
    toplevel = _git_toplevel(cwd)
    if toplevel is None:
        return None
    out = _git(["diff", "--cached", "--raw", "-z", "--no-abbrev"], toplevel)
    if out is None:
        return None
    entries = []
    for status, path, old_blob, new_blob in _parse_raw_diff(out):
        if os.path.splitext(path)[1].lower() != ".sql":
            continue
        content_blob = old_blob if status == "D" else new_blob
        entries.append((path, new_blob, content_blob))
    contents = _read_blobs([e[2] for e in entries], toplevel)
    if contents is None:
        return None
    models = []
    for (path, new_blob, _), content in zip(entries, contents):
        full_path = os.path.join(toplevel, path)
        if not is_dbt_model(full_path, content=content.decode("utf-8", errors="replace")):
            continue
        models.append(StagedModel(path=path, blob=new_blob, table=extract_table_name(full_path)))
    return toplevel, models


def _read_blobs(blob_ids: list[str], toplevel: str) -> list[bytes] | None:
    """Contents of each blob, in order, from one `git cat-file --batch`. None on failure."""
    if not blob_ids:
        return []
    out = _git(["cat-file", "--batch"], toplevel, text=False,
               input="".join(b + "\n" for b in blob_ids).encode("ascii"))
    if out is None:
        return None
    contents = []
    pos = 0
    for _ in blob_ids:
        end = out.find(b"\n", pos)
        if end == -1:
            return None
        header = out[pos:end].split()
        if len(header) != 3 or header[1] != b"blob" or not header[2].isdigit():
            return None
        size = int(header[2])
        start = end + 1
        if start + size > len(out):
            return None
        contents.append(out[start:start + size])
        pos = start + size + 1  # skip the newline after each object
    return contents


def _rev_blob(rev: str, toplevel: str) -> str | None:
    """Blob ID of `<rev>:<path>` or `:<path>`, or None if it doesn't exist."""
    out = _git(["rev-parse", "--verify", "--quiet", rev], toplevel)
    return out.strip() if out and out.strip() else None


def _read_commit_models(repo_dir: str, add_paths=()) -> tuple[str, list[StagedModel]] | None:
    """Return (toplevel, dbt models the commit will record) for `git add <add_paths> && git commit`.

    Starts from the staged models and replaces each added path with what git add
    will stage: the work-tree file's blob (hashed the way git add hashes it, with
    nothing written), or a deletion when a tracked file is gone. A path that ends
    up matching HEAD drops out. Returns None, so the checkpoint stays silent, if
    a path is a directory, a symlink or outside the repository, or if git add
    would fail because the path is neither on disk nor tracked.
    """
    staged = _read_staged_models(repo_dir)
    if staged is None:
        return None
    toplevel, models = staged
    for path in add_paths:
        full = os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path))
        # toplevel is already free of symlinks; resolve the path's directory to match.
        rel = os.path.relpath(full, toplevel)
        if rel == ".." or rel.startswith(".." + os.sep) or os.path.isabs(rel):
            return None
        rel = rel.replace(os.sep, "/")
        models = [m for m in models if m.path != rel]
        if os.path.islink(full) or os.path.isdir(full):
            return None
        head_blob = _rev_blob(f"HEAD:{rel}", toplevel)
        if os.path.isfile(full):
            out = _git(["hash-object", "--", rel], toplevel)
            if not out or not out.strip():
                return None
            new_blob = out.strip()
            if new_blob == head_blob or os.path.splitext(rel)[1].lower() != ".sql":
                continue
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                return None
        else:
            if _rev_blob(f":{rel}", toplevel) is None:
                return None  # git add fails, so the commit never runs
            if head_blob is None or os.path.splitext(rel)[1].lower() != ".sql":
                continue
            new_blob = "0" * len(head_blob)
            head_content = _git(["cat-file", "blob", head_blob], toplevel, text=False)
            if head_content is None:
                return None
            content = head_content.decode("utf-8", errors="replace")
        full_path = os.path.join(toplevel, rel)
        if is_dbt_model(full_path, content=content):
            models.append(StagedModel(path=rel, blob=new_blob, table=extract_table_name(full_path)))
    return toplevel, models


def _get_head_sha(cwd: str) -> str | None:
    """HEAD's sha; "" when the repo has no commits yet; None outside a repo."""
    sha = _git(["rev-parse", "--verify", "--quiet", "HEAD"], cwd)
    if sha is not None:
        return sha.strip()
    return "" if _git(["rev-parse", "--is-inside-work-tree"], cwd) is not None else None


def _get_committed_model_tables(cwd: str) -> list[str]:
    """Model tables changed by the HEAD commit. Macros are left out: the offer is
    about a table and what reads from it.

    diff-tree prints paths relative to the repository root, so they are joined
    to the root, not to cwd.
    """
    root = _git_toplevel(cwd)
    if root is None:
        return []
    files = _git(["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD"], root)
    if files is None:
        return []
    tables = []
    for line in files.splitlines():
        line = line.strip()
        if not line:
            continue
        full_path = os.path.join(root, line)
        if not is_dbt_model(full_path):
            continue
        table = extract_table_name(full_path)
        if not table.startswith("macro:"):
            tables.append(table)
    return list(dict.fromkeys(tables))


# --- Decision functions ---

def _prevent_hooks_disabled() -> bool:
    return os.environ.get("MC_PREVENT_HOOKS_DISABLED", "").strip() == "1"


def _bayes_followup_disabled() -> bool:
    return (
        _prevent_hooks_disabled()
        or os.environ.get("MC_BAYES_FOLLOWUP_DISABLED", "").strip() == "1"
    )


def _is_git_commit(command: str) -> bool:
    return "git commit" in command


def evaluate_pre_edit(inp: HookInput) -> HookOutput:
    """Gate logic: should this file edit be allowed?

    Returns deny if impact assessment hasn't run for this table,
    noop if the edit should proceed.
    """
    if _prevent_hooks_disabled():
        return HookOutput()
    cleanup_stale_cache()

    file_path = inp.file_path or ""
    if not is_dbt_model(file_path):
        return HookOutput()

    # New models have no blast radius — don't block
    if not os.path.exists(file_path):
        return HookOutput()

    session_id = inp.session_id
    table_name = extract_table_name(file_path)
    state = get_impact_check_state(session_id, table_name)

    if state == "verified":
        return HookOutput()

    if state == "injected":
        markers = _scan_markers(inp, table_name)
        if markers["monitor_gap"] and not has_monitor_gap(session_id, table_name):
            mark_monitor_gap(session_id, table_name)
        if markers["impact_check"]:
            mark_impact_check_verified(session_id, table_name)
            return HookOutput()
        # Assessment not completed — block without re-injecting if within grace period
        age = get_impact_check_age_seconds(session_id, table_name)
        if age < GRACE_PERIOD_SECONDS:
            reason = (
                f"Monte Carlo Prevent: the impact assessment for {table_name} "
                f"has not completed yet. Complete the assessment before editing this file."
            )
            return HookOutput(action="deny", reason=reason)
        # Grace period expired and no marker — re-inject full instruction below

    elif state is None:
        markers = _scan_markers(inp, table_name)
        if markers["monitor_gap"] and not has_monitor_gap(session_id, table_name):
            mark_monitor_gap(session_id, table_name)
        if markers["impact_check"]:
            mark_impact_check_verified(session_id, table_name)
            return HookOutput()

    # No marker or failed verification — block the edit
    mark_impact_check_injected(session_id, table_name)

    # The marker is shown as a `MC_IMPACT_CHECK_COMPLETE: <table>` template with a
    # separate substitution note rather than interpolating the table name directly
    # after the token. This keeps the rendered deny reason from satisfying the gate's
    # own scanner — harnesses that persist hook output back into the transcript (e.g.
    # Cortex records it as a tool_result) would otherwise let the gate self-unlock.
    hook_triggered_note = (
        "This assessment is hook-triggered — only emit MC_IMPACT_CHECK_COMPLETE "
        "markers for tables whose lineage and monitor coverage were fetched "
        "directly via Monte Carlo tools. When complete, emit the completion marker "
        "on its own line in the form `MC_IMPACT_CHECK_COMPLETE: <table>`, replacing "
        f"<table> with the bare table name {table_name}."
    )

    no_bypass_note = (
        "IMPORTANT: Do NOT bypass this check by using shell commands, git apply, "
        "or any other workaround. If Monte Carlo MCP tools are not available in "
        "this session, ask the user to authenticate the Monte Carlo MCP server "
        "in their editor settings before proceeding."
    )

    workflow_order_note = (
        "If Workflow 1 (asset-health pre-fetch) has not yet run for this table "
        "this session, run it first via the Skill tool to gather lineage / alerts "
        "/ monitors as data for the impact assessment. Read W1's report as data "
        "and do NOT relay it to the engineer — only surface a disambiguation "
        "prompt (if asset-health asks which match to use) or a one-line "
        "stop-the-world warning (active critical alerts, severe staleness). "
        "Then run Workflow 2 (change impact assessment), reusing the asset-health "
        "data rather than re-fetching. Workflow 2 is the user-facing artifact. "
        "If Workflow 1 already ran for this table, skip directly to Workflow 2."
    )

    if table_name.startswith("macro:"):
        macro_name = table_name.removeprefix("macro:")
        reason = (
            f"Monte Carlo Prevent: this macro ({macro_name}) is inlined into "
            f"models at compile time — changes here affect every model that calls it. "
            f"Identify which models use this macro, then run the change impact "
            f"assessment for the affected models before editing this file. "
            f"{workflow_order_note} {hook_triggered_note} {no_bypass_note}"
        )
    else:
        reason = (
            f"Monte Carlo Prevent: run the change impact assessment "
            f"for {table_name} before editing this file. Present the full "
            f"impact report and synthesis step, then ask the user whether to proceed before retrying the edit. "
            f"{workflow_order_note} {hook_triggered_note} {no_bypass_note}"
        )

    return HookOutput(action="deny", reason=reason)


def evaluate_post_edit(inp: HookInput) -> HookOutput:
    """Track which tables were edited. Always returns noop (silent)."""
    file_path = inp.file_path or ""
    if not is_dbt_model(file_path) and not is_dbt_schema_file(file_path):
        return HookOutput()

    table_name = extract_table_name(file_path)
    add_edited_table(inp.session_id, table_name)
    return HookOutput()


def _checkpoint_tables(session_id: str, staged_tables: list[str]) -> tuple[list[str], list[str]]:
    """Split staged tables into (verified tables, verified tables with a monitor gap).

    Reads state only. Callers clear the gaps they actually show.
    """
    verified = [t for t in staged_tables
                if get_impact_check_state(session_id, t) == "verified"]
    gaps = [t for t in verified if has_monitor_gap(session_id, t)]
    return verified, gaps


def evaluate_pre_commit(inp: HookInput) -> HookOutput:
    """Commit checkpoint: prompt for validation if dbt models are staged."""
    if _prevent_hooks_disabled():
        return HookOutput()
    command = inp.command or ""
    if not _is_git_commit(command):
        return HookOutput()

    cwd = inp.cwd or "."
    if not _bayes_followup_disabled():
        # Taken before any early return: `git commit -a` stages its files only
        # when it runs, so there may be nothing staged yet.
        head = _get_head_sha(cwd)
        if head is not None:
            save_head_snapshot(inp.session_id, cwd, head)

    staged_tables = _get_staged_model_tables(cwd)
    if not staged_tables:
        return HookOutput()

    w4_tables, gap_tables = _checkpoint_tables(inp.session_id, staged_tables)
    if not w4_tables:
        return HookOutput()

    table_list = ", ".join(w4_tables)
    message = (
        f"Committing changes to {table_list}. "
        f"Run validation queries before committing? (yes / no)"
    )
    if gap_tables:
        gap_list = ", ".join(gap_tables)
        message += (
            f"\n\nMonitor coverage: the impact assessment found no custom monitors "
            f"on {gap_list}. Generate monitor definitions before committing? (yes / no)"
        )
        for t in gap_tables:
            clear_monitor_gap(inp.session_id, t)

    return HookOutput(action="context", context=message)


_MARKER_TOKENS = ("MC_IMPACT_CHECK_COMPLETE", "MC_MONITOR_GAP")


def _display_table(name: str) -> str:
    """A table name as shown in a deny reason, unable to spell a completion marker.

    Table names come from file names, which can hold anything. A harness that
    writes the reason back into the scanned transcript would otherwise let a file
    named after a marker unlock the pre-edit gate.
    """
    for token in _MARKER_TOKENS:
        name = name.replace(token, token.replace("_", "-"))
    return name


def _pause_reason(tables: list[str], gap_tables: list[str], stages_files: bool = False) -> str:
    table_list = ", ".join(_display_table(t) for t in tables)
    validation = (
        f"run validation queries for {table_list} before committing? (yes / no)"
    )
    if gap_tables:
        gap_list = ", ".join(_display_table(t) for t in gap_tables)
        ask = (
            f"Before committing changes to {table_list}, ask the user and wait for "
            f"their answers:\n\n"
            f"1. Validation: {validation}\n"
            f"2. Monitors: the impact assessment found no custom monitors on "
            f"{gap_list}. Generate monitor definitions before committing? (yes / no)"
        )
        done = "and any validation or monitors they asked for are done"
    else:
        ask = (
            f"Before committing changes to {table_list}, ask the user and wait for "
            f"their answer:\n\n"
            f"Validation: {validation}"
        )
        done = "and any validation they asked for is done"
    if stages_files:
        # Agents read a paused `git add ... && git commit` as having staged the files.
        opening = ("Monte Carlo Prevent paused this command once. "
                   "Git did not run, so nothing was staged or committed.")
    else:
        opening = "Monte Carlo Prevent paused this commit once. Git did not run."
    return (
        f"{opening}\n\n"
        f"{ask}\n\n"
        f"When the user has answered, {done}, run the same commit command again. "
        "It will go through, because this pause happens once for these staged "
        "changes. If the user doesn't want to commit, don't. Don't use another "
        "command to get around this pause."
    )


def evaluate_pre_commit_once(inp: HookInput) -> HookOutput:
    """Commit checkpoint delivered as a one-time deny, for harnesses that drop
    a PreToolUse hook's added context.

    Pauses a `git commit` of the current index, or of the index plus files named
    in a `git add` chained before it, when that holds verified dbt models, with
    the checkpoint as the deny reason. The pause is keyed to this session and a
    digest of the repository and the committed models' blobs, so
    retrying the same staged change goes through and changing it pauses again.
    It is advisory: the retry is approved when the pause is shown, not when the
    user answers. Anything it can't pin down stays silent rather than blocking.
    """
    if _prevent_hooks_disabled() or not is_valid_session_id(inp.session_id):
        return HookOutput()
    target = parse_commit_command(inp.command or "", os.path.abspath(inp.cwd or "."))
    if target is None:
        return HookOutput()
    # Reading the commit runs git; skip it in sessions where Prevent hasn't verified anything.
    if not has_verified_impact_check(inp.session_id):
        return HookOutput()
    staged = _read_commit_models(target.repo_dir, target.add_paths)
    if staged is None:
        return HookOutput()
    toplevel, models = staged
    tables, gap_tables = _checkpoint_tables(
        inp.session_id, list(dict.fromkeys(m.table for m in models)))
    if not tables:
        return HookOutput()

    eligible = sorted((m.path, m.blob) for m in models if m.table in tables)
    digest = hashlib.sha256(
        json.dumps([toplevel, eligible], separators=(",", ":")).encode("utf-8", "surrogateescape")
    ).hexdigest()

    cleanup_stale_cache()
    # The claim is taken before the deny reaches the model, so if the harness
    # drops the deny, the retry commits without the question. The pause is
    # advisory, and claiming first is what keeps concurrent attempts to one pause.
    if not claim_commit_checkpoint(inp.session_id, digest):
        return HookOutput()

    for t in gap_tables:
        clear_monitor_gap(inp.session_id, t)
    # The pause asks the validation question, so the Stop hook needn't ask it
    # again for these tables. Editing one again puts it back.
    remove_edited_tables(inp.session_id, tables)
    return HookOutput(action="deny", reason=_pause_reason(
        tables, gap_tables, stages_files=bool(target.add_paths)))


def evaluate_turn_end(inp: HookInput) -> HookOutput:
    """End of turn: prompt for validation queries if dbt models were edited."""
    if _prevent_hooks_disabled():
        return HookOutput()
    if inp.stop_hook_active:
        return HookOutput()

    session_id = inp.session_id
    tables = get_edited_tables(session_id)
    if not tables:
        return HookOutput()

    if get_pending_validation_tables(session_id):
        move_to_pending_validation(session_id)
        return HookOutput()

    w4_tables = [t for t in tables
                 if get_impact_check_state(session_id, t) in ("injected", "verified")]
    if not w4_tables:
        return HookOutput()

    gap_tables = [t for t in tables if has_monitor_gap(session_id, t)]

    table_list = ", ".join(tables)
    count = len(tables)
    reason = (
        f"You've changed {count} dbt model(s): {table_list}. "
        f"ASK THE USER whether they would like to run validation queries to "
        f"verify these changes behaved as intended. Present these options and "
        f"WAIT for the user to respond — do NOT answer on their behalf:\n\n"
        f"→ Yes: I'll generate and run queries for all changed models\n"
        f"→ No: You can use {inp.validate_command} anytime to validate changes"
    )
    if gap_tables:
        gap_list = ", ".join(gap_tables)
        reason += (
            f"\n\nAlso ask about monitor coverage: the impact assessment found no "
            f"custom monitors on {gap_list}. Ask the user whether they would like "
            f"to generate monitor definitions:\n\n"
            f"→ Yes: I'll suggest monitors for the new or changed logic\n"
            f"→ No: Skip for now"
        )
        for t in gap_tables:
            clear_monitor_gap(session_id, t)

    move_to_pending_validation(session_id)
    return HookOutput(action="block", reason=reason)


def _bayes_offer_text(tables: list[str]) -> str:
    """What the hook tells the AI after a commit. The AI offers; only the user decides.

    `schedule_agent_task` must never run because a hook said so (its own description
    says so too), so this text asks the AI to ask, and nothing more.
    """
    table_list = ", ".join(tables)
    first = tables[0]
    return (
        f"Monte Carlo: this commit changed dbt model(s): {table_list}. "
        f"Bayes, Monte Carlo's AI teammate, can check these tables and the tables "
        f"downstream of them later, once the change is deployed, and send the answer "
        f"as a Slack direct message.\n\n"
        f"Only if the Monte Carlo MCP tool `schedule_agent_task` is available in this "
        f"session: when you have finished with the commit, ask the user once, in one "
        f"line, for example \"Do you want Bayes to check {first} and its downstream "
        f"tables after this deploys?\". Do NOT call `schedule_agent_task` unless the "
        f"user says yes. If they say yes, ask when to check (and their time zone if you "
        f"don't know it) and whether Bayes may run read-only SQL on their tables, then "
        f"follow the tool's instructions. Name the tables in `request`: the run cannot "
        f"see this conversation. If they say no, drop it and don't ask again. If the "
        f"tool is not available, say nothing about this."
    )


def evaluate_post_commit(inp: HookInput) -> HookOutput:
    """After `git commit`: offer a Bayes follow-up on the models the commit changed.

    Acts only when HEAD moved since the pre-commit snapshot, so a failed or aborted
    commit offers nothing. Each table is offered at most once per session.
    """
    if _bayes_followup_disabled():
        return HookOutput()
    if not _is_git_commit(inp.command or ""):
        return HookOutput()

    snapshot = get_head_snapshot(inp.session_id)
    if snapshot is None:
        return HookOutput()
    clear_head_snapshot(inp.session_id)

    cwd = snapshot["cwd"]
    head = _get_head_sha(cwd)
    if not head or head == snapshot["sha"]:
        return HookOutput()

    offered = set(get_bayes_offered_tables(inp.session_id))
    tables = [t for t in _get_committed_model_tables(cwd) if t not in offered]
    if not tables:
        return HookOutput()

    add_bayes_offered_tables(inp.session_id, tables)
    return HookOutput(action="context", context=_bayes_offer_text(tables))


def evaluate_validate_command(inp: HookInput) -> HookOutput:
    """Handle /mc-validate slash command."""
    session_id = inp.session_id

    tables = get_pending_validation_tables(session_id)
    if not tables:
        tables = get_edited_tables(session_id)

    if not tables:
        return HookOutput(
            action="context",
            context=f"No dbt model changes detected in this session. Edit a dbt model first, then run {inp.validate_command}.",
        )

    w4_tables = [t for t in tables
                 if get_impact_check_state(session_id, t) == "verified"]
    if not w4_tables:
        w4_tables = tables

    table_list = ", ".join(w4_tables)
    return HookOutput(
        action="context",
        context=(
            f"Generate validation queries for: {table_list}. "
            f"Use the validation query workflow from the Monte Carlo Prevent skill. "
            f"Save queries to validation/<table_name>_<timestamp>.sql."
        ),
    )
