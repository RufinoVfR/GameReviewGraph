import type { CameraState } from "./camera";
import { worldToScreen } from "./camera";
import type { ViewLevel, ViewSnapshot } from "../data/schemas";
import { isNodeVisible, labelOpacity, nodeOpacity } from "../model/scene";

export interface RenderOptions {
  highlightId?: string;
  brushedIds?: Set<string>;
  /** Screen-space ambient particles drawn behind the graph. */
  particles?: Array<{ x: number; y: number }>;
  showParticles?: boolean;
  /**
   * When a single level is explicitly filtered, keep its nodes fully visible at
   * any zoom so the whole level can be inspected when zoomed out.
   */
  forceVisible?: boolean;
}

const BRUSH_COLOR = "#FF1744";
const HIGHLIGHT_COLOR = "#FFD740";

/**
 * Trace the silhouette for a node, using a distinct primitive per graph level:
 * hexagon for communities, circle for comments, square for sentences and a
 * diamond for words — mirroring the legend in the design.
 */
function traceShape(context: CanvasRenderingContext2D, level: ViewLevel, x: number, y: number, radius: number) {
  context.beginPath();
  if (level === "comment") {
    context.arc(x, y, radius, 0, Math.PI * 2);
    return;
  }
  if (level === "sentence") {
    context.rect(x - radius, y - radius, radius * 2, radius * 2);
    return;
  }
  if (level === "word") {
    context.moveTo(x, y - radius);
    context.lineTo(x + radius, y);
    context.lineTo(x, y + radius);
    context.lineTo(x - radius, y);
    context.closePath();
    return;
  }
  // community → hexagon
  for (let corner = 0; corner < 6; corner += 1) {
    const angle = Math.PI / 6 + corner * (Math.PI / 3);
    const px = x + Math.cos(angle) * radius;
    const py = y + Math.sin(angle) * radius;
    if (corner === 0) {
      context.moveTo(px, py);
    } else {
      context.lineTo(px, py);
    }
  }
  context.closePath();
}

/** Draw the parallax grid and ambient particles behind the world transform. */
function drawBackdrop(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  camera: CameraState,
  options: RenderOptions,
) {
  if (camera.scale >= 0.3) {
    const spacing = 40 * camera.scale;
    if (spacing >= 6) {
      const gridAlpha = Math.max(0, Math.min(1, camera.scale < 0.4 ? (camera.scale - 0.3) / 0.1 : 1)) * 0.9;
      context.save();
      context.strokeStyle = "#0F1319";
      context.globalAlpha = gridAlpha;
      context.lineWidth = 1;
      context.beginPath();
      let offsetX = (width / 2 + camera.x * camera.scale * 0.6) % spacing;
      if (offsetX < 0) offsetX += spacing;
      let offsetY = (height / 2 + camera.y * camera.scale * 0.6) % spacing;
      if (offsetY < 0) offsetY += spacing;
      for (let x = offsetX; x < width; x += spacing) {
        context.moveTo(Math.round(x) + 0.5, 0);
        context.lineTo(Math.round(x) + 0.5, height);
      }
      for (let y = offsetY; y < height; y += spacing) {
        context.moveTo(0, Math.round(y) + 0.5);
        context.lineTo(width, Math.round(y) + 0.5);
      }
      context.stroke();
      context.restore();
    }
  }

  if (options.showParticles && options.particles) {
    context.save();
    context.fillStyle = "#1E2535";
    options.particles.forEach((particle) => {
      context.fillRect(particle.x, particle.y, 1, 1);
    });
    context.restore();
  }
}

