/**
 * Monte Carlo Prevent plugin for OpenCode, for both major versions from one module.
 *
 * OpenCode v1 (1.18.29 and newer) reads the default export's `server`; OpenCode v2
 * reads its `setup`. Each version ignores the other's key. See ./v1.ts and ./v2.ts;
 * the shared decisions are in ./core.ts.
 */
import { McPrevent } from "./v1.ts";
import { setup } from "./v2.ts";

export { McPrevent } from "./v1.ts";
export { MAX_CALL_RECORDS } from "./core.ts";

export default {
  id: "mc-prevent",
  setup,
  server: McPrevent,
};
