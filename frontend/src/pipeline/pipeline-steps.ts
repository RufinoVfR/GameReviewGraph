import type { BundleData, ReportData, ViewEdge, ViewSnapshot } from "../data/schemas";
import { layoutNodes } from "../layout/force-layout";
import { buildScene } from "../model/scene";

/** A single before/after panel of a filter step. */
export type PipelinePane =
  | { kind: "graph"; snapshot: ViewSnapshot; caption: string }
  | { kind: "text"; caption: string; items: Array<{ title: string; body: string }> }
  | { kind: "chips"; caption: string; items: Array<{ title: string; chips: string[] }> }
  | { kind: "tree"; caption: string; items: Array<{ title: string; groups: Array<{ label: string; leaves: string[] }> }> }
  | { kind: "list"; caption: string; items: Array<{ title: string; meta: string; chips: string[] }> }
  | { kind: "note"; caption: string; text: string };

export interface FilterStep {
  id: number;
  name: string;
  title: string;
  description: string;
  before: PipelinePane;
  after: PipelinePane;
}

const SAMPLE = 3;

function wordLabel(data: BundleData, id: string): string {
  return data.words.find((word) => word.id === id)?.label ?? id.replace(/^word-/, "");
}

/** Build a single-level graph snapshot from an adjacency matrix bundle. */
function wordGraphSnapshot(data: BundleData, withEdges: boolean): ViewSnapshot {
  const { nodes, matrix } = data.wordGraph;
  const items = nodes.map((id) => ({ id, label: wordLabel(data, id) }));
  const edges: ViewEdge[] = [];
  if (withEdges) {
    for (let i = 0; i < nodes.length; i += 1) {
      const row = matrix[i] ?? [];
      for (let j = i + 1; j < nodes.length; j += 1) {
        if ((row[j] ?? 0) > 0) {
          edges.push({ source: nodes[i], target: nodes[j], weight: row[j] });
        }
      }
    }
  }
  return { level: "word", title: "Grafo de palavras", nodes: layoutNodes(items, edges, "word"), edges };
}

/** Build a sentence-level graph from the sentence neighbor adjacency bundle. */
function sentenceGraphSnapshot(data: BundleData, withEdges: boolean): ViewSnapshot {
  const items = data.sentences.map((sentence) => ({ id: sentence.id, label: sentence.label }));
  const edges: ViewEdge[] = [];
  if (withEdges) {
    const seen = new Set<string>();
    for (const [source, neighbors] of Object.entries(data.sentenceNeighbors)) {
      for (const neighbor of neighbors) {
        const key = [source, neighbor.id].sort().join("|");
        if (!seen.has(key)) {
          seen.add(key);
          edges.push({ source, target: neighbor.id, weight: neighbor.weight });
        }
      }
    }
  }
  return { level: "sentence", title: "Grafo de frases", nodes: layoutNodes(items, edges, "sentence"), edges };
}

/** Comment nodes with no grouping — the input to community detection. */
function commentNodesSnapshot(data: BundleData): ViewSnapshot {
  const items = data.comments.map((comment) => ({ id: comment.id, label: comment.label, topic: comment.topic }));
  return { level: "comment", title: "Comentários", nodes: layoutNodes(items, [], "comment"), edges: [] };
}

/** Communities as nodes, sized by comment count — the detection result. */
function communitySnapshot(data: BundleData): ViewSnapshot {
  const items = data.communities.map((community) => ({
    id: community.id,
    label: community.label,
    topic: community.topic,
  }));
  const nodes = layoutNodes(items, [], "community").map((node) => {
    const record = data.communities.find((community) => community.id === node.id);
    const size = record?.size ?? 1;
    return { ...node, radius: 18 + Math.min(28, size), value: size };
  });
  return { level: "community", title: "Comunidades", nodes, edges: [] };
}

