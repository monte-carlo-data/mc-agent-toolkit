/**
 * Node smoke test: OpenCode v2 can run plugins under Node (its `opencode2-node`
 * build), which loads TypeScript sources natively. That needs explicit `.ts` import
 * extensions and no Bun-only APIs. Run with `node tests/node-smoke.ts` (Node 22.18+,
 * which strips types by default); exits non-zero on the first failure.
 */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createDbtProject } from "./prevent/helpers.ts";
import { createFakeContext } from "./prevent/v2-fake.ts";

const sandbox = mkdtempSync(join(tmpdir(), "mc-node-smoke-"));
process.env.TMPDIR = sandbox;
process.env.XDG_CONFIG_HOME = join(sandbox, "config");
delete process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED;

try {
  const { default: plugin } = await import("../src/index.ts");
  assert.equal(plugin.id, "mc-prevent");
  assert.equal(typeof plugin.setup, "function");
  assert.equal(typeof plugin.server, "function");

  const { projectDir } = createDbtProject(sandbox, {
    models: { "orders.sql": "SELECT * FROM {{ ref('raw') }}" },
  });
  const fake = createFakeContext({ directory: projectDir });
  const cleanup = await plugin.setup(fake.ctx as any);

  const event = (tool: string, input: unknown, id: string) => ({
    tool,
    input,
    codemode: false,
    sessionID: "ses_smoke",
    agent: "build",
    messageID: "msg_smoke",
    id,
  });

  // Gate: blocks the first edit of an existing model.
  await assert.rejects(
    async () => fake.before(event("edit", { path: "models/orders.sql" }, "c1")),
    /Monte Carlo Prevent: run the change impact assessment for orders/
  );

  // Commit checkpoint: runs git through node:child_process.
  const { markImpactCheckVerified } = await import("../src/prevent/cache.ts");
  markImpactCheckVerified("ses_smoke", "orders");
  execFileSync("git", ["init", "-q"], { cwd: projectDir });
  execFileSync("git", ["add", "models/orders.sql"], { cwd: projectDir });
  await assert.rejects(
    async () => fake.before(event("shell", { command: "git commit -m x" }, "c2")),
    /Committing changes to orders/
  );

  // MCP headers: the version comes from package.json via import.meta.url.
  const servers = fake.applyMcp({ "monte-carlo-mcp": { type: "remote", url: "https://x" } });
  assert.match(servers["monte-carlo-mcp"].headers["x-mcd-toolkit-version"], /^\d+\.\d+\.\d+/);

  if (typeof cleanup === "function") await cleanup();
  console.log("node smoke: ok");
} finally {
  rmSync(sandbox, { recursive: true, force: true });
}
