/**
 * ConversationGraph — Clinical network graph visualization.
 *
 * Force-directed layout with distinct node types:
 *   - Patient messages: orange filled circles
 *   - Iris responses: white/gray outlined circles
 *   - Action Packets: blue diamonds (clinical decisions)
 *   - Escalations: red pulsing circles
 *
 * Interactions: pan, pinch-zoom, tap node for detail card.
 * Theme-aware: adapts to dark/light themes.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { useTheme, glassStyle } from "../../context/ThemeContext";
import { useIris } from "../../context/IrisContext";
import { useIsMobile } from "../../hooks/useMediaQuery";
import type { ConversationTurn } from "./RadialNodes";
import type { ActionPacket } from "../../api/types";

interface Props {
  conversations: ConversationTurn[];
  onClose: () => void;
}

type NodeType = "patient" | "iris" | "action_packet" | "escalation" | "lab";

interface GraphNode {
  id: string;
  type: NodeType;
  x: number;
  y: number;
  vx: number;
  vy: number;
  content: string;
  packet?: ActionPacket;
  turnIndex?: number;
  /** For expansion animation: 0=collapsed, 1=expanded */
  expandProgress: number;
}

interface GraphEdge {
  source: number;
  target: number;
  causal?: boolean; // orange arrow for reasoning chains
}

