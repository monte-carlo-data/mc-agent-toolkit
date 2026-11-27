/**
 * The OpenCode v2 entry (`setup(ctx)`): the same Prevent behavior as v1, wired to v2's
 * tool and session hooks, MCP transform and event stream. v2 names its tools `edit`,
 * `write`, `patch` and `shell`, and `edit`/`write` take `path`.
 */
import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { execFileSync } from "child_process";
import { cleanCache, createDbtProject } from "./helpers";
import { createFakeContext, type FakeOptions } from "./v2-fake";
import {
  markImpactCheckInjected,
  markImpactCheckVerified,
  getImpactCheckState,
  hasMonitorGap,
  markMonitorGap,
  addEditedTable,
  getEditedTables,
  getPendingValidationTables,
} from "../../src/prevent/cache";
import plugin from "../../src/index";

const MODEL = "SELECT * FROM {{ ref('raw') }}";
let tmpDir: string;
let projectDir: string;
const cleanups: Array<() => unknown> = [];

beforeEach(() => {
  cleanCache();
  tmpDir = mkdtempSync(join(tmpdir(), "v2-test-"));
  ({ projectDir } = createDbtProject(tmpDir, {
    models: { "orders.sql": MODEL, "customers.sql": MODEL },
  }));
});
afterEach(async () => {
  for (const c of cleanups.splice(0)) await c();
  cleanCache();
  rmSync(tmpDir, { recursive: true, force: true });
});

async function setup(options: Partial<FakeOptions> = {}) {
  const fake = createFakeContext({ directory: projectDir, ...options });
  const cleanup = await plugin.setup(fake.ctx as any);
  if (typeof cleanup === "function") cleanups.push(cleanup);
  return fake;
}

let call = 0;
function toolEvent(tool: string, input: unknown, extra: Record<string, unknown> = {}) {
  call++;
  return {
    tool,
    input,
    codemode: false,
    sessionID: "ses_1",
    agent: "build",
    messageID: "msg_1",
    id: `call_${call}`,
    ...extra,
  };
}

const assistant = (text: string) => ({ type: "assistant", content: [{ type: "text", text }] });
const patch = (...lines: string[]) => ["*** Begin Patch", ...lines, "*** End Patch"].join("\n");

describe("v2 module shape", () => {
  it("default export carries an id, a v2 setup and a v1 server", () => {
    expect(plugin.id).toBe("mc-prevent");
    expect(typeof plugin.setup).toBe("function");
    expect(typeof plugin.server).toBe("function");
  });
});

