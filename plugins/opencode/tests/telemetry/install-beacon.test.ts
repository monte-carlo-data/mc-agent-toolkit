/**
 * Tests for the OpenCode install beacon (TypeScript equivalent of the bash
 * ensure-toolkit-ids.sh + install-beacon.sh). Mocks global fetch and points the
 * id directory at a temp XDG_CONFIG_HOME so no real network or home writes happen.
 */
import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import {
  readFileSync,
  writeFileSync,
  statSync,
  existsSync,
  mkdtempSync,
  rmSync,
} from "fs";
import { join } from "path";
import { tmpdir } from "os";
import {
  ensureToolkitIdsAndBeacon,
  buildInstallPayload,
  buildToolkitHeaders,
  ensureInstallId,
  idsDir,
} from "../../src/telemetry/install-beacon";

const V4_UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const PROD_URL = "https://mcp.getmontecarlo.com/mcp/toolkit/beacon";

let fetchCalls: Array<{ url: string; init: any }>;
let fetchImpl: (url: string, init: any) => Promise<any>;
const realFetch = globalThis.fetch;

let tmp: string;
let origXDG: string | undefined;

function installIdPath(): string {
  return join(idsDir(), "install_id");
}
function sessionIdPath(): string {
  return join(idsDir(), "toolkit_session_id");
}

beforeEach(() => {
  fetchCalls = [];
  fetchImpl = async (url, init) => {
    fetchCalls.push({ url, init });
    return { ok: true, status: 204 } as any;
  };
  globalThis.fetch = ((url: any, init: any) =>
    fetchImpl(String(url), init)) as any;

  tmp = mkdtempSync(join(tmpdir(), "mc-oc-tele-"));
  origXDG = process.env.XDG_CONFIG_HOME;
  process.env.XDG_CONFIG_HOME = tmp;
  delete process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED;
  delete process.env.MCD_TOOLKIT_BEACON_URL;
});

afterEach(() => {
  globalThis.fetch = realFetch;
  if (origXDG === undefined) delete process.env.XDG_CONFIG_HOME;
  else process.env.XDG_CONFIG_HOME = origXDG;
  rmSync(tmp, { recursive: true, force: true });
});

describe("buildInstallPayload", () => {
  it("carries no skill fields and matches the cross-harness key set", () => {
    const payload = buildInstallPayload(
      "11111111-1111-4111-8111-111111111111",
      "22222222-2222-4222-8222-222222222222"
    );
    expect("skill" in payload).toBe(false);
    expect("skill_args_present" in payload).toBe(false);
    // Same keys the bash install-beacon emits.
    expect(Object.keys(payload).sort()).toEqual([
      "event",
      "harness",
      "install_id",
      "session_id",
      "toolkit_version",
      "ts",
    ]);
    expect(payload.event).toBe("Toolkit Installed");
    expect(payload.harness).toBe("opencode");
  });

  it("resolves a real toolkit_version from package.json (not 'unknown')", () => {
    const expected = JSON.parse(
      readFileSync(join(import.meta.dir, "../../package.json"), "utf8")
    ).version;
    const payload = buildInstallPayload("a", "b");
    expect(payload.toolkit_version).toBe(expected);
    expect(payload.toolkit_version).not.toBe("unknown");
  });
});

