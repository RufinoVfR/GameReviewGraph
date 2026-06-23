import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { loadData, loadReport } from "./data/loader";
import type {
  BundleData,
  CommentRecord,
  CommunityRecord,
  ReportData,
  SentenceRecord,
  ViewLevel,
  ViewNode,
  ViewSnapshot,
  WordRecord,
} from "./data/schemas";
import { ReportView } from "./report/report-view";
import { createCamera, screenToWorld } from "./render/camera";
import type { CameraState } from "./render/camera";
import { renderSnapshot } from "./render/renderer";
import { pickNode } from "./interaction/picker";
import { buildScene, buildTrail, isNodeVisible } from "./model/scene";

const LEVEL_ACCENTS: Record<string, string> = {
  community: "#4D7CFF",
  comment: "#D500F9",
  sentence: "#69FF47",
  word: "#00E5FF",
};

function buildAncestorMaps(nodes: ViewNode[]) {
  const parents = new Map<string, string | undefined>();
  const children = new Map<string, string[]>();

  nodes.forEach((node) => {
    parents.set(node.id, node.parentId);
    if (node.parentId) {
      const current = children.get(node.parentId) ?? [];
      current.push(node.id);
      children.set(node.parentId, current);
    }
  });

  return { parents, children };
}

function expandVisibleIds(nodes: ViewNode[], selectedId: string | undefined, search: string, topicFilter: string) {
  const visible = new Set<string>();
  const { parents, children } = buildAncestorMaps(nodes);
  const needle = search.trim().toLowerCase();
  const topicNeedle = topicFilter.trim().toLowerCase();

  const matches = nodes.filter((node) => {
    const matchesSearch =
      !needle ||
      node.label.toLowerCase().includes(needle) ||
      node.topic?.toLowerCase().includes(needle) ||
      node.text?.toLowerCase().includes(needle);
    const matchesTopic = topicNeedle === "all" || !node.topic || node.topic.toLowerCase() === topicNeedle;
    return matchesSearch && matchesTopic;
  });

  const stack = [...matches.map((node) => node.id), ...(selectedId ? [selectedId] : [])];
  while (stack.length > 0) {
    const current = stack.pop();
    if (!current || visible.has(current)) {
      continue;
    }
    visible.add(current);
    const parent = parents.get(current);
    if (parent) {
      stack.push(parent);
    }
    children.get(current)?.forEach((child) => stack.push(child));
  }

  if (visible.size === 0) {
    nodes.forEach((node) => visible.add(node.id));
  }

  return visible;
}

function focusScaleForNode(node: ViewNode) {
  return focusScaleForLevel(node.level);
}

function focusScaleForLevel(level: ViewLevel) {
  if (level === "community") {
    return 0.95;
  }
  if (level === "comment") {
    return 1.35;
  }
  if (level === "sentence") {
    return 2.0;
  }
  return 2.25;
}

function computeGroupBounds(nodes: ViewNode[]) {
  if (nodes.length === 0) {
    return null;
  }

  let minX = nodes[0].x;
  let maxX = nodes[0].x;
  let minY = nodes[0].y;
  let maxY = nodes[0].y;

  for (const node of nodes) {
    minX = Math.min(minX, node.x);
    maxX = Math.max(maxX, node.x);
    minY = Math.min(minY, node.y);
    maxY = Math.max(maxY, node.y);
  }

  return {
    x: (minX + maxX) / 2,
    y: (minY + maxY) / 2,
    span: Math.max(maxX - minX, maxY - minY),
  };
}

type CameraTarget = { x: number; y: number; scale: number };

function makeCameraTarget(nodes: ViewNode[], scale: number): CameraTarget {
  const bounds = computeGroupBounds(nodes);
  if (!bounds) {
    return { x: 0, y: 0, scale };
  }

  return {
    x: -bounds.x,
    y: -bounds.y,
    scale: Math.min(2.4, Math.max(0.45, scale)),
  };
}

function easeOutCubic(value: number) {
  return 1 - Math.pow(1 - value, 3);
}

