/**
 * Per-table session cache backed by temp files.
 *
 * All state lives under $TMPDIR/mc_prevent_*. No external dependencies.
 * Cleans up naturally on reboot.
 *
 * Impact check gate uses three states:
 *   absent  -> injected (instruction sent, waiting for completion)
 *   injected -> verified (MC_IMPACT_CHECK_COMPLETE marker found)
 *
 * Port of plugins/claude-code/prevent/hooks/lib/cache.py
 */
import {
  readFileSync,
  writeFileSync,
  appendFileSync,
  existsSync,
  readdirSync,
  unlinkSync,
  statSync,
  openSync,
  writeSync,
  closeSync,
  constants,
  fstatSync,
} from "fs";
import { join, dirname, resolve } from "path";
import { createHash } from "crypto";
import { tmpdir } from "os";

const CACHE_DIR = tmpdir();
const FILE_PERMISSIONS = 0o600;
const SESSION_ID_RE = /^[a-zA-Z0-9_-]+$/;

const IC_PREFIX = "mc_prevent_ic_";
const MG_PREFIX = "mc_prevent_mg_";
const TURN_PREFIX = "mc_prevent_turn_";
const PENDING_PREFIX = "mc_prevent_pending_";
const DBT_CONFIG_PREFIX = "mc_prevent_dbt_config_";
const CLEANUP_MARKER = "mc_prevent_last_cleanup";

const ALL_PREFIXES = [
  IC_PREFIX,
  MG_PREFIX,
  TURN_PREFIX,
  PENDING_PREFIX,
  DBT_CONFIG_PREFIX,
];
const STALE_THRESHOLD_SECONDS = 6 * 3600; // 6 hours

// dbt_project.yml defaults per https://docs.getdbt.com/reference/project-configs
export type DbtPaths = Record<string, string[]>;
const DBT_DEFAULT_PATHS: DbtPaths = {
  "model-paths": ["models"],
  "macro-paths": ["macros"],
  "snapshot-paths": ["snapshots"],
  "seed-paths": ["seeds"],
  "analysis-paths": ["analyses"],
};

function writeSecure(path: string, content: string): void {
  const fd = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_TRUNC, FILE_PERMISSIONS);
  try {
    writeSync(fd, content);
  } finally {
    closeSync(fd);
  }
}

function appendSecure(path: string, content: string): void {
  const fd = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_APPEND, FILE_PERMISSIONS);
  try {
    writeSync(fd, content);
  } finally {
    closeSync(fd);
  }
}

function validateSessionId(sessionId: string): string {
  if (!SESSION_ID_RE.test(sessionId)) {
    throw new Error(`Invalid sessionId: ${sessionId}`);
  }
  return sessionId;
}

function w4Path(sessionId: string, tableName: string): string {
  return join(CACHE_DIR, `${IC_PREFIX}${validateSessionId(sessionId)}_${tableName}`);
}

function turnPath(sessionId: string): string {
  return join(CACHE_DIR, `${TURN_PREFIX}${validateSessionId(sessionId)}`);
}

function pendingPath(sessionId: string): string {
  return join(CACHE_DIR, `${PENDING_PREFIX}${validateSessionId(sessionId)}`);
}

function mgPath(sessionId: string, tableName: string): string {
  return join(CACHE_DIR, `${MG_PREFIX}${validateSessionId(sessionId)}_${tableName}`);
}

// --- Impact check three-state marker ---

export type ImpactCheckState = "injected" | "verified" | null;

export function getImpactCheckState(
  sessionId: string,
  tableName: string
): ImpactCheckState {
  const path = w4Path(sessionId, tableName);
  if (!existsSync(path)) return null;
  try {
    const data = JSON.parse(readFileSync(path, "utf-8"));
    return data.state ?? null;
  } catch {
    return null;
  }
}

export function markImpactCheckInjected(
  sessionId: string,
  tableName: string
): void {
  writeSecure(
    w4Path(sessionId, tableName),
    JSON.stringify({ state: "injected", timestamp: Date.now() / 1000 })
  );
}

export function markImpactCheckVerified(
  sessionId: string,
  tableName: string
): void {
  const path = w4Path(sessionId, tableName);
  let timestamp = Date.now() / 1000;
  try {
    const data = JSON.parse(readFileSync(path, "utf-8"));
    timestamp = data.timestamp ?? timestamp;
  } catch {
    // ignore
  }
  writeSecure(path, JSON.stringify({ state: "verified", timestamp }));
}

