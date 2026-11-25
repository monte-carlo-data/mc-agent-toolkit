/**
 * Hook behavior tests — port of test_pre_edit_hook.py, test_post_edit_hook.py,
 * test_pre_commit_hook.py, test_turn_end_hook.py
 */
import { describe, it, expect, beforeEach, afterEach, mock } from "bun:test";
import { mkdtempSync, writeFileSync, readFileSync, unlinkSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { cleanCache, createDbtProject, createMockClient } from "./helpers";
import {
  markImpactCheckInjected,
  markImpactCheckVerified,
  getImpactCheckState,
  hasMonitorGap,
  addEditedTable,
  getEditedTables,
  getPendingValidationTables,
  moveToPendingValidation,
  markMonitorGap,
} from "../../src/prevent/cache";
import { McPrevent } from "../../src/prevent/index";

let tmpDir: string;

beforeEach(() => {
  cleanCache();
  tmpDir = mkdtempSync(join(tmpdir(), "hook-test-"));
});
afterEach(() => cleanCache());

/** An apply_patch body inside the Begin/End envelope OpenCode requires. */
function patch(...lines: string[]): string {
  return ["*** Begin Patch", ...lines, "*** End Patch"].join("\n");
}

// Helper to initialize the plugin and get hooks
async function getHooks(
  clientOptions: Parameters<typeof createMockClient>[0] = {},
  dirs: { directory?: string; worktree?: string } = {}
) {
  const client = createMockClient(clientOptions);
  const hooks = await McPrevent({
    client,
    directory: dirs.directory ?? tmpDir,
    worktree: dirs.worktree ?? tmpDir,
    project: {} as any,
    serverUrl: new URL("http://localhost"),
    $: {} as any,
  });
  return { hooks, client };
}

describe("PreEditGate (tool.execute.before on edit tools)", () => {
  it("passes through non-SQL files", async () => {
    const { hooks } = await getHooks();
    // Should not throw
    await hooks["tool.execute.before"]!(
      { tool: "edit", sessionID: "s1", callID: "c1" },
      { args: { filePath: "/project/readme.md" } }
    );
  });

  it("passes through SQL files outside dbt dirs", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {});
    const scriptsDir = join(projectDir, "scripts");
    require("fs").mkdirSync(scriptsDir, { recursive: true });
    writeFileSync(join(scriptsDir, "adhoc.sql"), "SELECT * FROM {{ ref('x') }}");

    await hooks["tool.execute.before"]!(
      { tool: "edit", sessionID: "s1", callID: "c1" },
      { args: { filePath: join(scriptsDir, "adhoc.sql") } }
    );
  });

  it("blocks dbt model with no prior assessment", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    await expect(
      hooks["tool.execute.before"]!(
        { tool: "edit", sessionID: "s1", callID: "c1" },
        { args: { filePath: join(projectDir, "models/orders.sql") } }
      )
    ).rejects.toThrow("impact assessment");
  });

  it("passes through when state is verified", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    markImpactCheckInjected("s1", "orders");
    markImpactCheckVerified("s1", "orders");

    await hooks["tool.execute.before"]!(
      { tool: "edit", sessionID: "s1", callID: "c1" },
      { args: { filePath: join(projectDir, "models/orders.sql") } }
    );
    // No throw = pass
  });

  it("blocks within grace period when no marker found", async () => {
    const { hooks } = await getHooks({ messages: [] });
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    markImpactCheckInjected("s1", "orders");

    await expect(
      hooks["tool.execute.before"]!(
        { tool: "edit", sessionID: "s1", callID: "c1" },
        { args: { filePath: join(projectDir, "models/orders.sql") } }
      )
    ).rejects.toThrow("not completed yet");
  });

  it("verifies when marker found in messages (injected state)", async () => {
    const { hooks } = await getHooks({
      messages: [
        { parts: [{ type: "text", text: "<!-- MC_IMPACT_CHECK_COMPLETE: orders -->" }] },
      ],
    });
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    markImpactCheckInjected("s1", "orders");

    await hooks["tool.execute.before"]!(
      { tool: "edit", sessionID: "s1", callID: "c1" },
      { args: { filePath: join(projectDir, "models/orders.sql") } }
    );

    expect(getImpactCheckState("s1", "orders")).toBe("verified");
  });

  it("re-injects after grace period expires without marker", async () => {
    const { hooks } = await getHooks({ messages: [] });
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    markImpactCheckInjected("s1", "orders");

    // Age the marker past grace period
    const markerPath = join(tmpdir(), "mc_prevent_ic_s1_orders");
    const data = JSON.parse(readFileSync(markerPath, "utf-8"));
    data.timestamp = data.timestamp - 200;
    writeFileSync(markerPath, JSON.stringify(data));

    await expect(
      hooks["tool.execute.before"]!(
        { tool: "edit", sessionID: "s1", callID: "c1" },
        { args: { filePath: join(projectDir, "models/orders.sql") } }
      )
    ).rejects.toThrow("impact assessment");
  });

  it("blocks macro files with macro-specific message", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {
      macros: { "helper.sql": "{% macro helper() %} SELECT 1 {% endmacro %}" },
    });

    await expect(
      hooks["tool.execute.before"]!(
        { tool: "edit", sessionID: "s1", callID: "c1" },
        { args: { filePath: join(projectDir, "macros/helper.sql") } }
      )
    ).rejects.toThrow("macro");
  });

  it("passes through new files (do not exist on disk)", async () => {
    const { hooks } = await getHooks();

    await hooks["tool.execute.before"]!(
      { tool: "edit", sessionID: "s1", callID: "c1" },
      { args: { filePath: join(tmpDir, "project/models/new_model.sql") } }
    );
  });

  it("tracks monitor gap marker from messages", async () => {
    const { hooks } = await getHooks({
      messages: [
        {
          parts: [
            {
              type: "text",
              text: "<!-- MC_MONITOR_GAP: orders -->\n<!-- MC_IMPACT_CHECK_COMPLETE: orders -->",
            },
          ],
        },
      ],
    });
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    markImpactCheckInjected("s1", "orders");

    await hooks["tool.execute.before"]!(
      { tool: "edit", sessionID: "s1", callID: "c1" },
      { args: { filePath: join(projectDir, "models/orders.sql") } }
    );

    expect(hasMonitorGap("s1", "orders")).toBe(true);
    expect(getImpactCheckState("s1", "orders")).toBe("verified");
  });

  it("verifies on voluntary assessment (null state, marker in messages)", async () => {
    const { hooks } = await getHooks({
      messages: [
        { parts: [{ type: "text", text: "<!-- MC_IMPACT_CHECK_COMPLETE: orders -->" }] },
      ],
    });
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    // No prior injection — voluntary assessment
    await hooks["tool.execute.before"]!(
      { tool: "edit", sessionID: "s1", callID: "c1" },
      { args: { filePath: join(projectDir, "models/orders.sql") } }
    );

    expect(getImpactCheckState("s1", "orders")).toBe("verified");
  });

  it("works with write and multiedit tools", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    for (const tool of ["write", "multiedit"]) {
      cleanCache();
      await expect(
        hooks["tool.execute.before"]!(
          { tool, sessionID: "s1", callID: "c1" },
          { args: { filePath: join(projectDir, "models/orders.sql") } }
        )
      ).rejects.toThrow("impact assessment");
    }
  });

  it("blocks apply_patch with dbt model in patchText", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    await expect(
      hooks["tool.execute.before"]!(
        { tool: "apply_patch", sessionID: "s1", callID: "c1" },
        {
          args: {
            patchText: patch(`*** Update File: ${join(projectDir, "models/orders.sql")}`, "@@", "-SELECT *", "+SELECT id"),
          },
        }
      )
    ).rejects.toThrow("impact assessment");
  });

  it("passes apply_patch with no dbt files in patchText", async () => {
    const { hooks } = await getHooks();

    await hooks["tool.execute.before"]!(
      { tool: "apply_patch", sessionID: "s1", callID: "c1" },
      {
        args: {
          patchText: patch("*** Update File: /project/readme.md", "@@", "-old", "+new"),
        },
      }
    );
  });
});