describe("ensureToolkitIdsAndBeacon", () => {
  it("first run mints v4 ids and fires exactly one Toolkit Installed beacon", async () => {
    await ensureToolkitIdsAndBeacon();

    expect(fetchCalls.length).toBe(1);
    expect(fetchCalls[0].url).toBe(PROD_URL);
    expect(fetchCalls[0].init.method).toBe("POST");

    const installId = readFileSync(installIdPath(), "utf8").trim();
    const sessionId = readFileSync(sessionIdPath(), "utf8").trim();
    expect(installId).toMatch(V4_UUID_RE);
    expect(sessionId).toMatch(V4_UUID_RE);

    const body = JSON.parse(fetchCalls[0].init.body);
    expect(body.event).toBe("Toolkit Installed");
    expect(body.harness).toBe("opencode");
    expect(body.install_id).toBe(installId);
    expect(body.session_id).toBe(sessionId);
  });

  it("install_id is stable across runs; toolkit_session_id rotates", async () => {
    await ensureToolkitIdsAndBeacon();
    const install1 = readFileSync(installIdPath(), "utf8").trim();
    const session1 = readFileSync(sessionIdPath(), "utf8").trim();

    await ensureToolkitIdsAndBeacon();
    const install2 = readFileSync(installIdPath(), "utf8").trim();
    const session2 = readFileSync(sessionIdPath(), "utf8").trim();

    expect(install2).toBe(install1);
    expect(session2).not.toBe(session1);
  });

  it("second run does not fire the beacon (same version)", async () => {
    await ensureToolkitIdsAndBeacon();
    fetchCalls = [];
    await ensureToolkitIdsAndBeacon();
    expect(fetchCalls.length).toBe(0);
  });

  it("re-fires the beacon after a toolkit version change", async () => {
    await ensureToolkitIdsAndBeacon();
    // Simulate an older recorded version so the next run sees a version change.
    writeFileSync(join(idsDir(), "beacon_sent_version"), "0.0.0");
    fetchCalls = [];
    await ensureToolkitIdsAndBeacon();
    expect(fetchCalls.length).toBe(1);
    expect(JSON.parse(fetchCalls[0].init.body).event).toBe("Toolkit Installed");
  });

  it("opt-out env var suppresses the beacon and writes no id files", async () => {
    process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED = "1";
    await ensureToolkitIdsAndBeacon();
    expect(fetchCalls.length).toBe(0);
    expect(existsSync(installIdPath())).toBe(false);
  });

  it("is fail-open when the POST rejects (does not throw)", async () => {
    fetchImpl = async () => {
      throw new Error("network down");
    };
    await expect(ensureToolkitIdsAndBeacon()).resolves.toBeUndefined();
    // ids are still written even though the beacon failed
    expect(existsSync(installIdPath())).toBe(true);
    expect(existsSync(sessionIdPath())).toBe(true);
  });

  it("writes id files with mode 0600", async () => {
    await ensureToolkitIdsAndBeacon();
    expect(statSync(installIdPath()).mode & 0o777).toBe(0o600);
    expect(statSync(sessionIdPath()).mode & 0o777).toBe(0o600);
  });

  it("ensureInstallId creates a stable v4 id (mode 0600), idempotent across calls", () => {
    const first = ensureInstallId();
    expect(first).toMatch(V4_UUID_RE);
    expect(statSync(installIdPath()).mode & 0o777).toBe(0o600);
    expect(ensureInstallId()).toBe(first); // reads existing, doesn't regenerate
  });

  it("honors MCD_TOOLKIT_BEACON_URL override", async () => {
    process.env.MCD_TOOLKIT_BEACON_URL =
      "https://mcp.dev.getmontecarlo.com/mcp/toolkit/beacon";
    await ensureToolkitIdsAndBeacon();
    expect(fetchCalls[0].url).toBe(
      "https://mcp.dev.getmontecarlo.com/mcp/toolkit/beacon"
    );
  });
});

describe("buildToolkitHeaders (config-hook injection)", () => {
  it("returns install_id (matching ensureInstallId) + version, no session_id", () => {
    const headers = buildToolkitHeaders();
    expect(headers["x-mcd-toolkit-install-id"]).toMatch(V4_UUID_RE);
    expect(headers["x-mcd-toolkit-install-id"]).toBe(ensureInstallId());
    const expected = JSON.parse(
      readFileSync(join(import.meta.dir, "../../package.json"), "utf8")
    ).version;
    expect(headers["x-mcd-toolkit-version"]).toBe(expected);
    expect("x-mcd-toolkit-session-id" in headers).toBe(false);
  });

  it("the install_id it emits matches the install beacon's install_id (the join key)", async () => {
    await ensureToolkitIdsAndBeacon();
    const beaconId = JSON.parse(fetchCalls[0].init.body).install_id;
    expect(buildToolkitHeaders()["x-mcd-toolkit-install-id"]).toBe(beaconId);
  });

  it("opt-out returns no headers (and never throws)", () => {
    process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED = "1";
    expect(buildToolkitHeaders()).toEqual({});
  });

  it("is fail-open: a fresh machine with no id files still returns headers, never throws", () => {
    // idsDir points at the temp XDG home; nothing exists yet.
    expect(existsSync(installIdPath())).toBe(false);
    const headers = buildToolkitHeaders();
    expect(headers["x-mcd-toolkit-install-id"]).toMatch(V4_UUID_RE); // self-seeds
  });
});
