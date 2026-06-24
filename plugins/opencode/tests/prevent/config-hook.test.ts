/**
 * Tests for the McPrevent `config` hook — the path that actually injects toolkit
 * telemetry headers onto OpenCode's monte-carlo-mcp server at config load.
 * `buildToolkitHeaders()` is unit-tested in telemetry/install-beacon.test.ts; this
 * covers the hook's own wiring: the remote-only guard, header merge, opt-out, and
 * the absent-server no-op. XDG_CONFIG_HOME points at a temp dir so the id self-seeds.
 */
import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import { mkdtempSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { McPrevent } from "../../src/prevent/index";

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

let tmp: string;
let origXDG: string | undefined;

beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), "mc-oc-cfg-"));
  origXDG = process.env.XDG_CONFIG_HOME;
  process.env.XDG_CONFIG_HOME = tmp;
  delete process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED;
});

afterEach(() => {
  if (origXDG === undefined) delete process.env.XDG_CONFIG_HOME;
  else process.env.XDG_CONFIG_HOME = origXDG;
  rmSync(tmp, { recursive: true, force: true });
});

async function getConfigHook() {
  const hooks = await McPrevent({
    client: {} as any,
    directory: tmp,
    worktree: tmp,
    project: {} as any,
    serverUrl: new URL("http://localhost"),
    $: {} as any,
  });
  return hooks.config!;
}

describe("config hook — MCP header injection", () => {
  it("injects install_id + version onto the remote monte-carlo-mcp server", async () => {
    const config: any = {
      mcp: { "monte-carlo-mcp": { type: "remote", url: "https://x/mcp/toolkit" } },
    };
    await (await getConfigHook())(config);
    const h = config.mcp["monte-carlo-mcp"].headers;
    expect(h["x-mcd-toolkit-install-id"]).toMatch(V4);
    expect(h["x-mcd-toolkit-version"]).toBeDefined();
    expect("x-mcd-toolkit-session-id" in h).toBe(false); // omitted by design
  });

  it("is a no-op for a non-remote (stdio) server", async () => {
    const config: any = {
      mcp: { "monte-carlo-mcp": { type: "local", command: "x" } },
    };
    await (await getConfigHook())(config);
    expect(config.mcp["monte-carlo-mcp"].headers).toBeUndefined();
  });

  it("injects no headers when telemetry is opted out", async () => {
    process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED = "1";
    const config: any = {
      mcp: { "monte-carlo-mcp": { type: "remote", url: "https://x" } },
    };
    await (await getConfigHook())(config);
    expect(config.mcp["monte-carlo-mcp"].headers).toBeUndefined();
  });

  it("does not throw when monte-carlo-mcp is absent", async () => {
    const config: any = { mcp: {} };
    await expect((await getConfigHook())(config)).resolves.toBeUndefined();
  });
});
