"""Find `apply_patch` calls in a shell command Codex is about to run.

Codex (0.171.0) applies a patch itself, without a shell, when the whole command is one of
two forms (`intercept_apply_patch`, `codex-rs/apply-patch/src/invocation.rs`):

    apply_patch <<'EOF'            cd <dir> && apply_patch <<'EOF'
    ...patch...                    ...patch...
    EOF                            EOF

It takes the heredoc body and `<dir>` as written, with no expansion, relative to the
command's working directory. `applypatch` works too. Any other command runs in a real
shell, where Codex's standalone `apply_patch` executable reads the patch from its first
argument, or from stdin when it has none, relative to wherever the shell is by then.

So each call found here has a body (the patch text, or None when it isn't written out in
the command) and a base (a directory relative to the command's working directory, or None
when the hook can't know it). Only the two forms above, and calls outside a subshell in a
command where nothing else may change directory, get a base. A command may change
directory when its name is dynamic (`$C`), names a builtin that moves or runs other shell
text (`cd`, `pushd`, `source`, `eval`, `trap`, ...), or defines a function. The scan
understands quotes, comments, heredocs, line continuations and command positions; it
doesn't evaluate anything.

A call it doesn't recognise (`env apply_patch`, `bash -c "apply_patch ..."`, a patch piped
in or fed through a script's heredoc) still leaves its patch text in the command.
`unchecked_patch_paths` reads every `*** Begin Patch` in a command that names
`apply_patch` and returns the paths that may be dbt files in each patch that isn't the
body of a call found with a known base, so the hook can deny it rather than let it
through. A patch never written out in the command (`git apply`, a patch file made
earlier) isn't seen.
"""
import bisect
import os
import re
from dataclasses import dataclass
from typing import NamedTuple

from lib.apply_patch import BEGIN, END, op_paths, parse_operations, strip_codex_wrapper
from lib.detect import may_be_dbt_file

_NAMES = ("apply_patch", "applypatch")
# Commands that change directory, run other shell text that may, or make a later word do so.
_MAY_CHANGE_DIR = ("cd", "pushd", "popd", "chdir", "source", ".", "eval", "trap", "alias", "function")
# Words after which the next word is still in command position. `noglob`, `nocorrect` and
# `-` are zsh's precommand modifiers.
_PREFIX_WORDS = (
    "command", "builtin", "exec", "noglob", "nocorrect", "-",
    "{", "!", "then", "do", "else", "elif", "if", "while", "until", "time",
)
# The single-letter options each prefix word takes before the command it runs, and the
# ones that take the next word as their value. `--` ends them for any of these words.
_PREFIX_OPTIONS = {"command": "pvV", "builtin": "", "exec": "cla", "time": "p"}
_OPTIONS_WITH_VALUE = {"exec": "a"}
# `command -v` and `-V` only print what the word would run.
_LOOKUP_ONLY = {"command": "vV"}
_OPTION_RE = re.compile(r"-[A-Za-z]+")
# Each level of `"$(` nests a function call in the scan; past this the command is unread.
_MAX_NESTING = 64
_ASSIGNMENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
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


class UnreadableCommand(Exception):
    """The scan gave up on the command, so its calls and their folders are unknown."""


class Invocation(NamedTuple):
    body: str | None  # the patch text, or None when the command doesn't spell it out
    base: str | None  # directory relative to the command's cwd ("" = the cwd), or None
    span: tuple[int, int] | None = None  # where the body is written in the command


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


def _intercepted(command: str) -> Invocation | None:
    """The call, when the command is exactly one of the two forms Codex applies itself."""
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
    # hunk line is just content. Header lines that could expand are left to the general
    # scan, in case Codex's parser didn't match and a real shell runs the command.
    if not quoted and not _headers_literal(body):
        return None
    return Invocation(body, base, (head.end(), body_end))


class _Word(NamedTuple):
    text: str  # after quote removal
    dynamic: bool  # contains an expansion, so its value is unknown
    single_quoted: bool  # exactly one '...' segment
    assignment: bool  # starts with an unquoted NAME=, whatever follows
    quoted_span: tuple[int, int] | None = None  # where the last '...' segment's content is


@dataclass
class _Stdin:
    """A redirection of fd 0."""
    kind: str  # "heredoc", or "other" for a here-string or a file
    body: str | None = None  # a heredoc's text, once read; None if it can't be known
    quoted: bool = False  # the heredoc's delimiter is quoted, so the shell doesn't expand it
    span: tuple[int, int] | None = None  # where the heredoc's text is in the command


