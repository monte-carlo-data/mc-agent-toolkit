"""Read `apply_patch` calls in a shell command Codex is about to run.

Codex (0.171.0) applies a patch itself, without a shell, when the whole command is one of
two forms (`intercept_apply_patch`, `codex-rs/apply-patch/src/invocation.rs`):

    apply_patch <<'EOF'            cd <dir> && apply_patch <<'EOF'
    ...patch...                    ...patch...
    EOF                            EOF

It takes the heredoc body and `<dir>` as written, with no expansion, relative to the
command's working directory. `applypatch` works too. `find_invocation` recognises these
two forms, and only these, so the hook can gate the patch against the right folder.

Any other command runs in a real shell, where Codex's standalone `apply_patch` executable
reads the patch from its first argument, or from stdin when it has none, relative to
wherever the shell is by then. The hook doesn't work out where that is. Instead, in a
command that names `apply_patch`, it reads every `*** Begin Patch` up to the next
`*** End Patch` that isn't the body of a recognised call, and reports:
  - `unchecked_patch_paths`: the paths in that patch text that may be dbt files;
  - `patch_may_expand`: whether that text holds `$` or a backtick, which the shell may
    expand into other headers;
  - `reads_unwritten_patch`: whether a call reads its patch from somewhere the command
    doesn't spell out (a file, a pipe, a variable, an expanding heredoc).
The hook denies on any of these, since it couldn't check what the command changes.
"""
import bisect
import os
import re
from typing import NamedTuple

from lib.apply_patch import BEGIN, END, op_paths, parse_operations, strip_codex_wrapper
from lib.detect import may_be_dbt_file

_NAMES = ("apply_patch", "applypatch")
_EXPANSION_CHARS = ("$", "`", "\\")
# In an unquoted heredoc the shell drops the backslash before these, and a backslash-newline.
_HEREDOC_ESCAPE_RE = re.compile(r"\\([\\$`\n])")
_CONTINUATION = "\\\n"

# Codex's parser sees through a backslash-newline, where the shell removes it.
_WS = r"(?:[ \t]|\\\n)"
_INTERCEPT_HEAD_RE = re.compile(
    rf"""\A\s*
    (?:cd{_WS}+(?P<arg>"[^"\n]*"|'[^'\n]*'|[^\s;&|<>()'"]+){_WS}*&&{_WS}*)?
    (?:apply_patch|applypatch){_WS}*<<(?P<dash>-?)[ \t]*
    (?P<delim>'[^'\n]+'|"[^"\n]+"|[A-Za-z_][A-Za-z0-9_]*)[ \t]*\n""",
    re.VERBOSE,
)
_SAFE_BARE_DIR_RE = re.compile(r"[A-Za-z0-9_./@%+:,=][A-Za-z0-9_./@%+:,=-]*")

_QUOTE_CHARS_RE = re.compile(r"[\\'\"]")
# A rough split of shell text into operators, redirections and words, for finding calls.
_TOKEN_RE = re.compile(r"[;&|()`\n]|[<>]+|[^\s;&|()<>`]+")
# Words after which the next word still runs as a command.
_CALL_PREFIX_WORDS = (
    "env", "command", "builtin", "exec", "nohup", "time", "sudo", "xargs", "noglob", "nocorrect",
    "-", "{", "!", "if", "then", "else", "elif", "do", "while", "until",
)
_ASSIGNMENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_HEREDOC_OP_RE = re.compile(r"<<(?!<)-?[ \t]*(?P<delim>[^\s;&|()<>]+)")
# A redirection of stdin that isn't a heredoc or a process substitution.
_STDIN_REDIRECT_RE = re.compile(r"(?<!<)<(?![<(])")


class Invocation(NamedTuple):
    body: str  # the patch text, as Codex reads it
    base: str  # directory relative to the command's cwd ("" = the cwd)
    span: tuple[int, int]  # where the body is written in the command


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


def _heredoc_body(text: str, start: int, delim: str, dash: bool, quoted: bool) -> tuple[str, int, int] | None:
    """The body of a heredoc starting at `start`, the index where it ends, and the index after
    its delimiter line. With an unquoted delimiter the shell joins a line ending in an odd
    number of backslashes to the next before looking for the delimiter."""
    lines: list[str] = []
    pos = start
    logical_start, logical_lines, logical = start, 0, ""
    while True:
        end = text.find("\n", pos)
        line = text[pos:] if end == -1 else text[pos:end]
        if dash:
            line = line.lstrip("\t")
        continues = not quoted and end != -1 and (len(line) - len(line.rstrip("\\"))) % 2 == 1
        logical += line
        if not continues and logical == delim:
            body_end = max(start, logical_start - 1)
            return "\n".join(lines[:logical_lines]), body_end, (len(text) if end == -1 else end + 1)
        lines.append(line)
        if end == -1:
            return None
        pos = end + 1
        if continues:
            logical = logical[:-1]
        else:
            logical_start, logical_lines, logical = pos, len(lines), ""


