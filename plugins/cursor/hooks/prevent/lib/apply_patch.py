"""`apply_patch`: which files a patch touches, the gate over all of them, and tracking.

Cortex Code (for GPT and OpenAI models) and Codex edit files with `apply_patch`:

    *** Begin Patch
    *** Add File: <path>          (then "+" lines)
    *** Delete File: <path>
    *** Update File: <path>
    *** Move to: <path>           (optional, before the Update's first hunk)
    @@ ...                        (hunks: "@@", " ", "-", "+" lines)
    *** End Patch

The parser finds every header the client would apply and does not check the rest of the
envelope. A client writes nothing for a patch it rejects, so gating a malformed patch
costs only a spurious deny, while a parser stricter than a client could let an edit
through. Each client reads headers its own way, so the parser takes a dialect:

- "cortex" (CoCo Desktop 2.0.0, Cortex Code CLI 1.2.46): Desktop matches headers only at
  the start of a line; the CLI also trims a line before matching it, except inside an
  Update's hunks, where an indented line is content. Paths are trimmed again, the way
  JavaScript's trim does. A Move counts anywhere in its Update section.
- "codex" (Codex 0.171.0, `codex-rs/apply-patch`): lines are trimmed the way Rust's
  `str::trim` does (only `trim_end` inside an Update), the path is the rest of the line
  as is, a Move counts only before the Update's first hunk line (a leading
  `*** End of File` isn't one), and a `<<EOF` wrapper around the patch is accepted.
"""
import json
import os
from typing import Callable, NamedTuple

from lib.cache import add_edited_table, pop_patch_record, save_patch_record
from lib.detect import extract_table_name, is_dbt_model, is_dbt_schema_file

BEGIN = "*** Begin Patch"
END = "*** End Patch"
MOVE_TO = "*** Move to: "
EOF_MARKER = "*** End of File"
_HEADERS = (
    ("add", "*** Add File: "),
    ("delete", "*** Delete File: "),
    ("update", "*** Update File: "),
)
_CODEX_WRAPPERS = ("<<EOF", "<<'EOF'", '<<"EOF"')


class Op(NamedTuple):
    kind: str  # "add", "delete" or "update"
    path: str
    move_to: str | None = None


# Python's isspace counts these as whitespace; neither JavaScript's trim nor Rust's does.
_CONTROL_SEPARATORS = frozenset("\x1c\x1d\x1e\x1f")


def _is_js_space(char: str) -> bool:
    """Whitespace as JavaScript's trim sees it: U+FEFF counts, U+001C-U+001F and U+0085 don't."""
    return char == "\N{ZERO WIDTH NO-BREAK SPACE}" or (char.isspace() and char not in _CONTROL_SEPARATORS and char != "\x85")


def _is_rust_space(char: str) -> bool:
    """Whitespace as Rust's `char::is_whitespace` sees it: U+0085 counts, U+FEFF doesn't."""
    return char.isspace() and char not in _CONTROL_SEPARATORS


def _lstrip(text: str, is_space) -> str:
    i = 0
    while i < len(text) and is_space(text[i]):
        i += 1
    return text[i:]


def _rstrip(text: str, is_space) -> str:
    end = len(text)
    while end and is_space(text[end - 1]):
        end -= 1
    return text[:end]


def _strip(text: str, is_space) -> str:
    return _rstrip(_lstrip(text, is_space), is_space)


def _header(line: str, trim_path) -> tuple[str, str] | None:
    for kind, prefix in _HEADERS:
        if line.startswith(prefix):
            return kind, trim_path(line[len(prefix):])
    return None