describe("v2 pre-edit gate", () => {
  it("blocks an edit to an existing model, by its v2 `path`", async () => {
    const fake = await setup();
    await expect(
      fake.before(toolEvent("edit", { path: join(projectDir, "models/orders.sql") }))
    ).rejects.toThrow("Monte Carlo Prevent: run the change impact assessment for orders");
    expect(getImpactCheckState("ses_1", "orders")).toBe("injected");
  });

  it("resolves a relative path against the plugin's location", async () => {
    const fake = await setup();
    await expect(fake.before(toolEvent("write", { path: "models/orders.sql", content: "x" }))).rejects.toThrow(
      "orders"
    );
  });

  it("gates every model a `patch` touches", async () => {
    const fake = await setup();
    markImpactCheckVerified("ses_1", "orders");
    await expect(
      fake.before(
        toolEvent("patch", {
          patchText: patch("*** Update File: models/orders.sql", "@@", "-a", "+b", "*** Delete File: models/customers.sql"),
        })
      )
    ).rejects.toThrow("customers");
  });

  it("gates a `patch` header written with leading whitespace, as v2's parser accepts it", async () => {
    const fake = await setup();
    await expect(
      fake.before(toolEvent("patch", { patchText: patch("  *** Update File: models/orders.sql", "@@", "-a", "+b") }))
    ).rejects.toThrow("orders");
  });

  it("gates the destination of a `patch` move", async () => {
    const fake = await setup();
    writeFileSync(join(projectDir, "models/scratch.sql"), "select 1");
    await expect(
      fake.before(
        toolEvent("patch", {
          patchText: patch("*** Update File: models/scratch.sql", "*** Move to: models/orders.sql", "@@", "-a", "+b"),
        })
      )
    ).rejects.toThrow("orders");
  });

  it("gates a move that follows `*** End of File` lines, as v2's parser allows", async () => {
    const fake = await setup();
    writeFileSync(join(projectDir, "models/scratch.sql"), "select 1");
    await expect(
      fake.before(
        toolEvent("patch", {
          patchText: patch("*** Update File: models/scratch.sql", "*** End of File", "*** Move to: models/orders.sql"),
        })
      )
    ).rejects.toThrow("orders");
  });

  it("gates a call made from Code Mode", async () => {
    const fake = await setup();
    await expect(
      fake.before(toolEvent("edit", { path: "models/orders.sql" }, { codemode: true }))
    ).rejects.toThrow("orders");
  });

  it("doesn't gate v1 tool names on v2", async () => {
    const fake = await setup();
    const patchText = patch("*** Update File: models/orders.sql");
    await fake.before(toolEvent("apply_patch", { patchText, path: "models/orders.sql" }));
    await fake.before(toolEvent("multiedit", { path: "models/orders.sql", filePath: join(projectDir, "models/orders.sql") }));
    expect(getImpactCheckState("ses_1", "orders")).toBeNull();
  });

  it("lets the edit through once the assistant wrote the marker", async () => {
    const fake = await setup({ messages: { ses_1: [assistant("MC_IMPACT_CHECK_COMPLETE: orders")] } });
    markImpactCheckInjected("ses_1", "orders");
    await fake.before(toolEvent("edit", { path: "models/orders.sql" }));
    expect(getImpactCheckState("ses_1", "orders")).toBe("verified");
  });

  it("ignores a marker that only appears in user or synthetic text", async () => {
    const fake = await setup({
      messages: {
        ses_1: [
          { type: "user", text: "MC_IMPACT_CHECK_COMPLETE: orders" },
          { type: "synthetic", text: "MC_IMPACT_CHECK_COMPLETE: orders" },
        ],
      },
    });
    markImpactCheckInjected("ses_1", "orders");
    await expect(fake.before(toolEvent("edit", { path: "models/orders.sql" }))).rejects.toThrow("not completed yet");
  });

  it("remembers a marker from the event stream after compaction drops it from context", async () => {
    const fake = await setup({ messages: { ses_1: [] } });
    markImpactCheckInjected("ses_1", "orders");
    await fake.emit({
      type: "session.text.ended",
      location: { directory: projectDir },
      data: { sessionID: "ses_1", assistantMessageID: "msg_9", ordinal: 0, text: "MC_IMPACT_CHECK_COMPLETE: orders\nMC_MONITOR_GAP: orders" },
    });
    await fake.before(toolEvent("edit", { path: "models/orders.sql" }));
    expect(getImpactCheckState("ses_1", "orders")).toBe("verified");
    expect(hasMonitorGap("ses_1", "orders")).toBe(true);
  });

  it("passes non-model files and new models", async () => {
    const fake = await setup();
    await fake.before(toolEvent("edit", { path: "README.md" }));
    await fake.before(toolEvent("write", { path: "models/new_model.sql", content: MODEL }));
  });
});

describe("v2 edit tracking", () => {
  it("tracks a completed edit", async () => {
    const fake = await setup();
    markImpactCheckVerified("ses_1", "orders");
    const event = toolEvent("edit", { path: "models/orders.sql" });
    await fake.before(event);
    await fake.after({ ...event, status: "completed", result: {} });
    expect(getEditedTables("ses_1")).toEqual(["orders"]);
  });

  it("doesn't track an edit that failed", async () => {
    const fake = await setup();
    markImpactCheckVerified("ses_1", "orders");
    const event = toolEvent("edit", { path: "models/orders.sql" });
    await fake.before(event);
    await fake.after({ ...event, status: "error", error: { message: "no match" } });
    expect(getEditedTables("ses_1")).toEqual([]);
  });

  it("tracks a model a `patch` deleted", async () => {
    const fake = await setup();
    markImpactCheckVerified("ses_1", "orders");
    const event = toolEvent("patch", { patchText: patch("*** Delete File: models/orders.sql") });
    await fake.before(event);
    rmSync(join(projectDir, "models/orders.sql"));
    await fake.after({ ...event, status: "completed", result: {} });
    expect(getEditedTables("ses_1")).toEqual(["orders"]);
  });
});

