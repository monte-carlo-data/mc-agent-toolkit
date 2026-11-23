"""Recognize a shell command whose commit records a predictable git index.

The pause-once pre-commit checkpoint fingerprints what a commit will record
before it pauses it, so it may only pause a command whose commit is the current
index, or the current index plus files named in a `git add` just before it.
parse_commit_command accepts a deliberately small grammar and returns None for
everything else. None means "stay silent", never "block".

Accepted:
    [NAME=value ...] git [-C <dir> | -c <k=v> | --no-pager ...] commit [options]
    the same preceded by `git add [--] <path> ... &&` and
        `git checkout -b|-B <branch> &&` or `git switch -c|-C <branch> &&`,
        in any order, each once or more
    cd <dir> && <either of the above>
    any of those followed by more commands (`&& git status`, `; git log`, `| cat`)

A new branch is accepted only without a start point, so the index and work
tree stay as they are. `git add` takes only literal paths: no options, globs, pathspec magic or
expansions. The paths are returned resolved, and whether each one is a file
git can stage is left to the caller.

Rejected (None): dry runs; -a, pathspecs, --only, --include, --patch and
--interactive, which commit something other than the index; GIT_DIR,
GIT_WORK_TREE, GIT_INDEX_FILE and other repository overrides; any other
command before the commit (it could change the index); a commit inside a
subshell or group; wrappers such as env or sudo; directories that need
expansion; options this parser doesn't know.

The lexer is hand-written because shlex can't tell a quoted `&&` from an
operator and reads a newline between commands as plain whitespace.
Commit messages written as `-m "$(cat <<'EOF' ... EOF)"` are common, so
command substitutions, heredocs inside them and redirections are understood
well enough to find where each word ends.
"""
import os
import re
from typing import NamedTuple


class CommitTarget(NamedTuple):
    repo_dir: str
    add_paths: tuple[str, ...] = ()  # files a preceding `git add` stages, resolved


class _Unsupported(Exception):
    pass


class _Word(NamedTuple):
    text: str
    has_expansion: bool   # contains $..., $(...) or `...` outside single quotes
    tilde_ok: bool        # starts with an unquoted ~


_OPS = ("&&", "||", ";;", ";", "&", "|", "(", ")", "\n")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Environment variables that only describe the commit, not which repo or index.
_SAFE_GIT_ENV = {
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
    "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE",
    "GIT_EDITOR", "GIT_PAGER", "GIT_TERMINAL_PROMPT", "GIT_SEQUENCE_EDITOR",
}

_GIT_GLOBAL_FLAGS = {
    "--no-pager", "-P", "--no-replace-objects", "--literal-pathspecs",
    "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs",
    "--no-optional-locks", "--no-advice",
}

# Every option not listed below is unsupported. That covers the dry runs
# (--dry-run, --short, --long, --porcelain, and -z/--null, which imply one),
# and the options that commit something other than the index (--all, --only,
# --include, --patch, --interactive, --pathspec-from-file). A --fixup=reword:
# commit changes only the message, so it is rejected too.
_COMMIT_NOARG_LONG = {
    "--amend", "--no-edit", "--edit", "--signoff", "--no-signoff", "--no-verify",
    "--verify", "--quiet", "--verbose", "--allow-empty", "--allow-empty-message",
    "--reset-author", "--status", "--no-status", "--no-gpg-sign",
    "--no-post-rewrite",
}
_COMMIT_ARG_LONG = {
    "--message", "--file", "--reuse-message", "--reedit-message", "--fixup",
    "--squash", "--author", "--date", "--template", "--cleanup", "--trailer",
}
_COMMIT_OPTARG_LONG = {"--untracked-files", "--gpg-sign"}  # value only as --opt=value

_COMMIT_NOARG_SHORT = set("snevq")
_COMMIT_ARG_SHORT = set("mFcCt")
_COMMIT_OPTARG_SHORT = set("uS")  # value only attached, e.g. -uno


# --- Lexer ---

