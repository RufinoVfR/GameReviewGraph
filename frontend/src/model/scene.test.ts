import { describe, expect, it } from "vitest";

import { mockData } from "../data/mock-data";
import { buildTrail } from "./scene";

/** Collapse a trail into its node ids for concise assertions. */
function ids(trail: ReturnType<typeof buildTrail>): string[] {
  return trail.map((item) => item.id);
}

describe("buildTrail (navigation state)", () => {
  it("shows only the root when nothing is selected", () => {
    expect(ids(buildTrail(mockData))).toEqual(["root"]);
  });

  it("shows only the root when there is no data", () => {
    expect(ids(buildTrail(null, "comment-1"))).toEqual(["root"]);
  });

  it("descends to the selected community", () => {
    expect(ids(buildTrail(mockData, "community-3"))).toEqual(["root", "community-3"]);
  });

  it("descends to the selected comment via its community", () => {
    expect(ids(buildTrail(mockData, "comment-4"))).toEqual(["root", "community-2", "comment-4"]);
  });

  it("descends to the selected sentence via comment and community", () => {
    expect(ids(buildTrail(mockData, "sentence-5"))).toEqual([
      "root",
      "community-2",
      "comment-3",
      "sentence-5",
    ]);
  });

  it("descends through every level to the selected word", () => {
    expect(ids(buildTrail(mockData, "word-3"))).toEqual([
      "root",
      "community-1",
      "comment-1",
      "sentence-2",
      "word-3",
    ]);
  });

  it("does not duplicate frames that resolve to the same node", () => {
    const trail = buildTrail(mockData, "community-1");
    expect(ids(trail)).toEqual([...new Set(ids(trail))]);
  });
});