export function renderSnapshot(
  context: CanvasRenderingContext2D,
  snapshot: ViewSnapshot,
  camera: CameraState,
  options: RenderOptions = {},
) {
  const { canvas } = context;
  const width = canvas.clientWidth || canvas.width;
  const height = canvas.clientHeight || canvas.height;

  context.clearRect(0, 0, width, height);
  context.fillStyle = "#080B10";
  context.fillRect(0, 0, width, height);

  drawBackdrop(context, width, height, camera, options);

  context.save();
  context.translate(width / 2, height / 2);
  context.scale(camera.scale, camera.scale);
  context.translate(camera.x, camera.y);

  const nodesById = new Map(snapshot.nodes.map((node) => [node.id, node]));
  const scale = camera.scale;
  const force = options.forceVisible === true;
  const visibleFor = (level: ViewLevel) => force || isNodeVisible(level, scale);
  const opacityFor = (level: ViewLevel) => (force ? 1 : nodeOpacity(level, scale));
  const labelAlphaFor = (level: ViewLevel) => (force ? 1 : labelOpacity(level, scale));

  context.strokeStyle = "rgba(30, 37, 53, 0.85)";
  snapshot.edges.forEach((edge) => {
    const source = nodesById.get(edge.source);
    const target = nodesById.get(edge.target);
    if (!source || !target) {
      return;
    }

    const visibility = Math.min(opacityFor(source.level), opacityFor(target.level));
    if (visibility <= 0) {
      return;
    }
    // An edge belongs to the focus only when both of its endpoints are brushed,
    // so selecting a node lights up its connections rather than every edge that
    // happens to touch a neighbour.
    const hasBrush = Boolean(options.brushedIds && options.brushedIds.size > 0);
    const brushed = !hasBrush || (options.brushedIds!.has(source.id) && options.brushedIds!.has(target.id));
    context.globalAlpha = (brushed ? 0.95 : 0.12) * visibility;
    context.lineWidth = Math.max(0.75, Math.min(4, edge.weight * 2.1)) * (brushed && hasBrush ? 1.6 : 1) / camera.scale;
    if (edge.dashed) {
      context.setLineDash([4 / camera.scale, 3 / camera.scale]);
      context.strokeStyle = brushed && hasBrush ? "rgba(255, 215, 64, 0.95)" : "rgba(255, 215, 64, 0.5)";
    } else {
      context.setLineDash([]);
      context.strokeStyle = brushed && hasBrush ? source.color : "rgba(30, 37, 53, 0.85)";
    }
    context.beginPath();
    context.moveTo(source.x, source.y);
    context.lineTo(target.x, target.y);
    context.stroke();
  });
  context.setLineDash([]);
  context.globalAlpha = 1;

  snapshot.nodes.forEach((node) => {
    if (!visibleFor(node.level)) {
      return;
    }
    const isBrush = options.brushedIds && options.brushedIds.size > 0 && options.brushedIds.has(node.id);
    const dimmed = options.brushedIds && options.brushedIds.size > 0 && !isBrush;
    const highlighted = options.highlightId === node.id;
    const radius = highlighted ? node.radius + 4 : node.radius;

    context.save();
    context.globalAlpha = (dimmed ? 0.24 : 1) * opacityFor(node.level);
    const fill = highlighted ? HIGHLIGHT_COLOR : isBrush ? BRUSH_COLOR : node.color;
    if (highlighted || isBrush) {
      context.shadowColor = fill;
      context.shadowBlur = (highlighted ? 18 : 14) * camera.scale;
    }
    context.fillStyle = fill;
    traceShape(context, node.level, node.x, node.y, radius);
    context.fill();
    context.restore();

    context.save();
    context.globalAlpha = (dimmed ? 0.24 : 1) * opacityFor(node.level);
    context.strokeStyle = highlighted ? HIGHLIGHT_COLOR : "rgba(255,255,255,0.18)";
    context.lineWidth = (highlighted ? 1.5 : 2) / camera.scale;
    traceShape(context, node.level, node.x, node.y, radius + (highlighted ? 5 : 2));
    context.stroke();
    context.restore();
  });
  context.globalAlpha = 1;

  context.restore();

  context.fillStyle = "#D6E4FF";
  context.textAlign = "center";
  context.textBaseline = "middle";

  const labelCandidates = snapshot.nodes
    .filter((node) => visibleFor(node.level))
    .map((node) => {
      const screen = worldToScreen(camera, node.x, node.y, width, height);
      const label = node.label.length > 18 ? `${node.label.slice(0, 18)}…` : node.label;
      const alpha = labelAlphaFor(node.level);
      const highlighted = options.highlightId === node.id;
      const brushed = !options.brushedIds || options.brushedIds.size === 0 || options.brushedIds.has(node.id);
      const priority = (highlighted ? 1000 : 0) + (brushed ? 200 : -200) + (node.level === "community" ? 120 : node.level === "comment" ? 80 : node.level === "sentence" ? 40 : 10) + node.value;
      return { node, screen, label, alpha, highlighted, brushed, priority };
    })
    .filter((item) => item.alpha > 0)
    .sort((left, right) => right.priority - left.priority);

  const placedLabels: Array<{ x: number; y: number; width: number; height: number }> = [];

  labelCandidates.forEach((item) => {
    const { node, screen, label, alpha, highlighted, brushed } = item;
    const labelY = screen.y + node.radius + 14;
    const fontSize =
      node.level === "community"
        ? scale >= 1.2
          ? 14
          : 13
        : node.level === "comment"
          ? scale >= 1.5
            ? 13
            : 12
          : node.level === "sentence"
            ? scale >= 1.8
              ? 12
              : 11
            : 10;
    const textAlpha = (brushed ? 1 : 0.24) * alpha;
    context.font = `${fontSize}px Rajdhani, sans-serif`;
    const metrics = context.measureText(label);
    const boxWidth = Math.min(metrics.width + 16, 220);
    const boxHeight = Math.max(16, fontSize + 8);
    const boxX = screen.x - boxWidth / 2;
    const boxY = labelY - boxHeight / 2;

    const overlaps = placedLabels.some((rect) => {
      return !(
        boxX + boxWidth < rect.x ||
        boxX > rect.x + rect.width ||
        boxY + boxHeight < rect.y ||
        boxY > rect.y + rect.height
      );
    });

    if (overlaps && !highlighted && textAlpha < 0.75) {
      return;
    }

    placedLabels.push({ x: boxX, y: boxY, width: boxWidth, height: boxHeight });
    context.globalAlpha = textAlpha;
    context.fillStyle = highlighted ? "rgba(21, 26, 38, 0.96)" : "rgba(8, 11, 16, 0.84)";
    context.fillRect(boxX, boxY, boxWidth, boxHeight);
    context.strokeStyle = node.color;
    context.lineWidth = 1;
    context.strokeRect(boxX, boxY, boxWidth, boxHeight);

    context.fillStyle = node.color;
    context.globalAlpha = textAlpha * 0.42;
    context.fillText(label, screen.x + 1, labelY + 1);
    context.globalAlpha = textAlpha;
    context.fillStyle = "#EAF2FF";
    context.strokeStyle = "rgba(8, 11, 16, 0.9)";
    context.lineWidth = 3;
    context.strokeText(label, screen.x, labelY);
    context.fillText(label, screen.x, labelY);
    context.globalAlpha = 1;
  });
}
