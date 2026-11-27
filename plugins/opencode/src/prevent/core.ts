/**
 * Monte Carlo Prevent decisions shared by the OpenCode v1 and v2 entries.
 *
 * Each entry turns its host's hook events into file paths and session ids and calls
 * these functions; the gate and the commit checkpoint reject a tool call by throwing
 * a `Monte Carlo Prevent:` error, which both hosts return to the model as the call's
 * result. Nothing here depends on OpenCode types or on the Bun runtime, so it loads
 * under OpenCode's Node build too.
 */
import { existsSync } from "node:fs";
import { execFile } from "node:child_process";
import { join } from "node:path";
import { isDbtModel, isDbtSchemaFile, extractTableName } from "./detect.ts";
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
} from "./cache.ts";

const GRACE_PERIOD_SECONDS = 120;
const BLOCK_PREFIX = "Monte Carlo Prevent:";

// A call that passes the gate but fails, is denied or is aborted never reaches the
// post-edit hook, so its record lingers. The records are capped by count, not age,
// because a call can wait on OpenCode's edit-permission prompt for any length of time.
export const MAX_CALL_RECORDS = 500;

export type Markers = { impactCheck: boolean; monitorGap: boolean };

/** Reads the session's completion markers for one table. Must not throw. */
export type MarkerReader = (sessionID: string, tableName: string) => Promise<Markers>;

/** True for the errors the gate and checkpoint throw on purpose. */
export function isPreventBlock(e: unknown): e is Error {
  return e instanceof Error && e.message.startsWith(BLOCK_PREFIX);
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Which markers for `tableName` appear in any of `texts`. */
export function findMarkers(texts: Iterable<string>, tableName: string): Markers {
  const escaped = escapeRegExp(tableName);
  const icPattern = new RegExp(`MC_IMPACT_CHECK_COMPLETE: ${escaped}\\b`);
  const mgPattern = new RegExp(`MC_MONITOR_GAP: ${escaped}\\b`);
  const found = { impactCheck: false, monitorGap: false };
  for (const text of texts) {
    if (typeof text !== "string") continue;
    if (icPattern.test(text)) found.impactCheck = true;
    if (mgPattern.test(text)) found.monitorGap = true;
  }
  return found;
}

/**
 * The table an edited file counts toward in the validation prompt, or null if none.
 * `wasModel` maps the paths that were existing dbt models just before this call ran to
 * their table names: a file that is now gone (deleted or moved away), or whose new
 * content no longer looks like a model, can't be classified any more.
 */
function trackedTable(filePath: string, wasModel: Map<string, string> | undefined): string | null {
  if (isDbtSchemaFile(filePath)) return extractTableName(filePath);
  if (existsSync(filePath) && isDbtModel(filePath)) return extractTableName(filePath);
  return wasModel?.get(filePath) ?? null;
}

function editBlockMessage(tableName: string): string {
  const hookTriggeredNote =
    "This assessment is hook-triggered — only emit MC_IMPACT_CHECK_COMPLETE " +
    "markers for tables whose lineage and monitor coverage were fetched " +
    "directly via Monte Carlo tools. Write the completion marker only once the " +
    "edit is going ahead (if you ask the user whether to proceed, only after they " +
    "say yes), on its own line in your visible reply text (not only in your " +
    "reasoning, and not inside a tool call), in the form " +
    "`MC_IMPACT_CHECK_COMPLETE: <table>`, replacing <table> with the bare table " +
    `name ${tableName}. In that same message, re-read the file, then retry the ` +
    "edit in a later step, not in the same batch. If an edit is denied after you " +
    "wrote the marker, check that the marker line is in your reply text, not only " +
    "in your reasoning, before retrying.";

  const workflowOrderNote =
    "If Workflow 1 (asset-health pre-fetch) has not yet run for this table " +
    "this session, run it first: load the `monte-carlo-asset-health` skill via " +
    "the Skill tool (its full name may carry a plugin prefix, e.g. " +
    "`mc-agent-toolkit:monte-carlo-asset-health`) to gather lineage / alerts " +
    "/ monitors as data for the impact assessment. Read W1's report as data " +
    "and do NOT relay it to the engineer — only surface a disambiguation " +
    "prompt (if asset-health asks which match to use) or a one-line " +
    "stop-the-world warning (active critical alerts, severe staleness). " +
    "Then run Workflow 2 (change impact assessment), reusing the asset-health " +
    "data rather than re-fetching. Workflow 2 is the user-facing artifact. " +
    "If Workflow 1 already ran for this table, skip directly to Workflow 2.";

  if (tableName.startsWith("macro:")) {
    const macroName = tableName.slice("macro:".length);
    return (
      `${BLOCK_PREFIX} this macro (${macroName}) is inlined into ` +
      `models at compile time — changes here affect every model that calls it. ` +
      `Identify which models use this macro, then run the change impact ` +
      `assessment for the affected models before editing this file. ` +
      workflowOrderNote +
      " " +
      hookTriggeredNote
    );
  }
  return (
    `${BLOCK_PREFIX} run the change impact assessment ` +
    `for ${tableName} before editing this file. Present the full ` +
    `impact report and synthesis step, then ask the user whether to proceed before retrying the edit. ` +
    workflowOrderNote +
    " " +
    hookTriggeredNote
  );
}

function run(cmd: string, args: string[], cwd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, { cwd, encoding: "utf8" }, (error, stdout) => {
      if (error) reject(error);
      else resolve(stdout);
    });
  });
}

