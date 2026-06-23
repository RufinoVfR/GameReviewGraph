export interface CameraState {
  x: number;
  y: number;
  scale: number;
}

export function createCamera(): CameraState {
  return { x: 0, y: 0, scale: 0.7 };
}

export function worldToScreen(camera: CameraState, x: number, y: number, width: number, height: number) {
  return {
    x: width / 2 + (x + camera.x) * camera.scale,
    y: height / 2 + (y + camera.y) * camera.scale,
  };
}

export function screenToWorld(camera: CameraState, x: number, y: number, width: number, height: number) {
  return {
    x: (x - width / 2) / camera.scale - camera.x,
    y: (y - height / 2) / camera.scale - camera.y,
  };
}
