/**
 * Monte Carlo Prevent for OpenCode v1 (the `server` entry, `@opencode-ai/plugin`).
 *
 * Replicates the Claude Code prevent plugin's hook behavior:
 * - PreToolUse (edit gate): blocks dbt model edits until impact assessment runs
 * - PostToolUse (edit tracking): accumulates edited table names per turn
 * - PreToolUse (commit gate): prompts for validation before committing dbt changes
 * - Stop (turn-end): prompts for validation queries and monitor coverage
 *
 * Port of plugins/claude-code/prevent/hooks/*.py. The decisions live in ./core.ts,
 * shared with the v2 entry in ./v2.ts.
 */
import type { Plugin } from "@opencode-ai/plugin";
import { ensureToolkitIdsAndBeacon, buildToolkitHeaders } from "../telemetry/install-beacon.ts";
import { parsePatchOps, patchPaths, reportedPaths } from "./apply-patch.ts";
import { createPrevent, findMarkers, type Markers } from "./core.ts";

/** Tools that modify files — the names OpenCode v1 uses for its built-in tools. */
const EDIT_TOOLS = new Set(["edit", "write", "apply_patch", "multiedit"]);

type OpencodeClient = ReturnType<typeof import("@opencode-ai/sdk").createOpencodeClient>;

/**
 * Scan session messages for MC_IMPACT_CHECK_COMPLETE and MC_MONITOR_GAP markers.
 *
 * In OpenCode, we use the SDK client to read session messages instead of
 * scanning a transcript file.
 */
async function scanMessagesForMarkers(
  client: OpencodeClient,
  sessionId: string,
  tableName: string
): Promise<Markers> {
  try {
    const response = await client.session.messages({
      path: { id: sessionId },
    });
    const texts: string[] = [];
    for (const msg of response.data ?? []) {
      for (const part of msg.parts ?? []) {
        const text = "text" in part ? (part as any).text : "";
        if (typeof text === "string") texts.push(text);
      }
    }
    return findMarkers(texts, tableName);
  } catch {
    // If SDK call fails, fall back to not finding markers
    return { impactCheck: false, monitorGap: false };
  }
}

/**
 * Extract file path from tool args. OpenCode edit/write tools use `filePath`.
 */
function getFilePath(args: any): string {
  return args?.filePath ?? args?.file_path ?? args?.path ?? "";
}

/**
 * Files a tool call will touch. apply_patch paths are resolved against the session
 * directory, as OpenCode does; other tools' paths are used as given.
 */
function getAllFilePaths(tool: string, args: any, directory: string): string[] {
  if (tool === "apply_patch") {
    return patchPaths(parsePatchOps(args?.patchText), directory);
  }
  const fp = getFilePath(args);
  return fp ? [fp] : [];
}

/**
 * Extract command from bash tool args.
 */
function getCommand(args: any): string {
  return args?.command ?? args?.cmd ?? "";
}

export const McPrevent: Plugin = async ({ client, directory, worktree }) => {
  const prevent = createPrevent((sessionID, tableName) =>
    scanMessagesForMarkers(client, sessionID, tableName)
  );

  return {
    // Inject toolkit telemetry headers onto the monte-carlo-mcp server at
    // config-load time so install_id (+ version) ride authed MCP traffic and the
    // anonymous beacon stream joins to MCP Tool Called. Done programmatically
    // (not via opencode.json {file:}, which fatally fails config load on a missing
    // file) so it stays fail-open: any error leaves the config untouched.
    config: async (config) => {
      try {
        const server = config.mcp?.["monte-carlo-mcp"];
        if (server?.type !== "remote") return;
        const headers = buildToolkitHeaders();
        if (Object.keys(headers).length > 0) {
          server.headers = { ...(server.headers ?? {}), ...headers };
        }
      } catch {
        // Fail-open — telemetry must never break config load / startup.
      }
    },

    "tool.execute.before": async (input, output) => {
      const { tool, sessionID, callID } = input;
      let filePaths: string[];
      let command: string;
      try {
        filePaths = EDIT_TOOLS.has(tool) ? getAllFilePaths(tool, output.args, directory) : [];
        command = tool === "bash" ? getCommand(output.args) : "";
      } catch {
        return; // Never block the engineer on unexpected input
      }
      if (EDIT_TOOLS.has(tool)) await prevent.gateEdit(sessionID, callID, filePaths);
      if (tool === "bash") await prevent.checkCommit(sessionID, command, worktree || directory);
    },

    "tool.execute.after": async (input, output) => {
      try {
        const { tool, sessionID, callID, args } = input;
        if (!EDIT_TOOLS.has(tool)) return;
        // apply_patch reports the files it changed; parse the patch only when it doesn't.
        const reported = tool === "apply_patch" ? reportedPaths(output?.metadata) : null;
        prevent.trackEdit(sessionID, callID, reported ?? getAllFilePaths(tool, args, directory));
      } catch {
        // Never block on error
      }
    },

    event: async ({ event }) => {
      // Install telemetry: on the first-ever session start, fire a one-shot
      // "Toolkit Installed" beacon (deduped by the persistent install_id marker).
      // Detached + fail-open so it never blocks or breaks the session.
      if (event.type === "session.created") {
        void ensureToolkitIdsAndBeacon().catch(() => {});
        return;
      }

      try {
        if (event.type !== "session.idle") return;
        const sessionID = (event as any).properties?.sessionID;
        if (!sessionID) return;

        const reminder = prevent.turnEndReminder(sessionID);
        if (!reminder) return;
        prevent.markReminded(sessionID, reminder);

        // Use the SDK client to send a prompt to the session.
        // This sends the validation reminder as a user message so the LLM
        // can present it and wait for the user's response.
        try {
          await client.session.prompt({
            path: { id: sessionID },
            body: {
              parts: [{ type: "text", text: reminder.text }],
              noReply: true,
            },
          });
        } catch {
          // If SDK call fails, the prompt is best-effort.
          // The system prompt instructions in SKILL.md serve as a fallback.
        }
      } catch {
        // Never block on error
      }
    },
  };
};
