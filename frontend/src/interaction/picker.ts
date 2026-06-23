import type { CameraState } from "../render/camera";
import { screenToWorld } from "../render/camera";
import type { ViewNode } from "../data/schemas";

export function pickNode(
  nodes: ViewNode[],
  camera: CameraState,
  pointerX: number,
  pointerY: number,
  width: number,
  height: number,
) {
  const world = screenToWorld(camera, pointerX, pointerY, width, height);

  return nodes.find((node) => {
    const dx = world.x - node.x;
    const dy = world.y - node.y;
    return Math.hypot(dx, dy) <= node.radius + 6;
  });
}