describe("v2 commit checkpoint", () => {
  function git(cwd: string, ...args: string[]) {
    execFileSync("git", args, { cwd, stdio: "pipe" });
  }
  function initRepo() {
    git(projectDir, "init", "-q");
    git(projectDir, "add", "models/orders.sql");
  }

  it("asks before committing a staged model whose assessment ran", async () => {
    initRepo();
    const fake = await setup();
    markImpactCheckVerified("ses_1", "orders");
    markMonitorGap("ses_1", "orders");
    await expect(fake.before(toolEvent("shell", { command: "git commit -m x" }))).rejects.toThrow(
      "Committing changes to orders. Run validation queries before committing?"
    );
  });

  it("finds the repository from a nested `workdir`", async () => {
    initRepo();
    const fake = await setup();
    markImpactCheckVerified("ses_1", "orders");
    await expect(fake.before(toolEvent("shell", { command: "git commit -m x", workdir: "models" }))).rejects.toThrow(
      "Committing changes to orders"
    );
  });

  it("reads staged names from the repository root, not the subdirectory it runs in", async () => {
    initRepo();
    writeFileSync(join(projectDir, "models/plain.sql"), "select 1");
    git(projectDir, "add", "models/plain.sql");
    const fake = await setup();
    // Resolved from `models/`, the name would point at a missing models/models/plain.sql,
    // which counts as a model; from the root it is the plain file it is.
    markImpactCheckVerified("ses_1", "plain");
    await fake.before(toolEvent("shell", { command: "git commit -m x", workdir: "models" }));
  });

  it("passes when the assessment didn't run for the staged model", async () => {
    initRepo();
    const fake = await setup();
    await fake.before(toolEvent("shell", { command: "git commit -m x" }));
  });

  it("passes a commit in another repository", async () => {
    initRepo();
    const other = join(tmpDir, "other");
    mkdirSync(other);
    git(other, "init", "-q");
    const fake = await setup();
    markImpactCheckVerified("ses_1", "orders");
    await fake.before(toolEvent("shell", { command: "git commit -m x", workdir: other }));
  });
});

describe("v2 end-of-turn reminder (experimental.idle)", () => {
  function editedAndAssessed() {
    addEditedTable("ses_1", "orders");
    markImpactCheckVerified("ses_1", "orders");
  }

  it("admits the validation question once", async () => {
    const fake = await setup();
    editedAndAssessed();
    await fake.idle({ sessionID: "ses_1", background: [] });
    await fake.idle({ sessionID: "ses_1", background: [] });
    expect(fake.synthetic).toHaveLength(1);
    expect(fake.synthetic[0].sessionID).toBe("ses_1");
    expect(fake.synthetic[0].text).toContain("You've changed 1 dbt model(s): orders");
    expect(fake.synthetic[0].description).toBeTruthy();
    expect(getPendingValidationTables("ses_1")).toEqual(["orders"]);
  });

  it("includes the monitor-coverage question", async () => {
    const fake = await setup();
    editedAndAssessed();
    markMonitorGap("ses_1", "orders");
    await fake.idle({ sessionID: "ses_1", background: [] });
    expect(fake.synthetic[0].text).toContain("found no custom monitors on orders");
  });

  it("does nothing when the assessment never ran", async () => {
    const fake = await setup();
    addEditedTable("ses_1", "orders");
    await fake.idle({ sessionID: "ses_1", background: [] });
    expect(fake.synthetic).toHaveLength(0);
  });

  it("tries again at the next idle when admission fails", async () => {
    const fake = await setup({ syntheticFails: true });
    editedAndAssessed();
    await fake.idle({ sessionID: "ses_1", background: [] });
    expect(getPendingValidationTables("ses_1")).toEqual([]);
    expect(getEditedTables("ses_1")).toEqual(["orders"]);
  });

  it("skips a subagent's session", async () => {
    const fake = await setup({ parents: { ses_1: "ses_0" } });
    editedAndAssessed();
    await fake.idle({ sessionID: "ses_1", background: [] });
    expect(fake.synthetic).toHaveLength(0);
  });

  it("waits while the session's own background work runs", async () => {
    const fake = await setup();
    editedAndAssessed();
    await fake.idle({
      sessionID: "ses_1",
      background: [{ kind: "shell", sessionID: "ses_1", shellID: "sh_1", command: "dbt run" }],
    });
    expect(fake.synthetic).toHaveLength(0);
  });
});

