"""CoCo Desktop `apply_patch`: which files a patch touches, and which of them it changed.

CoCo Desktop gives GPT and OpenAI models an `apply_patch` tool in place of edit/write.
Its hook payload carries the patch text in `tool_input.input`:

    *** Begin Patch
    *** Add File: <path>          (then "+" lines)
    *** Delete File: <path>
    *** Update File: <path>
    *** Move to: <path>           (optional, only right after Update)
    @@ ...                        (hunks: "@@", " ", "-", "+" lines)
    *** End Patch

The parser reads operation headers the way Desktop does, but does not check the rest of
the envelope: Desktop writes nothing for a patch it rejects, so gating a malformed patch
costs only a spurious deny, while a parser stricter than Desktop could let an edit through.
"""
import json
import os
import re
from typing import NamedTuple

BEGIN = "*** Begin Patch"
END = "*** End Patch"
MOVE_TO = "*** Move to: "
_HEADERS = (
    ("add", "*** Add File: "),
    ("delete", "*** Delete File: "),
    ("update", "*** Update File: "),
)

# Result texts of Desktop's apply_patch tool (CoCo Desktop 2.0.0).
_PARSE_ERROR_PREFIX = "Error parsing apply_patch input"
_PARTIAL_RE = re.compile(r"Patch partially applied through operation (\d+)/(\d+)")


class Op(NamedTuple):
    kind: str  # "add", "delete" or "update"
    path: str
    move_to: str | None = None


def _strip_leading_whitespace(text: str) -> str:
    """Like JavaScript's trimStart, which also strips U+FEFF; Python's lstrip does not."""
    i = 0
    while i < len(text) and (text[i].isspace() or text[i] == "\ufeff"):
        i += 1
    return text[i:]


def parse_operations(text) -> list[Op]:
    """Operations in an apply_patch body, in order. [] when it is not a patch."""
    if not isinstance(text, str):
        return []
    body = _strip_leading_whitespace(text)
    if not body.startswith(BEGIN):
        return []
    lines = body.replace("\r\n", "\n").split("\n")[1:]

    ops: list[Op] = []
    for i, line in enumerate(lines):
        if line == END:
            break
        for kind, prefix in _HEADERS:
            if not line.startswith(prefix):
                continue
            path = line[len(prefix):].strip()
            if not path:
                break
            move_to = None
            if kind == "update" and i + 1 < len(lines) and lines[i + 1].startswith(MOVE_TO):
                move_to = lines[i + 1][len(MOVE_TO):].strip() or None
            ops.append(Op(kind, path, move_to))
            break
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
    """Resolve a patch path the way Desktop does: relative to the session's working
    directory, or to the filesystem root when there is none."""
    if not os.path.isabs(path):
        path = os.path.join(cwd or "/", path)
    return os.path.normpath(path)


def _response_text(tool_response) -> str | None:
    """The text of Desktop's PostToolUse `tool_response`, a JSON list of content parts."""
    if not isinstance(tool_response, str):
        return None
    try:
        parts = json.loads(tool_response)
    except ValueError:
        return tool_response
    if not isinstance(parts, list):
        return None
    texts = [p["value"] for p in parts if isinstance(p, dict) and isinstance(p.get("value"), str)]
    return "\n".join(texts) if texts else None


def applied_operations(ops: list[Op], tool_response) -> list[Op]:
    """The operations that may have changed files, judged from the tool's result.

    A parse error changes nothing. A failure at operation K means 1..K-1 completed; K
    itself counts only when it is a move, which writes its destination before removing
    the source. Any other result, including a missing or unknown one, counts every
    operation, so a real edit is never dropped.
    """
    text = _response_text(tool_response)
    if text is None:
        return ops
    if text.startswith(_PARSE_ERROR_PREFIX):
        return []
    match = _PARTIAL_RE.search(text)
    if not match:
        return ops
    failed = int(match.group(1))
    done = ops[:max(failed - 1, 0)]
    if 1 <= failed <= len(ops) and ops[failed - 1].move_to:
        done.append(ops[failed - 1])
    return done