class _Command:
    def __init__(self, depth: int):
        self.depth = depth
        self.words: list[_Word] = []
        self.stdin: list[_Stdin] = []  # in order, the last one winning


def _read_balanced(text: str, i: int, open_c: str, close_c: str, nesting: int = 0) -> int:
    """Index after the `close_c` matching the `open_c` just before `i`, skipping quotes."""
    if nesting > _MAX_NESTING:
        raise UnreadableCommand("nested too deeply")
    depth = 1
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            end = text.find("'", i + 1)
            i = len(text) if end == -1 else end + 1
            continue
        if c == '"':
            i = _read_double_quoted(text, i + 1, nesting + 1)[1]
            continue
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def _read_double_quoted(text: str, i: int, nesting: int = 0) -> tuple[str, int, bool]:
    """Content of a "..." string starting after its quote, the index after it, and
    whether it expands."""
    if nesting > _MAX_NESTING:
        raise UnreadableCommand("nested too deeply")
    out = []
    dynamic = False
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            out.append(text[i + 1])
            i += 2
            continue
        if c == '"':
            return "".join(out), i + 1, dynamic
        if c in "$`":
            dynamic = True
            if text.startswith("$(", i):
                i = _read_balanced(text, i + 2, "(", ")", nesting + 1)
                continue
            if c == "`":
                end = text.find("`", i + 1)
                i = len(text) if end == -1 else end + 1
                continue
        out.append(c)
        i += 1
    return "".join(out), i, dynamic


def _read_word(text: str, i: int) -> tuple[_Word, int]:
    out = []
    dynamic = False
    segments = 0
    single = False
    quoted_span = None
    assignment = _ASSIGNMENT_RE.match(text, i) is not None
    while i < len(text):
        c = text[i]
        if text.startswith(_CONTINUATION, i):
            i += 2  # the shell removes it, and the word goes on
            continue
        if c in " \t\n;&|()<>":
            break
        segments += 1
        if c == "'":
            end = text.find("'", i + 1)
            end = len(text) if end == -1 else end
            out.append(text[i + 1:end])
            single = segments == 1
            quoted_span = (i + 1, end)
            i = end + 1
        elif c == '"':
            content, i, expands = _read_double_quoted(text, i + 1)
            out.append(content)
            dynamic = dynamic or expands
        elif c == "\\":
            out.append(text[i + 1:i + 2])
            i += 2
        elif c == "$":
            dynamic = True
            if text.startswith("$(", i):
                i = _read_balanced(text, i + 2, "(", ")")
            elif text.startswith("${", i):
                i = _read_balanced(text, i + 2, "{", "}")
            else:
                i += 1
        elif c == "`":
            dynamic = True
            end = text.find("`", i + 1)
            i = len(text) if end == -1 else end + 1
        else:
            out.append(c)
            i += 1
    return _Word("".join(out), dynamic, single and segments == 1, assignment, quoted_span), i