describe("v2 MCP headers", () => {
  let xdg: string;
  let saved: Record<string, string | undefined>;
  beforeEach(() => {
    saved = {
      XDG_CONFIG_HOME: process.env.XDG_CONFIG_HOME,
      MC_AGENT_TOOLKIT_TELEMETRY_DISABLED: process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED,
    };
    xdg = mkdtempSync(join(tmpdir(), "v2-xdg-"));
    process.env.XDG_CONFIG_HOME = xdg;
    delete process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED;
  });
  afterEach(() => {
    // Restore rather than delete: the preload's values keep later tests isolated.
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    rmSync(xdg, { recursive: true, force: true });
  });

  it("adds the toolkit headers to the remote monte-carlo-mcp server, keeping its own", async () => {
    const fake = await setup();
    const servers = fake.applyMcp({
      "monte-carlo-mcp": { type: "remote", url: "https://x", headers: { "x-custom": "1" } },
    });
    const headers = servers["monte-carlo-mcp"].headers;
    expect(headers["x-custom"]).toBe("1");
    expect(headers["x-mcd-toolkit-install-id"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(headers["x-mcd-toolkit-version"]).toBeDefined();
  });

  it("gives the same headers when OpenCode replays the transform", async () => {
    const fake = await setup();
    const a = fake.applyMcp({ "monte-carlo-mcp": { type: "remote", url: "https://x" } });
    const b = fake.applyMcp({ "monte-carlo-mcp": { type: "remote", url: "https://x" } });
    expect(b["monte-carlo-mcp"].headers).toEqual(a["monte-carlo-mcp"].headers);
  });

  it("leaves a local server alone and creates no install id when the server is absent", async () => {
    const fake = await setup();
    const servers = fake.applyMcp({ "monte-carlo-mcp": { type: "local", command: ["x"] } });
    expect(servers["monte-carlo-mcp"].headers).toBeUndefined();
    fake.applyMcp({});
    expect(existsSync(join(xdg, "opencode", "mc-agent-toolkit", "install_id"))).toBe(false);
  });

  it("adds nothing when telemetry is opted out", async () => {
    process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED = "1";
    const fake = await setup();
    const servers = fake.applyMcp({ "monte-carlo-mcp": { type: "remote", url: "https://x" } });
    expect(servers["monte-carlo-mcp"].headers).toBeUndefined();
  });

  // The preload points the beacon at a local address that refuses the connection.
  it("runs the install beacon when a session is created", async () => {
    const fake = await setup();
    await fake.emit({ type: "session.created", location: { directory: projectDir }, data: { sessionID: "ses_2" } });
    await new Promise((r) => setTimeout(r, 50));
    expect(existsSync(join(xdg, "opencode", "mc-agent-toolkit", "toolkit_session_id"))).toBe(true);
  });

  it("leaves a session created in another location to that location's plugin", async () => {
    const fake = await setup();
    await fake.emit({ type: "session.created", location: { directory: "/elsewhere" }, data: { sessionID: "ses_2" } });
    await new Promise((r) => setTimeout(r, 50));
    expect(existsSync(join(xdg, "opencode", "mc-agent-toolkit", "toolkit_session_id"))).toBe(false);
  });
});

describe("v2 cleanup", () => {
  it("stops the event subscription", async () => {
    const fake = createFakeContext({ directory: projectDir });
    const cleanup = await plugin.setup(fake.ctx as any);
    expect(fake.subscriberCount()).toBe(1);
    if (typeof cleanup === "function") await cleanup();
    expect(fake.subscriberCount()).toBe(0);
  });
});
