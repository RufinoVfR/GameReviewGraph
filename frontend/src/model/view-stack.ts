import type { ViewLevel } from "../data/schemas";

export interface ViewFrame {
  level: ViewLevel;
  title: string;
  parentId?: string;
  selectedId?: string;
}

export function createRootFrame(): ViewFrame {
  return {
    level: "community",
    title: "Comunidades",
  };
}

export function nextFrameTitle(level: ViewLevel, label: string): string {
  if (level === "comment") {
    return `Comentários · ${label}`;
  }
  if (level === "sentence") {
    return `Sentenças · ${label}`;
  }
  if (level === "word") {
    return `Palavras · ${label}`;
  }
  return label;
}

export function pathLabel(level: ViewLevel): string {
  if (level === "community") {
    return "Comunidades";
  }
  if (level === "comment") {
    return "Comentários";
  }
  if (level === "sentence") {
    return "Sentenças";
  }
  return "Palavras";
}
