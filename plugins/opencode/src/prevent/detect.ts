/**
 * dbt SQL file detection. Reads dbt_project.yml paths (cached) instead of
 * hardcoding folder names.
 *
 * Port of plugins/claude-code/prevent/hooks/lib/detect.py
 */
import { readFileSync, existsSync, lstatSync, readlinkSync, realpathSync } from "fs";
import { basename, extname, dirname, join, resolve, sep } from "path";
import {
  findDbtProjectYmls,
  getDbtPaths,
  getDbtProjectPaths,
  type DbtPaths,
} from "./cache";

const REF_PATTERNS = ["{{ ref(", "{{ source("];
const DBT_BLOCK_PATTERNS = ["{% macro", "{% snapshot"];
const MAX_SCAN_LINES = 50;

const GATED_KEYS = ["model-paths", "macro-paths", "snapshot-paths"];
const EXCLUDED_KEYS = ["seed-paths", "analysis-paths"];
const MODEL_KEYS = ["model-paths"];
const MACRO_KEYS = ["macro-paths"];

/** The folder names a project's paths give under keys: 'my_models' from 'path/my_models'. */
function folderNames(paths: DbtPaths, keys: string[]): Set<string> {
  const names = new Set<string>();
  for (const key of keys) {
    for (const p of paths[key] ?? []) {
      names.add(p.replace(/\/+$/, "").split("/").pop()!);
    }
  }
  return names;
}

/**
 * True if one of parts is named in dirs, ignoring case. On a case-insensitive
 * filesystem (macOS, Windows) `MODELS/` is `models/`; on a case-sensitive one
 * the match costs at most an extra assessment.
 */
function inDirs(parts: string[], dirs: Set<string>): boolean {
  const lower = new Set(parts.map((p) => p.toLowerCase()));
  for (const d of dirs) {
    if (lower.has(d.toLowerCase())) return true;
  }
  return false;
}

function pathParts(path: string): string[] {
  return path.replace(/\\/g, "/").split("/");
}

/**
 * The rule on main: the nearest project's folder names, anywhere in the path.
 * Seed and analysis names match exactly and the others ignore case, so a
 * difference in case only adds gating. Without a dbt_project.yml the default
 * names apply.
 */
function byFolderNames(path: string, keys: string[]): boolean {
  const paths = getDbtPaths(path);
  const parts = pathParts(path);
  const excluded = folderNames(paths, EXCLUDED_KEYS);
  if (parts.some((p) => excluded.has(p))) return false;
  return inDirs(parts, folderNames(paths, keys));
}

/** Python's posixpath.split. */
function splitPosix(p: string): [string, string] {
  const i = p.lastIndexOf("/") + 1;
  let head = p.slice(0, i);
  if (head && !/^\/+$/.test(head)) head = head.replace(/\/+$/, "");
  return [head, p.slice(i)];
}

/** Python's posixpath.join for two parts. */
function joinPosix(a: string, b: string): string {
  if (b.startsWith("/")) return b;
  return !a || a.endsWith("/") ? a + b : `${a}/${b}`;
}

/**
 * Port of Python's posixpath._joinrealpath (non-strict): each component's
 * symlink is followed before the next `..` applies, a dangling link is still
 * followed, and a loop stops resolution there.
 */
function joinRealpath(
  path: string,
  rest: string,
  seen: Map<string, string | null>
): [string, boolean] {
  if (rest.startsWith("/")) {
    rest = rest.slice(1);
    path = "/";
  }
  while (rest) {
    const i = rest.indexOf("/");
    const name = i < 0 ? rest : rest.slice(0, i);
    rest = i < 0 ? "" : rest.slice(i + 1);
    if (!name || name === ".") continue;
    if (name === "..") {
      if (path) {
        const [head, tail] = splitPosix(path);
        path = tail === ".." ? joinPosix(joinPosix(head, ".."), "..") : head;
      } else {
        path = "..";
      }
      continue;
    }
    const next = joinPosix(path, name);
    let isLink = false;
    try {
      isLink = lstatSync(next).isSymbolicLink();
    } catch {
      isLink = false;
    }
    if (!isLink) {
      path = next;
      continue;
    }
    if (seen.has(next)) {
      const known = seen.get(next);
      if (known != null) {
        path = known;
        continue;
      }
      return [joinPosix(next, rest), false];
    }
    seen.set(next, null);
    const [resolved, ok] = joinRealpath(path, readlinkSync(next), seen);
    if (!ok) return [joinPosix(resolved, rest), false];
    path = resolved;
    seen.set(next, path);
  }
  return [path, true];
}

/**
 * path with symlinks resolved, with Python's os.path.realpath semantics, or
 * fallback if resolving fails: canonical paths only add matches.
 */
function realpathOr(path: string, fallback: string): string {
  try {
    if (sep !== "/") return realpathLoose(resolve(path));
    return resolve(joinRealpath("", path, new Map())[0]);
  } catch {
    return fallback;
  }
}

/** Windows: resolve the existing prefix and append the rest. */
function realpathLoose(path: string): string {
  let head = path;
  const tail: string[] = [];
  while (true) {
    try {
      return join(realpathSync(head), ...tail.reverse());
    } catch {
      const parent = dirname(head);
      if (parent === head) return path;
      tail.push(basename(head));
      head = parent;
    }
  }
}

/**
 * filePath as absolute, and with symlinks resolved, so an alias reaches the
 * projects above its target.
 */
