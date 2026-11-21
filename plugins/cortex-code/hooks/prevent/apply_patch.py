"""Cortex Code `apply_patch`: which files a patch touches, and which of them it changed.

Cortex Code gives GPT and OpenAI models an `apply_patch` tool in place of edit/write.
Its hook payload carries the patch text in `tool_input.input`:

    *** Begin Patch
    *** Add File: <path>          (then "+" lines)
    *** Delete File: <path>
    *** Update File: <path>
    *** Move to: <path>           (optional, before the Update's first hunk)
    @@ ...                        (hunks: "@@", " ", "-", "+" lines)
    *** End Patch

The parser finds every header that CoCo Desktop 2.0.0 or the Cortex Code CLI 1.2.46 would
apply, and does not check the rest of the envelope. A client writes nothing for a patch it
rejects, so gating a malformed patch costs only a spurious deny, while a parser stricter
than a client could let an edit through. Desktop matches headers only at the start of a
line; the CLI also trims a line before matching it, except inside an Update's hunks, where
an indented line is content.
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

# Results returned before any file is written: CoCo Desktop 2.0.0's parse error, and the
# Cortex Code CLI 1.2.46's parse, input and missing-input errors.
_NO_WRITE_PREFIXES = (
    "Error parsing apply_patch input",
    "apply_patch verification failed",
    "apply_patch received invalid input text",
    "apply_patch handler received non-apply_patch input",
    "Missing required parameter: input",
)
# Desktop's result when an operation fails after earlier ones were written.
_PARTIAL_RE = re.compile(r"Patch partially applied through operation (\d+)/(\d+)")


class Op(NamedTuple):
    kind: str  # "add", "delete" or "update"
    path: str
    move_to: str | None = None


# Python's isspace counts these as whitespace; JavaScript's trim keeps them.
_PYTHON_ONLY_SPACE = frozenset("\x1c\x1d\x1e\x1f\x85")


def _is_js_space(char: str) -> bool:
    """Whitespace as JavaScript's trim sees it: U+FEFF counts, U+001C-U+001F and U+0085 don't."""
    return char == "\ufeff" or (char.isspace() and char not in _PYTHON_ONLY_SPACE)


def _strip_leading_whitespace(text: str) -> str:
    """Like JavaScript's trimStart."""
    i = 0
    while i < len(text) and _is_js_space(text[i]):
        i += 1
    return text[i:]


def _strip_trailing_whitespace(text: str) -> str:
    """Like JavaScript's trimEnd."""
    end = len(text)
    while end and _is_js_space(text[end - 1]):
        end -= 1
    return text[:end]


def _js_trim(text: str) -> str:
    """Like JavaScript's trim, which the clients apply to header paths."""
    return _strip_trailing_whitespace(_strip_leading_whitespace(text))


def _header(line: str) -> tuple[str, str] | None:
    for kind, prefix in _HEADERS:
        if line.startswith(prefix):
            return kind, _js_trim(line[len(prefix):])
    return None


def parse_operations(text) -> list[Op]:
    """Operations in an apply_patch body, in order. [] when it is not a patch."""
    if not isinstance(text, str):
        return []
    body = _strip_leading_whitespace(text)
    if not body.startswith(BEGIN):
        return []
    lines = body.replace("\r\n", "\n").split("\n")[1:]

    # The candidate line is trimmed, so a matched header always has a non-empty path.
    # A Move is attached to the Update it follows even after a hunk line; the clients
    # reject that patch, so it only adds a file to check.
    ops: list[Op] = []
    in_update = False  # inside an Update section, where indented lines are hunk content
    for line in lines:
        if line == END:
            break
        candidate = _strip_trailing_whitespace(line) if in_update else _js_trim(line)
        header = _header(candidate)
        if header:
            kind, path = header
            in_update = kind == "update"
            ops.append(Op(kind, path))
        elif in_update and candidate.startswith(MOVE_TO) and ops[-1].move_to is None:
            ops[-1] = ops[-1]._replace(move_to=_js_trim(candidate[len(MOVE_TO):]))
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


def _response_text(tool_response) -> str:
    """The text of a PostToolUse `tool_response`.

    CoCo Desktop sends a JSON string of content parts ({"kind": "text", "value": ...});
    the Cortex Code CLI sends an object with `content` parts ({"type": "text", "text": ...}).
    A plain string is taken as the text itself; anything else gives "".
    """
    response = tool_response
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except ValueError:
            return tool_response
    if isinstance(response, dict):
        response = response.get("content")
    if not isinstance(response, list):
        return ""
    texts = []
    for part in response:
        if isinstance(part, dict):
            text = part.get("value", part.get("text"))
            if isinstance(text, str):
                texts.append(text)
    return "\n".join(texts)


def applied_operations(ops: list[Op], tool_response) -> list[Op]:
    """The operations that may have changed files, judged from the tool's result.

    An error the client returns before writing changes nothing. A failure at operation K
    (CoCo Desktop) means 1..K-1 completed; K itself counts only when it is a move, which
    writes its destination before removing the source. Any other result, including a
    missing or unknown one, counts every operation, so a real edit is never dropped.
    """
    text = _response_text(tool_response)
    if text.startswith(_NO_WRITE_PREFIXES):
        return []
    match = _PARTIAL_RE.search(text)
    if not match:
        return ops
    failed = int(match.group(1))
    done = ops[:max(failed - 1, 0)]
    if 1 <= failed <= len(ops) and ops[failed - 1].move_to:
        done.append(ops[failed - 1])
    return done