describe("PostEditTracking (tool.execute.after on edit tools)", () => {
  it("tracks dbt model edits", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    await hooks["tool.execute.after"]!(
      {
        tool: "edit",
        sessionID: "s1",
        callID: "c1",
        args: { filePath: join(projectDir, "models/orders.sql") },
      },
      { title: "", output: "", metadata: {} }
    );

    expect(getEditedTables("s1")).toEqual(["orders"]);
  });

  it("tracks dbt schema yml edits", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "schema.yml": "version: 2\nmodels:\n  - name: foo" },
    });

    await hooks["tool.execute.after"]!(
      {
        tool: "edit",
        sessionID: "s1",
        callID: "c1",
        args: { filePath: join(projectDir, "models/schema.yml") },
      },
      { title: "", output: "", metadata: {} }
    );

    expect(getEditedTables("s1")).toEqual(["schema"]);
  });

  it("ignores non-dbt files", async () => {
    const { hooks } = await getHooks();

    await hooks["tool.execute.after"]!(
      {
        tool: "edit",
        sessionID: "s1",
        callID: "c1",
        args: { filePath: "/project/readme.md" },
      },
      { title: "", output: "", metadata: {} }
    );

    expect(getEditedTables("s1")).toEqual([]);
  });

  it("deduplicates repeated edits", async () => {
    const { hooks } = await getHooks();
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
    });

    const input = {
      tool: "edit",
      sessionID: "s1",
      callID: "c1",
      args: { filePath: join(projectDir, "models/orders.sql") },
    };
    await hooks["tool.execute.after"]!(input, { title: "", output: "", metadata: {} });
    await hooks["tool.execute.after"]!(input, { title: "", output: "", metadata: {} });

    expect(getEditedTables("s1")).toEqual(["orders"]);
  });
});