export function getImpactCheckAgeSeconds(
  sessionId: string,
  tableName: string
): number {
  const path = w4Path(sessionId, tableName);
  try {
    const data = JSON.parse(readFileSync(path, "utf-8"));
    return Date.now() / 1000 - (data.timestamp ?? Date.now() / 1000);
  } catch {
    return 0;
  }
}

// --- Monitor coverage gap marker ---

export function hasMonitorGap(
  sessionId: string,
  tableName: string
): boolean {
  return existsSync(mgPath(sessionId, tableName));
}

export function markMonitorGap(
  sessionId: string,
  tableName: string
): void {
  writeSecure(mgPath(sessionId, tableName), String(Date.now() / 1000));
}

/**
 * Remove the monitor-gap marker for a table. Called by hooks after the
 * coverage prompt has been delivered so subsequent post-edit / pre-commit
 * prompts don't re-nag for the same gap. A fresh Workflow 2 run will
 * re-emit MC_MONITOR_GAP if the gap persists.
 */
export function clearMonitorGap(
  sessionId: string,
  tableName: string
): void {
  const path = mgPath(sessionId, tableName);
  if (existsSync(path)) unlinkSync(path);
}

// --- Turn-level edit accumulator ---

export function getEditedTables(sessionId: string): string[] {
  const path = turnPath(sessionId);
  if (!existsSync(path)) return [];
  try {
    const content = readFileSync(path, "utf-8");
    const tables = content
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    // deduplicate, preserve order
    return [...new Map(tables.map((t) => [t, t])).values()];
  } catch {
    return [];
  }
}

export function addEditedTable(
  sessionId: string,
  tableName: string
): void {
  const existing = getEditedTables(sessionId);
  if (existing.includes(tableName)) return;
  existing.push(tableName);
  writeSecure(turnPath(sessionId), existing.join("\n") + "\n");
}

export function clearEditedTables(sessionId: string): void {
  const path = turnPath(sessionId);
  if (existsSync(path)) unlinkSync(path);
}

// --- Pending validation ---

export function moveToPendingValidation(sessionId: string): void {
  const tables = getEditedTables(sessionId);
  if (tables.length > 0) {
    const existing = getPendingValidationTables(sessionId);
    const merged = [
      ...new Map([...existing, ...tables].map((t) => [t, t])).values(),
    ];
    writeSecure(pendingPath(sessionId), merged.join("\n") + "\n");
  }
  clearEditedTables(sessionId);
}

export function getPendingValidationTables(sessionId: string): string[] {
  const path = pendingPath(sessionId);
  if (!existsSync(path)) return [];
  try {
    return readFileSync(path, "utf-8")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
  } catch {
    return [];
  }
}

// --- dbt project config cache ---

