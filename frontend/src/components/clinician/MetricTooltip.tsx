/**
 * MetricTooltip — Tap/hover on a metric to see its plain language explanation.
 */

import { useState, useRef, useEffect, type ReactNode } from "react";
import { useTheme, glassStyle } from "../../context/ThemeContext";
import { educationContent } from "../../data/educationContent";

interface Props {
  metricKey: string;
  children: ReactNode;
}

export default function MetricTooltip({ metricKey, children }: Props) {
  const { theme: t } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const info = educationContent[metricKey];
  if (!info) return <>{children}</>;

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div
      ref={ref}
      style={{ position: "relative", display: "inline-block", cursor: "help" }}
      onClick={() => setOpen(!open)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <div style={{ borderBottom: `1px dotted ${t.textFaint}`, display: "inline-block" }}>
        {children}
      </div>

      {open && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: "50%",
            transform: "translateX(-50%)",
            ...glassStyle(t),
            borderRadius: 8,
            padding: 12,
            width: 240,
            zIndex: 1000,
            fontSize: 12,
            lineHeight: 1.6,
            color: t.text,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 13, color: t.text }}>
            {info.fullName}
          </div>
          <div style={{ marginBottom: 6, color: t.name === "dark" ? "#ccc" : t.text }}>
            {info.whatItMeasures}
          </div>
          <div style={{ marginBottom: 6 }}>
            <span style={{ color: "#4ade80", fontWeight: 500 }}>Normal range:</span>{" "}
            <span style={{ color: t.name === "dark" ? "#ddd" : t.text }}>{info.normalRange}</span>
          </div>
          <div style={{ color: t.name === "dark" ? "#bbb" : "#666", fontStyle: "italic" }}>
            {info.whyItMatters}
          </div>
          {info.simpleAnalogy && (
            <div
              style={{
                marginTop: 8,
                padding: "6px 8px",
                background: t.name === "dark" ? "rgba(96,165,250,0.08)" : "rgba(59,130,246,0.06)",
                borderRadius: 4,
                color: t.name === "dark" ? "#93c5fd" : "#2563eb",
                fontSize: 11,
              }}
            >
              {info.simpleAnalogy}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
