/**
 * Cache unit tests — port of plugins/claude-code/prevent/tests/test_cache.py
 */
import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import { statSync, writeFileSync, readFileSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { mkdtempSync } from "fs";
import { cleanCache, createDbtProject } from "./helpers";
import {
  getImpactCheckState,
  markImpactCheckInjected,
  markImpactCheckVerified,
  getImpactCheckAgeSeconds,
  hasMonitorGap,
  markMonitorGap,
  getEditedTables,
  addEditedTable,
  clearEditedTables,
  moveToPendingValidation,
  getPendingValidationTables,
  getDbtPaths,
} from "../../src/prevent/cache";

beforeEach(() => cleanCache());
afterEach(() => cleanCache());

describe("ImpactCheckState", () => {
  it("returns null for unknown session/table", () => {
    expect(getImpactCheckState("test_session", "my_table")).toBeNull();
  });

  it("marks injected state", () => {
    markImpactCheckInjected("test_session", "my_table");
    expect(getImpactCheckState("test_session", "my_table")).toBe("injected");
  });

  it("transitions from injected to verified", () => {
    markImpactCheckInjected("test_session", "my_table");
    markImpactCheckVerified("test_session", "my_table");
    expect(getImpactCheckState("test_session", "my_table")).toBe("verified");
  });

  it("tracks age correctly", () => {
    markImpactCheckInjected("test_session", "my_table");
    const age = getImpactCheckAgeSeconds("test_session", "my_table");
    expect(age).toBeGreaterThanOrEqual(0);
    expect(age).toBeLessThan(2);
  });

  it("preserves injection timestamp on verification", () => {
    markImpactCheckInjected("test_session", "my_table");
    const path = join(tmpdir(), "mc_prevent_ic_test_session_my_table");
    const before = JSON.parse(readFileSync(path, "utf-8"));

    markImpactCheckVerified("test_session", "my_table");
    const after = JSON.parse(readFileSync(path, "utf-8"));
    expect(after.timestamp).toBe(before.timestamp);
  });

  it("maintains independent state per table", () => {
    markImpactCheckInjected("test_session", "table_a");
    markImpactCheckVerified("test_session", "table_a");
    expect(getImpactCheckState("test_session", "table_a")).toBe("verified");
    expect(getImpactCheckState("test_session", "table_b")).toBeNull();
  });

  it("maintains independent state per session", () => {
    markImpactCheckInjected("session_1", "orders");
    expect(getImpactCheckState("session_1", "orders")).toBe("injected");
    expect(getImpactCheckState("session_2", "orders")).toBeNull();
  });
});

describe("MonitorGap", () => {
  it("returns false initially", () => {
    expect(hasMonitorGap("test_session", "my_table")).toBe(false);
  });

  it("returns true after marking", () => {
    markMonitorGap("test_session", "my_table");
    expect(hasMonitorGap("test_session", "my_table")).toBe(true);
  });
});

describe("EditAccumulator", () => {
  it("returns empty for unknown session", () => {
    expect(getEditedTables("session_1")).toEqual([]);
  });

  it("adds one table", () => {
    addEditedTable("session_1", "orders");
    expect(getEditedTables("session_1")).toEqual(["orders"]);
  });

  it("adds multiple tables", () => {
    addEditedTable("session_1", "orders");
    addEditedTable("session_1", "customers");
    const tables = getEditedTables("session_1");
    expect(tables).toContain("orders");
    expect(tables).toContain("customers");
  });

  it("deduplicates repeated edits", () => {
    addEditedTable("session_1", "orders");
    addEditedTable("session_1", "orders");
    expect(getEditedTables("session_1")).toEqual(["orders"]);
  });

  it("clears edited tables", () => {
    addEditedTable("session_1", "orders");
    clearEditedTables("session_1");
    expect(getEditedTables("session_1")).toEqual([]);
  });

  it("isolates sessions", () => {
    addEditedTable("session_1", "orders");
    addEditedTable("session_2", "customers");
    expect(getEditedTables("session_1")).toEqual(["orders"]);
    expect(getEditedTables("session_2")).toEqual(["customers"]);
  });
});

describe("PendingValidation", () => {
  it("moves turn edits to pending", () => {
    addEditedTable("session_1", "orders");
    addEditedTable("session_1", "customers");
    moveToPendingValidation("session_1");
    const pending = getPendingValidationTables("session_1");
    expect(pending).toContain("orders");
    expect(pending).toContain("customers");
    expect(getEditedTables("session_1")).toEqual([]);
  });

  it("returns empty for unknown session", () => {
    expect(getPendingValidationTables("session_1")).toEqual([]);
  });

  it("merges new edits into existing pending", () => {
    addEditedTable("session_1", "orders");
    moveToPendingValidation("session_1");

    addEditedTable("session_1", "customers");
    moveToPendingValidation("session_1");

    const pending = getPendingValidationTables("session_1");
    expect(pending).toContain("orders");
    expect(pending).toContain("customers");
  });
});

describe("SessionIdValidation", () => {
  it("accepts alphanumeric with dashes and underscores", () => {
    // Should not throw
    markImpactCheckInjected("abc-123_test", "table");
    expect(getImpactCheckState("abc-123_test", "table")).toBe("injected");
  });

  it("rejects path traversal", () => {
    expect(() => markImpactCheckInjected("../../etc/passwd", "table")).toThrow();
  });

  it("rejects spaces", () => {
    expect(() => markImpactCheckInjected("session 1", "table")).toThrow();
  });

  it("rejects shell metacharacters", () => {
    for (const bad of ["$(cmd)", "a;b", "a&b", "a|b"]) {
      expect(() => markImpactCheckInjected(bad, "table")).toThrow();
    }
  });

  it("rejects empty string", () => {
    expect(() => markImpactCheckInjected("", "table")).toThrow();
  });
});

describe("FilePermissions", () => {
  function getPerms(path: string): number {
    return statSync(path).mode & 0o777;
  }

  it("impact check file is owner-only (0o600)", () => {
    markImpactCheckInjected("test_session", "perm_table");
    const path = join(tmpdir(), "mc_prevent_ic_test_session_perm_table");
    expect(getPerms(path)).toBe(0o600);
  });

  it("turn file is owner-only (0o600)", () => {
    addEditedTable("perm_session", "orders");
    const path = join(tmpdir(), "mc_prevent_turn_perm_session");
    expect(getPerms(path)).toBe(0o600);
  });

  it("pending file is owner-only (0o600)", () => {
    addEditedTable("perm_session2", "orders");
    moveToPendingValidation("perm_session2");
    const path = join(tmpdir(), "mc_prevent_pending_perm_session2");
    expect(getPerms(path)).toBe(0o600);
  });
});

describe("DbtConfigCache", () => {
  it("returns defaults when no dbt_project.yml", () => {
    const paths = getDbtPaths("/nonexistent/models/foo.sql");
    expect(paths["model-paths"]).toEqual(["models"]);
    expect(paths["macro-paths"]).toEqual(["macros"]);
    expect(paths["snapshot-paths"]).toEqual(["snapshots"]);
    expect(paths["seed-paths"]).toEqual(["seeds"]);
    expect(paths["analysis-paths"]).toEqual(["analyses"]);
  });

  it("parses inline list syntax", () => {
    const tmpDir = mkdtempSync(join(tmpdir(), "dbt-test-"));
    const { projectDir } = createDbtProject(tmpDir, {
      dbtProjectYml: "name: test\nmodel-paths: ['transformations']\n",
      models: { "placeholder.sql": "SELECT 1" },
    });
    const paths = getDbtPaths(join(projectDir, "transformations", "foo.sql"));
    expect(paths["model-paths"]).toEqual(["transformations"]);
  });

  it("parses block list syntax", () => {
    const tmpDir = mkdtempSync(join(tmpdir(), "dbt-test-"));
    const { projectDir } = createDbtProject(tmpDir, {
      dbtProjectYml: "name: test\nmodel-paths:\n  - custom_models\n  - more_models\n",
      models: { "placeholder.sql": "SELECT 1" },
    });
    const paths = getDbtPaths(join(projectDir, "custom_models", "foo.sql"));
    expect(paths["model-paths"]).toEqual(["custom_models", "more_models"]);
  });

  it("invalidates when dbt_project.yml mtime changes", () => {
    const tmpDir = mkdtempSync(join(tmpdir(), "dbt-test-"));
    const { projectDir } = createDbtProject(tmpDir, {
      dbtProjectYml: "name: test\nmodel-paths: ['models']\n",
      models: { "foo.sql": "SELECT 1" },
    });
    const filePath = join(projectDir, "models", "foo.sql");

    // First call caches
    let paths = getDbtPaths(filePath);
    expect(paths["model-paths"]).toEqual(["models"]);

    // Update dbt_project.yml
    writeFileSync(
      join(projectDir, "dbt_project.yml"),
      "name: test\nmodel-paths: ['new_models']\n"
    );

    // Second call should pick up the change
    paths = getDbtPaths(filePath);
    expect(paths["model-paths"]).toEqual(["new_models"]);
  });
});
