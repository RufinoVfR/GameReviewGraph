import type { BundleData, ViewLevel, ViewSnapshot } from "../data/schemas";
import { buildScene } from "./scene";

export function buildView(data: BundleData, _level?: ViewLevel, _parentId?: string): ViewSnapshot {
  return buildScene(data);
}