describe("apply_patch moves and paths", () => {
  const MODEL = "SELECT * FROM {{ ref('raw') }}";
  const PLAIN = "SELECT 1";

  function verify(table: string) {
    markImpactCheckInjected("s1", table);
    markImpactCheckVerified("s1", table);
  }

  async function before(hooks: any, patchText: string) {
    await hooks["tool.execute.before"]!(
      { tool: "apply_patch", sessionID: "s1", callID: "c1" },
      { args: { patchText } }
    );
  }

  async function after(hooks: any, patchText: string, metadata: any = {}) {
    await hooks["tool.execute.after"]!(
      { tool: "apply_patch", sessionID: "s1", callID: "c1", args: { patchText } },
      { title: "", output: "", metadata }
    );
  }

  it("gates and tracks a model moved to a new name", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "orders.sql": MODEL } });
    const { hooks } = await getHooks({}, { directory: projectDir });
    const text = patch(
      "*** Update File: models/orders.sql",
      "*** Move to: models/orders_v2.sql",
      "@@",
      "-SELECT * FROM {{ ref('raw') }}",
      "+SELECT id FROM {{ ref('raw') }}"
    );

    await expect(before(hooks, text)).rejects.toThrow("for orders ");
    verify("orders");
    await before(hooks, text);

    writeFileSync(join(projectDir, "models/orders_v2.sql"), "SELECT id FROM {{ ref('raw') }}");
    unlinkSync(join(projectDir, "models/orders.sql"));
    await after(hooks, text);

    expect(getEditedTables("s1").sort()).toEqual(["orders", "orders_v2"]);
  });

  it("gates a file moved onto an existing model, and tracks the overwritten model", async () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": MODEL, "scratch.sql": PLAIN },
    });
    const { hooks } = await getHooks({}, { directory: projectDir });
    const text = patch(
      "*** Update File: models/scratch.sql",
      "*** Move to: models/orders.sql",
      "@@",
      "-SELECT 1",
      "+SELECT 2"
    );

    await expect(before(hooks, text)).rejects.toThrow("for orders ");
    verify("orders");
    await before(hooks, text);

    // The destination's new bytes no longer look like a dbt model.
    writeFileSync(join(projectDir, "models/orders.sql"), "SELECT 2");
    unlinkSync(join(projectDir, "models/scratch.sql"));
    await after(hooks, text);

    expect(getEditedTables("s1")).toEqual(["orders"]);
  });

  it("lets a move onto a verified model through", async () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": MODEL, "scratch.sql": PLAIN },
    });
    const { hooks } = await getHooks({}, { directory: projectDir });
    verify("orders");

    await before(
      hooks,
      patch("*** Update File: models/scratch.sql", "*** Move to: models/orders.sql", "@@", "-SELECT 1", "+SELECT 2")
    );
  });

  it("resolves relative paths against the session directory, not the process cwd", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "orders.sql": MODEL } });
    expect(process.cwd()).not.toBe(projectDir);
    const { hooks } = await getHooks({}, { directory: projectDir, worktree: tmpDir });

    await expect(
      before(hooks, patch("*** Update File: models/orders.sql", "@@", "-SELECT *", "+SELECT id"))
    ).rejects.toThrow("impact assessment");
  });

  it("ignores headers outside the Begin/End envelope", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "orders.sql": MODEL } });
    const { hooks } = await getHooks({}, { directory: projectDir });

    await before(
      hooks,
      [
        `*** Update File: ${join(projectDir, "models/orders.sql")}`,
        patch("*** Update File: notes.md", "@@", "-a", "+b"),
        `*** Update File: ${join(projectDir, "models/orders.sql")}`,
      ].join("\n")
    );
  });

  it("treats a Move line that doesn't follow its Update header as content", async () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": MODEL, "scratch.sql": PLAIN },
    });
    const { hooks } = await getHooks({}, { directory: projectDir });

    await before(
      hooks,
      patch("*** Update File: models/scratch.sql", "@@", "-SELECT 1", "+SELECT 2", "*** Move to: models/orders.sql")
    );
  });

  it("treats an empty Move as a plain update", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "scratch.sql": PLAIN } });
    const { hooks } = await getHooks({}, { directory: projectDir });
    const text = patch("*** Update File: models/scratch.sql", "*** Move to:   ", "@@", "-SELECT 1", "+SELECT 2");

    await before(hooks, text);
    await after(hooks, text);

    expect(getEditedTables("s1")).toEqual([]);
  });

  it("doesn't track a deleted .sql file that wasn't a model", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "scratch.sql": PLAIN } });
    const { hooks } = await getHooks({}, { directory: projectDir });
    const text = patch("*** Delete File: models/scratch.sql");

    await before(hooks, text);
    unlinkSync(join(projectDir, "models/scratch.sql"));
    await after(hooks, text);

    expect(getEditedTables("s1")).toEqual([]);
  });

  it("tracks a deleted model the gate saw", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "orders.sql": MODEL } });
    const { hooks } = await getHooks({}, { directory: projectDir });
    const text = patch("*** Delete File: models/orders.sql");
    verify("orders");

    await before(hooks, text);
    unlinkSync(join(projectDir, "models/orders.sql"));
    await after(hooks, text);

    expect(getEditedTables("s1")).toEqual(["orders"]);
  });

  it("doesn't track a .sql file outside the dbt folders that shares a gated table's name", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "orders.sql": MODEL } });
    require("fs").mkdirSync(join(projectDir, "scripts"), { recursive: true });
    writeFileSync(join(projectDir, "scripts/orders.sql"), PLAIN);
    const { hooks } = await getHooks({}, { directory: projectDir });
    verify("orders");

    await after(hooks, patch("*** Update File: scripts/orders.sql", "@@", "-SELECT 1", "+SELECT 2"));

    expect(getEditedTables("s1")).toEqual([]);
  });

  it("doesn't track a deleted non-model file whose name matches a gated model", async () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "orders.sql": MODEL, "legacy/orders.sql": PLAIN },
    });
    const { hooks } = await getHooks({}, { directory: projectDir });
    verify("orders");
    const text = patch("*** Delete File: models/legacy/orders.sql");

    await before(hooks, text);
    unlinkSync(join(projectDir, "models/legacy/orders.sql"));
    await after(hooks, text);

    expect(getEditedTables("s1")).toEqual([]);
  });

  it("doesn't track a new plain .sql file added under models", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "orders.sql": MODEL } });
    const { hooks } = await getHooks({}, { directory: projectDir });
    const text = patch("*** Add File: models/notes.sql", "+SELECT 1");

    await before(hooks, text);
    writeFileSync(join(projectDir, "models/notes.sql"), PLAIN);
    await after(hooks, text);

    expect(getEditedTables("s1")).toEqual([]);
  });

  it("forgets a call's models when the session goes idle", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "orders.sql": MODEL } });
    const { hooks } = await getHooks({}, { directory: projectDir });
    const text = patch("*** Delete File: models/orders.sql");
    verify("orders");

    await before(hooks, text);
    await hooks.event!({ event: { type: "session.idle", properties: { sessionID: "s1" } } as any });
    unlinkSync(join(projectDir, "models/orders.sql"));
    await after(hooks, text);

    expect(getEditedTables("s1")).toEqual([]);
  });

  it("tracks a deleted schema file", async () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "schema.yml": "version: 2\nmodels:\n  - name: foo" },
    });
    const { hooks } = await getHooks({}, { directory: projectDir });
    const text = patch("*** Delete File: models/schema.yml");

    unlinkSync(join(projectDir, "models/schema.yml"));
    await after(hooks, text);

    expect(getEditedTables("s1")).toEqual(["schema"]);
  });

  it("tracks the files the tool reports it changed", async () => {
    const { projectDir } = createDbtProject(tmpDir, { models: { "orders_v2.sql": MODEL } });
    const { hooks } = await getHooks({}, { directory: projectDir });

    await after(hooks, "", {
      files: [
        {
          filePath: join(projectDir, "models/orders.sql"),
          movePath: join(projectDir, "models/orders_v2.sql"),
          type: "move",
        },
      ],
    });

    expect(getEditedTables("s1")).toEqual(["orders_v2"]);
  });
});

