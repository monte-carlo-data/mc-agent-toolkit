/**
 * Shared test utilities for the OpenCode prevent plugin tests.
 */
import { mkdirSync, writeFileSync, readdirSync, unlinkSync, existsSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

/**
 * Clean up all mc_prevent_* temp files.
 */
export function cleanCache(): void {
  const dir = tmpdir();
  try {
    for (const f of readdirSync(dir)) {
      if (f.startsWith("mc_prevent_")) {
        unlinkSync(join(dir, f));
      }
    }
  } catch {
    // ignore
  }
}

/**
 * Create a mock dbt project structure under `baseDir`.
 * Returns paths to use in tests.
 */
export function createDbtProject(
  baseDir: string,
  options: {
    models?: Record<string, string>;
    macros?: Record<string, string>;
    snapshots?: Record<string, string>;
    seeds?: Record<string, string>;
    analyses?: Record<string, string>;
    dbtProjectYml?: string;
  } = {}
): { projectDir: string } {
  const projectDir = join(baseDir, "project");
  mkdirSync(projectDir, { recursive: true });

  // Write dbt_project.yml if provided
  if (options.dbtProjectYml) {
    writeFileSync(join(projectDir, "dbt_project.yml"), options.dbtProjectYml);
  }

  const dirs: Record<string, Record<string, string> | undefined> = {
    models: options.models,
    macros: options.macros,
    snapshots: options.snapshots,
    seeds: options.seeds,
    analyses: options.analyses,
  };

  for (const [dirName, files] of Object.entries(dirs)) {
    if (!files) continue;
    const dirPath = join(projectDir, dirName);
    mkdirSync(dirPath, { recursive: true });
    for (const [fileName, content] of Object.entries(files)) {
      // Support nested paths like "staging/orders.sql"
      const filePath = join(dirPath, fileName);
      mkdirSync(join(filePath, ".."), { recursive: true });
      writeFileSync(filePath, content);
    }
  }

  return { projectDir };
}

/**
 * Create a mock OpenCode SDK client for testing.
 */
export function createMockClient(options: {
  messages?: Array<{ parts: Array<{ type: string; text?: string }> }>;
  promptFn?: (args: any) => Promise<any>;
} = {}): any {
  return {
    session: {
      messages: async () => ({
        data: options.messages ?? [],
      }),
      prompt: options.promptFn ?? (async () => ({})),
    },
  };
}