export function buildFilterSteps(data: BundleData, report: ReportData | null): FilterStep[] {
  const sampleComments = data.comments.slice(0, SAMPLE);
  const detectionMethod = report?.methods.find((method) => method.id === 4) ?? report?.methods[0] ?? null;

  return [
    {
      id: 1,
      name: "preprocessing",
      title: "Pré-processamento",
      description: "Texto cru → tokens normalizados (lowercase, sem pontuação, sem stopwords, radical RSLP).",
      before: {
        kind: "text",
        caption: "Comentários crus",
        items: sampleComments.map((comment) => ({ title: comment.label, body: comment.text })),
      },
      after: {
        kind: "chips",
        caption: "Tokens normalizados",
        items: sampleComments.map((comment) => ({
          title: comment.label,
          chips: comment.sentenceIds
            .flatMap((sentenceId) => data.containment.sentenceToWords[sentenceId] ?? [])
            .map((wordId) => wordLabel(data, wordId)),
        })),
      },
    },
    {
      id: 2,
      name: "tree",
      title: "Árvore N-ária",
      description: "Tokens planos → árvore Dataset → Comentário → Frase → Palavra.",
      before: {
        kind: "chips",
        caption: "Tokens planos do comentário",
        items: sampleComments.map((comment) => ({
          title: comment.label,
          chips: comment.sentenceIds
            .flatMap((sentenceId) => data.containment.sentenceToWords[sentenceId] ?? [])
            .map((wordId) => wordLabel(data, wordId)),
        })),
      },
      after: {
        kind: "tree",
        caption: "Hierarquia comentário → frases → palavras",
        items: sampleComments.map((comment) => ({
          title: comment.label,
          groups: comment.sentenceIds.map((sentenceId) => ({
            label: data.sentences.find((sentence) => sentence.id === sentenceId)?.label ?? sentenceId,
            leaves: (data.containment.sentenceToWords[sentenceId] ?? []).map((wordId) => wordLabel(data, wordId)),
          })),
        })),
      },
    },
    {
      id: 3,
      name: "word_graph",
      title: "Grafo de palavras",
      description: "Palavras isoladas → grafo de co-ocorrência com peso posicional.",
      before: { kind: "graph", caption: "Palavras (sem arestas)", snapshot: wordGraphSnapshot(data, false) },
      after: { kind: "graph", caption: "Co-ocorrência ponderada", snapshot: wordGraphSnapshot(data, true) },
    },
    {
      id: 4,
      name: "sentence_graph",
      title: "Grafo de frases",
      description: "Frases isoladas → grafo de frases derivado das relações entre palavras.",
      before: { kind: "graph", caption: "Frases (sem arestas)", snapshot: sentenceGraphSnapshot(data, false) },
      after: { kind: "graph", caption: "Relações entre frases", snapshot: sentenceGraphSnapshot(data, true) },
    },
    {
      id: 5,
      name: "comment_graph",
      title: "Grafo de comentários",
      description: "Comentários isolados → grafo de comentários derivado das relações entre frases.",
      before: { kind: "graph", caption: "Comentários (sem arestas)", snapshot: commentNodesSnapshot(data) },
      after: {
        kind: "note",
        caption: "Relações entre comentários",
        text: "O grafo de comentários completo (c_↔c_) ainda não está no bundle. Em breve: emitir comment_graph como lista de nós/arestas.",
      },
    },
    {
      id: 6,
      name: "final_graph",
      title: "Grafo unificado",
      description: "Três grafos separados → grafo unificado com os 3 níveis + arestas hierárquicas.",
      before: { kind: "graph", caption: "Grafo de palavras (um dos níveis)", snapshot: wordGraphSnapshot(data, true) },
      after: { kind: "graph", caption: "3 níveis + hierárquicas", snapshot: buildScene(data) },
    },
    {
      id: 7,
      name: "community_detection",
      title: "Detecção de comunidades",
      description: "Comentários sem grupo → partição em comunidades (método 4, subgrafo c_↔c_).",
      before: { kind: "graph", caption: "200 comentários sem grupo", snapshot: commentNodesSnapshot(data) },
      after: { kind: "graph", caption: `${data.communities.length} comunidades`, snapshot: communitySnapshot(data) },
    },
    {
      id: 8,
      name: "metrics",
      title: "Métricas",
      description: "Comunidades → centralidade ponderada, termos centrais e modularidade Q.",
      before: {
        kind: "list",
        caption: "Comunidades (sem métricas)",
        items: data.communities.map((community) => ({
          title: community.label,
          meta: `${community.size} comentários`,
          chips: [],
        })),
      },
      after: {
        kind: "list",
        caption: "Comunidades anotadas com termos centrais",
        items: (detectionMethod?.communities ?? []).map((community) => ({
          title: community.topic ?? `Comunidade ${community.id}`,
          meta: `${community.comments.length} comentários`,
          chips: community.centralTerms,
        })),
      },
    },
    {
      id: 9,
      name: "analysis",
      title: "Relatório final",
      description: "Métricas → relatório estruturado comparando os 5 métodos de detecção.",
      before: {
        kind: "note",
        caption: "Métricas por método",
        text: "Cada um dos 5 métodos é avaliado por modularidade Q e equilíbrio da distribuição de comentários.",
      },
      after: {
        kind: "list",
        caption: "Matriz comparativa (veja a aba Relatório)",
        items: (report?.comparison ?? []).map((row) => ({
          title: `Método ${row.id}`,
          meta: `Q ${row.modularityQ.toFixed(3)} · ${row.nCommunities} comunidades`,
          chips: [],
        })),
      },
    },
  ];
}