export function App() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const dragRef = useRef<{ pointerDown: boolean; dragging: boolean; x: number; y: number }>({
    pointerDown: false,
    dragging: false,
    x: 0,
    y: 0,
  });
  const cameraRef = useRef<CameraState>(createCamera());
  const particlesRef = useRef<Array<{ x: number; y: number }>>([]);
  const [data, setData] = useState<BundleData | null>(null);
  const [report, setReport] = useState<ReportData | null>(null);
  const [showReport, setShowReport] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadProgress, setLoadProgress] = useState(0);
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [search, setSearch] = useState("");
  const [brushTerm, setBrushTerm] = useState<string | undefined>();
  const [showParticles, setShowParticles] = useState(true);
  const [zoomLayers, setZoomLayers] = useState(true);
  const [levelFilter, setLevelFilter] = useState("all");
  const [topicFilter, setTopicFilter] = useState("all");
  const [hoveredId, setHoveredId] = useState<string | undefined>();
  const [hoverPoint, setHoverPoint] = useState<{ x: number; y: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewportVersion, setViewportVersion] = useState(0);
  const animationRef = useRef<number | null>(null);
  const targetRef = useRef<CameraState | null>(null);

  // Keep a level fully visible regardless of zoom when it is explicitly
  // filtered, or whenever zoom-based layering is turned off entirely.
  const forceVisible = levelFilter !== "all" || !zoomLayers;

  useEffect(() => {
    let mounted = true;
    loadData()
      .then((loaded) => {
        if (!mounted) {
          return;
        }
        setData(loaded);
        setLoading(false);
      })
      .catch((loadError) => {
        if (!mounted) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Falha ao carregar dados");
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    loadReport().then((loaded) => {
      if (mounted) {
        setReport(loaded);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const startedAt = performance.now();
    const duration = 1700;
    let frame = 0;
    const tick = () => {
      const elapsed = Math.min(1, (performance.now() - startedAt) / duration);
      setLoadProgress(Math.round(easeOutCubic(elapsed) * 100));
      if (elapsed < 1) {
        frame = window.requestAnimationFrame(tick);
      }
    };
    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, []);

  const scene = useMemo<ViewSnapshot>(() => {
    if (!data) {
      return {
        level: "community",
        title: "Carregando",
        nodes: [],
        edges: [],
      };
    }
    return buildScene(data);
  }, [data]);

  const visibleIds = useMemo(
    () => expandVisibleIds(scene.nodes, selectedId, search, topicFilter),
    [scene.nodes, selectedId, search, topicFilter],
  );

  const snapshot = useMemo<ViewSnapshot>(() => {
    const nodes = scene.nodes.filter((node) => visibleIds.has(node.id));
    const levelFilteredNodes = levelFilter === "all" ? nodes : nodes.filter((node) => node.level === levelFilter);
    return {
      ...scene,
      nodes: levelFilteredNodes,
      edges: scene.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)),
    };
  }, [scene, visibleIds, levelFilter]);

  const degreeById = useMemo(() => {
    const levelById = new Map(scene.nodes.map((node) => [node.id, node.level]));
    const degrees = new Map<string, number>();
    scene.edges.forEach((edge) => {
      // Count similarity links between same-level siblings, not containment edges.
      if (levelById.get(edge.source) !== levelById.get(edge.target)) {
        return;
      }
      degrees.set(edge.source, (degrees.get(edge.source) ?? 0) + 1);
      degrees.set(edge.target, (degrees.get(edge.target) ?? 0) + 1);
    });
    return degrees;
  }, [scene.nodes, scene.edges]);

  const wordLabels = useMemo(() => {
    const labels = new Set<string>();
    data?.words.forEach((word) => labels.add(word.label.toLowerCase()));
    return labels;
  }, [data]);

  const termBrushedIds = useMemo(() => {
    const ids = new Set<string>();
    const term = brushTerm?.trim().toLowerCase();
    if (!data || !term) {
      return ids;
    }
    data.words.forEach((word) => {
      if (word.label.toLowerCase() === term) {
        ids.add(word.id);
      }
    });
    const entry = data.invertedIndex[term];
    entry?.comments.forEach((id) => ids.add(id));
    entry?.sentences.forEach((id) => ids.add(id));
    data.comments.forEach((comment) => {
      if (comment.text.toLowerCase().includes(term)) {
        ids.add(comment.id);
      }
    });
    return ids;
  }, [data, brushTerm]);

  const adjacency = useMemo(() => {
    const map = new Map<string, Set<string>>();
    scene.edges.forEach((edge) => {
      (map.get(edge.source) ?? map.set(edge.source, new Set()).get(edge.source)!).add(edge.target);
      (map.get(edge.target) ?? map.set(edge.target, new Set()).get(edge.target)!).add(edge.source);
    });
    return map;
  }, [scene.edges]);

  const brushedIds = useMemo(() => {
    if (termBrushedIds.size > 0) {
      return termBrushedIds;
    }
    if (!selectedId) {
      return new Set<string>();
    }
    // Highlight the selected node together with everything it connects to.
    const ids = new Set<string>([selectedId]);
    adjacency.get(selectedId)?.forEach((id) => ids.add(id));
    return ids;
  }, [selectedId, termBrushedIds, adjacency]);
  const trail = useMemo(() => buildTrail(data, selectedId), [data, selectedId]);

  const selectedNode = snapshot.nodes.find((node) => node.id === selectedId) ?? scene.nodes.find((node) => node.id === selectedId);
  const hoveredNode = snapshot.nodes.find((node) => node.id === hoveredId);
  const inspectedNode = hoveredNode ?? selectedNode;
  const selectedLevel = inspectedNode?.level ?? (selectedId ? selectedId.split("-")[0] : undefined);
  const panelAccent = selectedLevel ? LEVEL_ACCENTS[selectedLevel] ?? "#4D7CFF" : "#4D7CFF";
  const tooltipText = hoveredNode ? `${hoveredNode.label} · ${hoveredNode.level}` : undefined;
  const panel = useMemo(() => {
    if (!inspectedNode) {
      return null;
    }
    const tokenize = (text: string) =>
      text.split(/(\s+)/).map((part) => {
        const clean = part.replace(/[.,!?"“”():;]/g, "").trim().toLowerCase();
        return { text: part, isKey: clean.length > 0 && wordLabels.has(clean), term: clean };
      });
    // Resolve the record from the inspected node itself (which follows hover),
    // so the record type always matches the node's level — never selectedId.
    const level = inspectedNode.level;
    if (level === "community") {
      const record = data?.communities.find((item) => item.id === inspectedNode.id) as CommunityRecord | undefined;
      const size = record?.size ?? inspectedNode.value;
      const topic = inspectedNode.topic ?? inspectedNode.label;
      return {
        eyebrow: `COMUNIDADE · ${inspectedNode.label}`,
        title: topic,
        tokens: [{ text: `Agrupamento de ${size} comentários em torno do tópico “${topic}”.`, isKey: false, term: "" }],
        meta: [
          { k: "Tópico", v: topic },
          { k: "Comentários", v: size },
          { k: "Nível", v: "comunidade" },
        ],
        hint: "DUPLO-CLIQUE PARA EXPLORAR A COMUNIDADE",
      };
    }
    if (level === "comment") {
      const record = data?.comments.find((item) => item.id === inspectedNode.id) as CommentRecord | undefined;
      const community = data?.communities.find((item) => item.commentIds.includes(inspectedNode.id));
      const degree = degreeById.get(inspectedNode.id) ?? 0;
      return {
        eyebrow: `COMENTÁRIO · ${inspectedNode.label}`,
        title: inspectedNode.topic ?? "comentário",
        tokens: tokenize(record?.text ?? inspectedNode.text ?? inspectedNode.label),
        meta: [
          { k: "Tópico", v: inspectedNode.topic ?? "—" },
          { k: "Comunidade", v: community?.label ?? "—" },
          { k: "Grau", v: degree },
          { k: "Sentenças", v: record?.sentenceIds.length ?? 0 },
        ],
        hint: degree === 0 ? "SEM CONEXÕES NO THRESHOLD ATUAL" : undefined,
      };
    }
    if (level === "sentence") {
      const record = data?.sentences.find((item) => item.id === inspectedNode.id) as SentenceRecord | undefined;
      const text = data?.textStore[inspectedNode.id] ?? inspectedNode.text ?? inspectedNode.label;
      return {
        eyebrow: `SENTENÇA · ${inspectedNode.label}`,
        title: "sentença",
        tokens: tokenize(text),
        meta: [
          { k: "Nível", v: "sentença" },
          { k: "Palavras", v: record?.wordIds.length ?? inspectedNode.value },
        ],
        hint: undefined as string | undefined,
      };
    }
    const record = data?.words.find((item) => item.id === inspectedNode.id) as WordRecord | undefined;
    return {
      eyebrow: "PALAVRA",
      title: inspectedNode.label,
      tokens: [
        { text: "Elemento léxico atômico. Selecionar destaca todos os comentários que contêm esta palavra.", isKey: false, term: "" },
      ],
      meta: [
        { k: "Nível", v: "palavra" },
        { k: "Termo", v: inspectedNode.label },
        { k: "Frequência", v: record?.frequency ?? inspectedNode.value },
      ],
      hint: "NÓ SELECIONADO PROPAGA BRUSHING CROSS-NÍVEL",
    };
  }, [inspectedNode, data, degreeById, wordLabels]);
  const applyLevelFilter = (nextLevel: string) => {
    setLevelFilter(nextLevel);
    const levelNodes =
      nextLevel === "all" ? scene.nodes : scene.nodes.filter((node) => node.level === nextLevel);
    const target = makeCameraTarget(levelNodes, nextLevel === "all" ? 0.7 : focusScaleForLevel(nextLevel as ViewLevel));
    animateCamera(target);
    setViewportVersion((value) => value + 1);
  };
  const applyTopicFilter = (nextTopic: string) => {
    setTopicFilter(nextTopic);
    const topicNeedle = nextTopic.trim().toLowerCase();
    const topicNodes = scene.nodes.filter((node) => {
      const matchesTopic = topicNeedle === "all" || !node.topic || node.topic.toLowerCase() === topicNeedle;
      const matchesLevel = levelFilter === "all" || node.level === levelFilter;
      return matchesTopic && matchesLevel;
    });
    if (topicNodes.length > 0) {
      animateCamera(makeCameraTarget(topicNodes, cameraRef.current.scale));
      setViewportVersion((value) => value + 1);
    }
  };

  function focusNodeById(nodeId: string) {
    const node = scene.nodes.find((item) => item.id === nodeId);
    if (!node) {
      return;
    }
    setSelectedId(nodeId);
    setHoveredId(undefined);
    animateCamera(makeCameraTarget([node], focusScaleForNode(node)));
  }

  function stopCameraAnimation() {
    if (animationRef.current !== null) {
      window.cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    targetRef.current = null;
  }

  function animateCamera(target: CameraTarget, duration = 280) {
    stopCameraAnimation();
    const start = { ...cameraRef.current };
    const begunAt = performance.now();
    targetRef.current = { ...target };

    const step = (now: number) => {
      const elapsed = Math.min(1, (now - begunAt) / duration);
      const eased = easeOutCubic(elapsed);
      cameraRef.current.x = start.x + (target.x - start.x) * eased;
      cameraRef.current.y = start.y + (target.y - start.y) * eased;
      cameraRef.current.scale = start.scale + (target.scale - start.scale) * eased;
      setViewportVersion((value) => value + 1);
      if (elapsed < 1 && targetRef.current) {
        animationRef.current = window.requestAnimationFrame(step);
        return;
      }
      animationRef.current = null;
      targetRef.current = null;
    };

    animationRef.current = window.requestAnimationFrame(step);
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const draw = () => {
      renderSnapshot(context, snapshot, cameraRef.current, {
        highlightId: hoveredId ?? selectedId,
        brushedIds,
        particles: particlesRef.current,
        showParticles,
        forceVisible,
      });
    };

    const resize = () => {
      const ratio = window.devicePixelRatio || 1;
      const { width, height } = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(width * ratio));
      canvas.height = Math.max(1, Math.floor(height * ratio));
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      particlesRef.current = Array.from({ length: 70 }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
      }));
      draw();
    };

    const onMove = (event: MouseEvent) => {
      if (!canvasRef.current) {
        return;
      }

      const bounds = canvasRef.current.getBoundingClientRect();
      const pointerX = event.clientX - bounds.left;
      const pointerY = event.clientY - bounds.top;
      setHoverPoint({ x: pointerX, y: pointerY });

      if (dragRef.current.pointerDown) {
        stopCameraAnimation();
        const dx = pointerX - dragRef.current.x;
        const dy = pointerY - dragRef.current.y;
        if (!dragRef.current.dragging && Math.hypot(dx, dy) > 4) {
          dragRef.current.dragging = true;
        }

        if (dragRef.current.dragging) {
          cameraRef.current.x += dx / cameraRef.current.scale;
          cameraRef.current.y += dy / cameraRef.current.scale;
          dragRef.current.x = pointerX;
          dragRef.current.y = pointerY;
          draw();
        }
        return;
      }

      const visibleNodes = snapshot.nodes.filter((node) => forceVisible || isNodeVisible(node.level, cameraRef.current.scale));
      const node = pickNode(visibleNodes, cameraRef.current, pointerX, pointerY, bounds.width, bounds.height);
      setHoveredId(node?.id);
      canvas.style.cursor = node ? "pointer" : "grab";
      draw();
    };

    const onDown = (event: MouseEvent) => {
      if (!canvasRef.current) {
        return;
      }

      stopCameraAnimation();
      const bounds = canvasRef.current.getBoundingClientRect();
      dragRef.current = {
        pointerDown: true,
        dragging: false,
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      };
      canvas.style.cursor = "grabbing";
    };

    const onDoubleClick = (event: MouseEvent) => {
      if (!canvasRef.current) {
        return;
      }

      stopCameraAnimation();
      const bounds = canvasRef.current.getBoundingClientRect();
      const pointerX = event.clientX - bounds.left;
      const pointerY = event.clientY - bounds.top;
      const visibleNodes = snapshot.nodes.filter((node) => forceVisible || isNodeVisible(node.level, cameraRef.current.scale));
      const node = pickNode(visibleNodes, cameraRef.current, pointerX, pointerY, bounds.width, bounds.height);
      if (!node) {
        return;
      }

      setSelectedId(node.id);
      animateCamera(makeCameraTarget([node], focusScaleForNode(node)));
      draw();
    };

    const onUp = (event: MouseEvent) => {
      if (!canvasRef.current) {
        return;
      }

      const bounds = canvasRef.current.getBoundingClientRect();
      const pointerX = event.clientX - bounds.left;
      const pointerY = event.clientY - bounds.top;
      const wasDragging = dragRef.current.dragging;
      dragRef.current.pointerDown = false;
      dragRef.current.dragging = false;
      canvas.style.cursor = "grab";

      if (wasDragging) {
        return;
      }

      const visibleNodes = snapshot.nodes.filter((node) => forceVisible || isNodeVisible(node.level, cameraRef.current.scale));
      const node = pickNode(visibleNodes, cameraRef.current, pointerX, pointerY, bounds.width, bounds.height);
      if (!node) {
        setSelectedId(undefined);
        return;
      }

      setSelectedId(node.id);
      animateCamera(makeCameraTarget([node], focusScaleForNode(node)));
      draw();
    };

    const onWheel = (event: WheelEvent) => {
      if (!canvasRef.current) {
        return;
      }

      stopCameraAnimation();
      event.preventDefault();
      const bounds = canvasRef.current.getBoundingClientRect();
      const pointerX = event.clientX - bounds.left;
      const pointerY = event.clientY - bounds.top;
      const before = screenToWorld(cameraRef.current, pointerX, pointerY, bounds.width, bounds.height);
      const delta = Math.sign(event.deltaY);
      const factor = delta > 0 ? 0.92 : 1.08;
      cameraRef.current.scale = Math.min(2.4, Math.max(0.45, cameraRef.current.scale * factor));
      const after = screenToWorld(cameraRef.current, pointerX, pointerY, bounds.width, bounds.height);
      cameraRef.current.x += before.x - after.x;
      cameraRef.current.y += before.y - after.y;
      setViewportVersion((value) => value + 1);
      draw();
    };

    const onLeave = () => {
      setHoveredId(undefined);
      setHoverPoint(null);
      canvas.style.cursor = "grab";
      draw();
    };

    resize();
    window.addEventListener("resize", resize);
    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mousedown", onDown);
    canvas.addEventListener("dblclick", onDoubleClick);
    canvas.addEventListener("mouseleave", onLeave);
    window.addEventListener("mouseup", onUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      stopCameraAnimation();
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mousedown", onDown);
      canvas.removeEventListener("dblclick", onDoubleClick);
      canvas.removeEventListener("mouseleave", onLeave);
      window.removeEventListener("mouseup", onUp);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, [brushedIds, hoveredId, scene, selectedId, snapshot, showParticles, forceVisible]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    renderSnapshot(context, snapshot, cameraRef.current, {
      highlightId: hoveredId ?? selectedId,
      brushedIds,
      particles: particlesRef.current,
      showParticles,
      forceVisible,
    });
  }, [snapshot, hoveredId, selectedId, brushedIds, viewportVersion, showParticles, forceVisible]);

  return (
    <div className="shell">
      <canvas ref={canvasRef} className="graphCanvas" />

      <header className="topbar">
        <div className="brandMark">
          <span className="brandGlyph">◈</span>
          <div className="brand">GAMEREVIEWGRAPH</div>
        </div>

        <div className="searchBox">
          <span className="searchGlyph">⌕</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                setBrushTerm(search.trim().toLowerCase() || undefined);
              }
            }}
            placeholder="BUSCAR PALAVRA / COMENTÁRIO"
          />
        </div>

        <button
          className="reportButton"
          type="button"
          title="Relatório final — comparação de métodos"
          onClick={() => setShowReport(true)}
        >
          ▤ Relatório
        </button>

        <button
          className="iconButton"
          type="button"
          title="Partículas ambiente"
          data-active={showParticles}
          onClick={() => setShowParticles((value) => !value)}
        >
          ⚙
        </button>
      </header>

      <div className="breadcrumbBar">
        {trail.map((frame, index) => {
          const isActive = index === trail.length - 1;
          return (
            <button
              key={`${frame.level}-${frame.id}-${index}`}
              type="button"
              className="crumb"
              data-active={isActive}
              onClick={() => {
                if (frame.id === "root") {
                  setSelectedId(undefined);
                  setHoveredId(undefined);
                  animateCamera(makeCameraTarget(scene.nodes.filter((node) => node.level === "community"), 0.7));
                  return;
                }

                focusNodeById(frame.id);
              }}
            >
              <span className="crumbChevron">{index === 0 ? "▸" : "›"}</span>
              <span className="crumbLabel">{index === 0 ? "dataset" : frame.label}</span>
            </button>
          );
        })}
      </div>

      <aside className="sidePane" style={{ borderLeftColor: panelAccent }}>
        {panel ? (
          <div className="panelBody">
            <div className="panelHead">
              <span className="panelEyebrow">{panel.eyebrow}</span>
              <span
                className="panelClose"
                role="button"
                tabIndex={0}
                onClick={() => {
                  setSelectedId(undefined);
                  setHoveredId(undefined);
                }}
              >
                ✕
              </span>
            </div>
            <div className="panelTitle" style={{ color: panelAccent }}>
              {panel.title}
            </div>
            <div className="panelTokens">
              {panel.tokens.map((token, index) =>
                token.isKey ? (
                  <span
                    key={index}
                    className="tokenKey"
                    data-active={brushTerm === token.term}
                    onClick={() => setBrushTerm(brushTerm === token.term ? undefined : token.term)}
                  >
                    {token.text}
                  </span>
                ) : (
                  <span key={index}>{token.text}</span>
                ),
              )}
            </div>
            <div className="panelMeta">
              {panel.meta.map((row) => (
                <Fragment key={row.k}>
                  <span className="metaKey">{row.k}</span>
                  <span className="metaVal">{row.v}</span>
                </Fragment>
              ))}
            </div>
            {panel.hint ? <div className="panelHint">{panel.hint}</div> : null}
          </div>
        ) : (
          <div className="emptyPanel">
            <div className="emptyIcon">◇</div>
            <div className="emptyTitle">SELECIONE UM NÓ</div>
            <div className="emptyHint">clique em qualquer nó para inspecionar</div>
          </div>
        )}
      </aside>

      <footer className="footerBar">
        <div className="filtersBlock">
          <span className="sectionLabel">Filtros</span>
          <div className="filterPill">
            <span>Nível</span>
            <select value={levelFilter} onChange={(event) => applyLevelFilter(event.target.value)}>
              <option value="all">todos</option>
              <option value="community">comunidades</option>
              <option value="comment">comentários</option>
              <option value="sentence">frases</option>
              <option value="word">palavras</option>
            </select>
          </div>
          <div className="filterPill">
            <span>Tópico</span>
            <select value={topicFilter} onChange={(event) => applyTopicFilter(event.target.value)}>
              <option value="all">todos</option>
              {data?.meta.topics.map((topic) => (
                <option key={topic} value={topic}>
                  {topic}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="layerToggle"
            data-active={zoomLayers}
            title="Mostrar ou ocultar as camadas conforme o nível de zoom"
            onClick={() => setZoomLayers((value) => !value)}
          >
            Camadas por zoom: {zoomLayers ? "ON" : "OFF"}
          </button>
        </div>

        <div className="footerInfo">
          {data?.communities.length ?? 0} comunidades · {snapshot.nodes.length} nós · zoom {cameraRef.current.scale.toFixed(2)}x
        </div>

        <button
          className="backButton"
          type="button"
          data-active={Boolean(selectedId)}
          onClick={() => {
            setSelectedId(undefined);
            setHoveredId(undefined);
            setBrushTerm(undefined);
            cameraRef.current = createCamera();
            setViewportVersion((value) => value + 1);
          }}
        >
          ◀ Voltar
        </button>
      </footer>

      <div className="legend">
        <span>
          <i className="legendGlyph">⬡</i> comunidade
        </span>
        <span>
          <i className="legendGlyph">●</i> comentário
        </span>
        <span>
          <i className="legendGlyph">■</i> frase
        </span>
        <span>
          <i className="legendGlyph">◆</i> palavra
        </span>
      </div>

      <div className="hintBlock">
        SCROLL &middot; zoom | ARRASTAR &middot; pan<br />
        CLIQUE &middot; inspecionar | DUPLO-CLIQUE &middot; explorar
      </div>

      {hoverPoint && tooltipText ? (
        <div className="tooltip" style={{ left: hoverPoint.x, top: hoverPoint.y }}>
          {tooltipText}
        </div>
      ) : null}

      {loading || loadProgress < 100 ? (
        <div className="loadingOverlay">
          <div className="loadingHeader">
            <span className="loadingMark">◈</span>
            <span className="loadingBrand">GAMEREVIEWGRAPH</span>
          </div>
          <div className="loadingText">Carregando comunidades</div>
          <div className="loadingBarRow">
            <div className="loadingBar">
              <div className="loadingFill" style={{ width: `${loadProgress}%` }} />
            </div>
            <span className="loadingPct">{loadProgress} %</span>
          </div>
          <div className="loadingCounts">
            {data?.meta.counts.words ?? 0} palavras · {data?.meta.counts.sentences ?? 0} sentenças
            <br />
            {data?.meta.counts.comments ?? 0} comentários
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="errorToast">
          <span>Falha ao carregar dados</span>
          <button type="button" onClick={() => window.location.reload()}>
            Recarregar
          </button>
        </div>
      ) : null}

      {showReport && report ? <ReportView report={report} onClose={() => setShowReport(false)} /> : null}
    </div>
  );
}