def _skip_single_quoted(s: str, i: int) -> int:
    """i is just past an opening '. Return the index just past the closing '."""
    end = s.find("'", i)
    if end == -1:
        raise _Unsupported("unterminated single quote")
    return end + 1


def _skip_backticks(s: str, i: int) -> int:
    """i is just past an opening `. Return the index just past the closing `."""
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "`":
            return i + 1
        i += 1
    raise _Unsupported("unterminated backtick")


def _skip_double_quoted(s: str, i: int) -> int:
    """i is just past an opening ". Return the index just past the closing "."""
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
        elif c == '"':
            return i + 1
        elif c == "`":
            i = _skip_backticks(s, i + 1)
        elif s.startswith("$(", i):
            i = _skip_substitution(s, i + 2)
        else:
            i += 1
    raise _Unsupported("unterminated double quote")


_HEREDOC = re.compile(r"<<(-?)[ \t]*(?:'([^']*)'|\"([^\"]*)\"|\\?([A-Za-z0-9_.-]+))")


def _skip_substitution(s: str, i: int) -> int:
    """i is just past an opening $( . Return the index just past the matching ).

    Understands nested quotes, nested substitutions and heredoc bodies, whose
    lines may hold unbalanced quotes or parentheses.
    """
    depth = 1
    pending = []  # heredoc delimiters whose bodies start after the next newline
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
        elif c == "'":
            i = _skip_single_quoted(s, i + 1)
        elif c == '"':
            i = _skip_double_quoted(s, i + 1)
        elif c == "`":
            i = _skip_backticks(s, i + 1)
        elif s.startswith("<<", i) and not s.startswith("<<<", i):
            m = _HEREDOC.match(s, i)
            if not m:
                raise _Unsupported("unreadable heredoc")
            delim = m.group(2) if m.group(2) is not None else (
                m.group(3) if m.group(3) is not None else m.group(4))
            pending.append((delim, m.group(1) == "-"))
            i = m.end()
        elif c == "\n" and pending:
            i += 1
            for delim, strip_tabs in pending:
                while True:
                    if i >= len(s):
                        raise _Unsupported("unterminated heredoc")
                    end = s.find("\n", i)
                    line = s[i:] if end == -1 else s[i:end]
                    i = len(s) if end == -1 else end + 1
                    if (line.lstrip("\t") if strip_tabs else line) == delim:
                        break
            pending = []
        elif c == "(":
            depth += 1
            i += 1
        elif c == ")":
            depth -= 1
            i += 1
            if depth == 0:
                return i
        else:
            i += 1
    raise _Unsupported("unterminated command substitution")


_REDIRECT = re.compile(r"(?:\d*(?:>>|>\||>&|<&|<>|>|<)|&>>|&>)")


def _lex(s: str):
    """Split a command into _Word, operator strings and the marker 'redirect'."""
    tokens = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in " \t":
            i += 1
            continue
        if c == "\\" and i + 1 < n and s[i + 1] == "\n":
            i += 2
            continue
        if c == "#":
            end = s.find("\n", i)
            i = n if end == -1 else end
            continue
        if s.startswith("<<", i):
            raise _Unsupported("heredoc outside a substitution")
        m = _REDIRECT.match(s, i)
        if m:
            i = m.end()
            if m.group(0).endswith("&") and i < n and (s[i] == "-" or s[i].isdigit()):
                while i < n and (s[i] == "-" or s[i].isdigit()):
                    i += 1
            else:
                while i < n and s[i] in " \t":
                    i += 1
                target, i = _lex_word(s, i)
                if target is None:
                    raise _Unsupported("redirect without a target")
            tokens.append("redirect")
            continue
        op = next((o for o in _OPS if s.startswith(o, i)), None)
        if op:
            tokens.append(op)
            i += len(op)
            continue
        word, i = _lex_word(s, i)
        if word is None:
            # Nothing above consumed this character; never loop on it.
            raise _Unsupported(f"unexpected {c!r}")
        tokens.append(word)
    return tokens


