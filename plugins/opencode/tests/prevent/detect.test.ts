/**
 * dbt file detection tests — port of plugins/claude-code/prevent/tests/test_detect.py
 */
import { describe, it, expect, beforeEach, afterEach, spyOn } from "bun:test";
import * as fs from "fs";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, symlinkSync, writeFileSync } from "fs";
import { basename, dirname, extname, join, resolve } from "path";
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

// A folder named like a dbt path but in another case is the same folder on a
// case-insensitive filesystem (macOS, Windows), so it is gated as one. On a
// case-sensitive filesystem that costs at most an extra assessment.
describe("folder name case", () => {
  it("gates a new file under an upper-case models folder", () => {
    expect(isDbtModel(join(tmpDir, "MODELS", "orders.sql"))).toBe(true);
    expect(isDbtModel(join(tmpDir, "Models", "staging", "Orders.Sql"))).toBe(true);
  });

  it("matches a custom model path in another case", () => {
    require("fs").writeFileSync(join(tmpDir, "dbt_project.yml"), "model-paths: ['Transformations']\n");
    expect(isDbtModel(join(tmpDir, "transformations", "orders.sql"))).toBe(true);
  });

  it("keeps exclusions exact, so a differently cased seeds folder stays gated", () => {
    expect(isDbtModel(join(tmpDir, "models", "SEEDS", "orders.sql"))).toBe(true);
  });

  // Naming matches macro folders in exact case, as main does: a name main gives
  // a model never turns into a macro name, which would drop it from the commit list.
  it("gates a file under an upper-case macros folder but names it as on main", () => {
    const path = join(tmpDir, "MACROS", "helper.sql");
    expect(isDbtModel(path)).toBe(true);
    expect(isMacroFile(path)).toBe(false);
    expect(extractTableName(path)).toBe("helper");
  });

  it("keeps the name of a model under a differently cased macros folder", () => {
    const path = join(tmpDir, "Macros", "models", "x.sql");
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("x");
  });

  it("counts a schema file under an upper-case models folder", () => {
    expect(isDbtSchemaFile(join(tmpDir, "MODELS", "schema.yml"))).toBe(true);
  });
});

// With a dbt_project.yml, only the folders below the project count: a folder
// above it that shares a dbt folder name says nothing about the file.
describe("folders above the project", () => {
  function projectUnder(...ancestors: string[]): string {
    const project = join(tmpDir, ...ancestors, "proj");
    mkdirSync(project, { recursive: true });
    writeFileSync(join(project, "dbt_project.yml"), "name: proj\n");
    return project;
  }

  for (const ancestor of ["Macros", "macros"]) {
    it(`does not name a model a macro under a ${ancestor} ancestor`, () => {
      const path = join(projectUnder(ancestor), "models", "orders.sql");
      expect(isDbtModel(path)).toBe(true);
      expect(isMacroFile(path)).toBe(false);
      expect(extractTableName(path)).toBe("orders");
    });
  }

  for (const ancestor of ["seeds", "analyses"]) {
    it(`keeps models gated under a ${ancestor} ancestor`, () => {
      const project = projectUnder(ancestor);
      expect(isDbtModel(join(project, "models", "orders.sql"))).toBe(true);
      expect(isDbtSchemaFile(join(project, "models", "schema.yml"))).toBe(true);
    });
  }

  // Gating is never narrower than main, which matches folder names anywhere in
  // the path against the nearest project's settings.
  it("still gates other folders under a models ancestor, as on main", () => {
    const project = projectUnder("models");
    expect(isDbtModel(join(project, "scripts", "x.sql"))).toBe(true);
    expect(isDbtSchemaFile(join(project, "scripts", "x.yml"))).toBe(true);
  });

  it("still counts folders below the project", () => {
    const project = projectUnder("models");
    expect(isDbtModel(join(project, "seeds", "x.sql"))).toBe(false);
    expect(extractTableName(join(project, "macros", "helper.sql"))).toBe("macro:helper");
  });

  it("resolves a relative path against the project", () => {
    const project = projectUnder("seeds", "Macros");
    const cwd = process.cwd();
    process.chdir(project);
    try {
      expect(isDbtModel("models/orders.sql")).toBe(true);
      expect(extractTableName("models/orders.sql")).toBe("orders");
      expect(isDbtModel("scripts/x.sql")).toBe(false);
    } finally {
      process.chdir(cwd);
    }
  });

  it("matches every folder of a backslash path without a project", () => {
    expect(isDbtModel("C:\\no_such_dir\\models\\orders.sql")).toBe(true);
    expect(isDbtModel("C:\\no_such_dir\\seeds\\orders.sql")).toBe(false);
    expect(isMacroFile("C:\\no_such_dir\\macros\\helper.sql")).toBe(true);
  });
});