/**
 * Table names of the dbt models staged in the repository that contains `cwd`. Git
 * names staged files from the repository root, so they are resolved there rather than
 * against `cwd`, which may be a subdirectory. [] when `cwd` isn't in a repository.
 */
export async function getStagedModelTables(cwd: string): Promise<string[]> {
  try {
    const root = (await run("git", ["rev-parse", "--show-toplevel"], cwd)).trim();
    if (!root) return [];
    const text = await run("git", ["diff", "--cached", "--name-only"], root);
    const tables: string[] = [];
    for (const line of text.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const fullPath = join(root, trimmed);
      if (isDbtModel(fullPath)) tables.push(extractTableName(fullPath));
    }
    return tables;
  } catch {
    return [];
  }
}

export type Reminder = { text: string; gapTables: string[] };

export function createPrevent(readMarkers: MarkerReader) {
  // Per tool call (session + call id) that touches existing dbt models: those models
  // (path -> table name). Set before the gate runs, dropped when the gate blocks the
  // call, and taken by the post-edit hook. Idle isn't used for cleanup: OpenCode marks
  // a session idle on abort while the aborted tool can still finish and reach the
  // post-edit hook.
  const wasModelByCall = new Map<string, Map<string, string>>();
  const callKey = (sessionID: string, callID: string) => `${sessionID}\0${callID}`;

  async function gate(sessionID: string, callID: string, filePaths: string[]): Promise<void> {
    cleanupStaleCache();

    const key = callKey(sessionID, callID);
    // New models have no blast radius — let SKILL.md handle Workflow 1
    const tables = new Map<string, string>();
    for (const p of filePaths) {
      if (existsSync(p) && isDbtModel(p)) tables.set(p, extractTableName(p));
    }
    if (tables.size > 0) {
      wasModelByCall.set(key, tables);
      for (const k of wasModelByCall.keys()) {
        if (wasModelByCall.size <= MAX_CALL_RECORDS) break;
        wasModelByCall.delete(k);
      }
    }
    // Check each file in the tool call (a patch may touch several)
    for (const tableName of tables.values()) {
      const state = getImpactCheckState(sessionID, tableName);

      if (state === "verified") continue;

      if (state === "injected" || state === null) {
        // Injected: check for the completion marker. Absent: the assessment may have
        // been run voluntarily before any edit.
        const markers = await readMarkers(sessionID, tableName);
        if (markers.monitorGap && !hasMonitorGap(sessionID, tableName)) {
          markMonitorGap(sessionID, tableName);
        }
        if (markers.impactCheck) {
          markImpactCheckVerified(sessionID, tableName);
          continue;
        }
        if (state === "injected") {
          // Not completed — block without re-injecting if within grace period
          const age = getImpactCheckAgeSeconds(sessionID, tableName);
          if (age < GRACE_PERIOD_SECONDS) {
            throw new Error(
              `${BLOCK_PREFIX} the impact assessment for ${tableName} ` +
                `has not completed yet. If you already wrote the completion marker, ` +
                `check that it is on its own line in your visible reply text, not only ` +
                `in your reasoning or a tool call; otherwise complete the assessment ` +
                `before editing this file.`
            );
          }
          // Grace period expired — re-inject below
        }
      }

      // Block the edit until impact assessment runs
      markImpactCheckInjected(sessionID, tableName);
      throw new Error(editBlockMessage(tableName));
    }
  }

  return {
    /**
     * Pre-edit gate: throws a Prevent block for the first existing dbt model in
     * `filePaths` whose impact assessment hasn't completed. Any other error is
     * swallowed — the gate never blocks the engineer by accident.
     */
    async gateEdit(sessionID: string, callID: string, filePaths: string[]): Promise<void> {
      try {
        await gate(sessionID, callID, filePaths);
      } catch (e) {
        if (isPreventBlock(e)) {
          // A blocked call never runs, so it has nothing to track.
          wasModelByCall.delete(callKey(sessionID, callID));
          throw e;
        }
      }
    },

    /** Post-edit tracking: records the tables a finished call changed. Never throws. */
    trackEdit(sessionID: string, callID: string, filePaths: string[]): void {
      try {
        const key = callKey(sessionID, callID);
        const wasModel = wasModelByCall.get(key);
        wasModelByCall.delete(key);
        for (const filePath of filePaths) {
          const table = trackedTable(filePath, wasModel);
          if (table !== null) addEditedTable(sessionID, table);
        }
      } catch {
        // Never block on error
      }
    },

    /** Forgets a call the host won't report as finished. */
    dropCall(sessionID: string, callID: string): void {
      wasModelByCall.delete(callKey(sessionID, callID));
    },

    /**
     * Commit checkpoint: for a `git commit` run in `cwd`, throws a Prevent block that
     * asks about validation when a staged model's assessment ran. Never throws
     * anything else.
     */
    async checkCommit(sessionID: string, command: string, cwd: string): Promise<void> {
      try {
        if (!command.includes("git commit")) return;
        const stagedTables = await getStagedModelTables(cwd);
        if (stagedTables.length === 0) return;

        // Only prompt if impact assessment ran for at least one staged table
        const w4Tables = stagedTables.filter((t) => getImpactCheckState(sessionID, t) === "verified");
        if (w4Tables.length === 0) return;

        const tableList = w4Tables.join(", ");
        const gapTables = w4Tables.filter((t) => hasMonitorGap(sessionID, t));

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
        throw new Error(`${BLOCK_PREFIX} ${message}`);
      } catch (e) {
        if (isPreventBlock(e)) throw e;
      }
    },

    /**
     * The end-of-turn validation question for `sessionID`, or null when there is
     * nothing to ask. When the question was already asked this session, new edits are
     * merged into it silently and null is returned. The caller delivers the text and
     * then calls `markReminded`.
     */
    turnEndReminder(sessionID: string): Reminder | null {
      const tables = getEditedTables(sessionID);
      if (tables.length === 0) return null;

      // If validation was already prompted, silently merge new edits
      if (getPendingValidationTables(sessionID).length > 0) {
        moveToPendingValidation(sessionID);
        return null;
      }

      // Only prompt if impact assessment was triggered for at least one table
      const w4Tables = tables.filter((t) => {
        const state = getImpactCheckState(sessionID, t);
        return state === "injected" || state === "verified";
      });
      if (w4Tables.length === 0) return null;

      const gapTables = tables.filter((t) => hasMonitorGap(sessionID, t));

      const tableList = tables.join(", ");
      const count = tables.length;
      let text =
        `You've changed ${count} dbt model(s): ${tableList}. ` +
        `Would you like to run validation queries to verify these changes behaved as intended?\n\n` +
        `> Yes: generate and run queries for all changed models\n` +
        `> No: use /mc-validate anytime to validate changes`;

      if (gapTables.length > 0) {
        const gapList = gapTables.join(", ");
        text +=
          `\n\nMonitor coverage: the impact assessment found no custom monitors ` +
          `on ${gapList}. Would you like to generate monitor definitions?\n\n` +
          `> Yes: suggest monitors for the new or changed logic\n` +
          `> No: skip for now`;
      }
      return { text, gapTables };
    },

    /** Records that the reminder was delivered, so the next idle doesn't repeat it. */
    markReminded(sessionID: string, reminder: Reminder): void {
      for (const t of reminder.gapTables) clearMonitorGap(sessionID, t);
      moveToPendingValidation(sessionID);
    },
  };
}

export type Prevent = ReturnType<typeof createPrevent>;
