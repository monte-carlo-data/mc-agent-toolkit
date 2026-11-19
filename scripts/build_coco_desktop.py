#!/usr/bin/env python3
"""Build a CoCo Desktop-ready copy of the Cortex Code plugin.

CoCo Desktop installs plugins with "Add from GitHub", which runs an AI installer that
rewrites anything not already in Desktop's format. This build produces a copy that the
installer accepts as-is, so every customer gets the same files:

- symlinked skills become real copies, with file modes kept;
- dev-only files (plugin tests and scripts, hook tests, caches) are left out;
- each command becomes a skill; a command named like an existing skill is dropped, and a
  command whose folder name is taken gets `<name>-cmd`; `commands` leaves the manifest;
- the repo LICENSE is added, root Markdown other than README moves under docs/, and README
  links that point outside the plugin become GitHub URLs at the source ref.

Hook config is not rewritten: plugins/cortex-code/hooks/hooks.json is already in the
format both Cortex Code surfaces load.

Usage: build_coco_desktop.py <plugin dir> <out dir> [--ref <git ref>]
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

REPO_URL = "https://github.com/monte-carlo-data/mc-agent-toolkit"
ROOT_DEV_DIRS = {"tests", "scripts", "commands"}
MANIFEST = ".cortex-plugin/plugin.json"
MANIFEST_PATH_FIELDS = ("skills", "mcpServers", "hooks", "agents")
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
LINK = re.compile(r"\]\(([^)\s]+)\)")
BLOCK_SCALARS = {"|", ">", "|-", ">-", "|+", ">+"}


class BuildError(Exception):
    pass


def is_excluded(rel: str) -> bool:
    """Whether a plugin-relative path is left out of the Desktop copy."""
    parts = PurePosixPath(rel).parts
    if not parts:
        return False
    if parts[0] in ROOT_DEV_DIRS:
        return True
    if parts[0] == "hooks" and (
        (len(parts) >= 3 and parts[2] == "tests") or (len(parts) >= 4 and parts[2:4] == ("lib", "tests"))
    ):
        return True
    return "__pycache__" in parts or parts[-1] == ".DS_Store" or parts[-1].endswith(".pyc")


def parse_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split simple `key: value` frontmatter from the body. Returns (None, text) if absent."""
    match = FRONTMATTER.match(text)
    if not match:
        return None, text
    fields = {}
    lines = match.group(1).splitlines()
    for i, line in enumerate(lines):
        if not line or line[0].isspace():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.strip()
        if value in BLOCK_SCALARS:
            block = []
            for nxt in lines[i + 1:]:
                if nxt and not nxt[0].isspace():
                    break
                block.append(nxt.strip())
            value = " ".join(b for b in block if b)
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key.strip()] = value
    return fields, match.group(2)


def check_links(plugin: Path, repo_root: Path) -> None:
    """Fail on any link, at any depth reachable from the plugin, that resolves outside the repo."""
    root = Path(os.path.realpath(repo_root))
    seen = set()
    for directory, dirs, files in os.walk(plugin, followlinks=True):
        real_dir = os.path.realpath(directory)
        if real_dir in seen:
            dirs[:] = []
            continue
        seen.add(real_dir)
        for name in dirs + files:
            path = Path(directory, name)
            if not path.is_symlink():
                continue
            target = Path(os.path.realpath(path))
            if target != root and root not in target.parents:
                raise BuildError(f"{path} links outside the repo, to {target}")


