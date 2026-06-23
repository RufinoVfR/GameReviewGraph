import type { BundleData, ViewEdge, ViewLevel, ViewNode, ViewSnapshot } from "../data/schemas";

interface PositionedRecord {
  id: string;
  label: string;
  topic?: string;
  text?: string;
  x: number;
  y: number;
  radius: number;
  value: number;
  level: ViewLevel;
  parentId?: string;
}

const COLORS: Record<ViewLevel, string> = {
  community: "#4D7CFF",
  comment: "#D500F9",
  sentence: "#69FF47",
  word: "#00E5FF",
};

const LEVEL_THRESHOLDS: Record<ViewLevel, number> = {
  community: 0.45,
  comment: 0.82,
  sentence: 1.22,
  word: 1.85,
};

const LEVEL_ZOOMS: Record<ViewLevel, number> = {
  community: 0.7,
  comment: 1.05,
  sentence: 1.55,
  word: 2.15,
};

function hashText(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) | 0;
  }
  return Math.abs(hash);
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function baseRadius(level: ViewLevel) {
  if (level === "community") {
    return 28;
  }
  if (level === "comment") {
    return 20;
  }
  if (level === "sentence") {
    return 16;
  }
  return 11;
}

function itemTopic(topic?: string, fallback?: string) {
  return topic ?? fallback;
}

function placeRing(count: number, centerX: number, centerY: number, radius: number, phaseSeed: number) {
  const positions: Array<{ x: number; y: number }> = [];
  const total = Math.max(count, 1);
  if (total === 1) {
    positions.push({ x: centerX, y: centerY });
    return positions;
  }
  const phase = (phaseSeed % 360) * (Math.PI / 180);
  const golden = Math.PI * (3 - Math.sqrt(5));

  for (let index = 0; index < total; index += 1) {
    const angle = phase + index * golden;
    const ring = radius + Math.floor(index / 8) * radius * 0.28;
    positions.push({
      x: centerX + Math.cos(angle) * ring,
      y: centerY + Math.sin(angle) * ring,
    });
  }

  return positions;
}

function addNode(nodes: PositionedRecord[], node: PositionedRecord) {
  nodes.push(node);
}

function addEdge(edges: ViewEdge[], source: string, target: string, weight: number, dashed = false) {
  if (!source || !target || source === target || weight <= 0) {
    return;
  }

  edges.push({ source, target, weight, dashed });
}

function buildWordEdges(data: BundleData) {
  const edges = new Map<string, number>();
  for (const sentence of data.sentences) {
    const wordIds = data.containment.sentenceToWords[sentence.id] ?? sentence.wordIds;
    for (let left = 0; left < wordIds.length; left += 1) {
      for (let right = left + 1; right < wordIds.length; right += 1) {
        const leftId = wordIds[left];
        const rightId = wordIds[right];
        const leftIndex = data.wordGraph.index[leftId];
        const rightIndex = data.wordGraph.index[rightId];
        const weight =
          leftIndex !== undefined && rightIndex !== undefined
            ? data.wordGraph.matrix[leftIndex]?.[rightIndex] ?? 0
            : 0;
        if (weight <= 0) {
          continue;
        }
        const key = leftId < rightId ? `${leftId}::${rightId}` : `${rightId}::${leftId}`;
        edges.set(key, Math.max(edges.get(key) ?? 0, weight));
      }
    }
  }
  return edges;
}