export default function ConversationGraph({ conversations, onClose }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const nodesRef = useRef<GraphNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const [expandedPacket, setExpandedPacket] = useState<number | null>(null);
  const transitionRef = useRef<number>(0);
  const timeRef = useRef<number>(0);

  // Pan & zoom state
  const panRef = useRef({ x: 0, y: 0 });
  const zoomRef = useRef(1);
  const dragRef = useRef<{ startX: number; startY: number; panX: number; panY: number } | null>(null);
  const pinchRef = useRef<{ dist: number; zoom: number } | null>(null);

  const { theme: t } = useTheme();
  const { packets } = useIris();
  const isMobile = useIsMobile();
  const themeRef = useRef(t);
  useEffect(() => { themeRef.current = t; }, [t]);
  const packetsRef = useRef(packets);
  useEffect(() => { packetsRef.current = packets; }, [packets]);

  // Build graph nodes and edges from conversations + action packets
  useEffect(() => {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    const spacing = 100;

    // Add conversation nodes
    conversations.forEach((turn, i) => {
      const xBase = turn.role === "patient" ? -120 : 120;
      nodes.push({
        id: `conv-${i}`,
        type: turn.role === "patient" ? "patient" : "iris",
        x: xBase + (Math.random() - 0.5) * 60,
        y: i * spacing - (conversations.length * spacing) / 2 + (Math.random() - 0.5) * 30,
        vx: 0, vy: 0,
        content: turn.content,
        turnIndex: i,
        expandProgress: 0,
      });

      // Sequential edge
      if (i > 0) {
        edges.push({ source: i - 1, target: i });
      }
    });

    // Add Action Packet nodes
    const currentPackets = packetsRef.current;
    if (currentPackets.length > 0) {
      const lastIrisIdx = nodes.length - 1;
      currentPackets.forEach((pkt, pi) => {
        const isEscalation = pkt.tool_name === "escalation_manager" && pkt.decision !== "no_escalation";
        const nodeIdx = nodes.length;
        nodes.push({
          id: `pkt-${pi}`,
          type: isEscalation ? "escalation" : "action_packet",
          x: 250 + pi * 80 + (Math.random() - 0.5) * 40,
          y: (lastIrisIdx >= 0 ? nodes[lastIrisIdx].y : 0) + (pi - currentPackets.length / 2) * 70,
          vx: 0, vy: 0,
          content: `${pkt.tool_name}: ${pkt.decision}`,
          packet: pkt,
          expandProgress: 0,
        });

        // Edge from last Iris response to each packet
        if (lastIrisIdx >= 0) {
          edges.push({ source: lastIrisIdx, target: nodeIdx, causal: true });
        }
      });
    }

    nodesRef.current = nodes;
    edgesRef.current = edges;
    transitionRef.current = 0;
  }, [conversations, packets]);

  // Touch/mouse pan & zoom handlers
  const handlePointerDown = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      panX: panRef.current.x,
      panY: panRef.current.y,
    };
  }, []);

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
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
      const ratio = dist / pinchRef.current.dist;
      zoomRef.current = Math.max(0.3, Math.min(3, pinchRef.current.zoom * ratio));
    }
  }, []);

  const handleTouchEnd = useCallback(() => {
    pinchRef.current = null;
  }, []);

  // Tap to select node
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      // Only treat as tap if no significant drag occurred
      if (dragRef.current) return;

      const rect = canvas.getBoundingClientRect();
      const cx = rect.width / 2 + panRef.current.x;
      const cy = rect.height / 2 + panRef.current.y;
      const zoom = zoomRef.current;

      const mx = (e.clientX - rect.left - cx) / zoom;
      const my = (e.clientY - rect.top - cy) / zoom;

      const nodes = nodesRef.current;
      let closest = -1;
      let closestDist = 25; // px threshold

      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        const dx = n.x - mx;
        const dy = n.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < closestDist) {
          closestDist = dist;
          closest = i;
        }
      }

      if (closest >= 0) {
        if (closest === selectedNode) {
          // Double tap on packet node → expand reasoning
          if (nodes[closest].packet) {
            setExpandedPacket(expandedPacket === closest ? null : closest);
          } else {
            setSelectedNode(null);
          }
        } else {
          setSelectedNode(closest);
          setExpandedPacket(null);
        }
      } else {
        setSelectedNode(null);
        setExpandedPacket(null);
      }
    },
    [selectedNode, expandedPacket]
  );

  // Canvas animation loop with force-directed simulation
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

      transitionRef.current = Math.min(transitionRef.current + 0.015, 1);
      const tr = transitionRef.current;
      const eased = 1 - Math.pow(1 - tr, 3);

      timeRef.current += 0.016;
      const time = timeRef.current;

      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      const theme = themeRef.current;
      const isDark = theme.name === "dark";

      // Force-directed simulation (simple)
      if (tr < 0.95) {
        const repulsion = 8000;
        const attraction = 0.005;
        const damping = 0.85;

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
          const a = nodes[edge.source];
          const b = nodes[edge.target];
          if (!a || !b) continue;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const targetDist = edge.causal ? 150 : 100;
          const force = (dist - targetDist) * attraction;
          const fx = (dx / Math.max(dist, 1)) * force;
          const fy = (dy / Math.max(dist, 1)) * force;
          a.vx += fx;
          a.vy += fy;
          b.vx -= fx;
          b.vy -= fy;
        }

        // Chronological left-to-right gravity for conversation nodes
        for (let i = 0; i < nodes.length; i++) {
          const n = nodes[i];
          if (n.turnIndex !== undefined) {
            n.vy += (n.turnIndex * 80 - n.y) * 0.003;
            const targetX = n.type === "patient" ? -100 : 100;
            n.vx += (targetX - n.x) * 0.002;
          }

          // Apply velocity
          n.vx *= damping;
          n.vy *= damping;
          n.x += n.vx * eased;
          n.y += n.vy * eased;
        }
      }

      // Update expand progress
      for (let i = 0; i < nodes.length; i++) {
        const target = 1;
        nodes[i].expandProgress += (target - nodes[i].expandProgress) * 0.06;
      }

      // Transform: center + pan + zoom
      ctx.save();
      const cx = w / 2 + panRef.current.x;
      const cy = h / 2 + panRef.current.y;
      const zoom = zoomRef.current;
      ctx.translate(cx, cy);
      ctx.scale(zoom, zoom);

      // Draw edges
      for (const edge of edges) {
        const a = nodes[edge.source];
        const b = nodes[edge.target];
        if (!a || !b) continue;

        ctx.beginPath();
        const cpx = (a.x + b.x) / 2;
        ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo(cpx, (a.y + b.y) / 2, b.x, b.y);

        if (edge.causal) {
          ctx.strokeStyle = `rgba(255,107,0,${0.25 * eased})`;
          ctx.lineWidth = 1;
          ctx.setLineDash([4, 4]);
        } else {
          ctx.strokeStyle = isDark
            ? `rgba(255,255,255,${0.08 * eased})`
            : `rgba(26,26,26,${0.08 * eased})`;
          ctx.lineWidth = 1;
          ctx.setLineDash([]);
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // Arrowhead for causal edges
        if (edge.causal) {
          const angle = Math.atan2(b.y - a.y, b.x - a.x);
          const arrowLen = 7;
          ctx.beginPath();
          ctx.moveTo(b.x, b.y);
          ctx.lineTo(
            b.x - arrowLen * Math.cos(angle - 0.3),
            b.y - arrowLen * Math.sin(angle - 0.3)
          );
          ctx.moveTo(b.x, b.y);
          ctx.lineTo(
            b.x - arrowLen * Math.cos(angle + 0.3),
            b.y - arrowLen * Math.sin(angle + 0.3)
          );
          ctx.strokeStyle = `rgba(255,107,0,${0.3 * eased})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      // Draw nodes
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        const ep = n.expandProgress * eased;
        const isSelected = i === selectedNode;
        const float = Math.sin(time * 0.6 + i * 0.7) * 1.5;
        const nx = n.x;
        const ny = n.y + float;

        if (n.type === "patient") {
          // Ink filled circle
          const r = (8 + (isSelected ? 4 : 0)) * ep;
          const inkColor = isDark ? "235,230,220" : "26,25,23";
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${inkColor},${(isSelected ? 0.9 : 0.7) * ep})`;
          ctx.fill();
          // Outer ring
          ctx.beginPath();
          ctx.arc(nx, ny, r + 3, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(${inkColor},${0.25 * ep})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        } else if (n.type === "iris") {
          // White/gray outlined circle
          const r = (7 + (isSelected ? 3 : 0)) * ep;
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          ctx.fillStyle = isDark
            ? `rgba(255,255,255,${(isSelected ? 0.2 : 0.08) * ep})`
            : `rgba(26,26,26,${(isSelected ? 0.15 : 0.06) * ep})`;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          ctx.strokeStyle = isDark
            ? `rgba(255,255,255,${0.4 * ep})`
            : `rgba(26,26,26,${0.3 * ep})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
        } else if (n.type === "action_packet") {
          // Blue diamond
          const r = (9 + (isSelected ? 4 : 0)) * ep;
          ctx.save();
          ctx.translate(nx, ny);
          ctx.rotate(Math.PI / 4);
          ctx.beginPath();
          ctx.rect(-r / 1.4, -r / 1.4, r * 1.4, r * 1.4);
          ctx.fillStyle = `rgba(96,165,250,${(isSelected ? 0.5 : 0.3) * ep})`;
          ctx.fill();
          ctx.strokeStyle = `rgba(96,165,250,${0.6 * ep})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
          ctx.restore();
        } else if (n.type === "escalation") {
          // Red pulsing circle
          const pulse = 1 + Math.sin(time * 3) * 0.15;
          const r = (10 + (isSelected ? 4 : 0)) * ep * pulse;
          ctx.beginPath();
          ctx.arc(nx, ny, r, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(220,38,38,${(isSelected ? 0.6 : 0.35) * ep})`;
          ctx.fill();
          // Glow
          ctx.beginPath();
          ctx.arc(nx, ny, r + 4, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(220,38,38,${0.15 * ep})`;
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Labels (only after half expansion)
        if (ep > 0.5) {
          const labelAlpha = (ep - 0.5) * 2;
          let label = "";
          if (n.type === "patient") label = "You";
          else if (n.type === "iris") label = "Iris";
          else if (n.type === "action_packet" || n.type === "escalation") {
            label = n.packet?.tool_name?.replace(/_/g, " ") || "";
          }

          ctx.font = `11px -apple-system, sans-serif`;
          ctx.fillStyle = isDark
            ? `rgba(255,255,255,${0.35 * labelAlpha})`
            : `rgba(26,26,26,${0.35 * labelAlpha})`;
          ctx.textAlign = "center";
          ctx.fillText(label, nx, ny + (n.type === "action_packet" || n.type === "escalation" ? 22 : 20));
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
  }, [selectedNode]);

  // Get selected node data for detail card
  const selNode = selectedNode !== null ? nodesRef.current[selectedNode] : null;

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        background: t.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        fontFamily:
          "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif",
        position: "relative",
        animation: "scaleIn 0.5s ease both",
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
          fontSize: 13,
          fontWeight: 300,
          letterSpacing: "0.08em",
          color: t.textFaint,
        }}
      >
        clinical reasoning map
      </div>

      {/* Legend */}
      <div
        style={{
          position: "absolute",
          top: 54,
          display: "flex",
          gap: 16,
          fontSize: 10,
          color: t.textFaint,
          letterSpacing: "0.04em",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: t.name === "dark" ? "#EBE6DC" : "#1A1917", display: "inline-block" }} />
          patient
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", border: `1.5px solid ${t.name === "dark" ? "rgba(255,255,255,0.4)" : "rgba(26,26,26,0.3)"}`, display: "inline-block" }} />
          iris
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 8, height: 8, background: "rgba(96,165,250,0.5)", transform: "rotate(45deg)", display: "inline-block" }} />
          action packet
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "rgba(220,38,38,0.5)", display: "inline-block" }} />
          escalation
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

      {/* Detail card for selected node */}
      {selNode && (
        <div
          className="chat-bubble-enter"
          style={{
            position: "absolute",
            bottom: isMobile ? 20 : 40,
            left: isMobile ? 16 : "50%",
            right: isMobile ? 16 : "auto",
            transform: isMobile ? "none" : "translateX(-50%)",
            maxWidth: isMobile ? "none" : 500,
            padding: "16px 20px",
            ...glassStyle(t),
            borderRadius: 16,
            color: t.text,
            fontSize: 13,
            lineHeight: 1.6,
            zIndex: 20,
            maxHeight: "40vh",
            overflowY: "auto",
          }}
        >
          {/* Header */}
          <div
            style={{
              fontSize: 10,
              color: selNode.type === "patient" ? t.text :
                     selNode.type === "escalation" ? "#dc2626" :
                     selNode.type === "action_packet" ? "#60a5fa" : t.textFaint,
              marginBottom: 8,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              fontWeight: 600,
            }}
          >
            {selNode.type === "patient" ? "patient message" :
             selNode.type === "iris" ? "iris response" :
             selNode.type === "escalation" ? "escalation alert" :
             selNode.packet?.tool_name?.replace(/_/g, " ") || "action packet"}
          </div>

          {/* Content for conversation nodes */}
          {(selNode.type === "patient" || selNode.type === "iris") && (
            <div style={{ color: t.textMuted }}>{selNode.content}</div>
          )}

          {/* Action Packet summary */}
          {selNode.packet && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <span style={{ fontSize: 10, color: t.textFaint }}>Decision</span>
                  <div style={{ fontWeight: 600, color: t.accent }}>{selNode.packet.decision}</div>
                </div>
                {selNode.packet.drug && (
                  <div>
                    <span style={{ fontSize: 10, color: t.textFaint }}>Drug</span>
                    <div style={{ fontWeight: 500 }}>{selNode.packet.drug}</div>
                  </div>
                )}
                <div>
                  <span style={{ fontSize: 10, color: t.textFaint }}>Confidence</span>
                  <div style={{
                    fontWeight: 500,
                    color: selNode.packet.confidence === "high" ? "#4ade80" :
                           selNode.packet.confidence === "moderate" ? "#fbbf24" : "#f87171",
                  }}>{selNode.packet.confidence}</div>
                </div>
              </div>
              <div style={{ color: t.textMuted, fontSize: 12 }}>{selNode.packet.reason}</div>

              {/* Tap to expand hint */}
              {expandedPacket !== selectedNode && (
                <div style={{ fontSize: 10, color: t.textFaint, fontStyle: "italic" }}>
                  Tap again for full reasoning
                </div>
              )}

              {/* Expanded reasoning */}
              {expandedPacket === selectedNode && (
                <div
                  className="chat-bubble-enter"
                  style={{
                    borderTop: `1px solid ${t.borderSubtle}`,
                    paddingTop: 10,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                >
                  <div>
                    <span style={{ fontSize: 10, color: t.textFaint }}>Guideline</span>
                    <div style={{ fontSize: 12, color: "#60a5fa" }}>{selNode.packet.guideline}</div>
                  </div>
                  {selNode.packet.monitoring && (
                    <div>
                      <span style={{ fontSize: 10, color: t.textFaint }}>Monitoring Required</span>
                      <div style={{ fontSize: 12, color: t.textMuted }}>{selNode.packet.monitoring}</div>
                    </div>
                  )}
                  <div>
                    <span style={{ fontSize: 10, color: t.textFaint }}>Risk of Inaction</span>
                    <div style={{ fontSize: 12, color: "#f87171" }}>{selNode.packet.risk_of_inaction}</div>
                  </div>
                  {selNode.packet.inputs_used && (
                    <div>
                      <span style={{ fontSize: 10, color: t.textFaint }}>Input Data</span>
                      <div style={{ fontSize: 11, color: t.textMuted, fontFamily: "monospace" }}>
                        {Object.entries(selNode.packet.inputs_used).map(([k, v]) => (
                          <div key={k}>{k}: {JSON.stringify(v)}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {selNode.packet.data_quality && (
                    <div>
                      <span style={{ fontSize: 10, color: "#fbbf24" }}>Data Quality Warning</span>
                      <div style={{ fontSize: 12, color: "#fbbf24" }}>{selNode.packet.data_quality}</div>
                    </div>
                  )}
                  {(selNode.packet.current_dose_mg != null || selNode.packet.new_dose_mg != null) && (
                    <div style={{ display: "flex", gap: 12 }}>
                      {selNode.packet.current_dose_mg != null && (
                        <div>
                          <span style={{ fontSize: 10, color: t.textFaint }}>Current Dose</span>
                          <div style={{ fontSize: 12 }}>{selNode.packet.current_dose_mg}mg</div>
                        </div>
                      )}
                      {selNode.packet.new_dose_mg != null && (
                        <div>
                          <span style={{ fontSize: 10, color: t.textFaint }}>New Dose</span>
                          <div style={{ fontSize: 12, color: "#4ade80" }}>{selNode.packet.new_dose_mg}mg</div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {conversations.length === 0 && (
        <div
          style={{
            position: "absolute",
            color: t.textFaint,
            fontSize: 14,
            fontWeight: 300,
          }}
        >
          No conversations yet
        </div>
      )}
    </div>
  );
}