describe("PreCommitGate (tool.execute.before on bash)", () => {
  it("passes through non-commit commands", async () => {
    const { hooks } = await getHooks();
    await hooks["tool.execute.before"]!(
      { tool: "bash", sessionID: "s1", callID: "c1" },
      { args: { command: "ls -la" } }
    );
  });

  it("passes through git commit with no staged dbt files", async () => {
    const { hooks } = await getHooks();
    // Bun.spawn runs `git diff --cached` in tmpDir which has no git repo,
    // so getStagedModelTables returns [] — no staged files → passes through
    await hooks["tool.execute.before"]!(
      { tool: "bash", sessionID: "s1", callID: "c1" },
      { args: { command: "git commit -m 'test'" } }
    );
  });

  it("passes through git commit when W4 not ran", async () => {
    const { hooks } = await getHooks();
    // Even if there were staged files, no W4 ran → passes through.
    // getStagedModelTables returns [] here (no git repo in tmpDir).
    await hooks["tool.execute.before"]!(
      { tool: "bash", sessionID: "s1", callID: "c1" },
      { args: { command: "git commit -m 'test'" } }
    );
  });
});

describe("TurnEnd (event handler on session.idle)", () => {
  it("does nothing with no edited tables", async () => {
    const promptFn = mock(async () => ({}));
    const { hooks } = await getHooks({ promptFn });

    await hooks.event!({ event: { type: "session.idle", properties: { sessionID: "s1" } } as any });

    expect(promptFn).not.toHaveBeenCalled();
  });

  it("does nothing when W4 not triggered", async () => {
    const promptFn = mock(async () => ({}));
    const { hooks } = await getHooks({ promptFn });

    addEditedTable("s1", "orders");

    await hooks.event!({ event: { type: "session.idle", properties: { sessionID: "s1" } } as any });

    expect(promptFn).not.toHaveBeenCalled();
  });

  it("sends validation prompt when W4 ran", async () => {
    const promptFn = mock(async () => ({}));
    const { hooks } = await getHooks({ promptFn });

    addEditedTable("s1", "orders");
    markImpactCheckInjected("s1", "orders");
    markImpactCheckVerified("s1", "orders");

    await hooks.event!({ event: { type: "session.idle", properties: { sessionID: "s1" } } as any });

    expect(promptFn).toHaveBeenCalledTimes(1);
    const callArgs = promptFn.mock.calls[0][0];
    expect(callArgs.path.id).toBe("s1");
    expect(callArgs.body.parts[0].text).toContain("orders");
    expect(callArgs.body.parts[0].text).toContain("validation");
  });

  it("silently merges when pending tables already exist", async () => {
    const promptFn = mock(async () => ({}));
    const { hooks } = await getHooks({ promptFn });

    // First prompt already happened
    addEditedTable("s1", "orders");
    moveToPendingValidation("s1");
    markImpactCheckInjected("s1", "orders");

    // New edits
    addEditedTable("s1", "customers");
    markImpactCheckInjected("s1", "customers");

    await hooks.event!({ event: { type: "session.idle", properties: { sessionID: "s1" } } as any });

    // Should NOT call prompt again
    expect(promptFn).not.toHaveBeenCalled();
    // But should have merged
    const pending = getPendingValidationTables("s1");
    expect(pending).toContain("orders");
    expect(pending).toContain("customers");
  });

  it("includes monitor gap tables in prompt", async () => {
    const promptFn = mock(async () => ({}));
    const { hooks } = await getHooks({ promptFn });

    addEditedTable("s1", "orders");
    markImpactCheckInjected("s1", "orders");
    markImpactCheckVerified("s1", "orders");
    markMonitorGap("s1", "orders");

    await hooks.event!({ event: { type: "session.idle", properties: { sessionID: "s1" } } as any });

    const callArgs = promptFn.mock.calls[0][0];
    expect(callArgs.body.parts[0].text).toContain("Monitor coverage");
    expect(callArgs.body.parts[0].text).toContain("orders");
  });

  it("ignores non-idle events", async () => {
    const promptFn = mock(async () => ({}));
    const { hooks } = await getHooks({ promptFn });

    addEditedTable("s1", "orders");
    markImpactCheckInjected("s1", "orders");

    await hooks.event!({ event: { type: "session.created", properties: { sessionID: "s1" } } as any });

    expect(promptFn).not.toHaveBeenCalled();
  });
});