def _lex_word(s: str, i: int):
    """Read one word starting at i. Return (_Word or None, next index)."""
    out = []
    has_expansion = False
    tilde_ok = i < len(s) and s[i] == "~"
    start = i
    n = len(s)
    while i < n:
        c = s[i]
        if c in " \t\n;&|()<>":
            if c in "<>" and i > start and s[start:i].isdigit():
                # `2>` style: the digits belong to the redirect, not a word.
                return None, start
            break
        if c == "\\":
            if i + 1 < n and s[i + 1] != "\n":
                out.append(s[i + 1])
            i += 2
        elif c == "'":
            end = _skip_single_quoted(s, i + 1)
            out.append(s[i + 1:end - 1])
            i = end
        elif c == '"':
            end = _skip_double_quoted(s, i + 1)
            inner = s[i + 1:end - 1]
            if "$" in inner or "`" in inner:
                has_expansion = True
            out.append(re.sub(r'\\([$`"\\])', r"\1", inner))
            i = end
        elif c == "`":
            end = _skip_backticks(s, i + 1)
            out.append(s[i:end])
            has_expansion = True
            i = end
        elif s.startswith("$(", i):
            end = _skip_substitution(s, i + 2)
            out.append(s[i:end])
            has_expansion = True
            i = end
        else:
            if c == "$":
                has_expansion = True
            out.append(c)
            i += 1
    if i == start:
        return None, i
    return _Word("".join(out), has_expansion, tilde_ok), i


# --- Parser ---

def _resolve_dir(base: str, word: _Word) -> str:
    if word.has_expansion or not word.text:
        raise _Unsupported("directory needs expansion")
    path = os.path.expanduser(word.text) if word.tilde_ok else word.text
    return os.path.normpath(os.path.join(base, path))


def _parse_commit_options(words) -> None:
    """Validate `git commit` arguments; raise _Unsupported for any it can't accept."""
    i = 0
    while i < len(words):
        w = words[i]
        text = w.text
        i += 1
        if text == "--":
            if i < len(words):
                raise _Unsupported("pathspec after --")
            break
        if text.startswith("--"):
            name, eq, _ = text.partition("=")
            if name in _COMMIT_NOARG_LONG and not eq:
                continue
            if name in _COMMIT_ARG_LONG:
                if eq:
                    value = text.partition("=")[2]
                else:
                    if i >= len(words):
                        raise _Unsupported(f"{name} needs a value")
                    value = words[i].text
                    i += 1
                if name == "--fixup" and value.startswith("reword:"):
                    raise _Unsupported("--fixup=reword: doesn't record the index")
                continue
            if name in _COMMIT_OPTARG_LONG:
                continue
            raise _Unsupported(f"unknown option {name}")
        if text.startswith("-") and len(text) > 1:
            j = 1
            while j < len(text):
                ch = text[j]
                j += 1
                if ch in _COMMIT_NOARG_SHORT:
                    continue
                if ch in _COMMIT_OPTARG_SHORT:
                    break
                if ch in _COMMIT_ARG_SHORT:
                    if j >= len(text):
                        if i >= len(words):
                            raise _Unsupported(f"-{ch} needs a value")
                        i += 1
                    break
                raise _Unsupported(f"-{ch} is unsupported")
            continue
        raise _Unsupported("pathspec")


_PATHSPEC_GLOB = re.compile(r"[*?\[]")


def _parse_add_paths(words, cwd: str) -> list[str]:
    """Validate `git add` arguments: literal paths only. Return them resolved."""
    paths = []
    end_of_options = False
    for w in words:
        if not end_of_options and w.text == "--":
            end_of_options = True
            continue
        if not end_of_options and w.text.startswith("-"):
            raise _Unsupported(f"git add option {w.text}")
        if w.text.startswith(":") or _PATHSPEC_GLOB.search(w.text):
            raise _Unsupported("pathspec magic or glob")
        paths.append(_resolve_dir(cwd, w))
    if not paths:
        raise _Unsupported("git add without a path")
    return paths


