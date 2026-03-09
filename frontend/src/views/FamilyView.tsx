/**
 * FamilyView — Simple, clean patient status page for family/caregivers.
 * No orb, no graph. Just name, status, recent changes, next dates.
 * Orange and white, large readable text, mobile-first.
 * Access via share code — no login required.
 */

import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

interface FamilyData {
  name: string;
  age: number;
  status: "Stable" | "Needs Attention" | "Urgent";
  recent_changes: string[];
  next_monitoring: string;
  last_updated: string | null;
}

export default function FamilyView() {
  const { code } = useParams<{ code: string }>();
  const [data, setData] = useState<FamilyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    fetch(`${API_BASE}/family/${code}`)
      .then((r) => {
        if (!r.ok) throw new Error("Invalid or expired share code");
        return r.json();
      })
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [code]);

  const statusColors: Record<string, { bg: string; text: string; border: string }> = {
    Stable: { bg: "rgba(74,222,128,0.1)", text: "#22c55e", border: "rgba(74,222,128,0.2)" },
    "Needs Attention": { bg: "rgba(251,191,36,0.1)", text: "#f59e0b", border: "rgba(251,191,36,0.2)" },
    Urgent: { bg: "rgba(220,38,38,0.1)", text: "#dc2626", border: "rgba(220,38,38,0.2)" },
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#FFFFFF",
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "40px 20px",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 32 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "rgba(255,107,0,0.1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
        </div>
        <span style={{ fontSize: 16, fontWeight: 500, color: "#1A1A1A", letterSpacing: "0.02em" }}>
          Iris Care Update
        </span>
      </div>

      {loading && (
        <div style={{ color: "#999", fontSize: 15, marginTop: 60 }}>
          <div className="shimmer-bar" style={{ width: 200, marginBottom: 16 }} />
          Loading...
        </div>
      )}

      {error && (
        <div
          style={{
            maxWidth: 400,
            width: "100%",
            padding: "24px",
            borderRadius: 16,
            background: "rgba(220,38,38,0.05)",
            border: "1px solid rgba(220,38,38,0.15)",
            textAlign: "center",
            color: "#dc2626",
            fontSize: 15,
            marginTop: 40,
          }}
        >
          {error}
        </div>
      )}

      {data && (
        <div style={{ maxWidth: 480, width: "100%" }}>
          {/* Patient name & age */}
          <div style={{ marginBottom: 24 }}>
            <h1 style={{ fontSize: 28, fontWeight: 600, color: "#1A1A1A", margin: 0, lineHeight: 1.3 }}>
              {data.name}
            </h1>
            {data.age > 0 && (
              <div style={{ fontSize: 14, color: "#999", marginTop: 4 }}>Age {data.age}</div>
            )}
          </div>

          {/* Status badge */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 20px",
              borderRadius: 24,
              background: statusColors[data.status]?.bg || statusColors.Stable.bg,
              border: `1px solid ${statusColors[data.status]?.border || statusColors.Stable.border}`,
              marginBottom: 32,
            }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: statusColors[data.status]?.text || "#22c55e",
                display: "inline-block",
                animation: data.status === "Urgent" ? "breathe 1.5s ease-in-out infinite" : "none",
              }}
            />
            <span
              style={{
                fontSize: 15,
                fontWeight: 600,
                color: statusColors[data.status]?.text || "#22c55e",
              }}
            >
              {data.status}
            </span>
          </div>

          {/* Recent changes */}
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 14, fontWeight: 500, color: "#999", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12 }}>
              Recent Updates
            </h2>
            {data.recent_changes.map((change, i) => (
              <div
                key={i}
                className="chat-bubble-enter"
                style={{
                  animationDelay: `${i * 100}ms`,
                  padding: "14px 18px",
                  borderRadius: 12,
                  background: "rgba(26,26,26,0.03)",
                  border: "1px solid rgba(26,26,26,0.06)",
                  marginBottom: 8,
                  fontSize: 15,
                  color: "#1A1A1A",
                  lineHeight: 1.5,
                }}
              >
                {change}
              </div>
            ))}
          </div>

          {/* Next monitoring */}
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 14, fontWeight: 500, color: "#999", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12 }}>
              Next Steps
            </h2>
            <div
              style={{
                padding: "14px 18px",
                borderRadius: 12,
                background: "rgba(255,107,0,0.05)",
                border: "1px solid rgba(255,107,0,0.12)",
                fontSize: 15,
                color: "#1A1A1A",
                lineHeight: 1.5,
              }}
            >
              {data.next_monitoring}
            </div>
          </div>

          {/* Last updated */}
          {data.last_updated && (
            <div style={{ fontSize: 12, color: "#bbb", textAlign: "center" }}>
              Last updated: {new Date(data.last_updated).toLocaleDateString()}
            </div>
          )}

          {/* Footer */}
          <div
            style={{
              marginTop: 48,
              textAlign: "center",
              fontSize: 11,
              color: "#ccc",
              lineHeight: 1.5,
            }}
          >
            Powered by Iris Core
            <br />
            This is a summary view. Contact the care team for detailed information.
          </div>
        </div>
      )}
    </div>
  );
}
