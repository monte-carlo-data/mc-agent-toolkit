/**
 * One-shot "Toolkit Installed" telemetry beacon for OpenCode.
 *
 * OpenCode has no bash/Python hook layer, so this is the TypeScript equivalent of
 * the other editors' ensure-toolkit-ids.sh + shared install-beacon.sh: it persists
 * a per-machine install_id plus a rotating toolkit_session_id, and fires a "Toolkit
 * Installed" beacon once per (machine+editor, toolkit version) — on first install
 * and on every version change — deduped by a beacon_sent_version marker. The payload
 * shape matches the bash beacon exactly (a cross-harness parity test guards this).
 *
 * Fail-open and non-blocking: every path swallows errors, the POST is detached with
 * a hard timeout, and an empty id is never sent (the sink requires valid v4 UUIDs).
 */
import { mkdirSync, readFileSync, writeFileSync, chmodSync } from "fs";
import { homedir } from "os";
import { join } from "path";
import { randomUUID } from "node:crypto";

const HARNESS = "opencode";
const BEACON_TIMEOUT_MS = 2000;

/** Beacon endpoint; defaults to prod, overridable to dev for verification work. */
function beaconUrl(): string {
  return (
    process.env.MCD_TOOLKIT_BEACON_URL ||
    "https://mcp.getmontecarlo.com/mcp/toolkit/beacon"
  );
}

/**
 * Per-editor id directory under OpenCode's config home (XDG-aware), NOT ~/.claude:
 * an OpenCode install is a distinct installation from one in another editor, so each
 * keeps its own install/session identity.
 */
export function idsDir(): string {
  const base = process.env.XDG_CONFIG_HOME || join(homedir(), ".config");
  return join(base, "opencode", "mc-agent-toolkit");
}

function readId(path: string): string {
  try {
    return readFileSync(path, "utf8").trim();
  } catch {
    return "";
  }
}

/** Resolve the toolkit version from the plugin's package.json (../../ from here). */
function toolkitVersion(): string {
  try {
    const pkg = JSON.parse(
      readFileSync(join(import.meta.dir, "..", "..", "package.json"), "utf8")
    );
    return typeof pkg.version === "string" && pkg.version ? pkg.version : "unknown";
  } catch {
    return "unknown";
  }
}

/**
 * Build the "Toolkit Installed" payload. Same key set as the bash install-beacon:
 * event, install_id, session_id, toolkit_version, harness, ts. No skill fields.
 */
export function buildInstallPayload(installId: string, sessionId: string) {
  return {
    event: "Toolkit Installed",
    install_id: installId,
    session_id: sessionId,
    toolkit_version: toolkitVersion(),
    harness: HARNESS,
    ts: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
  };
}

/** POST the beacon with a hard timeout. Never throws. */
async function postInstallBeacon(installId: string, sessionId: string): Promise<void> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), BEACON_TIMEOUT_MS);
  try {
    await fetch(beaconUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildInstallPayload(installId, sessionId)),
      signal: controller.signal,
    });
  } catch {
    // Swallow — telemetry must never surface an error to the session.
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Ensure a stable install_id and a fresh toolkit_session_id, and fire the install
 * beacon once per (machine+editor, toolkit version) — first install and every
 * version change, deduped by a beacon_sent_version marker. Awaitable for tests;
 * callers fire it detached so it never blocks session start.
 */
export async function ensureToolkitIdsAndBeacon(): Promise<void> {
  if (process.env.MC_AGENT_TOOLKIT_TELEMETRY_DISABLED === "1") return;
  try {
    const dir = idsDir();
    mkdirSync(dir, { recursive: true });
    try {
      chmodSync(dir, 0o700);
    } catch {
      // best-effort
    }

    const installPath = join(dir, "install_id");
    const sessionPath = join(dir, "toolkit_session_id");

    let installId = readId(installPath);
    if (!installId) {
      installId = randomUUID();
      writeFileSync(installPath, installId, { mode: 0o600 });
      try {
        chmodSync(installPath, 0o600);
      } catch {
        // best-effort
      }
    }

    // Rotate the session id every session.
    const sessionId = randomUUID();
    writeFileSync(sessionPath, sessionId, { mode: 0o600 });
    try {
      chmodSync(sessionPath, 0o600);
    } catch {
      // best-effort
    }

    if (!installId || !sessionId) return; // never send empty/null ids

    // Dedup: fire once per (install, version). The marker records the version we
    // last beaconed for; re-fire only when it differs from the current version
    // (first run, or any upgrade/downgrade). The sink also dedups on
    // (install_id, toolkit_version) as a backstop if the marker is lost.
    const version = toolkitVersion();
    const sentPath = join(dir, "beacon_sent_version");
    if (readId(sentPath) === version) return;
    writeFileSync(sentPath, version, { mode: 0o600 });
    try {
      chmodSync(sentPath, 0o600);
    } catch {
      // best-effort
    }

    await postInstallBeacon(installId, sessionId);
  } catch {
    // Fail-open — telemetry must never break a session.
  }
}