function buildSentenceAnchors(data: BundleData) {
  const sentenceAnchors = new Map<string, { x: number; y: number }>();
  const wordAnchors = new Map<string, { x: number; y: number }>();
  const wordParents = new Map<string, string>();
  const commentBySentence = new Map<string, string>();
  const commentById = new Map(data.comments.map((comment) => [comment.id, comment]));
  const wordById = new Map(data.words.map((word) => [word.id, word]));
  const nodes: PositionedRecord[] = [];
  const edges: ViewEdge[] = [];
  const communities = [...data.communities].sort((left, right) => right.size - left.size || left.label.localeCompare(right.label));

  const communityRadius = Math.max(220, communities.length * 70);
  const communityPositions = placeRing(communities.length, 0, 0, communityRadius, 19);

  communities.forEach((community, communityIndex) => {
    const communityPos = communityPositions[communityIndex] ?? { x: 0, y: 0 };
    const communityNode = {
      id: community.id,
      label: community.label,
      topic: community.topic,
      x: communityPos.x,
      y: communityPos.y,
      radius: baseRadius("community"),
      value: community.size,
      level: "community" as const,
    };
    addNode(nodes, communityNode);

    const comments = data.comments
      .filter((comment) => community.commentIds.includes(comment.id))
      .sort((left, right) => left.label.localeCompare(right.label));
    const commentPositions = placeRing(comments.length, communityNode.x, communityNode.y, 112, hashText(community.id));

    comments.forEach((comment, commentIndex) => {
      const commentPos = commentPositions[commentIndex] ?? { x: communityNode.x, y: communityNode.y };
      const commentNode = {
        id: comment.id,
        label: comment.label,
        topic: comment.topic,
        text: comment.text,
        x: commentPos.x,
        y: commentPos.y,
        radius: baseRadius("comment"),
        value: comment.sentenceIds.length,
        level: "comment" as const,
        parentId: community.id,
      };
      addNode(nodes, commentNode);
      addEdge(edges, community.id, comment.id, 1, true);

      const sentences = data.sentences
        .filter((sentence) => comment.sentenceIds.includes(sentence.id))
        .sort((left, right) => left.label.localeCompare(right.label));
      const sentencePositions = placeRing(sentences.length, commentNode.x, commentNode.y, 58, hashText(comment.id));

      sentences.forEach((sentence, sentenceIndex) => {
        commentBySentence.set(sentence.id, comment.id);
        const sentencePos = sentencePositions[sentenceIndex] ?? { x: commentNode.x, y: commentNode.y };
        const sentenceNode = {
          id: sentence.id,
          label: sentence.label,
          topic: itemTopic(comment.topic, community.topic),
          x: sentencePos.x,
          y: sentencePos.y,
          radius: baseRadius("sentence"),
          value: sentence.wordIds.length,
          level: "sentence" as const,
          parentId: comment.id,
        };
        addNode(nodes, sentenceNode);
        addEdge(edges, comment.id, sentence.id, 1, true);
        sentenceAnchors.set(sentence.id, { x: sentenceNode.x, y: sentenceNode.y });

        const wordIds = data.containment.sentenceToWords[sentence.id] ?? sentence.wordIds;
        const wordPositions = placeRing(wordIds.length, sentenceNode.x, sentenceNode.y, 24, hashText(sentence.id));

        wordIds.forEach((wordId, wordIndex) => {
          const word = wordById.get(wordId);
          if (!word) {
            return;
          }

          const existingAnchor = wordAnchors.get(word.id);
          const currentPos = wordPositions[wordIndex] ?? { x: sentenceNode.x, y: sentenceNode.y };
          if (!wordParents.has(word.id)) {
            wordParents.set(word.id, sentence.id);
          }
          const blendedPos = existingAnchor
            ? {
                x: (existingAnchor.x + currentPos.x) / 2,
                y: (existingAnchor.y + currentPos.y) / 2,
              }
            : currentPos;

          wordAnchors.set(word.id, blendedPos);
        });
      });
    });
  });

  const wordEdges = buildWordEdges(data);
  for (const [edgeKey, weight] of wordEdges.entries()) {
    const [leftId, rightId] = edgeKey.split("::");
    addEdge(edges, leftId, rightId, weight);
  }

  for (const sentence of data.sentences) {
    const anchor = sentenceAnchors.get(sentence.id);
    if (!anchor) {
      continue;
    }

    const wordIds = data.containment.sentenceToWords[sentence.id] ?? sentence.wordIds;
    const wordPositions = placeRing(wordIds.length, anchor.x, anchor.y, 24, hashText(sentence.id));

    wordIds.forEach((wordId, wordIndex) => {
      const word = wordById.get(wordId);
      if (!word) {
        return;
      }

      const currentPos = wordPositions[wordIndex] ?? { x: anchor.x, y: anchor.y };
      const existing = wordAnchors.get(word.id);
      if (existing) {
        wordAnchors.set(word.id, {
          x: (existing.x + currentPos.x) / 2,
          y: (existing.y + currentPos.y) / 2,
        });
      } else {
        wordAnchors.set(word.id, currentPos);
      }
    });
  }

  const wordNodes: PositionedRecord[] = [];
  data.words.forEach((word) => {
    const anchor = wordAnchors.get(word.id);
    if (!anchor) {
      return;
    }

    const parentSentenceId = wordParents.get(word.id);
    const parentCommentId = parentSentenceId ? commentBySentence.get(parentSentenceId) : undefined;
    const parentComment = parentCommentId ? commentById.get(parentCommentId) : undefined;
    addNode(wordNodes, {
      id: word.id,
      label: word.label,
      topic: parentComment?.topic,
      x: anchor.x,
      y: anchor.y,
      radius: baseRadius("word"),
      value: word.frequency,
      level: "word",
      parentId: parentSentenceId,
    });
  });

  wordNodes.forEach((node) => addNode(nodes, node));

  const commentPairs = new Map<string, number>();
  for (const community of communities) {
    const comments = data.comments
      .filter((comment) => community.commentIds.includes(comment.id))
      .sort((left, right) => left.label.localeCompare(right.label));
    for (let index = 0; index < comments.length - 1; index += 1) {
      const left = comments[index].id;
      const right = comments[index + 1].id;
      commentPairs.set(`${left}::${right}`, 1);
    }
  }
  for (const [edgeKey, weight] of commentPairs.entries()) {
    const [left, right] = edgeKey.split("::");
    addEdge(edges, left, right, weight, true);
  }

  for (const sentence of data.sentences) {
    const neighbors = data.sentenceNeighbors[sentence.id] ?? [];
    neighbors.forEach((neighbor) => addEdge(edges, sentence.id, neighbor.id, neighbor.weight));
  }

  const containmentEdges = new Set<string>();
  for (const community of communities) {
    community.commentIds.forEach((commentId) => {
      containmentEdges.add(`${community.id}::${commentId}`);
    });
  }
  for (const [commentId, sentenceIds] of Object.entries(data.containment.commentToSentences)) {
    sentenceIds.forEach((sentenceId) => {
      containmentEdges.add(`${commentId}::${sentenceId}`);
    });
  }
  for (const [sentenceId, wordIds] of Object.entries(data.containment.sentenceToWords)) {
    wordIds.forEach((wordId) => {
      containmentEdges.add(`${sentenceId}::${wordId}`);
    });
  }
  containmentEdges.forEach((edgeKey) => {
    const [left, right] = edgeKey.split("::");
    addEdge(edges, left, right, 1, true);
  });

  const sceneNodes = nodes.map((node) => ({
    id: node.id,
    label: node.label,
    level: node.level,
    x: node.x,
    y: node.y,
    radius: node.radius,
    color: COLORS[node.level],
    value: node.value,
    text: node.text,
    topic: node.topic,
    parentId: node.parentId,
  })) satisfies ViewNode[];

  return {
    level: "community" as const,
    title: "Cena integrada",
    nodes: sceneNodes,
    edges,
  };
}

