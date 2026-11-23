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
when the hook can't know it). Only the two forms above, and calls in a command with no
`cd`, `pushd`, `popd`, `source`, `.` or `eval` (a sourced file or evaluated string can
change directory) and outside a subshell, get a base. The scan understands quotes,
comments, heredocs, line continuations and command positions; it doesn't evaluate
anything. A call it doesn't recognise as one (`bash -c "apply_patch ..."`,
`xargs apply_patch`) isn't found, like `git apply` or `sed`.
"""
import os
import re
from typing import NamedTuple

_NAMES = ("apply_patch", "applypatch")
_DIR_CHANGERS = ("cd", "pushd", "popd")
# Commands that run other shell text, which may itself change directory.
_MAY_CHANGE_DIR = ("source", ".", "eval")
# Words after which the next word is still in command position.
_PREFIX_WORDS = (
    "command", "builtin", "exec", "{", "!", "then", "do", "else", "elif", "if", "while", "until", "time",
)
_ASSIGNMENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_EXPANSION_CHARS = ("$", "`", "\\")

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


class Invocation(NamedTuple):
    body: str | None  # the patch text, or None when the command doesn't spell it out
    base: str | None  # directory relative to the command's cwd ("" = the cwd), or None


def _has_expansion(text: str) -> bool:
    return any(c in text for c in _EXPANSION_CHARS)


def _heredoc_body(text: str, start: int, delim: str, dash: bool) -> tuple[str, int] | None:
    """The body of a heredoc starting at `start`, and the index after its delimiter line."""
    lines = []
    pos = start
    while pos <= len(text):
        end = text.find("\n", pos)
        line = text[pos:] if end == -1 else text[pos:end]
        if dash:
            line = line.lstrip("\t")
        if line == delim:
            return "\n".join(lines), (len(text) if end == -1 else end + 1)
        lines.append(line)
        if end == -1:
            return None
        pos = end + 1
    return None


def _intercepted(command: str) -> Invocation | None:
    """The call, when the command is exactly one of the two forms Codex applies itself."""
    head = _INTERCEPT_HEAD_RE.match(command)
    if not head:
        return None
    raw_delim = head.group("delim")
    quoted = raw_delim[0] in "'\""
    delim = raw_delim[1:-1] if quoted else raw_delim
    found = _heredoc_body(command, head.end(), delim, bool(head.group("dash")))
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
    # If this matched while Codex's own parser didn't, the shell runs it and an unquoted
    # heredoc expands. Leave those to the general scan, which treats them as unknown.
    if not quoted and _has_expansion(body):
        return None
    return Invocation(body, base)


class _Word(NamedTuple):
    text: str  # after quote removal
    dynamic: bool  # contains an expansion, so its value is unknown
    single_quoted: bool  # exactly one '...' segment
    assignment: bool  # starts with an unquoted NAME=, whatever follows


class _Command:
    def __init__(self, depth: int):
        self.depth = depth
        self.words: list[_Word] = []
        # Redirections of fd 0 in order, the last one winning: ["heredoc", body, quoted] or
        # ["other"] for a here-string or a file.
        self.stdin: list[list] = []
        # Character ranges of heredoc bodies, on any fd, so the text they hold can be told
        # apart from commands.
        self.data_spans: list[tuple[int, int]] = []


def _read_balanced(text: str, i: int, open_c: str, close_c: str) -> int:
    """Index after the `close_c` matching the `open_c` just before `i`, skipping quotes."""
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
            i = _read_double_quoted(text, i + 1)[1]
            continue
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def _read_double_quoted(text: str, i: int) -> tuple[str, int, bool]:
    """Content of a "..." string starting after its quote, the index after it, and
    whether it expands."""
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
                i = _read_balanced(text, i + 2, "(", ")")
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
    assignment = _ASSIGNMENT_RE.match(text, i) is not None
    while i < len(text):
        c = text[i]
        if text.startswith("\\\n", i):
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
    return _Word("".join(out), dynamic, single and segments == 1, assignment), i


def _scan(command: str) -> tuple[list[_Command], bool]:
    """The simple commands in `command`, and whether any of them may change directory."""
    commands: list[_Command] = []
    # (command, delimiter, quoted, dash, its stdin entry when it's on fd 0)
    pending: list[tuple[_Command, str, bool, bool, list | None]] = []
    depth = 0
    current = _Command(depth)
    commands.append(current)

    def start() -> _Command:
        cmd = _Command(depth)
        commands.append(cmd)
        return cmd

    i = 0
    n = len(command)
    while i < n:
        c = command[i]
        if c in " \t":
            i += 1
        elif command.startswith("\\\n", i):
            i += 2
        elif c == "\n":
            i += 1
            for cmd, delim, quoted, dash, entry in pending:
                body_start = i
                found = _heredoc_body(command, i, delim, dash)
                body, i = found if found else (command[i:], n)
                if entry is not None:
                    entry[1] = body
                cmd.data_spans.append((body_start, i))
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
            depth += 1
            i += 1
            current = start()
        elif c == ")":
            depth = max(depth - 1, 0)
            i += 1
            current = start()
        elif c in "<>":
            fd = None
            if (current.words and current.words[-1].text.isdigit() and not current.words[-1].dynamic
                    and i > 0 and command[i - 1].isdigit()):
                fd = current.words.pop().text  # a file descriptor number, as in 2>
            on_stdin = c == "<" and fd in (None, "0")
            if command.startswith("<<<", i):
                i += 3
                if on_stdin:
                    current.stdin.append(["other"])
            elif command.startswith("<<", i):
                i += 2
                dash = command.startswith("-", i)
                i += 1 if dash else 0
                while i < n and command[i] in " \t":
                    i += 1
                raw_start = i
                word, i = _read_word(command, i)
                quoted = any(q in command[raw_start:i] for q in "'\"\\")
                entry = ["heredoc", None, quoted] if on_stdin else None
                if entry is not None:
                    current.stdin.append(entry)
                pending.append((current, word.text, quoted, dash, entry))
                continue
            else:
                if on_stdin:
                    current.stdin.append(["other"])
                i += 1
                while i < n and command[i] in "<>&|":
                    i += 1
            while i < n and command[i] in " \t":
                i += 1
            _, i = _read_word(command, i)  # the redirection's target
        else:
            word, i = _read_word(command, i)
            current.words.append(word)

    changes_dir = False
    for cmd in commands:
        name = _command_name(cmd)
        if name is not None and not name.dynamic and name.text in _DIR_CHANGERS + _MAY_CHANGE_DIR:
            changes_dir = True
    return commands, changes_dir


def _command_name(cmd: _Command) -> _Word | None:
    for word in cmd.words:
        if word.assignment:
            continue  # whatever its value expands to, it isn't the command
        if word.dynamic:
            return word
        if word.text in _PREFIX_WORDS:
            continue
        return word
    return None


def _calls_apply_patch(cmd: _Command) -> bool:
    return any(not w.dynamic and os.path.basename(w.text) in _NAMES for w in cmd.words)


def text_outside_data(command: str) -> str:
    """`command` without the heredoc bodies of commands that don't mention `apply_patch`
    (`cat > notes.md <<'EOF'`), which hold text rather than run it."""
    spans = sorted(s for cmd in _scan(command)[0] if not _calls_apply_patch(cmd) for s in cmd.data_spans)
    for start, end in reversed(spans):
        command = command[:start] + command[end:]
    return command


def _body(cmd: _Command) -> str | None:
    name_index = cmd.words.index(_command_name(cmd))
    args = cmd.words[name_index + 1:]
    if args:
        # The executable takes the patch from its first argument and ignores stdin.
        return args[0].text if args[0].single_quoted else None
    if not cmd.stdin or cmd.stdin[-1][0] != "heredoc":
        return None  # stdin from a pipe, a file, a here-string or nothing at all
    _, body, quoted = cmd.stdin[-1]
    if body is None:
        return None
    return body if quoted or not _has_expansion(body) else None


def find_invocations(command) -> list[Invocation]:
    """Every `apply_patch` call in a shell command, in order."""
    if not isinstance(command, str) or not any(name in command for name in _NAMES):
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
        found.append(Invocation(_body(cmd), "" if known_base else None))
    return found
