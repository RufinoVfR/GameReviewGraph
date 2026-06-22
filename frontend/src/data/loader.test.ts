import { afterEach, describe, expect, it, vi } from "vitest";

import { mockData } from "./mock-data";
import type { BundleData } from "./schemas";
import { isUsableBundle, loadData } from "./loader";

const { source: _source, ...usableBundle } = mockData;

/** Map every bundle endpoint to a usable payload drawn from the fixture. */
const fullResponses: Record<string, unknown> = {
  "meta.json": mockData.meta,
  "communities.json": mockData.communities,
  "comments.json": mockData.comments,
  "sentences.json": mockData.sentences,
  "words.json": mockData.words,
  "word_graph.json": mockData.wordGraph,
  "sentence_neighbors.json": mockData.sentenceNeighbors,
  "containment.json": mockData.containment,
  "inverted_index.json": mockData.invertedIndex,
  "text_store.json": mockData.textStore,
};

/**
 * Replace global fetch with a stub that serves `responses` by path and fails
 * any path listed in `failPaths` with a non-ok response.
 */
function stubFetch(responses: Record<string, unknown>, failPaths: string[] = []) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const path = url.replace("/bundle/", "");
      if (failPaths.includes(path)) {
        return { ok: false, json: async () => ({}) } as Response;
      }
      return { ok: true, json: async () => responses[path] } as Response;
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("isUsableBundle (schema validation)", () => {
  it("accepts a bundle with every level populated", () => {
    expect(isUsableBundle(usableBundle)).toBe(true);
  });

  it.each([
    ["communities", { communities: [] }],
    ["comments", { comments: [] }],
    ["sentences", { sentences: [] }],
    ["words", { words: [] }],
    ["wordGraph nodes", { wordGraph: { nodes: [], index: {}, matrix: [] } }],
  ] satisfies Array<[string, Partial<Omit<BundleData, "source">>]>)(
    "rejects a bundle with empty %s",
    (_label, override) => {
      expect(isUsableBundle({ ...usableBundle, ...override })).toBe(false);
    },
  );
});

describe("loadData", () => {
  it("returns the assembled bundle when every artifact is present and usable", async () => {
    stubFetch(fullResponses);

    const result = await loadData();

    expect(result.source).toBe("bundle");
    expect(result.communities).toHaveLength(mockData.communities.length);
    expect(result.comments[0].id).toBe("comment-1");
  });

  it("falls back to mock data when a required artifact fails to load", async () => {
    // Mock-only startup path: a missing bundle file aborts the real load.
    stubFetch(fullResponses, ["communities.json"]);

    const result = await loadData();

    expect(result.source).toBe("mock");
    expect(result).toBe(mockData);
  });

  it("falls back to mock data when the bundle loads but is not usable", async () => {
    stubFetch({ ...fullResponses, "communities.json": [] });

    const result = await loadData();

    expect(result.source).toBe("mock");
  });
});
