"""Recognise the `apply_patch` shell commands Codex applies itself.

Codex (0.171.0) applies a patch itself, without a shell, when the whole command is one of
two forms (`intercept_apply_patch`, `codex-rs/apply-patch/src/invocation.rs`):

    apply_patch <<'EOF'            cd <dir> && apply_patch <<'EOF'
    ...patch...                    ...patch...
    EOF                            EOF

It takes the heredoc body and `<dir>` as written, with no expansion, relative to the
command's working directory. `applypatch` works too. `find_invocation` recognises these
two forms, and only these, so the hook can gate the patch against the right folder.

The rule is closed: the hook doesn't read any other command. Any command that
`names_apply_patch` but isn't recognised may run apply_patch in a real shell, from a folder
or with a patch the hook can't know, so the hook denies it as one it couldn't check.
"""
import re
from typing import NamedTuple

from lib.apply_patch import BEGIN, parse_operations, strip_codex_wrapper

_NAMES = ("apply_patch", "applypatch")
_EXPANSION_CHARS = ("$", "`", "\\")
# In an unquoted heredoc the shell drops the backslash before these, and a backslash-newline.
_HEREDOC_ESCAPE_RE = re.compile(r"\\([\\$`\n])")
_CONTINUATION = "\\\n"

# Codex's parser sees through a backslash-newline, where the shell removes it. `<<-` isn't
# recognised: Codex keeps the leading tabs a shell strips, so the two may read different
# headers.
_WS = r"(?:[ \t]|\\\n)"
_INTERCEPT_HEAD_RE = re.compile(
    rf"""\A\s*
    (?:cd{_WS}+(?P<arg>"[^"\n]*"|'[^'\n]*'|[^\s;&|<>()'"]+){_WS}*&&{_WS}*)?
    (?:apply_patch|applypatch){_WS}*<<[ \t]*
    (?P<delim>'[^'\n]+'|"[^"\n]+"|[A-Za-z_][A-Za-z0-9_]*)[ \t]*\n""",
    re.VERBOSE,
)
_SAFE_BARE_DIR_RE = re.compile(r"[A-Za-z0-9_./@%+:,=][A-Za-z0-9_./@%+:,=-]*")
_QUOTE_CHARS_RE = re.compile(r"[\\'\"]")


class Invocation(NamedTuple):
    body: str  # the patch text, as Codex reads it
    base: str  # directory relative to the command's cwd ("" = the cwd)


def _has_expansion(text: str) -> bool:
    return any(c in text for c in _EXPANSION_CHARS)


def _headers_literal(body: str) -> bool:
    """Whether expanding an unquoted heredoc can't change which files its patch touches. Any
    line starting with `*` counts, since a backslash-newline can join `**\\` and
    `* Delete File:` into one, and the shell's backslash handling must leave the headers as
    they are: a backslash-newline after a hunk line can swallow the `*** End Patch` below it."""
    if any(_has_expansion(line) for line in body.split("\n") if line.lstrip().startswith("*")):
        return False
    expanded = _HEREDOC_ESCAPE_RE.sub(lambda m: "" if m.group(1) == "\n" else m.group(1), body)
    return parse_operations(body, "codex") == parse_operations(expanded, "codex")


def _one_patch(body: str) -> bool:
    """Whether the body holds at most one `*** Begin Patch`, where Codex reads it: at the
    start, past blank lines and a `<<EOF` wrapper line. One further in is text a real shell
    may hand apply_patch on its own, if Codex's parser didn't match. Read as written and
    with backslash-newlines removed, as the shell may join them."""
    count = body.count(BEGIN)
    if count != body.replace(_CONTINUATION, "").count(BEGIN) or count > 1:
        return False
    return count == 0 or strip_codex_wrapper(body).startswith(BEGIN)


def _heredoc_body(text: str, start: int, delim: str, quoted: bool) -> tuple[str, int] | None:
    """The body of a heredoc starting at `start`, and the index after its delimiter line.
    With an unquoted delimiter the shell joins a line ending in an odd number of
    backslashes to the next before looking for the delimiter."""
    lines: list[str] = []
    pos = start
    logical_lines, logical = 0, ""
    while True:
        end = text.find("\n", pos)
        line = text[pos:] if end == -1 else text[pos:end]
        continues = not quoted and end != -1 and (len(line) - len(line.rstrip("\\"))) % 2 == 1
        logical += line
        if not continues and logical == delim:
            return "\n".join(lines[:logical_lines]), (len(text) if end == -1 else end + 1)
        lines.append(line)
        if end == -1:
            return None
        pos = end + 1
        if continues:
            logical = logical[:-1]
        else:
            logical_lines, logical = len(lines), ""


def find_invocation(command) -> Invocation | None:
    """The call, when the whole command is one of the two forms Codex applies itself."""
    if not isinstance(command, str):
        return None
    head = _INTERCEPT_HEAD_RE.match(command)
    if not head:
        return None
    raw_delim = head.group("delim")
    quoted = raw_delim[0] in "'\""
    delim = raw_delim[1:-1] if quoted else raw_delim
    found = _heredoc_body(command, head.end(), delim, quoted)
    if not found or command[found[1]:].strip():
        return None
    body = found[0]

    arg = head.group("arg")
    base = ""
    if arg is not None:
        if arg[0] == "'":
            base = arg[1:-1]
        elif arg[0] == '"':
            if _has_expansion(arg[1:-1]):
                return None
            base = arg[1:-1]
        elif _SAFE_BARE_DIR_RE.fullmatch(arg):
            base = arg
        else:
            return None
        if not base:
            return None
    if not _one_patch(body):
        return None
    # Codex takes the body as written even with an unquoted delimiter, so `$` or `\` in a
    # hunk line is just content. A header line that could expand isn't recognised, in case
    # Codex's parser didn't match and a real shell runs the command.
    if not quoted and not _headers_literal(body):
        return None
    return Invocation(body, base)


def names_apply_patch(command) -> bool:
    """Whether the command may name `apply_patch`, anywhere, even as a mention. Quotes,
    backslashes and backslash-newlines are dropped first, as the shell drops them from a
    word, so `ap''ply_patch`, `apply\\_patch` and `$'apply_patch'` count. A name built by
    expansion (`ap${x}ply_patch`) doesn't."""
    if not isinstance(command, str):
        return False
    joined = _QUOTE_CHARS_RE.sub("", command.replace(_CONTINUATION, ""))
    return any(name in joined for name in _NAMES)