def _heredoc_delimiter(raw: str) -> str | None:
    """The line that ends a heredoc whose delimiter word is `raw`: the shell removes quotes
    from it but expands nothing, so `<<$X` ends at a line `$X`. None for `$'...'` and
    `$"..."`, which shells quote differently."""
    out = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == "$" and raw[i + 1:i + 2] in ("'", '"'):
            return None
        if c == "'":
            end = raw.find("'", i + 1)
            end = len(raw) if end == -1 else end
            out.append(raw[i + 1:end])
            i = end + 1
        elif c == '"':
            i += 1
            while i < len(raw) and raw[i] != '"':
                if raw[i] == "\\" and raw[i + 1:i + 2] in ("\\", "$", "`", '"'):
                    i += 1
                out.append(raw[i:i + 1])
                i += 1
            i += 1
        elif c == "\\":
            out.append(raw[i + 1:i + 2])
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _scan(command: str) -> tuple[list[_Command], bool]:
    """The simple commands in `command`, and whether any of them may change directory."""
    commands: list[_Command] = []
    # (delimiter, or None when it can't be known; quoted; dash; its stdin entry when on fd 0)
    pending: list[tuple[str | None, bool, bool, _Stdin | None]] = []
    depth = 0
    defines_function = False
    current = _Command(depth)
    commands.append(current)

    def start() -> _Command:
        cmd = _Command(depth)
        commands.append(cmd)
        return cmd

    def skip_blanks(i: int) -> int:
        while i < n and (command[i] in " \t" or command.startswith(_CONTINUATION, i)):
            i += 2 if command[i] == "\\" else 1
        return i

    i = 0
    n = len(command)
    while i < n:
        c = command[i]
        if c in " \t":
            i += 1
        elif command.startswith(_CONTINUATION, i):
            i += 2
        elif c == "\n":
            i += 1
            for delim, quoted, dash, entry in pending:
                body_start = i
                found = None if delim is None else _heredoc_body(command, i, delim, dash, quoted)
                if found:
                    body, body_end, i = found
                else:
                    # The shell reads an unterminated heredoc to the end of the command, and
                    # one whose delimiter can't be known may end anywhere.
                    body, body_end, i = (None if delim is None else command[i:]), n, n
                if entry is not None:
                    entry.body, entry.span = body, (body_start, body_end)
            pending = []
            current = start()
        elif c == "#":
            end = command.find("\n", i)
            i = n if end == -1 else end
        elif c in ";&|":
            op = command[i:i + 2]
            if op in ("&&", "||", ";;", "|&", ";&"):
                i += 2
            else:
                i += 1
            current = start()
        elif c == "(":
            last = current.words[-1] if current.words else None
            if last is not None and not last.assignment and last.text not in _PREFIX_WORDS:
                defines_function = True  # `name() ...`, which could later run anything
            depth += 1
            i += 1
            current = start()
        elif c == ")":
            depth = max(depth - 1, 0)
            i += 1
            current = start()
        elif c in "<>" and command.startswith("(", i + 1):
            # `<(...)` or `>(...)` stands for a file name argument, not a redirection.
            i = _read_balanced(command, i + 2, "(", ")")
            current.words.append(_Word("", True, False, False))
        elif c in "<>":
            fd = None
            if (current.words and current.words[-1].text.isdigit() and not current.words[-1].dynamic
                    and i > 0 and command[i - 1].isdigit()):
                fd = current.words.pop().text  # a file descriptor number, as in 2>
            on_stdin = c == "<" and fd in (None, "0")
            if command.startswith("<<<", i):
                i += 3
                if on_stdin:
                    current.stdin.append(_Stdin("other"))
            elif command.startswith("<<", i):
                i += 2
                while command.startswith(_CONTINUATION, i):
                    i += 2
                dash = command.startswith("-", i)
                i = skip_blanks(i + 1 if dash else i)
                raw_start = i
                _, i = _read_word(command, i)
                # The shell removes backslash-newlines before it reads the delimiter word.
                raw = command[raw_start:i].replace(_CONTINUATION, "")
                quoted = any(q in raw for q in "'\"\\")
                entry = _Stdin("heredoc", quoted=quoted) if on_stdin else None
                if entry is not None:
                    current.stdin.append(entry)
                pending.append((_heredoc_delimiter(raw), quoted, dash, entry))
                continue
            else:
                if on_stdin:
                    current.stdin.append(_Stdin("other"))
                i += 1
                while i < n and command[i] in "<>&|":
                    i += 1
            while i < n and command[i] in " \t":
                i += 1
            _, i = _read_word(command, i)  # the redirection's target
        else:
            word, i = _read_word(command, i)
            current.words.append(word)

    # A wrong base would check the wrong files, so any command that might move the shell
    # makes every base unknown.
    changes_dir = defines_function
    for cmd in commands:
        name = _command_name(cmd)
        # A name starting with `-` is an option of a prefix word the scan doesn't know,
        # so the command it runs is unknown.
        if name is not None and (name.dynamic or name.text in _MAY_CHANGE_DIR or name.text.startswith("-")):
            changes_dir = True
    return commands, changes_dir


def _name_index(cmd: _Command) -> int | None:
    """Where the command's name is in its words. For `command -v`, it is `command` itself,
    which runs nothing."""
    words = cmd.words
    i = 0
    while i < len(words):
        word = words[i]
        if word.assignment:
            i += 1  # whatever its value expands to, it isn't the command
            continue
        if word.dynamic or word.text not in _PREFIX_WORDS:
            return i
        prefix, prefix_index, i = word.text, i, i + 1
        if prefix not in _PREFIX_OPTIONS:
            continue
        while i < len(words) and not words[i].dynamic:
            option = words[i].text
            if option == "--":
                i += 1
                break
            if not _OPTION_RE.fullmatch(option) or not set(option[1:]) <= set(_PREFIX_OPTIONS[prefix]):
                break  # an unknown option is left as the name, which the scan treats as unknown
            if set(option[1:]) & set(_LOOKUP_ONLY.get(prefix, "")):
                return prefix_index
            with_value = _OPTIONS_WITH_VALUE.get(prefix, "")
            if set(option[1:-1]) & set(with_value):
                return i  # the value is glued to the option in a way the scan doesn't split
            i += 2 if option[-1] in with_value else 1
    return None


