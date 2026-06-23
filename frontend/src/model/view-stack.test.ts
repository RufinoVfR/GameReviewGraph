import { describe, expect, it } from "vitest";

import type { ViewLevel } from "../data/schemas";
import { createRootFrame, nextFrameTitle, pathLabel } from "./view-stack";

describe("createRootFrame", () => {
  it("starts navigation at the community level", () => {
    expect(createRootFrame()).toEqual({ level: "community", title: "Comunidades" });
  });
});

describe("nextFrameTitle", () => {
  it.each([
    ["comment", "Desempenho", "Comentários · Desempenho"],
    ["sentence", "Comentário 1", "Sentenças · Comentário 1"],
    ["word", "História envolvente", "Palavras · História envolvente"],
    ["community", "Comunidades", "Comunidades"],
  ] satisfies Array<[ViewLevel, string, string]>)(
    "labels a %s frame",
    (level, label, expected) => {
      expect(nextFrameTitle(level, label)).toBe(expected);
    },
  );
});

describe("pathLabel", () => {
  it.each([
    ["community", "Comunidades"],
    ["comment", "Comentários"],
    ["sentence", "Sentenças"],
    ["word", "Palavras"],
  ] satisfies Array<[ViewLevel, string]>)("names the %s level", (level, expected) => {
    expect(pathLabel(level)).toBe(expected);
  });
});