def parse_operations(text, dialect: str = "cortex") -> list[Op]:
    """Operations in an apply_patch body, in order. [] when it is not a patch."""
    if not isinstance(text, str):
        return []
    codex = dialect == "codex"
    is_space = _is_rust_space if codex else _is_js_space
    body = _lstrip(text, is_space)
    if codex:
        first, _, rest = body.partition("\n")
        if _strip(first, is_space) in _CODEX_WRAPPERS:
            body = _lstrip(rest, is_space)
    if not body.startswith(BEGIN):
        return []
    lines = body.replace("\r\n", "\n").split("\n")[1:]
    trim_path = (lambda path: path) if codex else (lambda path: _strip(path, is_space))

    # The candidate line is trimmed, so a matched header always has a non-empty path.
    ops: list[Op] = []
    in_update = False  # inside an Update section, where indented lines are hunk content
    update_has_hunk = False
    for line in lines:
        candidate = _rstrip(line, is_space) if in_update else _strip(line, is_space)
        if candidate == END if codex else line == END:
            break
        header = _header(candidate, trim_path)
        if header:
            kind, path = header
            in_update = kind == "update"
            update_has_hunk = False
            ops.append(Op(kind, path))
        elif in_update and candidate.startswith(MOVE_TO) and ops[-1].move_to is None:
            if codex and update_has_hunk:
                continue
            ops[-1] = ops[-1]._replace(move_to=trim_path(candidate[len(MOVE_TO):]))
        elif in_update:
            # Codex opens no chunk for an `*** End of File` line before any hunk content.
            if not (codex and not update_has_hunk and candidate == EOF_MARKER):
                update_has_hunk = True
    return ops


def op_paths(ops: list[Op]) -> list[str]:
    """Every path the operations touch, in order and without repeats; a move gives both."""
    paths: list[str] = []
    for op in ops:
        for path in (op.path, op.move_to):
            if path and path not in paths:
                paths.append(path)
    return paths


def resolve_path(path: str, cwd: str | None) -> str:
    """Resolve a patch path relative to `cwd`, or to the filesystem root when there is none."""
    if not os.path.isabs(path):
        path = os.path.join(cwd or "/", path)
    return os.path.normpath(path)


def link_targets(path: str) -> list[str]:
    """The path as written, then the file it reaches through symlinks when that differs.

    The dbt classifier reads folder names in the path, so `link/orders.sql`, where `link`
    points at `models/`, is only seen as a model through its target. A missing file is
    resolved through its existing parent folders.
    """
    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        return [path]
    return [path] if real == path else [path, real]


def op_groups(ops: list[Op], cwd: str | None) -> list[list[str]]:
    """The resolved paths of each operation: one, or two for a move."""
    return [[resolve_path(p, cwd) for p in (op.path, op.move_to) if p] for op in ops]


# --- The gate over a whole patch ---

def _patch_deny_reason(denied: dict[str, str], file_count: int, other_files: bool) -> str:
    """One reason for a denied patch: the tables, then each table's own instructions.

    Names tables bare (never after a marker token), so the reason can't unlock the gate
    when a client records it in the transcript.
    """
    if len(denied) == 1 and not other_files:
        return next(iter(denied.values()))
    names = ", ".join(denied)
    retry = (
        "Retry the patch after the assessment, or split out the changes to other files."
        if other_files else "Retry the patch after the assessment."
    )
    lead = (
        f"Monte Carlo Prevent: this patch touches {file_count} files. Run the change "
        f"impact assessment first for: {names}. The whole patch was blocked and no "
        f"file in it was changed. {retry}"
    )
    return "\n\n".join([lead, *denied.values()])