export function buildScene(data: BundleData): ViewSnapshot {
  return buildSentenceAnchors(data);
}

export function buildTrail(data: BundleData | null, selectedId?: string) {
  const root = [{ id: "root", label: "Comunidades", level: "community" as ViewLevel }];
  if (!data || !selectedId) {
    return root;
  }

  const community =
    data.communities.find((item) => item.id === selectedId) ??
    data.communities.find((item) => item.commentIds.some((commentId) => commentId === selectedId)) ??
    data.communities.find((item) =>
      data.comments.some((comment) => item.commentIds.includes(comment.id) && comment.sentenceIds.includes(selectedId)),
    ) ??
    data.communities.find((item) =>
      data.comments.some((comment) =>
        item.commentIds.includes(comment.id) &&
        comment.sentenceIds.some((sentenceId) => data.containment.sentenceToWords[sentenceId]?.includes(selectedId)),
      ),
    );

  const comment =
    data.comments.find((item) => item.id === selectedId) ??
    data.comments.find((item) => item.sentenceIds.includes(selectedId)) ??
    data.comments.find((item) =>
      item.sentenceIds.some((sentenceId) => data.containment.sentenceToWords[sentenceId]?.includes(selectedId)),
    );

  const sentence =
    data.sentences.find((item) => item.id === selectedId) ??
    data.sentences.find((item) => data.containment.sentenceToWords[item.id]?.includes(selectedId));

  const trail = [...root];
  if (community) {
    trail.push({ id: community.id, label: community.label, level: "community" });
  }
  if (comment) {
    trail.push({ id: comment.id, label: comment.label, level: "comment" });
  }
  if (sentence) {
    trail.push({ id: sentence.id, label: sentence.label, level: "sentence" });
  }
  const word = data.words.find((item) => item.id === selectedId);
  if (word) {
    trail.push({ id: word.id, label: word.label, level: "word" });
  }

  const unique = new Map<string, { id: string; label: string; level: ViewLevel }>();
  trail.forEach((item) => unique.set(item.id, item));
  return [...unique.values()];
}

export function levelVisibilityThreshold(level: ViewLevel) {
  return LEVEL_THRESHOLDS[level];
}

export function levelFocusScale(level: ViewLevel) {
  return LEVEL_ZOOMS[level];
}

export function visibleLevelForScale(scale: number): ViewLevel {
  if (scale >= LEVEL_THRESHOLDS.word) {
    return "word";
  }
  if (scale >= LEVEL_THRESHOLDS.sentence) {
    return "sentence";
  }
  if (scale >= LEVEL_THRESHOLDS.comment) {
    return "comment";
  }
  return "community";
}

export function isNodeVisible(level: ViewLevel, scale: number) {
  return scale >= levelVisibilityThreshold(level);
}

export function nodeOpacity(level: ViewLevel, scale: number) {
  const threshold = levelVisibilityThreshold(level);
  return clamp((scale - threshold) / 0.42, 0, 1);
}

export function labelOpacity(level: ViewLevel, scale: number) {
  const threshold = levelVisibilityThreshold(level);
  return clamp((scale - threshold - 0.12) / 0.32, 0, 1);
}