/** True if path is a regular file, following symlinks; false on any error. */
function isRegularFile(path: string): boolean {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

/**
 * Every dbt_project.yml above filePath, nearest first. Only regular files
 * count: a directory or FIFO with that name is not a project, and reading a
 * FIFO would block.
 */
export function findDbtProjectYmls(filePath: string): string[] {
  const found: string[] = [];
  let directory = dirname(resolve(filePath));
  while (true) {
    const candidate = join(directory, "dbt_project.yml");
    if (isRegularFile(candidate)) found.push(candidate);
    const parent = dirname(directory);
    if (parent === directory) return found;
    directory = parent;
  }
}

function dbtConfigCachePath(projectYmlPath: string): string {
  const key = createHash("md5")
    .update(projectYmlPath)
    .digest("hex")
    .slice(0, 12);
  return join(CACHE_DIR, `${DBT_CONFIG_PREFIX}${key}`);
}

/**
 * The text of path, opened without blocking and read only if the opened file is
 * a regular one: a FIFO swapped in after discovery would otherwise block the
 * hook. Throws if it can't be read. Invalid UTF-8 is replaced, as main's
 * readFileSync(path, "utf-8") did, so a stray byte in a comment keeps the
 * settings around it.
 */
function readRegularFile(path: string): string {
  const fd = openSync(path, constants.O_RDONLY | (constants.O_NONBLOCK ?? 0));
  try {
    if (!fstatSync(fd).isFile()) throw new Error(`not a regular file: ${path}`);
    return readFileSync(fd, "utf-8");
  } finally {
    closeSync(fd);
  }
}

/**
 * Parse path configs from dbt_project.yml. Throws if the file can't be read,
 * so a failed read is never taken for a project with default paths.
 */
function parseDbtProjectPaths(projectYmlPath: string): Partial<DbtPaths> {
  const result: Partial<DbtPaths> = {};
  const lines = readRegularFile(projectYmlPath).split("\n");

  let currentKey: string | null = null;
  const knownKeys = Object.keys(DBT_DEFAULT_PATHS);

  for (const line of lines) {
    const stripped = line.trim();

    let matched = false;
    for (const key of knownKeys) {
      if (stripped.startsWith(`${key}:`)) {
        const valuePart = stripped.slice(key.length + 1).trim();
        if (valuePart.startsWith("[")) {
          // Inline list: key: ['a', 'b']
          const inner = valuePart.replace(/^\[|\]$/g, "");
          const items = inner
            .split(",")
            .map((s) => s.trim().replace(/^['"]|['"]$/g, ""))
            .filter(Boolean);
          if (items.length > 0) result[key] = items;
          currentKey = null;
        } else if (!valuePart || valuePart === "") {
          // Block list follows
          currentKey = key;
          result[key] = [];
        }
        matched = true;
        break;
      }
    }

    if (!matched) {
      if (currentKey && stripped.startsWith("- ")) {
        const item = stripped.slice(2).trim().replace(/^['"]|['"]$/g, "");
        if (item) {
          (result[currentKey] ??= []).push(item);
        }
      } else if (
        currentKey &&
        !stripped.startsWith("#") &&
        stripped.length > 0
      ) {
        currentKey = null;
      }
    }
  }

  return result;
}

/**
 * dbt project paths for the nearest project containing filePath, or defaults
 * when there is none, it isn't a regular file, or it can't be read.
 */
export function getDbtPaths(filePath: string): DbtPaths {
  const nearest = findNearestDbtProjectEntry(filePath);
  if (nearest === null || !isRegularFile(nearest)) return { ...DBT_DEFAULT_PATHS };
  try {
    return getDbtProjectPaths(nearest);
  } catch {
    return { ...DBT_DEFAULT_PATHS };
  }
}

/**
 * The nearest entry of any kind named dbt_project.yml above filePath, as main's
 * lookup found it: a directory or FIFO there still marks the nearest project
 * (with default settings), so this rule never gates less than main did. Only a
 * regular file is ever read.
 */
function findNearestDbtProjectEntry(filePath: string): string | null {
  let directory = dirname(resolve(filePath));
  while (true) {
    const candidate = join(directory, "dbt_project.yml");
    if (existsSync(candidate)) return candidate;
    const parent = dirname(directory);
    if (parent === directory) return null;
    directory = parent;
  }
}

/**
 * The paths one dbt_project.yml configures, with defaults for the rest. Cached
 * while the file's mtime is unchanged. Throws if the file can't be stat'ed or
 * read, and caches nothing then.
 */
export function getDbtProjectPaths(projectYml: string): DbtPaths {
  const cachePath = dbtConfigCachePath(projectYml);
  const mtime = statSync(projectYml).mtimeMs;

  // Check cache
  if (existsSync(cachePath)) {
    try {
      const cached = JSON.parse(readFileSync(cachePath, "utf-8"));
      if (cached.mtime === mtime) {
        return cached.paths ?? { ...DBT_DEFAULT_PATHS };
      }
    } catch {
      // ignore
    }
  }

  // Parse and cache
  const parsed = parseDbtProjectPaths(projectYml);
  const paths: DbtPaths = { ...DBT_DEFAULT_PATHS };
  for (const [key, value] of Object.entries(parsed)) {
    if (value) paths[key] = value;
  }
  try {
    writeSecure(cachePath, JSON.stringify({ mtime, paths }));
  } catch {
    // ignore
  }

  return paths;
}

// --- Lazy cleanup ---

export function cleanupStaleCache(): void {
  const markerPath = join(CACHE_DIR, CLEANUP_MARKER);
  const now = Date.now() / 1000;

  if (existsSync(markerPath)) {
    try {
      const markerMtime = statSync(markerPath).mtimeMs / 1000;
      if (now - markerMtime < 3600) return;
    } catch {
      // ignore
    }
  }

  try {
    writeSecure(markerPath, String(now));
  } catch {
    return;
  }

  const LEGACY_PREFIX = "mc_safe_change_";
  try {
    for (const filename of readdirSync(CACHE_DIR)) {
      const isOurs =
        ALL_PREFIXES.some((p) => filename.startsWith(p)) ||
        filename.startsWith(LEGACY_PREFIX);
      if (!isOurs) continue;
      const filepath = join(CACHE_DIR, filename);
      try {
        const fileMtime = statSync(filepath).mtimeMs / 1000;
        if (now - fileMtime > STALE_THRESHOLD_SECONDS) {
          unlinkSync(filepath);
        }
      } catch {
        continue;
      }
    }
  } catch {
    // ignore
  }
}