function spellings(filePath: string): string[] {
  const absolute = resolve(filePath);
  const real = realpathOr(filePath, absolute);
  return real === absolute ? [absolute] : [absolute, real];
}

interface Project {
  dir: string;
  paths: DbtPaths;
}

/**
 * Each readable dbt project above path. A project whose file can't be read is
 * skipped: it says nothing about the file, and another project may still own it.
 */
function projects(path: string): Project[] {
  const found: Project[] = [];
  for (const yml of findDbtProjectYmls(path)) {
    try {
      found.push({ dir: dirname(yml), paths: getDbtProjectPaths(yml) });
    } catch {
      // skip this project
    }
  }
  return found;
}

/**
 * The folders a project's paths under keys name, resolved against the project
 * like dbt does ('../x' and 'src/models' included), plus their symlink targets.
 */
function roots({ dir, paths }: Project, keys: string[]): string[] {
  const found: string[] = [];
  for (const key of keys) {
    for (const p of paths[key] ?? []) {
      // resolve, like Python's os.path.join, keeps an absolute configured path.
      const root = resolve(dir, p);
      found.push(root);
      const real = realpathOr(root, root);
      if (real !== root) found.push(real);
    }
  }
  return found;
}

function inside(path: string, rootList: string[], ignoreCase: boolean): boolean {
  for (const root of rootList) {
    const a = ignoreCase ? path.toLowerCase() : path;
    const b = ignoreCase ? root.toLowerCase() : root;
    if (a === b || a.startsWith(b.endsWith(sep) ? b : b + sep)) return true;
  }
  return false;
}

/**
 * True if path is inside one of the project's folders under keys (any case)
 * and not inside one of its seed or analysis folders (exact case).
 */
function projectHolds(path: string, project: Project, keys: string[]): boolean {
  if (inside(path, roots(project, EXCLUDED_KEYS), false)) return false;
  return inside(path, roots(project, keys), true);
}

/**
 * True if main's folder-name rule or any project above the file counts it
 * under keys. Gating is never narrower than main's rule; the exact check adds
 * the files that rule misses (a project inside another one's model folder, a
 * seeds or Macros folder above a project, multi-segment configured paths).
 */
function counts(filePath: string, keys: string[]): boolean {
  // The written path first, before anything that resolves symlinks.
  if (byFolderNames(filePath, keys)) return true;
  const all = spellings(filePath);
  for (const path of all) {
    if (path !== filePath && byFolderNames(path, keys)) return true;
  }
  for (const path of all) {
    for (const project of projects(path)) {
      if (projectHolds(path, project, keys)) return true;
    }
  }
  return false;
}

/**
 * Check if filePath is a dbt SQL file that could affect data.
 *
 * Gates any .sql file in a dbt project (models, macros, snapshots) since
 * macros are inlined into models at compile time and can have equal or
 * greater blast radius than a single model change.
 */
export function isDbtModel(filePath: string): boolean {
  if (extname(filePath).toLowerCase() !== ".sql") return false;

  if (!counts(filePath, GATED_KEYS)) return false;

  // New file being created — treat as dbt SQL
  if (!existsSync(filePath)) return true;

  // Existing .sql files must contain dbt patterns in first N lines
  try {
    const content = readFileSync(filePath, "utf-8");
    const lines = content.split("\n").slice(0, MAX_SCAN_LINES);
    for (const line of lines) {
      for (const pattern of REF_PATTERNS) {
        if (line.includes(pattern)) return true;
      }
      for (const pattern of DBT_BLOCK_PATTERNS) {
        if (line.includes(pattern)) return true;
      }
    }
  } catch {
    return false;
  }

  return false;
}

/**
 * Check if filePath is a dbt schema yml file under a model directory.
 * Used by post-edit tracking, but not for pre-edit gating.
 */
export function isDbtSchemaFile(filePath: string): boolean {
  const ext = extname(filePath).toLowerCase();
  if (ext !== ".yml" && ext !== ".yaml") return false;

  return counts(filePath, MODEL_KEYS);
}

/**
 * Check if filePath should be named as a macro. Main's rule names it first: a
 * folder in the written path named exactly (same case) like one of the nearest
 * project's macro folders. The exact check can only veto that, never add a macro name main
 * wouldn't give, so a model never drops out of the commit-time table list.
 * When some project's configured model, macro, or snapshot folder holds the
 * file, it stays a macro only if a macro folder holds it and no model or
 * snapshot folder of any project does: dbt builds models/macros/x.sql as a model.
 */
export function isMacroFile(filePath: string): boolean {
  const macroNames = folderNames(getDbtPaths(filePath), MACRO_KEYS);
  if (!pathParts(filePath).some((p) => macroNames.has(p))) return false;
  const held = new Set<string>();
  for (const path of spellings(filePath)) {
    for (const project of projects(path)) {
      for (const key of GATED_KEYS) {
        if (inside(path, roots(project, [key]), true)) held.add(key);
      }
    }
  }
  if (held.size === 0) return true;
  return (
    held.has("macro-paths") &&
    !held.has("model-paths") &&
    !held.has("snapshot-paths")
  );
}

/**
 * Extract table or macro name from file path.
 *
 * Example: /project/models/staging/client_hub_master.sql -> client_hub_master
 * Example: /project/macros/filters/internal_accounts.sql -> macro:internal_accounts
 */
export function extractTableName(filePath: string): string {
  const base = basename(filePath);
  const name = base.slice(0, base.length - extname(base).length);
  if (isMacroFile(filePath)) return `macro:${name}`;
  return name;
}