def _command_name(cmd: _Command) -> _Word | None:
    index = _name_index(cmd)
    return None if index is None else cmd.words[index]


def _body(cmd: _Command) -> tuple[str, tuple[int, int] | None] | None:
    """The patch a call reads, and where it is written in the command."""
    args = cmd.words[_name_index(cmd) + 1:]
    if args:
        # The executable takes the patch from its first argument and ignores stdin.
        return (args[0].text, args[0].quoted_span) if args[0].single_quoted else None
    if not cmd.stdin or cmd.stdin[-1].kind != "heredoc":
        return None  # stdin from a pipe, a file, a here-string or nothing at all
    stdin = cmd.stdin[-1]
    if stdin.body is None:
        return None
    # A real shell expands an unquoted body. A backslash can only join lines, but `$` or a
    # backtick could write new header lines.
    if not stdin.quoted and ("$" in stdin.body or "`" in stdin.body or not _headers_literal(stdin.body)):
        return None
    return stdin.body, stdin.span


def _without_continuations(command: str) -> tuple[str, list[int]]:
    """`command` with every backslash-newline removed, and where each one was."""
    return command.replace(_CONTINUATION, ""), [m.start() for m in re.finditer(re.escape(_CONTINUATION), command)]


_QUOTE_CHARS_RE = re.compile(r"[\\'\"]")


def names_apply_patch(command: str) -> bool:
    """Whether the command may name `apply_patch`. Quotes and backslashes are dropped first,
    as the shell drops them from a plain word, so `ap''ply_patch` and `apply\\_patch` count.
    A name built by expansion (`ap${x}ply_patch`) doesn't."""
    if not isinstance(command, str):
        return False
    joined = _QUOTE_CHARS_RE.sub("", _without_continuations(command)[0])
    return any(name in joined for name in _NAMES)


def find_invocations(command) -> list[Invocation]:
    """Every `apply_patch` call in a shell command, in order."""
    if not names_apply_patch(command):
        return []
    intercepted = _intercepted(command)
    if intercepted:
        return [intercepted]
    commands, changes_dir = _scan(command)
    found = []
    for cmd in commands:
        name = _command_name(cmd)
        if name is None or name.dynamic or os.path.basename(name.text) not in _NAMES:
            continue
        known_base = not changes_dir and cmd.depth == 0
        body, span = _body(cmd) or (None, None)
        found.append(Invocation(body, "" if known_base else None, span))
    return found


def unchecked_patch_paths(command, invocations: list[Invocation]) -> list[str]:
    """Paths that may be dbt files in patch text that no call in `invocations` gates.

    In a command that names `apply_patch`, every `*** Begin Patch` up to the next
    `*** End Patch` is a patch something may apply, unless it is the body of a call found
    with a known base, which is gated as written. Only a patch that starts the body counts
    as that body (after the `<<EOF` line Codex's parser skips): one further in may be text
    the scan wrongly took for part of it. Each is
    read twice, as written and with backslash-newlines removed, since the shell removes them
    in some places and not in others."""
    if not names_apply_patch(command):
        return []
    joined, cuts = _without_continuations(command)

    def in_joined(i: int) -> int:
        return i - 2 * bisect.bisect_right(cuts, i - 2)

    spans = [inv.span for inv in invocations if inv.base is not None and inv.span is not None]
    views = [(command, spans)]
    if cuts:
        views.append((joined, [(in_joined(a), in_joined(b)) for a, b in spans]))
    paths: list[str] = []
    for text, accounted in views:
        start = text.find(BEGIN)
        while start != -1:
            end = text.find(END, start)
            end = len(text) if end == -1 else end + len(END)
            if not any(a <= start and end <= b and b - a - len(strip_codex_wrapper(text[a:b])) == start - a
                       for a, b in accounted):
                paths += [p for p in op_paths(parse_operations(text[start:], "codex")) if may_be_dbt_file(p)]
            start = text.find(BEGIN, start + 1)
    return list(dict.fromkeys(paths))
