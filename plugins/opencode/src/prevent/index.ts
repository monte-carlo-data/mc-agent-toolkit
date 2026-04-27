/**
 * Monte Carlo Prevent plugin for OpenCode.
 *
 * Replicates the Claude Code prevent plugin's hook behavior:
 * - PreToolUse (edit gate): blocks dbt model edits until impact assessment runs
 * - PostToolUse (edit tracking): accumulates edited table names per turn
 * - PreToolUse (commit gate): prompts for validation before committing dbt changes
 * - Stop (turn-end): prompts for validation queries and monitor coverage
 *
 * Port of plugins/claude-code/prevent/hooks/*.py
 */
import type { Plugin } from "@opencode-ai/plugin";
import { existsSync } from "fs";
import { isDbtModel, isDbtSchemaFile, extractTableName } from "./detect";
import {
  cleanupStaleCache,
  getImpactCheckState,
  markImpactCheckInjected,
  markImpactCheckVerified,
  getImpactCheckAgeSeconds,
  hasMonitorGap,
  markMonitorGap,
  clearMonitorGap,
  addEditedTable,
  getEditedTables,
  getPendingValidationTables,
  moveToPendingValidation,
} from "./cache";

const GRACE_PERIOD_SECONDS = 120;

/** Tools that modify files — the names OpenCode uses for its built-in tools. */
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
): Promise<{ impactCheck: boolean; monitorGap: boolean }> {
  const found = { impactCheck: false, monitorGap: false };
  const escaped = tableName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const icPattern = new RegExp(`MC_IMPACT_CHECK_COMPLETE: ${escaped}\\b`);
  const mgPattern = new RegExp(`MC_MONITOR_GAP: ${escaped}\\b`);

  try {
    const response = await client.session.messages({
      path: { id: sessionId },
    });
    const messages = response.data ?? [];
    for (const msg of messages) {
      for (const part of msg.parts ?? []) {
        const text = "text" in part ? (part as any).text : "";
        if (typeof text !== "string") continue;
        if (icPattern.test(text)) found.impactCheck = true;
        if (mgPattern.test(text)) found.monitorGap = true;
      }
    }
  } catch {
    // If SDK call fails, fall back to not finding markers
  }
  return found;
}

/**
 * Extract file path from tool args. OpenCode edit/write tools use `filePath`.
 */
function getFilePath(args: any): string {
  return args?.filePath ?? args?.file_path ?? args?.path ?? "";
}

/**
 * Extract all file paths from apply_patch patchText.
 * Parses markers like `*** Update File: path/to/file.sql`
 */
function getFilePathsFromPatch(args: any): string[] {
  const patchText: string = args?.patchText ?? "";
  if (!patchText) return [];
  const paths: string[] = [];
  const pattern = /^\*\*\*\s+(?:Update|Add|Delete)\s+File:\s*(.+)$/gm;
  let match;
  while ((match = pattern.exec(patchText)) !== null) {
    const p = match[1].trim();
    if (p) paths.push(p);
  }
  return paths;
}

/**
 * Get all file paths from tool args, handling both regular tools and apply_patch.
 */
