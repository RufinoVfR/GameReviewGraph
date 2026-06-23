export type ViewLevel = "community" | "comment" | "sentence" | "word";

export interface MetaData {
  version: string;
  generatedAt: string;
  counts: {
    communities: number;
    comments: number;
    sentences: number;
    words: number;
  };
  topics: string[];
}

export interface CommunityRecord {
  id: string;
  label: string;
  topic: string;
  size: number;
  commentIds: string[];
}

export interface SentenceRecord {
  id: string;
  label: string;
  wordIds: string[];
}

export interface CommentRecord {
  id: string;
  label: string;
  text: string;
  sentenceIds: string[];
  topic: string;
}

export interface WordRecord {
  id: string;
  label: string;
  frequency: number;
}

export interface InvertedIndexEntry {
  comments: string[];
  sentences: string[];
}

export interface BundleData {
  source: "mock" | "bundle";
  meta: MetaData;
  communities: CommunityRecord[];
  comments: CommentRecord[];
  sentences: SentenceRecord[];
  words: WordRecord[];
  wordGraph: {
    nodes: string[];
    index: Record<string, number>;
    matrix: number[][];
  };
  sentenceNeighbors: Record<string, Array<{ id: string; weight: number }>>;
  containment: {
    commentToSentences: Record<string, string[]>;
    sentenceToWords: Record<string, string[]>;
  };
  invertedIndex: Record<string, InvertedIndexEntry>;
  textStore: Record<string, string>;
}

export interface ReportCommunity {
  id: number;
  topic: string | null;
  centralTerms: string[];
  comments: string[];
}

export interface ReportMethodStats {
  nCommunities: number;
  sizeMin: number;
  sizeMax: number;
  singletons: number;
  nComments: number;
}

export interface ReportMethod {
  id: number;
  label: string;
  modularityQ: number;
  stats: ReportMethodStats;
  communities: ReportCommunity[];
}

export interface ReportComparisonRow {
  id: number;
  label: string;
  modularityQ: number;
  nCommunities: number;
  sizeMin: number;
  sizeMax: number;
  singletons: number;
}

export interface ReportData {
  source: "mock" | "bundle";
  k: number;
  nComments: number;
  methods: ReportMethod[];
  comparison: ReportComparisonRow[];
}

export interface ViewNode {
  id: string;
  label: string;
  level: ViewLevel;
  x: number;
  y: number;
  radius: number;
  color: string;
  value: number;
  text?: string;
  topic?: string;
  parentId?: string;
}

export interface ViewEdge {
  source: string;
  target: string;
  weight: number;
  dashed?: boolean;
}

export interface ViewSnapshot {
  level: ViewLevel;
  title: string;
  parentId?: string;
  nodes: ViewNode[];
  edges: ViewEdge[];
}
