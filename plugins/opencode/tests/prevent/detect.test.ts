/**
 * dbt file detection tests — port of plugins/claude-code/prevent/tests/test_detect.py
 */
import { describe, it, expect, beforeEach, afterEach } from "bun:test";
import { mkdtempSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { cleanCache, createDbtProject } from "./helpers";
import {
  isDbtModel,
  isDbtSchemaFile,
  isMacroFile,
  extractTableName,
} from "../../src/prevent/detect";

let tmpDir: string;

beforeEach(() => {
  cleanCache();
  tmpDir = mkdtempSync(join(tmpdir(), "detect-test-"));
});
afterEach(() => cleanCache());

describe("isDbtModel", () => {
  it("detects .sql file in models/ with {{ ref() }}", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "staging/client_hub_master.sql": "SELECT * FROM {{ ref('upstream_table') }}" },
    });
    expect(isDbtModel(join(projectDir, "models/staging/client_hub_master.sql"))).toBe(true);
  });

  it("detects .sql file in models/ with {{ source() }}", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "raw_orders.sql": "SELECT * FROM {{ source('raw', 'orders') }}" },
    });
    expect(isDbtModel(join(projectDir, "models/raw_orders.sql"))).toBe(true);
  });

  it("rejects .sql file outside models/", () => {
    const { projectDir } = createDbtProject(tmpDir);
    const scriptsDir = join(projectDir, "scripts");
    require("fs").mkdirSync(scriptsDir, { recursive: true });
    require("fs").writeFileSync(
      join(scriptsDir, "adhoc.sql"),
      "SELECT * FROM {{ ref('something') }}"
    );
    expect(isDbtModel(join(scriptsDir, "adhoc.sql"))).toBe(false);
  });

  it("rejects .sql file in seeds/", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      seeds: { "seed_data.sql": "SELECT * FROM {{ ref('x') }}" },
    });
    expect(isDbtModel(join(projectDir, "seeds/seed_data.sql"))).toBe(false);
  });

  it("detects .sql file in macros/ with {% macro %}", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      macros: { "helper.sql": "{% macro helper() %} SELECT 1 {% endmacro %}" },
    });
    expect(isDbtModel(join(projectDir, "macros/helper.sql"))).toBe(true);
  });

  it("rejects .sql file in analyses/", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      analyses: { "report.sql": "SELECT * FROM {{ ref('x') }}" },
    });
    expect(isDbtModel(join(projectDir, "analyses/report.sql"))).toBe(false);
  });

  it("detects .sql file in snapshots/ with {% snapshot %}", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      snapshots: { "snap.sql": "{% snapshot snap %} SELECT * FROM {{ ref('x') }} {% endsnapshot %}" },
    });
    expect(isDbtModel(join(projectDir, "snapshots/snap.sql"))).toBe(true);
  });

  it("rejects .sql file in models/ without dbt patterns", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "plain.sql": "SELECT 1 AS id" },
    });
    expect(isDbtModel(join(projectDir, "models/plain.sql"))).toBe(false);
  });

  it("rejects .yml file in models/", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "schema.yml": "version: 2\nmodels:\n  - name: foo" },
    });
    expect(isDbtModel(join(projectDir, "models/schema.yml"))).toBe(false);
  });

  it("rejects .yaml file in models/", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "schema.yaml": "version: 2\nmodels:\n  - name: foo" },
    });
    expect(isDbtModel(join(projectDir, "models/schema.yaml"))).toBe(false);
  });

  it("rejects non-sql non-yml file", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "script.py": "print('hello')" },
    });
    expect(isDbtModel(join(projectDir, "models/script.py"))).toBe(false);
  });

  it("rejects ref() past line 50", () => {
    const lines = Array(55).fill("-- comment\n").join("") + "SELECT * FROM {{ ref('x') }}";
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "deep_ref.sql": lines },
    });
    expect(isDbtModel(join(projectDir, "models/deep_ref.sql"))).toBe(false);
  });

  it("treats nonexistent .sql in models/ as new model", () => {
    expect(isDbtModel("/nonexistent/models/foo.sql")).toBe(true);
  });

  it("rejects nonexistent file outside models/", () => {
    expect(isDbtModel("/nonexistent/scripts/foo.sql")).toBe(false);
  });

  it("detects models with custom dbt_project.yml paths", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      dbtProjectYml: "name: test\nmodel-paths: ['transformations']\n",
    });
    // Create the custom dir and file
    const customDir = join(projectDir, "transformations");
    require("fs").mkdirSync(customDir, { recursive: true });
    require("fs").writeFileSync(
      join(customDir, "orders.sql"),
      "SELECT * FROM {{ ref('raw') }}"
    );
    expect(isDbtModel(join(customDir, "orders.sql"))).toBe(true);
  });
});

describe("isDbtSchemaFile", () => {
  it("detects .yml file in models/", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "schema.yml": "version: 2" },
    });
    expect(isDbtSchemaFile(join(projectDir, "models/schema.yml"))).toBe(true);
  });

  it("detects .yaml file in models/", () => {
    const { projectDir } = createDbtProject(tmpDir, {
      models: { "schema.yaml": "version: 2" },
    });
    expect(isDbtSchemaFile(join(projectDir, "models/schema.yaml"))).toBe(true);
  });

  it("rejects .yml file outside models/", () => {
    const { projectDir } = createDbtProject(tmpDir);
    const otherDir = join(projectDir, "other");
    require("fs").mkdirSync(otherDir, { recursive: true });
    require("fs").writeFileSync(join(otherDir, "config.yml"), "key: value");
    expect(isDbtSchemaFile(join(otherDir, "config.yml"))).toBe(false);
  });
});

describe("isMacroFile", () => {
  it("returns true for file in macros/", () => {
    expect(isMacroFile("/project/macros/helper.sql")).toBe(true);
  });

  it("returns false for file in models/", () => {
    expect(isMacroFile("/project/models/orders.sql")).toBe(false);
  });
});

describe("extractTableName", () => {
  it("extracts name from model path", () => {
    expect(extractTableName("/project/models/staging/client_hub_master.sql")).toBe(
      "client_hub_master"
    );
  });

  it("extracts macro: prefix from macro path", () => {
    expect(extractTableName("/project/macros/filters/internal_accounts.sql")).toBe(
      "macro:internal_accounts"
    );
  });

  it("extracts name from yml file", () => {
    expect(extractTableName("/project/models/schema.yml")).toBe("schema");
  });

  it("handles nested paths", () => {
    expect(extractTableName("/a/b/c/models/staging/finance/orders.sql")).toBe("orders");
  });
});
