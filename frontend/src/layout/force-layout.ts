import type { ViewEdge, ViewLevel, ViewNode } from "../data/schemas";

export interface LayoutItem {
  id: string;
  label: string;
  topic?: string;
  text?: string;
}

const COLORS: Record<ViewLevel, string> = {
  community: "#4D7CFF",
  comment: "#D500F9",
  sentence: "#69FF47",
  word: "#00E5FF",
};

function initialRadius(level: ViewLevel): number {
  if (level === "community") {
    return 28;
  }
  if (level === "comment") {
    return 20;
  }
  if (level === "sentence") {
    return 16;
  }
  return 12;
}

export function layoutNodes(items: LayoutItem[], edges: ViewEdge[], level: ViewLevel, parentId?: string): ViewNode[] {
  const total = Math.max(items.length, 1);
  const nodes = items.map((item, index) => {
    const angle = (Math.PI * 2 * index) / total;
    return {
      id: item.id,
      label: item.label,
      level,
      x: Math.cos(angle) * 140 + (index % 2 === 0 ? -10 : 10),
      y: Math.sin(angle) * 140 + (index % 3 === 0 ? -10 : 10),
      radius: initialRadius(level),
      color: COLORS[level],
      value: initialRadius(level),
      parentId,
      text: item.text,
      topic: item.topic,
    } satisfies ViewNode;
  });

  if (nodes.length < 2 || edges.length === 0) {
    return nodes;
  }

  const positions = new Map(nodes.map((node) => [node.id, { x: node.x, y: node.y }]));
  const desiredDistance = 90;

  for (let iteration = 0; iteration < 50; iteration += 1) {
    const delta = new Map<string, { x: number; y: number }>();
    for (const node of nodes) {
      delta.set(node.id, { x: 0, y: 0 });
    }

    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const left = positions.get(nodes[i].id)!;
        const right = positions.get(nodes[j].id)!;
        const dx = left.x - right.x;
        const dy = left.y - right.y;
        const dist = Math.max(20, Math.hypot(dx, dy));
        const force = 2200 / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const leftDelta = delta.get(nodes[i].id)!;
        const rightDelta = delta.get(nodes[j].id)!;
        leftDelta.x += fx;
        leftDelta.y += fy;
        rightDelta.x -= fx;
        rightDelta.y -= fy;
      }
    }

    for (const edge of edges) {
      const left = positions.get(edge.source);
      const right = positions.get(edge.target);
      if (!left || !right) {
        continue;
      }
      const dx = right.x - left.x;
      const dy = right.y - left.y;
      const dist = Math.max(10, Math.hypot(dx, dy));
      const spring = ((dist - desiredDistance) * (edge.weight || 1)) / 160;
      const fx = (dx / dist) * spring;
      const fy = (dy / dist) * spring;
      const leftDelta = delta.get(edge.source)!;
      const rightDelta = delta.get(edge.target)!;
      leftDelta.x += fx;
      leftDelta.y += fy;
      rightDelta.x -= fx;
      rightDelta.y -= fy;
    }

    for (const node of nodes) {
      const move = delta.get(node.id)!;
      const pos = positions.get(node.id)!;
      pos.x = Math.max(-260, Math.min(260, pos.x + move.x * 0.02));
      pos.y = Math.max(-220, Math.min(220, pos.y + move.y * 0.02));
    }
  }

  return nodes.map((node) => {
    const pos = positions.get(node.id)!;
    return {
      ...node,
      x: pos.x,
      y: pos.y,
    };
  });
}
