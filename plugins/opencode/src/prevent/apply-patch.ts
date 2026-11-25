/**
 * OpenCode `apply_patch`: which files a patch touches.
 *
 * The tool's `patchText` looks like:
 *
 *     *** Begin Patch
 *     *** Add File: <path>          (then "+" lines)
 *     *** Delete File: <path>
 *     *** Update File: <path>
 *     *** Move to: <path>           (optional, on the line right after Update)
 *     @@ ...                        (hunks)
 *     *** End Patch
 *
 * The parser follows OpenCode 1.x's own (`parsePatch` in anomalyco/opencode v1.19.6,
 * packages/opencode/src/patch/index.ts), so it reports the files OpenCode would
 * change: headers only between the Begin and End markers and only at the start of
 * a line, and a Move only when it directly follows its Update header. Markers are
 * found by trimmed line, so a patch wrapped in a heredoc parses the same way.
 * OpenCode resolves every path against the session directory.
 */
import { resolve } from "path";

export type PatchOp = {
  kind: "add" | "delete" | "update";
  path: string;
  movePath?: string;
};

const BEGIN = "*** Begin Patch";
const END = "*** End Patch";
const MOVE_TO = "*** Move to:";
const HEADERS: Array<[PatchOp["kind"], string]> = [
  ["add", "*** Add File:"],
  ["delete", "*** Delete File:"],
  ["update", "*** Update File:"],
];

function header(line: string): [PatchOp["kind"], string] | null {
  for (const [kind, prefix] of HEADERS) {
    if (line.startsWith(prefix)) {
      const path = line.slice(prefix.length).trim();
      return path ? [kind, path] : null;
    }
  }
  return null;
}

/** Operations in a patch, in order. [] when OpenCode would reject the envelope. */
export function parsePatchOps(patchText: unknown): PatchOp[] {
  if (typeof patchText !== "string") return [];
  const lines = patchText.split("\n");
  const begin = lines.findIndex((line) => line.trim() === BEGIN);
  const end = lines.findIndex((line) => line.trim() === END);
  if (begin === -1 || end === -1 || begin >= end) return [];

  const ops: PatchOp[] = [];
  for (let i = begin + 1; i < end; i++) {
    const found = header(lines[i]);
    if (!found) continue;
    const [kind, path] = found;
    const op: PatchOp = { kind, path };
    if (kind === "update" && i + 1 < end && lines[i + 1].startsWith(MOVE_TO)) {
      const movePath = lines[i + 1].slice(MOVE_TO.length).trim();
      if (movePath) op.movePath = movePath;
      i++;
    }
    ops.push(op);
  }
  return ops;
}

function unique(paths: string[]): string[] {
  return [...new Set(paths)];
}

/** Every path the operations touch, resolved against `directory`; a move gives both. */
export function patchPaths(ops: PatchOp[], directory: string): string[] {
  return unique(
    ops.flatMap((op) => [op.path, op.movePath].filter((p): p is string => !!p).map((p) => resolve(directory, p)))
  );
}

/**
 * The files a successful apply_patch reports in its result metadata (`files[]` with
 * absolute `filePath` and, for a move, `movePath`). null when it reports none, so the
 * caller can fall back to parsing the patch.
 */
export function reportedPaths(metadata: unknown): string[] | null {
  const files = (metadata as any)?.files;
  if (!Array.isArray(files)) return null;
  const paths: string[] = [];
  for (const file of files) {
    for (const p of [file?.filePath, file?.movePath]) {
      if (typeof p === "string" && p) paths.push(p);
    }
  }
  return unique(paths);
}
