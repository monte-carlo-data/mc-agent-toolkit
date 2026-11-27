/**
 * Monte Carlo Prevent for OpenCode v2 (the `setup` entry, `@opencode/plugin`).
 *
 * The same behavior as the v1 entry (./v1.ts), on v2's API:
 * - pre-edit gate and commit checkpoint: `ctx.tool.hook("execute.before")`; a thrown
 *   error rejects the call and reaches the model as its result
 * - edit tracking: `ctx.tool.hook("execute.after")`, completed calls only
 * - end-of-turn reminder: `ctx.session.hook("experimental.idle")` admits the question
 *   as a synthetic message, so the model takes one more step and asks it (like Claude
 *   Code's Stop hook; v1 adds it without a reply)
 * - MCP headers: `ctx.mcp.transform`
 * - install beacon: the `session.created` event
 *
 * v2 names its built-in tools `edit`, `write` and `patch` (with `path` / `patchText`)
 * and `shell` (`command`, optional `workdir`). Its input-repair plugin rewrites `bash`
 * to `shell` before this hook runs. Paths are resolved against the session's
 * directory on this machine; a session on a remote workspace isn't checked.
 */
import type { Plugin } from "@opencode/plugin";
import { homedir } from "node:os";
import { isAbsolute, join, resolve } from "node:path";
import { ensureToolkitIdsAndBeacon, buildToolkitHeaders } from "../telemetry/install-beacon.ts";
import { parsePatchOpsV2, patchPaths } from "./apply-patch.ts";
import { createPrevent, findMarkers } from "./core.ts";

type Context = Plugin.Context;

const EDIT_TOOLS = new Set(["edit", "write", "patch"]);
const SHELL_TOOL = "shell";
const MARKER_LINE = /MC_(?:IMPACT_CHECK_COMPLETE|MONITOR_GAP): \S+/g;
// Sessions whose markers are kept in memory; the oldest is dropped past this.
const MAX_MARKER_SESSIONS = 200;
const REMINDER_DESCRIPTION = "Monte Carlo Prevent: validation reminder";

/** `path` resolved the way OpenCode resolves a tool path: `~` is home, relative is `base`. */
function resolvePath(path: string, base: string): string {
  if (path === "~") return homedir();
  if (path.startsWith("~/")) return join(homedir(), path.slice(2));
  return isAbsolute(path) ? path : resolve(base, path);
}

function editedPaths(tool: string, input: any, base: string): string[] {
  if (tool === "patch") return patchPaths(parsePatchOpsV2(input?.patchText), base);
  const path = input?.path;
  return typeof path === "string" && path ? [resolvePath(path, base)] : [];
}

/** Text the assistant wrote in a v2 session message; nothing for user or synthetic text. */
function assistantText(message: any): string[] {
  if (message?.type !== "assistant" || !Array.isArray(message.content)) return [];
  return message.content
    .filter((part: any) => part?.type === "text" && typeof part.text === "string")
    .map((part: any) => part.text);
}