def gate_patch(groups: list[list[str]], make_input: Callable, evaluate: Callable) -> str | None:
    """Check every file of a patch; the deny reason for the whole patch, or None to allow.

    `groups` holds each operation's resolved paths. Every path, and the file it reaches
    through symlinks, is evaluated once, even after a deny, so each table gets its own
    assessment state. An error on one file doesn't drop denials found for others; a
    patch whose only problem is an error is allowed, like any other hook error.
    """
    denied: dict[str, str] = {}
    denied_paths: set[str] = set()
    checked: set[str] = set()
    for files in groups:
        for path in files:
            if path in checked:
                continue
            checked.add(path)
            for target in link_targets(path):
                try:
                    result = evaluate(make_input(target))
                    if result.action == "deny":
                        # Keep the first file's reason: it carries the assessment
                        # instructions and starts the grace period, so a later file of the
                        # same table only gets the short "not completed yet" text.
                        denied.setdefault(extract_table_name(target), result.reason)
                        denied_paths.add(path)
                except Exception:
                    continue
    if not denied:
        return None
    other_files = any(denied_paths.isdisjoint(files) for files in groups)
    return _patch_deny_reason(denied, len(checked), other_files)


# --- Tracking after the patch ran ---

def existing_models(paths: list[str]) -> list[str]:
    """The paths that are dbt models on disk now, directly or through symlinks, before
    the patch runs."""
    return [path for path in paths if any(_is_model_on_disk(t) for t in link_targets(path))]


def _is_model_on_disk(path: str) -> bool:
    try:
        return os.path.exists(path) and is_dbt_model(path)
    except Exception:
        return False


def remember_existing_models(session_id: str, call_id, paths: list[str]) -> None:
    """Record, for this call's PostToolUse, which of its paths were models before it ran."""
    if not call_id:
        return
    try:
        save_patch_record(session_id, str(call_id), existing_models(paths))
    except (OSError, ValueError):
        pass


def recall_existing_models(session_id: str, call_id) -> set[str]:
    """The paths recorded for this call, consuming the record; empty when there is none."""
    if not call_id:
        return set()
    try:
        return set(pop_patch_record(session_id, str(call_id)) or [])
    except (OSError, ValueError, json.JSONDecodeError):
        return set()


def patched_tables(paths: list[str], were_models: set[str]) -> list[str]:
    """Tables to track after a patch changed `paths`.

    A path counts when it is a dbt schema file, when it is a dbt model on disk after the
    patch, or when it was a model before (`were_models`): a model the patch deleted,
    moved away or overwrote with plain SQL is still a changed model. A path is also
    judged by the file it reaches through symlinks, which names the table.
    """
    tables: list[str] = []
    for path in paths:
        targets = link_targets(path)
        counts = path in were_models or any(
            _is_schema_file(t) or _is_model_on_disk(t) for t in targets
        )
        table = extract_table_name(targets[-1])
        if counts and table not in tables:
            tables.append(table)
    return tables


def gate_and_remember(patch_text, dialect: str, raw: dict, make_input: Callable, evaluate: Callable) -> str | None:
    """PreToolUse for an `apply_patch` tool call: the deny reason, or None after recording.

    On allow, records which of the patch's paths are models now, for the call's PostToolUse.
    `raw` is the hook payload; `cwd`, `session_id` and `tool_use_id` are read from it.
    """
    groups = op_groups(parse_operations(patch_text, dialect), raw.get("cwd"))
    reason = gate_patch(groups, make_input, evaluate)
    if reason:
        return reason
    remember_existing_models(raw.get("session_id", "unknown"), raw.get("tool_use_id"),
                             [p for files in groups for p in files])
    return None


def track_patch(patch_text, dialect: str, raw: dict, keep_ops: Callable | None = None) -> None:
    """PostToolUse for an `apply_patch` tool call: add the tables it changed to the session.

    `keep_ops`, when given, filters the parsed operations (e.g. to those that may have run).
    """
    session_id = raw.get("session_id", "unknown")
    were_models = recall_existing_models(session_id, raw.get("tool_use_id"))
    ops = parse_operations(patch_text, dialect)
    if keep_ops:
        ops = keep_ops(ops)
    paths = [resolve_path(p, raw.get("cwd")) for p in op_paths(ops)]
    for table in patched_tables(paths, were_models):
        add_edited_table(session_id, table)


def _is_schema_file(path: str) -> bool:
    try:
        return is_dbt_schema_file(path)
    except Exception:
        return False