def copy_plugin(plugin: Path, staging: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        rel_dir = os.path.relpath(directory, plugin)
        rel_dir = "" if rel_dir == "." else rel_dir
        return {n for n in names if is_excluded(str(PurePosixPath(rel_dir.replace(os.sep, "/"), n)))}

    try:
        shutil.copytree(plugin, staging, symlinks=False, ignore=ignore, dirs_exist_ok=True)
    except shutil.Error as exc:
        problems = "; ".join(f"{src}: {why}" for src, _, why in exc.args[0])
        raise BuildError(f"could not copy (dangling or unreadable link?): {problems}") from exc


def first_paragraph(body: str) -> str:
    """The body's first paragraph of text, skipping headings, with wrapped lines joined."""
    lines = []
    for line in body.splitlines():
        text = line.strip()
        if not text:
            if lines:
                break
            continue
        if text.startswith("#"):
            if lines:
                break
            continue
        lines.append(text)
    return " ".join(lines)


def convert_commands(plugin: Path, staging: Path) -> dict:
    skills_dir = staging / "skills"
    skill_names = set()
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        fields, _ = parse_frontmatter(skill_md.read_text())
        skill_names.add((fields or {}).get("name") or skill_md.parent.name)

    # Only what the manifest declares, as CoCo's installer does; a command's own `name` wins.
    declared = json.loads((plugin / MANIFEST).read_text()).get("commands") or []
    sources = []
    for entry in [declared] if isinstance(declared, str) else declared:
        path = (plugin / entry).resolve()
        if path.is_dir():
            sources += sorted(path.rglob("*.md"))
        elif path.is_file():
            sources.append(path)
        else:
            raise BuildError(f"manifest command path {entry} does not exist")
    commands = {}
    for path in sorted(set(sources)):
        fields, _ = parse_frontmatter(path.read_text())
        name = (fields or {}).get("name") or path.stem
        if name in commands:
            raise BuildError(f"two commands are named {name}: {commands[name]} and {path}")
        commands[name] = path

    report = {"converted": [], "dropped": [], "renamed": []}
    for name, path in sorted(commands.items()):
        if name in skill_names:
            report["dropped"].append(name)
            continue
        text = path.read_text()
        fields, body = parse_frontmatter(text)
        if fields is None:
            fields, body = {}, "\n" + text
        if not body.strip():
            raise BuildError(f"command {name} ({path}) has an empty body")
        description = fields.get("description") or first_paragraph(body)
        if not description:
            raise BuildError(f"command {name} ({path}) has no description and no text line")
        description = f"{description.rstrip('.')}. Triggers: /{name}, {name.replace('-', ' ')}."

        target = skills_dir / name
        if target.exists():
            target = skills_dir / f"{name}-cmd"
            if target.exists():
                raise BuildError(f"command {name}: skills/{name} and skills/{name}-cmd are both taken")
            report["renamed"].append(target.name)
        target.mkdir()
        (target / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n{body}"
        )
        report["converted"].append(target.name)

    report["converted"].sort()
    return report


def rewrite_manifest(staging: Path) -> dict:
    path = staging / MANIFEST
    manifest = json.loads(path.read_text())
    manifest.pop("commands", None)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def move_root_docs(staging: Path) -> dict[str, str]:
    """Move root Markdown other than README under docs/ (the installer asks about the rest)."""
    moves = {}
    for path in sorted(staging.glob("*.md")):
        if path.name != "README.md":
            target = staging / "docs" / path.name
            if target.exists():
                raise BuildError(f"docs/{path.name} already exists")
            target.parent.mkdir(exist_ok=True)
            path.rename(target)
            moves[path.name] = f"docs/{path.name}"
    return moves


def rewrite_links(text: str, src_dir: Path, out_dir: Path, plugin: Path, repo_root: Path,
                  staging: Path, moves: dict[str, str], ref: str) -> str:
    def replace(match: re.Match) -> str:
        target = match.group(1)
        if "://" in target or target.startswith(("#", "mailto:")):
            return match.group(0)
        path, hash_, frag = target.partition("#")
        frag = hash_ + frag
        resolved = Path(os.path.normpath(src_dir / path))
        if resolved == plugin or plugin in resolved.parents:
            rel = resolved.relative_to(plugin).as_posix()
            rel = moves.get(rel, rel)
            if (staging / rel).exists():
                return f"]({os.path.relpath(staging / rel, out_dir).replace(os.sep, '/')}{frag})"
        try:
            repo_rel = resolved.relative_to(repo_root).as_posix()
        except ValueError:
            return match.group(0)
        kind = "tree" if resolved.is_dir() else "blob"
        return f"]({REPO_URL}/{kind}/{ref}/{repo_rel}{frag})"

    return LINK.sub(replace, text)


def fix_doc_links(plugin: Path, repo_root: Path, staging: Path, moves: dict[str, str], ref: str) -> None:
    docs = {"README.md": "README.md", **moves}
    for src_name, out_rel in docs.items():
        out_path = staging / out_rel
        if out_path.exists():
            out_path.write_text(
                rewrite_links(out_path.read_text(), plugin, out_path.parent, plugin, repo_root, staging, moves, ref)
            )


def check_output(staging: Path) -> list[str]:
    """Everything Desktop needs to load the copy unchanged. Returns sorted skill folders."""
    links = sorted(str(p.relative_to(staging)) for p in staging.rglob("*") if p.is_symlink())
    if links:
        raise BuildError(f"symlinks left in output: {links}")

    manifest = json.loads((staging / MANIFEST).read_text())
    if "commands" in manifest:
        raise BuildError("manifest still declares commands")
    for field in MANIFEST_PATH_FIELDS:
        values = manifest.get(field)
        if values is None or isinstance(values, dict):
            continue
        for value in [values] if isinstance(values, str) else values:
            resolved = Path(os.path.normpath(staging / value))
            if resolved != staging and staging not in resolved.parents:
                raise BuildError(f"manifest {field} path {value} points outside the plugin")
            if not resolved.exists():
                raise BuildError(f"manifest {field} path {value} is missing")

    hooks = staging / "hooks" / "hooks.json"
    if not hooks.is_file():
        raise BuildError("hooks/hooks.json is missing")
    json.loads(hooks.read_text())

    stray = sorted(p.name for p in staging.glob("*.md") if p.name != "README.md")
    if stray:
        raise BuildError(f"root Markdown besides README: {stray}")

    names = {}
    folders = sorted(p.name for p in (staging / "skills").iterdir() if p.is_dir())
    for folder in folders:
        skill_md = staging / "skills" / folder / "SKILL.md"
        if not skill_md.is_file():
            raise BuildError(f"skills/{folder} has no SKILL.md")
        fields, body = parse_frontmatter(skill_md.read_text())
        for key in ("name", "description"):
            if not (fields or {}).get(key):
                raise BuildError(f"skills/{folder}/SKILL.md has no {key}")
        if not body.strip():
            raise BuildError(f"skills/{folder}/SKILL.md has an empty body")
        if fields["name"] in names:
            raise BuildError(f"skill name {fields['name']} is used by skills/{names[fields['name']]} and skills/{folder}")
        names[fields["name"]] = folder
    return folders


def build(plugin_dir: Path, out_dir: Path, ref: str = "main", repo_root: Path | None = None) -> dict:
    plugin = Path(plugin_dir).resolve()
    out = Path(os.path.realpath(out_dir))
    repo_root = Path(repo_root).resolve() if repo_root else plugin.parents[1]
    if not (plugin / MANIFEST).is_file():
        raise BuildError(f"{plugin} has no {MANIFEST}")
    if out.exists():
        raise BuildError(f"{out} exists; refusing to overwrite")
    if out == plugin or plugin in out.parents or out in plugin.parents:
        raise BuildError(f"{out} is inside the plugin (or contains it)")
    license_file = repo_root / "LICENSE"
    if not license_file.is_file():
        raise BuildError(f"{license_file} is missing")

    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out.name}.", dir=out.parent))
    try:
        check_links(plugin, repo_root)
        copy_plugin(plugin, staging)
        report = convert_commands(plugin, staging)
        manifest = rewrite_manifest(staging)
        shutil.copy2(license_file, staging / "LICENSE")
        moves = move_root_docs(staging)
        fix_doc_links(plugin, repo_root, staging, moves, ref)
        report["skills"] = check_output(staging)
        report["dropped"].sort()
        report["renamed"].sort()
        report["version"] = manifest.get("version")
        staging.rename(out)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("plugin_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--ref", default="main", help="git ref for README links outside the plugin")
    args = parser.parse_args(argv)
    try:
        report = build(args.plugin_dir, args.out_dir, ref=args.ref)
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
