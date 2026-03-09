/**
 * EducationTooltip — Tappable clinical term explanations.
 * Wraps clinical terms in chat text with interactive tooltips
 * that show patient-friendly explanations.
 */

import { useState, useRef, useEffect, type ReactNode } from "react";
import { useTheme, glassStyle } from "../context/ThemeContext";
import { useIris } from "../context/IrisContext";
import type { EducationTopic, EducationContent } from "../api/types";

/** Keywords that map to education topics */
const KEYWORD_MAP: Record<string, string> = {
  "potassium": "potassium",
  "k+": "potassium",
  "creatinine": "creatinine",
  "egfr": "egfr",
  "gfr": "egfr",
  "kidney": "egfr",
  "kidneys": "egfr",
  "bnp": "bnp",
  "sodium": "sodium",
  "ejection fraction": "ejection_fraction",
  "nyha": "nyha_class",
};

/** Find keyword matches in text and wrap them in tappable spans */
export function AnnotatedText({
  text,
  education,
}: {
  text: string;
  education: EducationContent | null;
}) {
  if (!education || Object.keys(education).length === 0) {
    return <>{text}</>;
  }

  // Build regex from keywords (longest first to avoid partial matches)
  const keywords = Object.keys(KEYWORD_MAP).sort((a, b) => b.length - a.length);
  const pattern = new RegExp(`\\b(${keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`, "gi");

  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    const keyword = match[0];
    const topicKey = KEYWORD_MAP[keyword.toLowerCase()];
    const topic = topicKey ? education[topicKey] : null;

    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (topic) {
      parts.push(
        <TermWithTooltip key={match.index} term={keyword} topic={topic} />
      );
    } else {
      parts.push(keyword);
    }

    lastIndex = match.index + keyword.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts}</>;
}

function TermWithTooltip({
  term,
  topic,
}: {
  term: string;
  topic: EducationTopic;
}) {
  const { theme: t } = useTheme();
  const [open, setOpen] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <span style={{ position: "relative", display: "inline" }}>
      <span
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        style={{
          borderBottom: `1px dotted ${t.accent}`,
          cursor: "pointer",
          color: "inherit",
        }}
      >
        {term}
      </span>

      {open && (
        <div
          ref={tooltipRef}
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: "50%",
            transform: "translateX(-50%)",
            width: 280,
            zIndex: 100,
            ...glassStyle(t),
            borderRadius: 12,
            padding: "14px 16px",
            animation: "fadeIn 0.2s ease",
          }}
        >
          <div
            style={{
              fontSize: 14,
              fontWeight: 600,
              color: t.text,
              marginBottom: 6,
            }}
          >
            {topic.full_name}
          </div>
          <div
            style={{
              fontSize: 13,
              lineHeight: 1.6,
              color: t.textMuted,
              marginBottom: 6,
            }}
          >
            {topic.what_it_measures}
          </div>
          {topic.why_it_matters && (
            <div
              style={{
                fontSize: 13,
                lineHeight: 1.6,
                color: t.textMuted,
                marginBottom: 6,
              }}
            >
              {topic.why_it_matters}
            </div>
          )}
          {topic.simple_analogy && (
            <div
              style={{
                fontSize: 13,
                lineHeight: 1.6,
                color: t.accent,
                fontStyle: "italic",
                marginBottom: 8,
              }}
            >
              {topic.simple_analogy}
            </div>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
            }}
            style={{
              background: "none",
              border: `1px solid ${t.border}`,
              borderRadius: 8,
              padding: "4px 12px",
              fontSize: 12,
              color: t.textMuted,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Got it
          </button>
        </div>
      )}
    </span>
  );
}

/** Hook to fetch and cache education content */
export function useEducationContent(): EducationContent | null {
  const { educationContent } = useIris();
  return educationContent;
}