function getAllFilePaths(tool: string, args: any): string[] {
  if (tool === "apply_patch") {
    return getFilePathsFromPatch(args);
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
  return {
    "tool.execute.before": async (input, output) => {
      try {
        const { tool, sessionID } = input;

        // --- Pre-edit gate ---
        if (EDIT_TOOLS.has(tool)) {
          cleanupStaleCache();

          const filePaths = getAllFilePaths(tool, output.args);
          // Check each file in the tool call (apply_patch may touch multiple)
          for (const filePath of filePaths) {
            if (!isDbtModel(filePath)) continue;

            // New models have no blast radius — let SKILL.md handle Workflow 1
            if (!existsSync(filePath)) continue;

            const tableName = extractTableName(filePath);
            const state = getImpactCheckState(sessionID, tableName);

            if (state === "verified") continue;

            if (state === "injected") {
              // Check messages for completion marker
              const markers = await scanMessagesForMarkers(
                client,
                sessionID,
                tableName
              );
              if (markers.monitorGap && !hasMonitorGap(sessionID, tableName)) {
                markMonitorGap(sessionID, tableName);
              }
              if (markers.impactCheck) {
                markImpactCheckVerified(sessionID, tableName);
                continue;
              }
              // Not completed — block without re-injecting if within grace period
              const age = getImpactCheckAgeSeconds(sessionID, tableName);
              if (age < GRACE_PERIOD_SECONDS) {
                throw new Error(
                  `Monte Carlo Prevent: the impact assessment for ${tableName} ` +
                    `has not completed yet. Complete the assessment before editing this file.`
                );
              }
              // Grace period expired — re-inject below
            } else if (state === null) {
              // Check if skill was invoked voluntarily before any edit
              const markers = await scanMessagesForMarkers(
                client,
                sessionID,
                tableName
              );
              if (markers.monitorGap && !hasMonitorGap(sessionID, tableName)) {
                markMonitorGap(sessionID, tableName);
              }
              if (markers.impactCheck) {
                markImpactCheckVerified(sessionID, tableName);
                continue;
              }
            }

            // Block the edit until impact assessment runs
            markImpactCheckInjected(sessionID, tableName);

            const hookTriggeredNote =
              "This assessment is hook-triggered — only emit MC_IMPACT_CHECK_COMPLETE " +
              "markers for tables whose lineage and monitor coverage were fetched " +
              "directly via Monte Carlo tools.";

            const workflowOrderNote =
              "If Workflow 1 (asset-health delegation) has not yet run for this table " +
              "this session, run it first via the Skill tool — it surfaces the table's " +
              "health, lineage, alerts, and monitors as framing. Then run Workflow 2 " +
              "(change impact assessment), reusing the asset-health data rather than " +
              "re-fetching. If Workflow 1 already ran for this table, skip directly to " +
              "Workflow 2.";

            if (tableName.startsWith("macro:")) {
              const macroName = tableName.slice("macro:".length);
              throw new Error(
                `Monte Carlo Prevent: this macro (${macroName}) is inlined into ` +
                  `models at compile time — changes here affect every model that calls it. ` +
                  `Identify which models use this macro, then run the change impact ` +
                  `assessment for the affected models before editing this file. ` +
                  workflowOrderNote +
                  " " +
                  hookTriggeredNote
              );
            } else {
              throw new Error(
                `Monte Carlo Prevent: run the change impact assessment ` +
                  `for ${tableName} before editing this file. Present the full ` +
                  `impact report and synthesis step, then retry the edit. ` +
                  workflowOrderNote +
                  " " +
                  hookTriggeredNote
              );
            }
          }
        }

        // --- Pre-commit gate ---
        if (tool === "bash") {
          const command = getCommand(output.args);
          if (!command.includes("git commit")) return;

          const cwd = worktree || directory;
          const stagedTables = await getStagedModelTables(cwd);
          if (stagedTables.length === 0) return;

          // Only prompt if impact assessment ran for at least one staged table
          const w4Tables = stagedTables.filter(
            (t) => getImpactCheckState(sessionID, t) === "verified"
          );
          if (w4Tables.length === 0) return;

          const tableList = w4Tables.join(", ");
          const gapTables = w4Tables.filter((t) =>
            hasMonitorGap(sessionID, t)
          );

          let message = `Committing changes to ${tableList}. Run validation queries before committing? (yes / no)`;

          if (gapTables.length > 0) {
            const gapList = gapTables.join(", ");
            message +=
              `\n\nMonitor coverage: the impact assessment found no custom monitors ` +
              `on ${gapList}. Generate monitor definitions before committing? (yes / no)`;
            for (const t of gapTables) {
              clearMonitorGap(sessionID, t);
            }
          }

          // Inject context by throwing — the LLM will see this message and can
          // present it to the user before retrying the commit.
          throw new Error(`Monte Carlo Prevent: ${message}`);
        }
      } catch (e) {
        // Re-throw intentional blocks (our own errors)
        if (e instanceof Error && e.message.startsWith("Monte Carlo Prevent:")) {
          throw e;
        }
        // Swallow unexpected errors — never block the engineer
      }
    },

    "tool.execute.after": async (input, output) => {
      try {
        const { tool, sessionID, args } = input;
        if (!EDIT_TOOLS.has(tool)) return;

        const filePaths = getAllFilePaths(tool, args);
        for (const filePath of filePaths) {
          if (!isDbtModel(filePath) && !isDbtSchemaFile(filePath)) continue;
          const tableName = extractTableName(filePath);
          addEditedTable(sessionID, tableName);
        }
      } catch {
        // Never block on error
      }
    },

    event: async ({ event }) => {
      try {
        if (event.type !== "session.idle") return;
        const sessionID = (event as any).properties?.sessionID;
        if (!sessionID) return;

        const tables = getEditedTables(sessionID);
        if (tables.length === 0) return;

        // If validation was already prompted, silently merge new edits
        if (getPendingValidationTables(sessionID).length > 0) {
          moveToPendingValidation(sessionID);
          return;
        }

        // Only prompt if impact assessment was triggered for at least one table
        const w4Tables = tables.filter((t) => {
          const state = getImpactCheckState(sessionID, t);
          return state === "injected" || state === "verified";
        });
        if (w4Tables.length === 0) return;

        const gapTables = tables.filter((t) => hasMonitorGap(sessionID, t));

        const tableList = tables.join(", ");
        const count = tables.length;
        let reason =
          `You've changed ${count} dbt model(s): ${tableList}. ` +
          `Would you like to run validation queries to verify these changes behaved as intended?\n\n` +
          `> Yes: generate and run queries for all changed models\n` +
          `> No: use /mc-validate anytime to validate changes`;

        if (gapTables.length > 0) {
          const gapList = gapTables.join(", ");
          reason +=
            `\n\nMonitor coverage: the impact assessment found no custom monitors ` +
            `on ${gapList}. Would you like to generate monitor definitions?\n\n` +
            `> Yes: suggest monitors for the new or changed logic\n` +
            `> No: skip for now`;
          for (const t of gapTables) {
            clearMonitorGap(sessionID, t);
          }
        }

        moveToPendingValidation(sessionID);

        // Use the SDK client to send a prompt to the session.
        // This sends the validation reminder as a user message so the LLM
        // can present it and wait for the user's response.
        try {
          await client.session.prompt({
            path: { id: sessionID },
            body: {
              parts: [{ type: "text", text: reason }],
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

/**
 * Get table names from staged dbt SQL files.
 */
async function getStagedModelTables(cwd: string): Promise<string[]> {
  try {
    const proc = Bun.spawn(["git", "diff", "--cached", "--name-only"], {
      cwd,
      stdout: "pipe",
      stderr: "pipe",
    });
    const text = await new Response(proc.stdout).text();
    await proc.exited;

    const tables: string[] = [];
    for (const line of text.trim().split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const fullPath = `${cwd}/${trimmed}`;
      if (isDbtModel(fullPath)) {
        tables.push(extractTableName(fullPath));
      }
    }
    return tables;
  } catch {
    return [];
  }
}

export default {
  id: "mc-prevent",
  server: McPrevent,
};
