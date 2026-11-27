/**
 * The test preload (tests/setup.ts) keeps every test away from the engineer's real
 * OpenCode config and from the production beacon: a hook test that emits
 * `session.created` runs the real install beacon.
 */
import { describe, it, expect } from "bun:test";
import { homedir, tmpdir } from "os";
import { idsDir } from "../src/telemetry/install-beacon";

describe("test isolation", () => {
  it("keeps toolkit ids out of the real OpenCode config", () => {
    expect(idsDir().startsWith(homedir())).toBe(false);
    expect(idsDir().startsWith(tmpdir())).toBe(true);
  });

  it("sends beacons to a local address, never production", () => {
    const url = new URL(process.env.MCD_TOOLKIT_BEACON_URL ?? "https://mcp.getmontecarlo.com");
    expect(url.hostname).toBe("127.0.0.1");
  });
});
