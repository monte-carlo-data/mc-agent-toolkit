/**
 * dbt SQL file detection. Reads dbt_project.yml paths (cached) instead of
 * hardcoding folder names.
 *
 * Port of plugins/claude-code/prevent/hooks/lib/detect.py
 */
import { readFileSync, existsSync, statSync } from "fs";
import { basename, extname, dirname, join, resolve } from "path";
import { getDbtPaths } from "./cache";

const REF_PATTERNS = ["{{ ref(", "{{ source("];
const DBT_BLOCK_PATTERNS = ["{% macro", "{% snapshot"];
const MAX_SCAN_LINES = 50;

function getGatedDirs(filePath: string): Set<string> {
  const paths = getDbtPaths(filePath);
  const gated = new Set<string>();
  for (const key of ["model-paths", "macro-paths", "snapshot-paths"] as const) {
    for (const p of paths[key] ?? []) {
      const last = p.replace(/\/+$/, "").split("/").pop()!;
      gated.add(last);
    }
  }
  return gated;
}

function getExcludedDirs(filePath: string): Set<string> {
  const paths = getDbtPaths(filePath);
  const excluded = new Set<string>();
  for (const key of ["seed-paths", "analysis-paths"] as const) {
    for (const p of paths[key] ?? []) {
      const last = p.replace(/\/+$/, "").split("/").pop()!;
      excluded.add(last);
    }
  }
  return excluded;
}

function getMacroDirs(filePath: string): Set<string> {
  const paths = getDbtPaths(filePath);
  return new Set(
    (paths["macro-paths"] ?? []).map((p) =>
      p.replace(/\/+$/, "").split("/").pop()!
    )
  );
}

function setsIntersect(a: Set<string>, b: Set<string>): boolean {
  for (const item of a) {
    if (b.has(item)) return true;
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

  const normalized = filePath.replace(/\\/g, "/");
  const parts = new Set(normalized.split("/"));

  const excluded = getExcludedDirs(filePath);
  if (setsIntersect(parts, excluded)) return false;

  const gated = getGatedDirs(filePath);
  if (!setsIntersect(parts, gated)) return false;

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

  const normalized = filePath.replace(/\\/g, "/");
  const parts = new Set(normalized.split("/"));

  const excluded = getExcludedDirs(filePath);
  if (setsIntersect(parts, excluded)) return false;

  const paths = getDbtPaths(filePath);
  const modelDirs = new Set(
    (paths["model-paths"] ?? []).map((p) =>
      p.replace(/\/+$/, "").split("/").pop()!
    )
  );
  return setsIntersect(parts, modelDirs);
}

/**
 * Check if filePath is under a macro directory.
 */
export function isMacroFile(filePath: string): boolean {
  const normalized = filePath.replace(/\\/g, "/");
  const parts = new Set(normalized.split("/"));
  return setsIntersect(parts, getMacroDirs(filePath));
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