const MODEL_SQL = "SELECT * FROM {{ ref('raw') }}";
const MACRO_SQL = "{% macro helper() %}1{% endmacro %}";
const SNAPSHOT_SQL = "{% snapshot orders %}1{% endsnapshot %}";

function project(dir: string, yml = "name: p\n"): string {
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "dbt_project.yml"), yml);
  return dir;
}

function write(path: string, text = MODEL_SQL): string {
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, text);
  return path;
}

// Gating is main's rule (nearest project's folder names anywhere in the path)
// united with an exact check against every project above the file: the file
// sits inside one of that project's configured model/macro/snapshot folders and
// not inside one of its seed or analysis folders. Names come from the exact
// check when any project contains the file.
describe("nested projects", () => {
  it("does not ungate models below a stray project in models/", () => {
    const o = project(join(tmpDir, "outer"));
    project(join(o, "models"));
    for (const rel of ["top.sql", "staging/stg.sql"]) {
      const path = write(join(o, "models", rel));
      expect(isDbtModel(path)).toBe(true);
      expect(isMacroFile(path)).toBe(false);
      expect(extractTableName(path)).toBe(basename(rel, extname(rel)));
    }
    expect(isDbtSchemaFile(join(o, "models", "schema.yml"))).toBe(true);
  });

  it("does not ungate a models subfolder holding a stray project", () => {
    const o = project(join(tmpDir, "outer"));
    project(join(o, "models", "sub"));
    const path = write(join(o, "models", "sub", "x.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("x");
    expect(isDbtSchemaFile(join(o, "models", "sub", "schema.yml"))).toBe(true);
  });

  it("keeps inner models gated under a seeds folder between projects", () => {
    const i = project(join(project(join(tmpDir, "outer")), "seeds", "inner"));
    const path = write(join(i, "models", "x.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("x");
    expect(isDbtSchemaFile(join(i, "models", "schema.yml"))).toBe(true);
  });

  it("does not name an inner model a macro under a Macros folder between projects", () => {
    const i = project(join(project(join(tmpDir, "outer")), "Macros", "inner"));
    const path = write(join(i, "models", "x.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(isMacroFile(path)).toBe(false);
    expect(extractTableName(path)).toBe("x");
  });

  it("gates an inner project under the outer custom model path", () => {
    const o = project(join(tmpDir, "outer"), "model-paths: ['transformations']\n");
    project(join(o, "transformations", "sub"));
    const path = write(join(o, "transformations", "sub", "x.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("x");
    expect(isDbtSchemaFile(join(o, "transformations", "sub", "schema.yml"))).toBe(true);
  });

  // The inner project claims `staging` as a model folder and also excludes it,
  // so only the outer project's claim can gate the file.
  it("does not let one project's exclusion ungate another's model", () => {
    const o = project(join(tmpDir, "outer"));
    project(join(o, "models"), "model-paths: ['staging']\nanalysis-paths: ['staging']\n");
    const path = write(join(o, "models", "staging", "stg.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(isDbtSchemaFile(join(o, "models", "staging", "schema.yml"))).toBe(true);
  });

  it("gates a models folder between projects, as on main", () => {
    const o = project(join(tmpDir, "outer"), "model-paths: ['transformations']\n");
    const i = project(join(o, "models", "inner"));
    expect(isDbtModel(write(join(i, "scripts", "x.sql")))).toBe(true);
    expect(isDbtModel(write(join(i, "models", "y.sql")))).toBe(true);
  });

  it("names a macro of the inner project only as a macro", () => {
    const i = project(join(project(join(tmpDir, "outer")), "tools", "inner"));
    const path = write(join(i, "macros", "helper.sql"), MACRO_SQL);
    expect(isDbtModel(path)).toBe(true);
    expect(isMacroFile(path)).toBe(true);
    expect(extractTableName(path)).toBe("macro:helper");
  });

  it("applies a configured exclusion inside a model folder", () => {
    const p = project(join(tmpDir, "p"), "model-paths: ['src']\nseed-paths: ['src/seeds']\n");
    expect(isDbtModel(write(join(p, "src", "seeds", "x.sql")))).toBe(false);
    expect(isDbtSchemaFile(join(p, "src", "seeds", "schema.yml"))).toBe(false);
    expect(isDbtModel(write(join(p, "src", "y.sql")))).toBe(true);
  });

  // dbt builds models/macros/x.sql as a model; main named it a macro.
  it("names a macros folder inside a model folder as a model", () => {
    const path = write(join(project(join(tmpDir, "p")), "models", "macros", "helper.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("helper");
  });
});

// Fixtures from review, each built by dbt; main gates every one.
describe("configured paths", () => {
  it("gates despite an exclusion sharing a basename with an unrelated folder", () => {
    const o = project(join(tmpDir, "outer"), "model-paths: ['src/models']\nseed-paths: ['data/seeded']\n");
    const nested = project(join(o, "src", "models", "nested"));
    const path = write(join(nested, "seeded", "orders.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(isDbtSchemaFile(join(nested, "seeded", "schema.yml"))).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });

  it("gates a model path through a parent segment", () => {
    const x = project(join(tmpDir, "x"), "model-paths: ['../x']\n");
    expect(isDbtModel(write(join(x, "staging", "orders.sql")))).toBe(true);
    expect(isDbtSchemaFile(join(x, "staging", "schema.yml"))).toBe(true);
  });

  it("gates a file whose project is outside its ancestry", () => {
    project(join(tmpDir, "build"), "model-paths: ['../models']\n");
    const nested = project(join(tmpDir, "models", "nested"), "name: other\n");
    expect(isDbtModel(write(join(nested, "orders.sql")))).toBe(true);
    expect(isDbtSchemaFile(join(nested, "schema.yml"))).toBe(true);
  });

  it("gates a file whose project is outside its ancestry beside a directory named dbt_project.yml", () => {
    project(join(tmpDir, "build"), "model-paths: ['../models']\n");
    mkdirSync(join(tmpDir, "models", "nested", "dbt_project.yml"), { recursive: true });
    expect(isDbtModel(write(join(tmpDir, "models", "nested", "orders.sql")))).toBe(true);
    expect(isDbtSchemaFile(join(tmpDir, "models", "nested", "schema.yml"))).toBe(true);
  });

  it("reaches the outer project through a symlink alias", () => {
    const o = project(join(tmpDir, "outer"));
    project(join(o, "models"));
    write(join(o, "models", "orders.sql"));
    mkdirSync(join(tmpDir, "models"));
    symlinkSync(join(o, "models"), join(tmpDir, "models", "alias"));
    const path = join(tmpDir, "models", "alias", "orders.sql");
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });

  // No folder in the written path is a dbt folder; only the resolved path is.
  it("gates a symlink alias under a neutral folder", () => {
    const o = project(join(tmpDir, "outer"), "model-paths: ['transformations']\n");
    project(join(o, "transformations"), "model-paths: ['nothing']\n");
    write(join(o, "transformations", "orders.sql"));
    mkdirSync(join(tmpDir, "links"));
    symlinkSync(join(o, "transformations"), join(tmpDir, "links", "alias"));
    expect(isDbtModel(join(tmpDir, "links", "alias", "orders.sql"))).toBe(true);
  });

  // Main's OpenCode lookup took any entry named dbt_project.yml as the nearest
  // project, with default settings when it isn't a readable file.
  it("reads a directory named like a project file as the nearest project with defaults, as on main", () => {
    const o = project(join(tmpDir, "outer"), "model-paths: ['transformations']\n");
    mkdirSync(join(o, "x", "dbt_project.yml"), { recursive: true });
    expect(isDbtModel(write(join(o, "x", "models", "a.sql")))).toBe(true);
    expect(isDbtSchemaFile(join(o, "x", "models", "schema.yml"))).toBe(true);
  });

  it("skips a directory named like a project file", () => {
    const o = project(join(tmpDir, "outer"), "model-paths: ['transformations']\n");
    mkdirSync(join(o, "transformations", "dbt_project.yml"), { recursive: true });
    expect(isDbtModel(write(join(o, "transformations", "orders.sql")))).toBe(true);
  });
});

// Cases only the exact check gates: a seed or analysis folder elsewhere shares
// a folder name with the file's path, so main's name rule excludes it.
describe("exact folder matching", () => {
  it("resolves a parent segment", () => {
    const p = project(join(tmpDir, "p"), "model-paths: ['../p/core']\nseed-paths: ['data/stuff']\n");
    expect(isDbtModel(write(join(p, "core", "stuff", "x.sql")))).toBe(true);
  });

  it("matches a model folder in another case", () => {
    const p = project(join(tmpDir, "p"), "model-paths: ['src/Models']\nseed-paths: ['data/seeded']\n");
    // A new file, so no symlink resolution can fix the folder's case.
    expect(isDbtModel(join(p, "src", "models", "seeded", "x.sql"))).toBe(true);
  });

  it("matches an exclusion folder in exact case only", () => {
    const p = project(
      join(tmpDir, "p"),
      "model-paths: ['src']\nseed-paths: ['src/seeds']\nanalysis-paths: ['other/SEEDS']\n"
    );
    expect(isDbtModel(write(join(p, "src", "SEEDS", "x.sql")))).toBe(true);
  });
});

describe("naming by configured paths", () => {
  it("names an inner macro under an outer folder named like a model folder", () => {
    const o = project(join(tmpDir, "outer"), "model-paths: ['src/models']\nmacro-paths: ['udfs']\n");
    const i = project(join(o, "other", "models", "inner"));
    expect(extractTableName(write(join(i, "macros", "helper.sql"), MACRO_SQL))).toBe("macro:helper");
  });

  it("names an inner snapshot under an outer folder named like a macro folder", () => {
    const o = project(join(tmpDir, "outer"), "macro-paths: ['ops/macros']\n");
    const i = project(join(o, "macros", "inner"));
    const path = write(join(i, "snapshots", "orders.sql"), SNAPSHOT_SQL);
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });

  it("names an inner snapshot inside an outer macro folder as a snapshot", () => {
    const i = project(join(project(join(tmpDir, "outer")), "macros", "inner"));
    expect(extractTableName(write(join(i, "snapshots", "orders.sql"), SNAPSHOT_SQL))).toBe("orders");
  });

  it("falls back to folder names when no project contains the file", () => {
    const p = project(join(tmpDir, "p"), "model-paths: ['src']\n");
    expect(extractTableName(join(p, "lib", "macros", "helper.sql"))).toBe("macro:helper");
  });
});

// A project file that can't be read skips that project; it never aborts or
// stalls classification by another.
describe("unreadable projects", () => {
  /**
   * Make statSync throw for target when reading its mtime, after discovery
   * (isFile) has found it: the file vanished or became unreadable in between.
   */
  function failAfterDiscovery(target: string) {
    const real = fs.statSync;
    return spyOn(fs, "statSync").mockImplementation(((p: fs.PathLike, o?: unknown) => {
      if (String(p) === target && new Error().stack!.includes("getDbtProjectPaths")) {
        throw new Error(`ENOENT: ${p}`);
      }
      return (real as (p: fs.PathLike, o?: unknown) => fs.Stats)(p, o);
    }) as typeof fs.statSync);
  }

  it("classifies with the inner project when the outer config vanishes after discovery", () => {
    const o = project(join(tmpDir, "outer"));
    const i = project(join(o, "inner"));
    const path = write(join(i, "models", "orders.sql"));
    const spy = failAfterDiscovery(join(o, "dbt_project.yml"));
    try {
      expect(isDbtModel(path)).toBe(true);
      expect(isDbtSchemaFile(join(i, "models", "schema.yml"))).toBe(true);
      expect(extractTableName(path)).toBe("orders");
    } finally {
      spy.mockRestore();
    }
  });

  it("falls back to defaults when the nearest config can't be read", () => {
    const p = project(join(tmpDir, "p"));
    const path = write(join(p, "models", "orders.sql"));
    const spy = failAfterDiscovery(join(p, "dbt_project.yml"));
    try {
      expect(isDbtModel(path)).toBe(true);
    } finally {
      spy.mockRestore();
    }
  });

  it("does not read a FIFO that is the nearest entry named like a project file", () => {
    const o = join(tmpDir, "outer");
    mkdirSync(o);
    const made = Bun.spawnSync(["mkfifo", join(o, "dbt_project.yml")]);
    expect(made.exitCode).toBe(0);
    const path = join(o, "models", "orders.sql");
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });

  it("does not read a FIFO named like a project file", () => {
    const o = join(tmpDir, "outer");
    mkdirSync(o);
    const made = Bun.spawnSync(["mkfifo", join(o, "dbt_project.yml")]);
    expect(made.exitCode).toBe(0);
    const i = project(join(o, "inner"));
    const path = write(join(i, "models", "orders.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });
});

// The exact check can only veto a macro name main's rule gives, never add one.
describe("naming never macro where main says model", () => {
  it("names a sibling project's model beside an inner macro root as a model", () => {
    project(join(tmpDir, "build"), "model-paths: ['../models']\n");
    const nested = project(join(tmpDir, "models", "nested"), "macro-paths: ['.']\n");
    write(join(tmpDir, "models", "raw.sql"), "select 1 as id");
    const path = write(join(nested, "orders.sql"), "select * from {{ ref('raw') }}");
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });

  it("names a model under an outer macro root over an inner project as a model", () => {
    const o = project(join(tmpDir, "outer"), "macro-paths: ['udfs']\n");
    const i = project(join(o, "udfs", "inner"), "model-paths: ['a/models']\n");
    const path = write(join(i, "b", "models", "x.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("x");
  });

  it("resolves an absolute configured model path", () => {
    const p = join(tmpDir, "p");
    project(p, `model-paths: ['${p}/warehouse']\nmacro-paths: ['warehouse/udfs']\n`);
    const path = write(join(p, "warehouse", "udfs", "orders.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });
});

function symlinkChain(folder: string, hops: number, target: string): void {
  mkdirSync(folder, { recursive: true });
  for (let i = 0; i < hops - 1; i++) symlinkSync(String(i + 1), join(folder, String(i)));
  symlinkSync(target, join(folder, String(hops - 1)));
}

describe("canonical paths", () => {
  it("classifies through a deep symlink chain in the written path", () => {
    const p = project(join(tmpDir, "p"));
    mkdirSync(join(p, "real"));
    symlinkChain(join(p, "chain"), 1100, "../real");
    mkdirSync(join(p, "models"));
    symlinkSync("../chain/0", join(p, "models", "loop"));
    const path = join(p, "models", "loop", "orders.sql");
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });

  it("classifies with a deep symlink chain in a configured root", () => {
    const p = project(join(tmpDir, "p"), "macro-paths: ['chain/0']\n");
    mkdirSync(join(p, "real"));
    symlinkChain(join(p, "chain"), 1100, "../real");
    const path = write(join(p, "models", "orders.sql"));
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });

  // Resolving is reached here, so its failure must fall back, not throw.
  it("classifies through a deep symlink chain where main's rule does not decide", () => {
    const p = project(join(tmpDir, "p"));
    mkdirSync(join(p, "real"));
    symlinkChain(join(p, "chain"), 1100, "../real");
    mkdirSync(join(p, "scripts"));
    symlinkSync("../chain/0", join(p, "scripts", "loop"));
    expect(isDbtModel(join(p, "scripts", "loop", "orders.sql"))).toBe(false);
    expect(isDbtSchemaFile(join(p, "scripts", "loop", "schema.yml"))).toBe(false);
  });

  it("names with a deep symlink chain in a configured root", () => {
    const p = project(join(tmpDir, "p"), "macro-paths: ['macros', 'chain/0']\n");
    mkdirSync(join(p, "real"));
    symlinkChain(join(p, "chain"), 1100, "../real");
    const path = write(join(p, "macros", "helper.sql"), MACRO_SQL);
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("macro:helper");
  });

  it("follows a dangling alias to a model folder", () => {
    const p = project(join(tmpDir, "p"), "model-paths: ['src']\nseed-paths: ['data/alias']\n");
    symlinkSync("src/future", join(p, "alias"));
    expect(isDbtModel(join(p, "alias", "orders.sql"))).toBe(true);
  });

  it("follows an alias before a parent segment", () => {
    const p = project(join(tmpDir, "p"), "model-paths: ['src']\nseed-paths: ['data/alias']\n");
    write(join(p, "src", "orders.sql"));
    mkdirSync(join(p, "src", "deeper"));
    symlinkSync("src/deeper", join(p, "alias"));
    // Not join(): it would apply the `..` before the alias.
    expect(isDbtModel(`${p}/alias/../orders.sql`)).toBe(true);
  });
});

const isRoot = typeof process.getuid === "function" && process.getuid() === 0;

describe("unreadable configs", () => {
  it("does not read a config replaced by a FIFO after discovery", () => {
    const o = join(tmpDir, "outer");
    mkdirSync(o);
    const fifo = join(o, "dbt_project.yml");
    expect(Bun.spawnSync(["mkfifo", fifo]).exitCode).toBe(0);
    // Read as an empty project, the outer defaults would claim outer/models and
    // rename the inner macro.
    const i = project(join(o, "models", "inner"));
    const path = write(join(i, "macros", "helper.sql"), MACRO_SQL);
    // Discovery and the mtime read see a regular file; by the read it is a FIFO.
    const script = join(tmpDir, "probe.ts");
    writeFileSync(
      script,
      `const fs = require("fs");
const realStat = fs.statSync;
fs.statSync = (p, o) => (String(p) === ${JSON.stringify(fifo)}
  ? { isFile: () => true, mtimeMs: 1 }
  : realStat(p, o));
const d = require(${JSON.stringify(resolve(__dirname, "../../src/prevent/detect.ts"))});
console.log(JSON.stringify([d.isDbtModel(${JSON.stringify(path)}), d.extractTableName(${JSON.stringify(path)})]));
`
    );
    const run = Bun.spawnSync(["bun", script], { timeout: 5000 });
    expect(run.exitCode).toBe(0);
    expect(JSON.parse(run.stdout.toString())).toEqual([true, "macro:helper"]);
  });

  it.skipIf(isRoot)("skips a config that can't be read and caches nothing for it", () => {
    const o = project(join(tmpDir, "outer"), "model-paths: ['warehouse']\n");
    const i = project(join(o, "models", "inner"));
    const path = write(join(i, "macros", "helper.sql"), MACRO_SQL);
    const yml = join(o, "dbt_project.yml");
    chmodSync(yml, 0);
    try {
      expect(isDbtModel(path)).toBe(true);
      expect(extractTableName(path)).toBe("macro:helper");
    } finally {
      chmodSync(yml, 0o644);
    }
    expect(extractTableName(path)).toBe("macro:helper");
  });

  it.skipIf(isRoot)("uses defaults when the nearest config can't be read", () => {
    const p = project(join(tmpDir, "p"), "model-paths: ['warehouse']\n");
    const path = write(join(p, "models", "orders.sql"));
    chmodSync(join(p, "dbt_project.yml"), 0);
    try {
      expect(isDbtModel(path)).toBe(true);
    } finally {
      chmodSync(join(p, "dbt_project.yml"), 0o644);
    }
  });
});

const MAIN_DEFAULT_PATHS: Record<string, string[]> = {
  "model-paths": ["models"],
  "macro-paths": ["macros"],
  "snapshot-paths": ["snapshots"],
  "seed-paths": ["seeds"],
  "analysis-paths": ["analyses"],
};

/** main's lookup (797fc40), copied: nearest entry of any kind. */
function mainFindDbtProjectYml(filePath: string): string | null {
  let directory = dirname(resolve(filePath));
  while (true) {
    const candidate = join(directory, "dbt_project.yml");
    if (existsSync(candidate)) return candidate;
    const parent = dirname(directory);
    if (parent === directory) return null;
    directory = parent;
  }
}

/**
 * main's parser (797fc40), copied, so the reference shares nothing with the
 * loader under test.
 */
function mainParseDbtProjectPaths(projectYmlPath: string): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  let lines: string[];
  try {
    lines = readFileSync(projectYmlPath, "utf-8").split("\n");
  } catch {
    return result;
  }
  let currentKey: string | null = null;
  const knownKeys = Object.keys(MAIN_DEFAULT_PATHS);
  for (const line of lines) {
    const stripped = line.trim();
    let matched = false;
    for (const key of knownKeys) {
      if (stripped.startsWith(`${key}:`)) {
        const valuePart = stripped.slice(key.length + 1).trim();
        if (valuePart.startsWith("[")) {
          const inner = valuePart.replace(/^\[|\]$/g, "");
          const items = inner
            .split(",")
            .map((x) => x.trim().replace(/^['"]|['"]$/g, ""))
            .filter(Boolean);
          if (items.length > 0) result[key] = items;
          currentKey = null;
        } else if (!valuePart || valuePart === "") {
          currentKey = key;
          result[key] = [];
        }
        matched = true;
        break;
      }
    }
    if (!matched) {
      if (currentKey && stripped.startsWith("- ")) {
        const item = stripped.slice(2).trim().replace(/^['"]|['"]$/g, "");
        if (item) (result[currentKey] ??= []).push(item);
      } else if (currentKey && !stripped.startsWith("#") && stripped.length > 0) {
        currentKey = null;
      }
    }
  }
  return result;
}

function mainGetDbtPaths(filePath: string): Record<string, string[]> {
  const yml = mainFindDbtProjectYml(filePath);
  return yml ? { ...MAIN_DEFAULT_PATHS, ...mainParseDbtProjectPaths(yml) } : { ...MAIN_DEFAULT_PATHS };
}

/** main's isMacroFile (797fc40), copied, over main's own lookup and parser. */
function mainIsMacroFile(filePath: string): boolean {
  const parts = new Set(filePath.replace(/\\/g, "/").split("/"));
  const names = (mainGetDbtPaths(filePath)["macro-paths"] ?? []).map((p) =>
    p.replace(/\/+$/, "").split("/").pop()!
  );
  return names.some((n) => parts.has(n));
}

const LS = "\u2028";

/**
 * A quoted YAML scalar whose text holds keyLine between U+2028 separators: one
 * YAML line, which main's parser never reads as a key.
 */
function hidden(keyLine: string): string {
  return `vars:\n  note: "a${LS}${keyLine}${LS}b"\n`;
}

// isMacroFile true implies main's isMacroFile true, over every fixture layout
// in this file and a file in each of their folders.
describe("macro name never beyond main", () => {
  it("holds in every folder", () => {
    const r = tmpDir;
    project(join(r, "a", "outer"));
    project(join(r, "a", "outer", "models"));
    project(join(r, "b", "outer", "Macros", "inner"));
    project(join(r, "c", "outer"), "macro-paths: ['udfs']\n");
    project(join(r, "c", "outer", "udfs", "inner"), "model-paths: ['a/models']\n");
    project(join(r, "d", "build"), "model-paths: ['../models']\n");
    project(join(r, "d", "models", "nested"), "macro-paths: ['.']\n");
    project(join(r, "e", "outer"), "model-paths: ['src/models']\nmacro-paths: ['udfs']\n");
    project(join(r, "e", "outer", "other", "models", "inner"));
    project(join(r, "f", "outer"), "macro-paths: ['ops/macros']\n");
    project(join(r, "f", "outer", "macros", "inner"));
    project(join(r, "g", "p"), "model-paths: ['MODELS']\nmacro-paths: ['Macros', 'lib/macros']\n");
    const h = join(r, "h", "p");
    project(h, `model-paths: ['${h}/warehouse']\nmacro-paths: ['warehouse/udfs']\n`);
    project(join(r, "j", "build"), "model-paths: ['../models']\n");
    project(join(r, "j", "models", "nested"), "macro-paths: ['udfs']\n" + hidden("macro-paths: ['macros']"));
    mkdirSync(join(r, "k", "p"), { recursive: true });
    writeFileSync(
      join(r, "k", "p", "dbt_project.yml"),
      Buffer.concat([Buffer.from("model-paths: ['warehouse']\nmacro-paths: ['udfs']\n# "), Buffer.from([0xff]), Buffer.from("\n")])
    );
    for (const rel of [
      "a/outer/models/macros", "b/outer/Macros/inner/models", "b/outer/Macros/inner/macros",
      "c/outer/udfs/inner/b/models", "c/outer/udfs/inner/macros", "d/models/nested",
      "e/outer/other/models/inner/macros", "e/outer/udfs", "f/outer/macros/inner/snapshots",
      "f/outer/ops/macros", "g/p/macros", "g/p/Macros/models", "g/p/lib/MACROS", "h/p/warehouse/udfs",
      "i/MACROS", "i/Macros/models", "i/macros/models", "i/models/macros",
      "j/models/nested/macros", "j/models/nested/udfs", "k/p/warehouse/macros", "k/p/udfs",
    ]) {
      mkdirSync(join(r, rel), { recursive: true });
    }
    let checked = 0;
    const walk = (dir: string) => {
      const path = join(dir, "x.sql");
      if (isMacroFile(path)) expect([path, mainIsMacroFile(path)]).toEqual([path, true]);
      checked++;
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        if (e.isDirectory()) walk(join(dir, e.name));
      }
    };
    walk(r);
    expect(checked).toBeGreaterThan(40);
  });
});

// The config parser reads lines and bytes as main's did.
describe("parser matches main", () => {
  const FF = (text: string) =>
    Buffer.concat([Buffer.from(text), Buffer.from("# "), Buffer.from([0xff]), Buffer.from("\n")]);

  it("does not break a line at a separator inside a quoted value", () => {
    const p = project(join(tmpDir, "p"), "model-paths: ['warehouse']\n" + hidden("seed-paths: ['warehouse']"));
    expect(isDbtModel(write(join(p, "warehouse", "orders.sql")))).toBe(true);
    expect(isDbtSchemaFile(join(p, "warehouse", "schema.yml"))).toBe(true);
  });

  it("does not let a hidden macro path rename a sibling project's model", () => {
    project(join(tmpDir, "build"), "model-paths: ['../models']\n");
    const nested = project(join(tmpDir, "models", "nested"), "macro-paths: ['udfs']\n" + hidden("macro-paths: ['macros']"));
    write(join(tmpDir, "models", "raw.sql"), "select 1 as id");
    const path = write(join(nested, "macros", "orders.sql"), "select * from {{ ref('raw') }}");
    expect(isDbtModel(path)).toBe(true);
    expect(extractTableName(path)).toBe("orders");
  });

  it("reads settings past an undecodable byte in a comment", () => {
    const p = join(tmpDir, "p");
    mkdirSync(p);
    writeFileSync(join(p, "dbt_project.yml"), FF("model-paths: ['warehouse']\n"));
    expect(isDbtModel(write(join(p, "warehouse", "orders.sql")))).toBe(true);
    expect(isDbtSchemaFile(join(p, "warehouse", "schema.yml"))).toBe(true);
  });

  it("names by settings past an undecodable byte in a comment", () => {
    const p = join(tmpDir, "p");
    mkdirSync(p);
    writeFileSync(join(p, "dbt_project.yml"), FF("model-paths: ['warehouse']\nmacro-paths: ['udfs']\n"));
    expect(extractTableName(write(join(p, "warehouse", "macros", "orders.sql")))).toBe("orders");
  });
});
