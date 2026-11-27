import { afterAll } from "bun:test";
import { mkdtempSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

// Private temp dir so the tests' cache cleanup never deletes another process's Prevent state.
const dir = mkdtempSync(join(tmpdir(), "mc-prevent-tests-"));
process.env.TMPDIR = dir;
// Hook tests that emit `session.created` run the real install beacon: keep its ids out
// of the engineer's OpenCode config and its POST off the production endpoint.
// Port 9 (discard) refuses the connection at once.
process.env.XDG_CONFIG_HOME = join(dir, "config");
process.env.MCD_TOOLKIT_BEACON_URL = "http://127.0.0.1:9/beacon";
afterAll(() => rmSync(dir, { recursive: true, force: true }));
