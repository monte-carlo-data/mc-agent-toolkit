/**
 * apply_patch parsing — mirrors OpenCode v1's `parsePatch`
 * (anomalyco/opencode packages/opencode/src/patch/index.ts).
 */
import { describe, it, expect } from "bun:test";
import { parsePatchOps, patchPaths, reportedPaths } from "../../src/prevent/apply-patch";

function patch(...lines: string[]): string {
  return ["*** Begin Patch", ...lines, "*** End Patch"].join("\n");
}

describe("parsePatchOps", () => {
  it("reads Add, Delete, Update and Move headers in order", () => {
    expect(
      parsePatchOps(
        patch(
          "*** Add File: a.sql",
          "+select 1",
          "*** Delete File: b.sql",
          "*** Update File: c.sql",
          "*** Move to: d.sql",
          "@@",
          "-x",
          "+y"
        )
      )
    ).toEqual([
      { kind: "add", path: "a.sql" },
      { kind: "delete", path: "b.sql" },
      { kind: "update", path: "c.sql", movePath: "d.sql" },
    ]);
  });

  it("returns nothing without both envelope markers, or with End before Begin", () => {
    expect(parsePatchOps("*** Update File: a.sql\n@@\n-x\n+y")).toEqual([]);
    expect(parsePatchOps("*** Begin Patch\n*** Update File: a.sql")).toEqual([]);
    expect(parsePatchOps("*** Update File: a.sql\n*** End Patch")).toEqual([]);
    expect(parsePatchOps("*** End Patch\n*** Update File: a.sql\n*** Begin Patch")).toEqual([]);
    expect(parsePatchOps(undefined)).toEqual([]);
  });

  it("reads only between the markers", () => {
    expect(
      parsePatchOps(["*** Delete File: x.sql", patch("*** Delete File: a.sql"), "*** Delete File: y.sql"].join("\n"))
    ).toEqual([{ kind: "delete", path: "a.sql" }]);
  });

  it("matches markers after trimming the line, headers only at column 0", () => {
    expect(
      parsePatchOps(["  *** Begin Patch  ", "  *** Delete File: a.sql", "*** Delete File: b.sql", "*** End Patch "].join("\n"))
    ).toEqual([{ kind: "delete", path: "b.sql" }]);
  });

  it("takes a Move only from the line right after its Update header", () => {
    expect(
      parsePatchOps(patch("*** Update File: a.sql", "@@", "-x", "+y", "*** Move to: b.sql"))
    ).toEqual([{ kind: "update", path: "a.sql" }]);
  });

  it("treats an empty Move as a plain update and skips an empty header path", () => {
    expect(
      parsePatchOps(patch("*** Update File: a.sql", "*** Move to:   ", "@@", "*** Delete File:  "))
    ).toEqual([{ kind: "update", path: "a.sql" }]);
  });

  it("trims paths, including a CRLF line ending, and needs no space after the colon", () => {
    expect(
      parsePatchOps("*** Begin Patch\r\n*** Update File:a.sql \r\n*** Move to:\tb.sql\r\n@@\r\n*** End Patch\r\n")
    ).toEqual([{ kind: "update", path: "a.sql", movePath: "b.sql" }]);
  });

  it("unwraps a heredoc", () => {
    expect(
      parsePatchOps(["cat <<'EOF'", patch("*** Delete File: a.sql"), "EOF"].join("\n"))
    ).toEqual([{ kind: "delete", path: "a.sql" }]);
  });
});

describe("patchPaths", () => {
  it("resolves every source and destination against the directory, without repeats", () => {
    const ops = parsePatchOps(
      patch(
        "*** Update File: models/a.sql",
        "*** Move to: models/b.sql",
        "*** Update File: /abs/c.sql",
        "*** Move to: /abs/c.sql",
        "*** Delete File: ./models/a.sql"
      )
    );
    expect(patchPaths(ops, "/proj")).toEqual(["/proj/models/a.sql", "/proj/models/b.sql", "/abs/c.sql"]);
  });
});

describe("reportedPaths", () => {
  it("reads filePath and movePath from the tool's metadata", () => {
    expect(
      reportedPaths({
        files: [
          { filePath: "/p/a.sql", movePath: "/p/b.sql", type: "move" },
          { filePath: "/p/c.sql", type: "delete" },
          { filePath: "/p/a.sql", type: "update" },
        ],
      })
    ).toEqual(["/p/a.sql", "/p/b.sql", "/p/c.sql"]);
  });

  it("returns null when the metadata has no file list", () => {
    expect(reportedPaths({})).toBeNull();
    expect(reportedPaths(undefined)).toBeNull();
    expect(reportedPaths({ files: "nope" })).toBeNull();
  });
});