def find_invocation(command) -> Invocation | None:
    """The call, when the whole command is one of the two forms Codex applies itself."""
    if not names_apply_patch(command):
        return None
    head = _INTERCEPT_HEAD_RE.match(command)
    if not head:
        return None
    raw_delim = head.group("delim")
    quoted = raw_delim[0] in "'\""
    delim = raw_delim[1:-1] if quoted else raw_delim
    found = _heredoc_body(command, head.end(), delim, bool(head.group("dash")), quoted)
    if not found or command[found[2]:].strip():
        return None
    body, body_end, _ = found

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
    # Codex takes the body as written even with an unquoted delimiter, so `$` or `\` in a
    # hunk line is just content. A header line that could expand isn't recognised, in case
    # Codex's parser didn't match and a real shell runs the command; it is then read like
    # any other form.
    if not quoted and not _headers_literal(body):
        return None
    return Invocation(body, base, (head.end(), body_end))


def _without_continuations(command: str) -> tuple[str, list[int]]:
    """`command` with every backslash-newline removed, and where each one was."""
    return command.replace(_CONTINUATION, ""), [m.start() for m in re.finditer(re.escape(_CONTINUATION), command)]


def names_apply_patch(command) -> bool:
    """Whether the command may name `apply_patch`. Quotes and backslashes are dropped first,
    as the shell drops them from a plain word, so `ap''ply_patch` and `apply\\_patch` count.
    A name built by expansion (`ap${x}ply_patch`) doesn't."""
    if not isinstance(command, str):
        return False
    joined = _QUOTE_CHARS_RE.sub("", _without_continuations(command)[0])
    return any(name in joined for name in _NAMES)


def _unaccounted_patches(command: str, invocation: Invocation | None) -> list[str]:
    """The text of every patch in `command` that isn't the body of `invocation`, each from
    its `*** Begin Patch` to the end of the command.

    Only a patch that starts the body counts as that body (after the `<<EOF` line Codex's
    parser skips): one further in may be text a real shell would apply on its own. Each is
    read twice, as written and with backslash-newlines removed, since the shell removes them
    in some places and not in others."""
    joined, cuts = _without_continuations(command)

    def in_joined(i: int) -> int:
        return i - 2 * bisect.bisect_right(cuts, i - 2)

    spans = [invocation.span] if invocation else []
    views = [(command, spans)]
    if cuts:
        views.append((joined, [(in_joined(a), in_joined(b)) for a, b in spans]))
    found: list[str] = []
    for text, accounted in views:
        start = text.find(BEGIN)
        while start != -1:
            end = text.find(END, start)
            end = len(text) if end == -1 else end + len(END)
            if not any(a <= start and end <= b and b - a - len(strip_codex_wrapper(text[a:b])) == start - a
                       for a, b in accounted):
                found.append(text[start:])
            start = text.find(BEGIN, start + 1)
    return found


def unchecked_patch_paths(command, invocation: Invocation | None) -> list[str]:
    """Paths that may be dbt files in patch text that `invocation` doesn't gate."""
    if not names_apply_patch(command):
        return []
    paths = [p for text in _unaccounted_patches(command, invocation)
             for p in op_paths(parse_operations(text, "codex")) if may_be_dbt_file(p)]
    return list(dict.fromkeys(paths))


def patch_may_expand(command, invocation: Invocation | None) -> bool:
    """Whether patch text that `invocation` doesn't gate holds `$` or a backtick, up to its
    `*** End Patch`. In an unquoted heredoc or a double-quoted word the shell expands them,
    and `$(...)` or a variable can write header lines the hook never sees."""
    if not names_apply_patch(command):
        return False
    for text in _unaccounted_patches(command, invocation):
        end = text.find(END)
        if any(c in text[:None if end == -1 else end] for c in "$`"):
            return True
    return False


def _calls(text: str) -> list[str]:
    """For each word in `text` that runs `apply_patch`, the rest of its line. A word runs it
    when it is the first of a command (after an operator, a newline, assignments or a word
    such as `env` or `command`) and, without quotes and leading folders, is the name. This
    is a rough reading: it doesn't know quotes, so `echo "x; apply_patch"` counts."""
    found = []
    at_start = True
    for m in _TOKEN_RE.finditer(text):
        token = m.group()
        if token in ";&|()`\n":
            at_start = True
            continue
        if token[0] in "<>":
            at_start = False
            continue
        word = _QUOTE_CHARS_RE.sub("", token)
        if at_start and os.path.basename(word) in _NAMES:
            end = text.find("\n", m.end())
            found.append(text[m.end():None if end == -1 else end])
            at_start = False
            continue
        at_start = at_start and (word in _CALL_PREFIX_WORDS or _ASSIGNMENT_RE.match(token) is not None)
    return found


def reads_unwritten_patch(command) -> bool:
    """Whether a call to `apply_patch` in the command may read a patch the command doesn't
    spell out. The executable reads its first argument, or stdin when it has none, so the
    patch is written out only when the call is followed by a single-quoted argument, or by
    a heredoc that no later `<` on its line replaces and that the shell can't expand into
    other text (a quoted delimiter, or no `$` or backtick in the command). A pipe, a file,
    a here-string, a variable or a heredoc on another fd all read text the hook can't see."""
    if not names_apply_patch(command):
        return False
    joined = _without_continuations(command)[0]
    expands = "$" in joined or "`" in joined
    for rest in _calls(joined):
        rest = rest.lstrip(" \t")
        if rest.startswith("'"):
            continue
        heredoc = _HEREDOC_OP_RE.match(rest)
        if not heredoc or _STDIN_REDIRECT_RE.search(rest, heredoc.end()):
            return True
        if expands and not any(q in heredoc.group("delim") for q in "'\"\\"):
            return True
    return False
