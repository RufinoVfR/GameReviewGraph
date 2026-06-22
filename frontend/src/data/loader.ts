import { mockData } from "./mock-data";
import type { BundleData, CommentRecord, CommunityRecord, MetaData, SentenceRecord, WordRecord } from "./schemas";

const BUNDLE_BASE = "/bundle";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BUNDLE_BASE}/${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return (await response.json()) as T;
}

export function isUsableBundle(bundle: Omit<BundleData, "source">): boolean {
  return (
    bundle.communities.length > 0 &&
    bundle.comments.length > 0 &&
    bundle.sentences.length > 0 &&
    bundle.words.length > 0 &&
    bundle.wordGraph.nodes.length > 0
  );
}

export async function loadData(): Promise<BundleData> {
  try {
    const [meta, communities, comments, sentences, words, wordGraph, sentenceNeighbors, containment, invertedIndex, textStore] = await Promise.all([
      fetchJson<MetaData>("meta.json"),
      fetchJson<CommunityRecord[]>("communities.json"),
      fetchJson<CommentRecord[]>("comments.json"),
      fetchJson<SentenceRecord[]>("sentences.json"),
      fetchJson<WordRecord[]>("words.json"),
      fetchJson<BundleData["wordGraph"]>("word_graph.json").catch(() => ({ nodes: [], index: {}, matrix: [] })),
      fetchJson<Record<string, Array<{ id: string; weight: number }>>>("sentence_neighbors.json").catch(() => ({})),
      fetchJson<BundleData["containment"]>("containment.json"),
      fetchJson<Record<string, BundleData["invertedIndex"][string]>>("inverted_index.json"),
      fetchJson<Record<string, string>>("text_store.json"),
    ]);

    const bundle: BundleData = {
      source: "bundle",
      meta,
      communities,
      comments,
      sentences,
      words,
      wordGraph,
      sentenceNeighbors,
      containment,
      invertedIndex,
      textStore,
    };

    return isUsableBundle(bundle) ? bundle : mockData;
  } catch {
    return mockData;
  }
}