export async function setup(ctx: Context) {
  const controller = new AbortController();

  // Marker lines the assistant wrote, per session, from the event stream. The session
  // context the gate reads starts at the latest compaction, so a marker written before
  // one would otherwise be lost.
  const seenMarkers = new Map<string, string[]>();
  function rememberMarkers(sessionID: string, text: string) {
    const lines = text.match(MARKER_LINE);
    if (!lines) return;
    const known = seenMarkers.get(sessionID) ?? [];
    seenMarkers.delete(sessionID);
    seenMarkers.set(sessionID, [...known, ...lines]);
    for (const k of seenMarkers.keys()) {
      if (seenMarkers.size <= MAX_MARKER_SESSIONS) break;
      seenMarkers.delete(k);
    }
  }

  const prevent = createPrevent(async (sessionID, tableName) => {
    const texts = [...(seenMarkers.get(sessionID) ?? [])];
    try {
      const messages = await ctx.session.context({ sessionID });
      for (const message of messages ?? []) texts.push(...assistantText(message));
    } catch {
      // Fall back to the markers seen on the event stream
    }
    return findMarkers(texts, tableName);
  });

  async function sessionDirectory(sessionID: string): Promise<string> {
    try {
      const info: any = await ctx.session.get({ sessionID });
      const directory = info?.location?.directory;
      if (typeof directory === "string" && directory) return directory;
    } catch {
      // Fall back to where this plugin instance loaded
    }
    return ctx.location.directory;
  }

  await ctx.tool.hook("execute.before", async (event) => {
    const { tool, sessionID, id } = event;
    if (!EDIT_TOOLS.has(tool) && tool !== SHELL_TOOL) return;
    let filePaths: string[] = [];
    let command = "";
    let cwd = "";
    try {
      const base = await sessionDirectory(sessionID);
      const input = event.input as any;
      if (EDIT_TOOLS.has(tool)) filePaths = editedPaths(tool, input, base);
      else {
        command = typeof input?.command === "string" ? input.command : "";
        cwd = typeof input?.workdir === "string" && input.workdir ? resolvePath(input.workdir, base) : base;
      }
    } catch {
      return; // Never block the engineer on unexpected input
    }
    if (EDIT_TOOLS.has(tool)) await prevent.gateEdit(sessionID, id, filePaths);
    else await prevent.checkCommit(sessionID, command, cwd);
  });

  await ctx.tool.hook("execute.after", async (event) => {
    try {
      if (!EDIT_TOOLS.has(event.tool)) return;
      if (event.status !== "completed") {
        prevent.dropCall(event.sessionID, event.id);
        return;
      }
      const base = await sessionDirectory(event.sessionID);
      prevent.trackEdit(event.sessionID, event.id, editedPaths(event.tool, event.input, base));
    } catch {
      // Never block on error
    }
  });

  await ctx.session.hook("experimental.idle", async (event) => {
    try {
      const { sessionID } = event;
      // The session's own shell or subagent wakes it when done, and this runs again.
      if (event.background.some((job) => job.sessionID === sessionID)) return;
      const info: any = await ctx.session.get({ sessionID }).catch(() => undefined);
      if (info?.parentID) return; // a subagent's session; its parent asks

      const reminder = prevent.turnEndReminder(sessionID);
      if (!reminder) return;
      await ctx.session.synthetic({ sessionID, text: reminder.text, description: REMINDER_DESCRIPTION });
      // Only once it is admitted, so a failed admission is retried at the next idle.
      prevent.markReminded(sessionID, reminder);
    } catch {
      // Best-effort; the SKILL.md instructions are the fallback
    }
  });

  // Headers are computed on the first transform that finds the remote server, so no
  // install id is created when it isn't configured, and replays reuse the same value.
  let headers: Record<string, string> | undefined;
  await ctx.mcp.transform((editor) => {
    try {
      editor.update("monte-carlo-mcp", (server) => {
        if (server.type !== "remote") return;
        headers ??= buildToolkitHeaders();
        if (Object.keys(headers).length > 0) server.headers = { ...(server.headers ?? {}), ...headers };
      });
    } catch {
      // Fail-open — telemetry must never break MCP setup.
    }
  });

  void (async () => {
    const events = ctx.event.subscribe({
      types: ["session.created", "session.text.ended"],
      signal: controller.signal,
    });
    for await (const event of events) {
      try {
        if (event.type === "session.text.ended") {
          rememberMarkers(event.data.sessionID, event.data.text);
        } else if (event.type === "session.created") {
          if (event.location && event.location.directory !== ctx.location.directory) continue;
          void ensureToolkitIdsAndBeacon().catch(() => {});
        }
      } catch {
        // Never let one event stop the loop
      }
    }
  })().catch(() => {});

  return () => controller.abort();
}
