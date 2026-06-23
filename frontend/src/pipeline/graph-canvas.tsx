import { useEffect, useRef } from "react";
import { createCamera, screenToWorld } from "../render/camera";
import type { CameraState } from "../render/camera";
import { renderSnapshot } from "../render/renderer";
import type { ViewSnapshot } from "../data/schemas";

/** Fit the camera so the whole snapshot is visible and centered. */
function fitCamera(snapshot: ViewSnapshot, width: number, height: number): CameraState {
  const camera = createCamera();
  if (snapshot.nodes.length === 0) {
    return camera;
  }
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const node of snapshot.nodes) {
    minX = Math.min(minX, node.x);
    maxX = Math.max(maxX, node.x);
    minY = Math.min(minY, node.y);
    maxY = Math.max(maxY, node.y);
  }
  const spanX = Math.max(maxX - minX, 1);
  const spanY = Math.max(maxY - minY, 1);
  camera.x = -(minX + maxX) / 2;
  camera.y = -(minY + maxY) / 2;
  camera.scale = Math.min(2.2, Math.max(0.2, (Math.min(width, height) * 0.8) / Math.max(spanX, spanY)));
  return camera;
}

interface GraphCanvasProps {
  snapshot: ViewSnapshot;
}

/**
 * Self-contained graph canvas with pan and zoom, decoupled from the main
 * explorer. Renders any ViewSnapshot (positioned nodes + edges) via the shared
 * renderer, so each pipeline filter can show a full graph before/after.
 */
export function GraphCanvas({ snapshot }: GraphCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const cameraRef = useRef<CameraState>(createCamera());
  const dragRef = useRef<{ down: boolean; x: number; y: number }>({ down: false, x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    let width = 0;
    let height = 0;

    const draw = () => {
      renderSnapshot(context, snapshot, cameraRef.current, {
        forceVisible: true,
        showParticles: false,
        particles: [],
        brushedIds: new Set(),
      });
    };

    const resize = () => {
      const ratio = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.max(1, Math.floor(width * ratio));
      canvas.height = Math.max(1, Math.floor(height * ratio));
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      cameraRef.current = fitCamera(snapshot, width, height);
      draw();
    };

    const onDown = (event: MouseEvent) => {
      dragRef.current = { down: true, x: event.clientX, y: event.clientY };
      canvas.style.cursor = "grabbing";
    };
    const onMove = (event: MouseEvent) => {
      if (!dragRef.current.down) {
        return;
      }
      cameraRef.current.x += (event.clientX - dragRef.current.x) / cameraRef.current.scale;
      cameraRef.current.y += (event.clientY - dragRef.current.y) / cameraRef.current.scale;
      dragRef.current.x = event.clientX;
      dragRef.current.y = event.clientY;
      draw();
    };
    const onUp = () => {
      dragRef.current.down = false;
      canvas.style.cursor = "grab";
    };
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const px = event.clientX - rect.left;
      const py = event.clientY - rect.top;
      const before = screenToWorld(cameraRef.current, px, py, width, height);
      const factor = event.deltaY > 0 ? 0.9 : 1.1;
      cameraRef.current.scale = Math.min(3, Math.max(0.12, cameraRef.current.scale * factor));
      const after = screenToWorld(cameraRef.current, px, py, width, height);
      cameraRef.current.x += before.x - after.x;
      cameraRef.current.y += before.y - after.y;
      draw();
    };

    resize();
    window.addEventListener("resize", resize);
    canvas.addEventListener("mousedown", onDown);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousedown", onDown);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, [snapshot]);

  return <canvas ref={canvasRef} className="pipelineCanvas" />;
}
