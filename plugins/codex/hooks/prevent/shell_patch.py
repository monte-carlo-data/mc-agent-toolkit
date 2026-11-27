"""Recognise the `apply_patch` shell commands Codex applies itself.

Codex (0.171.0) applies a patch itself, without a shell, when the whole command is one of
two forms (`intercept_apply_patch`, `codex-rs/apply-patch/src/invocation.rs`):

    apply_patch <<'EOF'            cd <dir> && apply_patch <<'EOF'
    ...patch...                    ...patch...
    EOF                            EOF

It takes the heredoc body and `<dir>` as written, with no expansion, relative to the
command's working directory. `applypatch` works too. `find_invocation` recognises these
two forms, and only these, so the hook can gate the patch against the right folder.

When Codex's parser doesn't match, a real shell runs the command, so `find_invocation`
recognises only commands both read the same way: words separated by spaces and tabs; a
plain-word delimiter, bare or quoted with nothing else inside; an unquoted body with no `$`,
backtick or backslash, which a shell would expand; no body line that starts with the
delimiter, which another heredoc reader could take for the end; a closing delimiter line;
and a `cd` folder written out plainly, which Codex's parser reads as one word and a shell
as a folder, not a number, an option or a directory-stack entry.

The rule is closed: the hook doesn't read any other command. Any command that
`names_apply_patch` but isn't recognised may run apply_patch in a real shell, from a folder
or with a patch the hook can't know, so the hook denies it as one it couldn't check.
"""
import re
from typing import NamedTuple

from lib.apply_patch import BEGIN, strip_codex_wrapper

# `codex --codex-run-as-apply-patch <patch>` is Codex's hidden option that applies a patch
# given as an argument (codex-rs/arg0).
_NAMES = ("apply_patch", "applypatch", "codex-run-as-apply-patch")
_EXPANSION_CHARS = ("$", "`", "\\")
_CONTINUATION = "\\\n"

# Only spaces and tabs separate words, as anything else (a Unicode space, `\r`) may read
# differently to Codex's parser and to a shell. Codex's parser sees through a
# backslash-newline around `cd`'s folder and `&&`, where the shell removes it, but not
# between the name and `<<`. `<<-` isn't recognised: Codex keeps the leading tabs a shell
# strips, so the two may read different headers.
_WS = r"(?:[ \t]|\\\n)"
_INTERCEPT_HEAD_RE = re.compile(
    rf"""\A[ \t\n]*
    (?:cd{_WS}+(?P<arg>"[^"\n]*"|'[^'\n]*'|[^\s;&|<>()'"]+){_WS}*&&{_WS}*)?
    (?:apply_patch|applypatch)[ \t]*<<[ \t]*
    (?P<delim>'[A-Za-z_][A-Za-z0-9_]*'|"[A-Za-z_][A-Za-z0-9_]*"|[A-Za-z_][A-Za-z0-9_]*)[ \t]*\n""",
    re.VERBOSE,
)
_SAFE_BARE_DIR_RE = re.compile(r"[A-Za-z0-9_./@%+:,=][A-Za-z0-9_./@%+:,=-]*")
_QUOTE_CHARS_RE = re.compile(r"\$?['\"]|\\")
# A bare folder Codex's parser reads as a number (`2024`, `0x1`), or that zsh expands
# (`=cmd`, `==`).
_UNREAD_BARE_DIR_RE = re.compile(r"=.*|(?:0[xX])?[0-9]+")
# Codex's parser reads a double-quoted folder holding `\r` in part.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


class Invocation(NamedTuple):
    body: str  # the patch text, as Codex reads it
    base: str  # directory relative to the command's cwd ("" = the cwd)


def _has_expansion(text: str) -> bool:
    return any(c in text for c in _EXPANSION_CHARS)


def _one_patch(body: str) -> bool:
    """Whether the body holds at most one `*** Begin Patch`, where Codex reads it: at the
    start, past blank lines and a `<<EOF` wrapper line. One further in is text a real shell
    may hand apply_patch on its own, if Codex's parser didn't match. Read as written and
    with backslash-newlines removed, as the shell may join them."""
    count = body.count(BEGIN)
    if count != body.replace(_CONTINUATION, "").count(BEGIN) or count > 1:
        return False
    return count == 0 or strip_codex_wrapper(body).startswith(BEGIN)


def _heredoc_body(text: str, start: int, delim: str) -> tuple[str, int] | None:
    """The body of a heredoc starting at `start`, and the index after its delimiter line.
    None when a body line starts with the delimiter, after any whitespace (`EOFX`, `EOF `,
    `  EOF`, ` \\rEOF`), which a heredoc reader other than bash's may take for the end, or
    when no line closes the heredoc."""
    lines: list[str] = []
    pos = start
    while True:
        end = text.find("\n", pos)
        line = text[pos:] if end == -1 else text[pos:end]
        if line == delim:
            return "\n".join(lines), (len(text) if end == -1 else end + 1)
        if end == -1 or line.lstrip().startswith(delim):
            return None
        lines.append(line)
        pos = end + 1


def find_invocation(command) -> Invocation | None:
    """The call, when the whole command is one of the two forms Codex applies itself."""
    if not isinstance(command, str) or "\x00" in command:
        return None
    head = _INTERCEPT_HEAD_RE.match(command)
    if not head:
        return None
    raw_delim = head.group("delim")
    quoted = raw_delim[0] in "'\""
    delim = raw_delim[1:-1] if quoted else raw_delim
    found = _heredoc_body(command, head.end(), delim)
    if not found or command[found[1]:].strip(" \t\n"):
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
        # Blank (Codex's parser reads `cd " "` as no folder, so applies in the cwd), or
        # `cd -P`, `cd +0`: an option or a directory-stack entry to a shell.
        if not base.strip() or base.startswith(("-", "+")):
            return None
        if _CONTROL_CHAR_RE.search(base) or (arg[0] not in "'\"" and _UNREAD_BARE_DIR_RE.fullmatch(arg)):
            return None
    if not _one_patch(body):
        return None
    # Codex takes an unquoted body as written, but a real shell expands it if Codex's
    # parser didn't match, so the two may apply different patches.
    if not quoted and _has_expansion(body):
        return None
    return Invocation(body, base)


def names_apply_patch(command) -> bool:
    """Whether the command may name `apply_patch`, anywhere, even as a mention. Quotes
    (with a `$` before one), backslashes and backslash-newlines are dropped first, as the
    shell drops them from a word, so `ap''ply_patch`, `apply\\_patch`, `$'apply_patch'` and
    `apply_pa$''tch` count, as does Codex's `--codex-run-as-apply-patch` option. A name
    built by expansion (`ap${x}ply_patch`, an escape inside `$'...'`) doesn't."""
    if not isinstance(command, str):
        return False
    joined = _QUOTE_CHARS_RE.sub("", command.replace(_CONTINUATION, ""))
    return any(name in joined for name in _NAMES)
