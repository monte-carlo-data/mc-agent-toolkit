"""Cortex Code `apply_patch`: which of a patch's operations may have changed files.

Cortex Code gives GPT and OpenAI models an `apply_patch` tool in place of edit/write. Its
hook payload carries the patch text in `tool_input.input`. The parser and the gate are in
`lib/apply_patch.py` (dialect "cortex"); this module reads the tool's result.
"""
import json
import re

from lib.apply_patch import Op

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
