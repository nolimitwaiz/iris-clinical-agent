/**
 * ClinicalGraph — Full-screen clinical knowledge graph visualization.
 *
 * Force-directed layout showing relationships between drugs, labs, vitals,
 * symptoms, and conditions. Built from patient data + action packets.
 *
 * Node shapes:
 *   - Drug: filled circle with accent border
 *   - Lab: diamond
 *   - Vital: rounded square
 *   - Symptom: small muted circle
 *   - Condition: large outlined circle
 *
 * Interactions: pan, pinch-zoom, tap node for detail card, back button.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { useTheme, glassStyle } from "../../context/ThemeContext";
import { useIris } from "../../context/IrisContext";
import { useIsMobile } from "../../hooks/useMediaQuery";
import {
  buildClinicalGraph,
  type ClinicalNode,
  type ClinicalEdge,
  type ClinicalGraphData,
} from "../../utils/clinicalGraph";

interface Props {
  onClose: () => void;
}

// Force sim node with position + velocity
interface SimNode extends ClinicalNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  expandProgress: number;
}

// ── Edge visuals by type ───────────────────────────────────────

function edgeColor(type: ClinicalEdge["type"], blocked: boolean, alpha: number): string {
  if (blocked) return `rgba(220,38,38,${alpha})`;
  switch (type) {
    case "interacts": return `rgba(220,38,38,${alpha})`;
    case "triggers": return `rgba(255,160,60,${alpha})`;
    case "affects": return `rgba(96,165,250,${alpha})`;
    case "blocks": return `rgba(220,38,38,${alpha})`;
    case "depends_on": return `rgba(150,150,150,${alpha})`;
    case "indicates": return `rgba(150,150,150,${alpha * 0.6})`;
    case "treated_by": return `rgba(96,165,250,${alpha * 0.6})`;
    default: return `rgba(150,150,150,${alpha})`;
  }
}

function edgeDash(type: ClinicalEdge["type"]): number[] {
  switch (type) {
    case "depends_on": return [4, 4];
    case "interacts": return [6, 3];
    case "indicates": return [2, 3];
    default: return [];
  }
}

// ── Node sizing ────────────────────────────────────────────────

function nodeRadius(type: ClinicalNode["type"], selected: boolean): number {
  const base = {
    drug: 14,
    lab: 12,
    vital: 12,
    symptom: 8,
    condition: 18,
  }[type];
  return base + (selected ? 4 : 0);
}

// ── Component ──────────────────────────────────────────────────

export default function ClinicalGraph({ onClose }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const nodesRef = useRef<SimNode[]>([]);
  const edgesRef = useRef<ClinicalEdge[]>([]);
  const graphDataRef = useRef<ClinicalGraphData>({ nodes: [], edges: [] });
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const transitionRef = useRef<number>(0);
  const timeRef = useRef<number>(0);

  // Pan & zoom
  const panRef = useRef({ x: 0, y: 0 });
  const zoomRef = useRef(1);
  const dragRef = useRef<{
    startX: number; startY: number;
    panX: number; panY: number;
    moved: boolean;
  } | null>(null);
  const pinchRef = useRef<{ dist: number; zoom: number } | null>(null);

  const { theme: t } = useTheme();
  const { patientDetail, packets } = useIris();
  const isMobile = useIsMobile();
  const themeRef = useRef(t);
  useEffect(() => { themeRef.current = t; }, [t]);

  // Build graph when data changes
  useEffect(() => {
    const graph = buildClinicalGraph(patientDetail, packets);
    graphDataRef.current = graph;

    // Position nodes in a type-clustered layout
    const typeGroups: Record<string, number> = {
      condition: 0,
      drug: 1,
      lab: 2,
      vital: 3,
      symptom: 4,
    };

    const simNodes: SimNode[] = graph.nodes.map((n) => {
      const group = typeGroups[n.type] ?? 2;
      const angle = (group / 5) * Math.PI * 2 + (Math.random() - 0.5) * 0.8;
      const radius = 120 + Math.random() * 80;
      return {
        ...n,
        x: Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
        y: Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
        expandProgress: 0,
      };
    });

    nodesRef.current = simNodes;
    edgesRef.current = graph.edges;
    transitionRef.current = 0;
  }, [patientDetail, packets]);

  // ── Pan/zoom handlers ──────────────────────────────────────

  const handlePointerDown = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      panX: panRef.current.x,
      panY: panRef.current.y,
      moved: false,
    };
  }, []);

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragRef.current.moved = true;
    panRef.current.x = dragRef.current.panX + dx;
    panRef.current.y = dragRef.current.panY + dy;
  }, []);

  const handlePointerUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    zoomRef.current = Math.max(0.3, Math.min(3, zoomRef.current * delta));
  }, []);

  const handleTouchStart = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      pinchRef.current = { dist: Math.sqrt(dx * dx + dy * dy), zoom: zoomRef.current };
    }
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    if (e.touches.length === 2 && pinchRef.current) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      zoomRef.current = Math.max(0.3, Math.min(3, pinchRef.current.zoom * (dist / pinchRef.current.dist)));
    }
  }, []);

  const handleTouchEnd = useCallback(() => {
    pinchRef.current = null;
  }, []);

  // ── Tap to select node ─────────────────────────────────────

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (dragRef.current?.moved) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const cx = rect.width / 2 + panRef.current.x;
    const cy = rect.height / 2 + panRef.current.y;
    const zoom = zoomRef.current;

    const mx = (e.clientX - rect.left - cx) / zoom;
    const my = (e.clientY - rect.top - cy) / zoom;

    const nodes = nodesRef.current;
    let closest: string | null = null;
    let closestDist = 30;

    for (const n of nodes) {
      const dx = n.x - mx;
      const dy = n.y - my;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < closestDist) {
        closestDist = dist;
        closest = n.id;
      }
    }

    setSelectedNodeId(closest);
  }, []);

  // ── Canvas animation loop ──────────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const animate = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      ctx.clearRect(0, 0, w, h);

      transitionRef.current = Math.min(transitionRef.current + 0.012, 1);
      const tr = transitionRef.current;
      const eased = 1 - Math.pow(1 - tr, 3);

      timeRef.current += 0.016;
      const time = timeRef.current;

      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      const theme = themeRef.current;
      const isDark = theme.name === "dark";

      // Build node index for edge lookups
      const nodeIndex = new Map<string, SimNode>();
      for (const n of nodes) nodeIndex.set(n.id, n);

      // ── Force simulation (settle over ~1s) ──
      if (tr < 0.95) {
        const repulsion = 6000;
        const attraction = 0.004;
        const damping = 0.82;

        // Charge repulsion
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const dx = nodes[i].x - nodes[j].x;
            const dy = nodes[i].y - nodes[j].y;
            const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
            const force = repulsion / (dist * dist);
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            nodes[i].vx += fx;
            nodes[i].vy += fy;
            nodes[j].vx -= fx;
            nodes[j].vy -= fy;
          }
        }

        // Link attraction
        for (const edge of edges) {
          const a = nodeIndex.get(edge.source);
          const b = nodeIndex.get(edge.target);
          if (!a || !b) continue;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const targetDist = edge.type === "indicates" || edge.type === "treated_by" ? 180 : 130;
          const force = (dist - targetDist) * attraction;
          const fx = (dx / Math.max(dist, 1)) * force;
          const fy = (dy / Math.max(dist, 1)) * force;
          a.vx += fx;
          a.vy += fy;
          b.vx -= fx;
          b.vy -= fy;
        }

        // Type clustering gravity
        const typeAnchors: Record<string, { x: number; y: number }> = {
          condition: { x: 0, y: -140 },
          drug: { x: -120, y: 40 },
          lab: { x: 130, y: -60 },
          vital: { x: 130, y: 80 },
          symptom: { x: -100, y: -120 },
        };

        for (const n of nodes) {
          const anchor = typeAnchors[n.type];
          if (anchor) {
            n.vx += (anchor.x - n.x) * 0.001;
            n.vy += (anchor.y - n.y) * 0.001;
          }
          n.vx *= damping;
          n.vy *= damping;
          n.x += n.vx * eased;
          n.y += n.vy * eased;
        }
      }

      // Expand progress
      for (const n of nodes) {
        n.expandProgress += (1 - n.expandProgress) * 0.06;
      }

      // ── Draw ──────────────────────────────────────────────

      ctx.save();
      const cx = w / 2 + panRef.current.x;
      const cy = h / 2 + panRef.current.y;
      const zoom = zoomRef.current;
      ctx.translate(cx, cy);
      ctx.scale(zoom, zoom);

      // Draw edges
      for (const edge of edges) {
        const a = nodeIndex.get(edge.source);
        const b = nodeIndex.get(edge.target);
        if (!a || !b) continue;

        const ep = Math.min(a.expandProgress, b.expandProgress) * eased;
        const baseAlpha = edge.active ? 0.5 : 0.15;
        const color = edgeColor(edge.type, edge.blocked, baseAlpha * ep);
        const dash = edgeDash(edge.type);

        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = color;
        ctx.lineWidth = edge.blocked ? 1.5 : 1;
        ctx.setLineDash(dash);
        ctx.stroke();
        ctx.setLineDash([]);

        // Arrowhead for directional edges
        if (edge.type === "triggers" || edge.type === "affects" || edge.type === "blocks" || edge.type === "treated_by") {
          const angle = Math.atan2(b.y - a.y, b.x - a.x);
          const r = nodeRadius(b.type, false);
          const tipX = b.x - Math.cos(angle) * r;
          const tipY = b.y - Math.sin(angle) * r;
          const arrowLen = 8;
          ctx.beginPath();
          ctx.moveTo(tipX, tipY);
          ctx.lineTo(tipX - arrowLen * Math.cos(angle - 0.35), tipY - arrowLen * Math.sin(angle - 0.35));
          ctx.moveTo(tipX, tipY);
          ctx.lineTo(tipX - arrowLen * Math.cos(angle + 0.35), tipY - arrowLen * Math.sin(angle + 0.35));
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        // Edge label (only when zoomed in enough)
        if (edge.label && zoom > 0.7 && edge.active) {
          const midX = (a.x + b.x) / 2;
          const midY = (a.y + b.y) / 2;
          ctx.font = "9px -apple-system, sans-serif";
          ctx.fillStyle = isDark ? `rgba(255,255,255,${0.3 * ep})` : `rgba(26,26,26,${0.3 * ep})`;
          ctx.textAlign = "center";
          ctx.fillText(edge.label, midX, midY - 4);
        }
      }

      // Draw nodes
      for (const n of nodes) {
        const ep = n.expandProgress * eased;
        const isSelected = n.id === selectedNodeId;
        const float = Math.sin(time * 0.5 + n.x * 0.01) * 1.5;
        const nx = n.x;
        const ny = n.y + float;
        const r = nodeRadius(n.type, isSelected) * ep;

        // Active glow
        if (n.active && ep > 0.5) {
          const pulse = 1 + Math.sin(time * 2.5) * 0.15;
          ctx.save();
          ctx.filter = "blur(6px)";
          ctx.beginPath();
          ctx.arc(nx, ny, r * pulse + 6, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255,107,0,${0.12 * ep})`;
          ctx.fill();
          ctx.restore();
        }

        if (n.type === "drug") {
          // Filled circle with accent border
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          const fillAlpha = isSelected ? 0.25 : 0.15;
          ctx.fillStyle = isDark
            ? `rgba(255,107,0,${fillAlpha * ep})`
            : `rgba(255,107,0,${fillAlpha * ep})`;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(255,107,0,${(isSelected ? 0.8 : 0.5) * ep})`;
          ctx.lineWidth = isSelected ? 2 : 1.5;
          ctx.stroke();
        } else if (n.type === "lab") {
          // Diamond
          ctx.save();
          ctx.translate(nx, ny);
          ctx.rotate(Math.PI / 4);
          const s = r * 0.85;
          ctx.beginPath();
          ctx.rect(-s, -s, s * 2, s * 2);
          ctx.fillStyle = isDark
            ? `rgba(96,165,250,${(isSelected ? 0.35 : 0.2) * ep})`
            : `rgba(96,165,250,${(isSelected ? 0.3 : 0.15) * ep})`;
          ctx.fill();
          ctx.strokeStyle = `rgba(96,165,250,${(isSelected ? 0.7 : 0.45) * ep})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
          ctx.restore();
        } else if (n.type === "vital") {
          // Rounded square
          const s = r * 0.9;
          const rr = 4;
          ctx.beginPath();
          ctx.moveTo(nx - s + rr, ny - s);
          ctx.lineTo(nx + s - rr, ny - s);
          ctx.quadraticCurveTo(nx + s, ny - s, nx + s, ny - s + rr);
          ctx.lineTo(nx + s, ny + s - rr);
          ctx.quadraticCurveTo(nx + s, ny + s, nx + s - rr, ny + s);
          ctx.lineTo(nx - s + rr, ny + s);
          ctx.quadraticCurveTo(nx - s, ny + s, nx - s, ny + s - rr);
          ctx.lineTo(nx - s, ny - s + rr);
          ctx.quadraticCurveTo(nx - s, ny - s, nx - s + rr, ny - s);
          ctx.closePath();
          ctx.fillStyle = isDark
            ? `rgba(74,222,128,${(isSelected ? 0.3 : 0.15) * ep})`
            : `rgba(34,197,94,${(isSelected ? 0.25 : 0.12) * ep})`;
          ctx.fill();
          ctx.strokeStyle = isDark
            ? `rgba(74,222,128,${(isSelected ? 0.7 : 0.4) * ep})`
            : `rgba(34,197,94,${(isSelected ? 0.6 : 0.35) * ep})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
        } else if (n.type === "symptom") {
          // Small muted circle
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          const inkColor = isDark ? "235,230,220" : "26,25,23";
          ctx.fillStyle = `rgba(${inkColor},${(isSelected ? 0.25 : 0.12) * ep})`;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(${inkColor},${(isSelected ? 0.4 : 0.2) * ep})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        } else if (n.type === "condition") {
          // Large outlined circle
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          const condColor = isDark ? "255,255,255" : "26,26,26";
          ctx.fillStyle = `rgba(${condColor},${(isSelected ? 0.08 : 0.03) * ep})`;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(${condColor},${(isSelected ? 0.5 : 0.25) * ep})`;
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Label + value
        if (ep > 0.4) {
          const labelAlpha = (ep - 0.4) * (1 / 0.6);
          const textColor = isDark ? "255,255,255" : "26,26,26";
          ctx.textAlign = "center";

          // Label
          ctx.font = `${isSelected ? "bold " : ""}11px -apple-system, sans-serif`;
          ctx.fillStyle = `rgba(${textColor},${(isSelected ? 0.8 : 0.55) * labelAlpha})`;
          ctx.fillText(n.label, nx, ny + r + 14);

          // Value
          if (n.value) {
            ctx.font = "10px -apple-system, sans-serif";
            ctx.fillStyle = `rgba(${textColor},${0.35 * labelAlpha})`;
            ctx.fillText(n.value, nx, ny + r + 26);
          }
        }
      }

      ctx.restore();
      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("resize", resize);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [selectedNodeId]);

  // Get selected node for detail card
  const selNode = selectedNodeId ? nodesRef.current.find((n) => n.id === selectedNodeId) : null;

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        background: t.bg,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        position: "relative",
        animation: "scaleIn 0.4s ease both",
      }}
    >
      {/* Back button */}
      <button
        onClick={onClose}
        style={{
          position: "absolute",
          top: 20,
          left: 20,
          ...glassStyle(t),
          borderRadius: 12,
          color: t.textMuted,
          fontSize: 13,
          padding: "8px 18px",
          cursor: "pointer",
          letterSpacing: "0.04em",
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        Back to orb
      </button>

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 24,
          width: "100%",
          textAlign: "center",
          fontSize: 13,
          fontWeight: 300,
          letterSpacing: "0.08em",
          color: t.textFaint,
          pointerEvents: "none",
        }}
      >
        health relationship map
      </div>

      {/* Legend */}
      <div
        style={{
          position: "absolute",
          top: 50,
          width: "100%",
          display: "flex",
          justifyContent: "center",
          gap: isMobile ? 10 : 18,
          fontSize: 10,
          color: t.textFaint,
          letterSpacing: "0.04em",
          flexWrap: "wrap",
          padding: "0 16px",
          pointerEvents: "none",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "rgba(255,107,0,0.3)", border: "1.5px solid rgba(255,107,0,0.6)", display: "inline-block" }} />
          drug
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 8, height: 8, background: "rgba(96,165,250,0.3)", border: "1.5px solid rgba(96,165,250,0.5)", transform: "rotate(45deg)", display: "inline-block" }} />
          lab
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: "rgba(74,222,128,0.2)", border: "1.5px solid rgba(74,222,128,0.45)", display: "inline-block" }} />
          vital
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: t.name === "dark" ? "rgba(235,230,220,0.15)" : "rgba(26,25,23,0.12)", border: `1px solid ${t.name === "dark" ? "rgba(235,230,220,0.25)" : "rgba(26,25,23,0.2)"}`, display: "inline-block" }} />
          symptom
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 10, height: 10, borderRadius: "50%", border: `1.5px solid ${t.name === "dark" ? "rgba(255,255,255,0.3)" : "rgba(26,26,26,0.25)"}`, display: "inline-block" }} />
          condition
        </span>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={{
          width: "100%",
          height: "100%",
          cursor: "grab",
          touchAction: "none",
        }}
      />

      {/* Detail card */}
      {selNode && (
        <div
          className="chat-bubble-enter"
          style={{
            position: "absolute",
            bottom: isMobile ? 20 : 40,
            left: isMobile ? 16 : "50%",
            right: isMobile ? 16 : "auto",
            transform: isMobile ? "none" : "translateX(-50%)",
            maxWidth: isMobile ? "none" : 420,
            minWidth: isMobile ? "auto" : 300,
            padding: "16px 20px",
            ...glassStyle(t),
            borderRadius: 16,
            color: t.text,
            fontSize: 13,
            lineHeight: 1.6,
            zIndex: 20,
          }}
        >
          {/* Type badge */}
          <div
            style={{
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              fontWeight: 600,
              marginBottom: 8,
              color: selNode.type === "drug" ? t.accent
                : selNode.type === "lab" ? "#60a5fa"
                : selNode.type === "vital" ? "#4ade80"
                : selNode.type === "condition" ? t.textMuted
                : t.textFaint,
            }}
          >
            {selNode.type}
          </div>

          {/* Drug detail */}
          {selNode.type === "drug" && selNode.meta && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{selNode.label}</div>
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                <div>
                  <span style={{ fontSize: 10, color: t.textFaint }}>Current dose</span>
                  <div style={{ fontWeight: 500 }}>{String(selNode.meta.dose_mg)}mg {selNode.meta.frequency === 2 ? "twice daily" : "daily"}</div>
                </div>
                {!!selNode.meta.decision && (
                  <div>
                    <span style={{ fontSize: 10, color: t.textFaint }}>Decision</span>
                    <div style={{ fontWeight: 600, color: t.accent }}>{String(selNode.meta.decision)}</div>
                  </div>
                )}
              </div>
              <div style={{ fontSize: 11, color: t.textFaint }}>
                Started {String(selNode.meta.start_date)} {"\u00B7"} last changed {String(selNode.meta.last_changed)}
              </div>
            </div>
          )}

          {/* Lab detail */}
          {selNode.type === "lab" && selNode.meta && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{selNode.label}</div>
              <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: 10, color: t.textFaint }}>Latest</span>
                  <div style={{ fontWeight: 500, fontSize: 18 }}>{String(selNode.meta.latest_value)} <span style={{ fontSize: 12, color: t.textMuted }}>{String(selNode.meta.unit)}</span></div>
                </div>
                {!!selNode.meta.normal_range && (
                  <div>
                    <span style={{ fontSize: 10, color: t.textFaint }}>Normal range</span>
                    <div style={{ fontSize: 13, color: t.textMuted }}>{String(selNode.meta.normal_range)}</div>
                  </div>
                )}
              </div>
              {/* Sparkline */}
              {selNode.trend && selNode.trend.length > 1 && (
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 10, color: t.textFaint }}>Trend</span>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4, fontSize: 12, color: t.textMuted }}>
                    {selNode.trend.map((v, i) => (
                      <span key={i}>
                        {i > 0 && <span style={{ color: t.textFaint, margin: "0 2px" }}>{"\u2192"}</span>}
                        {v}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div style={{ fontSize: 10, color: t.textFaint }}>
                as of {String(selNode.meta.latest_date)}
              </div>
            </div>
          )}

          {/* Vital detail */}
          {selNode.type === "vital" && selNode.meta && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{selNode.label}</div>
              <div style={{ fontWeight: 500, fontSize: 18 }}>
                {String(selNode.meta.latest_value)} <span style={{ fontSize: 12, color: t.textMuted }}>{String(selNode.meta.unit)}</span>
              </div>
              {selNode.trend && selNode.trend.length > 1 && (
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 10, color: t.textFaint }}>5 day trend</span>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4, fontSize: 12, color: t.textMuted }}>
                    {selNode.trend.map((v, i) => (
                      <span key={i}>
                        {i > 0 && <span style={{ color: t.textFaint, margin: "0 2px" }}>{"\u2192"}</span>}
                        {v}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Symptom detail */}
          {selNode.type === "symptom" && (
            <div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{selNode.label}</div>
              <div style={{ fontSize: 12, color: t.textMuted, marginTop: 4 }}>Reported in current session</div>
            </div>
          )}

          {/* Condition detail */}
          {selNode.type === "condition" && (
            <div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{selNode.label}</div>
              <div style={{ fontSize: 12, color: t.textMuted, marginTop: 4 }}>
                {(() => {
                  const linked = edgesRef.current.filter(
                    (e) => (e.source === selNode.id || e.target === selNode.id)
                  );
                  const drugEdges = linked.filter((e) => e.type === "treated_by");
                  if (drugEdges.length === 0) return "No linked medications";
                  return `Linked to ${drugEdges.length} medication${drugEdges.length > 1 ? "s" : ""}`;
                })()}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {nodesRef.current.length === 0 && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            color: t.textFaint,
            fontSize: 14,
            fontWeight: 300,
            textAlign: "center",
          }}
        >
          No clinical data available yet
        </div>
      )}
    </div>
  );
}