describe("ErrorResilience", () => {
  it("swallows unexpected errors in pre-edit logic", async () => {
    const { hooks } = await getHooks({
      // SDK throws on messages call
      messages: undefined,
    });
    const badClient = createMockClient();
    badClient.session.messages = async () => {
      throw new Error("SDK crash");
    };

    // Re-initialize with broken client — but the hook should handle it
    const hooks2 = await McPrevent({
      client: badClient,
      directory: tmpDir,
      worktree: tmpDir,
      project: {} as any,
      serverUrl: new URL("http://localhost"),
      $: {} as any,
    });

    // Non-dbt file should still pass (error occurs only in dbt path)
    await hooks2["tool.execute.before"]!(
      { tool: "edit", sessionID: "s1", callID: "c1" },
      { args: { filePath: "/project/readme.md" } }
    );
  });

  it("swallows unexpected errors in post-edit logic", async () => {
    const { hooks } = await getHooks();

    // Null args should be handled gracefully
    await hooks["tool.execute.after"]!(
      { tool: "edit", sessionID: "s1", callID: "c1", args: null },
      { title: "", output: "", metadata: {} }
    );
  });

  it("swallows SDK prompt failure in event handler", async () => {
    const promptFn = mock(async () => {
      throw new Error("SDK crash");
    });
    const { hooks } = await getHooks({ promptFn });

    addEditedTable("s1", "orders");
    markImpactCheckInjected("s1", "orders");
    markImpactCheckVerified("s1", "orders");

    // Should not throw even though SDK fails
    await hooks.event!({ event: { type: "session.idle", properties: { sessionID: "s1" } } as any });
  });
});
