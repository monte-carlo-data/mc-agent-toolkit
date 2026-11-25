import { afterAll } from "bun:test";
import { mkdtempSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

// Private temp dir so the tests' cache cleanup never deletes another process's Prevent state.
const dir = mkdtempSync(join(tmpdir(), "mc-prevent-tests-"));
process.env.TMPDIR = dir;
afterAll(() => rmSync(dir, { recursive: true, force: true }));