_NEW_BRANCH_FLAGS = {"checkout": ("-b", "-B"), "switch": ("-c", "-C")}


def _is_new_branch_from_head(subcommand: str, args) -> bool:
    """`git checkout -b <name>` or `git switch -c <name>`, which keep the index."""
    return (
        subcommand in _NEW_BRANCH_FLAGS
        and len(args) == 2
        and args[0].text in _NEW_BRANCH_FLAGS[subcommand]
        and not args[1].has_expansion
        and bool(args[1].text)
        and not args[1].text.startswith("-")
    )


def _parse_git(words, cwd: str):
    """Parse `[NAME=value ...] git [global options] <subcommand> ...`.

    Return (subcommand, its arguments, the directory git runs in).
    """
    i = 0
    while i < len(words) and _ASSIGNMENT.match(words[i].text):
        name = words[i].text.split("=", 1)[0]
        if name.startswith("GIT_") and name not in _SAFE_GIT_ENV:
            raise _Unsupported(f"{name} changes the repository or index")
        i += 1
    if i >= len(words):
        raise _Unsupported("no command")
    argv0 = words[i]
    if argv0.has_expansion or os.path.basename(argv0.text) != "git":
        raise _Unsupported("not git")
    i += 1

    repo_dir = cwd
    while i < len(words):
        text = words[i].text
        if text == "-C":
            if i + 1 >= len(words):
                raise _Unsupported("-C needs a directory")
            repo_dir = _resolve_dir(repo_dir, words[i + 1])
            i += 2
        elif text == "-c":
            if i + 1 >= len(words):
                raise _Unsupported("-c needs a value")
            i += 2
        elif text in _GIT_GLOBAL_FLAGS:
            i += 1
        elif text.startswith("-"):
            raise _Unsupported(f"git option {text}")
        else:
            break
    if i >= len(words):
        raise _Unsupported("no subcommand")
    return words[i].text, words[i + 1:], repo_dir


def _split_segments(tokens):
    """Split tokens on operators. Return (list of word lists, list of operators)."""
    segments, ops = [[]], []
    for tok in tokens:
        if tok == "redirect":
            continue
        if isinstance(tok, _Word):
            segments[-1].append(tok)
        else:
            ops.append(tok)
            segments.append([])
    return segments, ops


def parse_commit_command(command: str, cwd: str) -> CommitTarget | None:
    """Return where a supported `git commit` runs and what a `git add` before it names, else None."""
    try:
        tokens = _lex(command or "")
        while tokens and tokens[-1] == "\n":
            tokens.pop()
        while tokens and tokens[0] == "\n":
            tokens.pop(0)
        segments, ops = _split_segments(tokens)
        cwd_now = cwd
        k = 0
        first = segments[0]
        if ops and ops[0] == "&&" and first and first[0].text == "cd":
            if len(first) != 2 or first[0].has_expansion or first[1].text == "-":
                raise _Unsupported("only `cd <dir> &&` may precede the commit")
            cwd_now = _resolve_dir(cwd, first[1])
            k = 1
        # Before the commit, only `git add <paths> &&` and creating a branch from
        # HEAD are allowed: their effect on the index can be predicted. Whatever
        # follows the commit runs after it and can't change what it records.
        add_paths = []
        while True:
            subcommand, args, repo_dir = _parse_git(segments[k], cwd_now)
            if subcommand == "add" and k < len(ops) and ops[k] == "&&":
                add_paths.extend(_parse_add_paths(args, repo_dir))
                k += 1
                continue
            if _is_new_branch_from_head(subcommand, args) and k < len(ops) and ops[k] == "&&":
                k += 1
                continue
            if subcommand != "commit":
                raise _Unsupported("not a commit")
            _parse_commit_options(args)
            return CommitTarget(repo_dir=repo_dir, add_paths=tuple(add_paths))
    except _Unsupported:
        return None
