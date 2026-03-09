/**
 * ThemeContext — dark/light theme toggle with orange (#FF6B00) accent.
 * Persists preference in localStorage.
 */

import React, { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";

export type ThemeName = "dark" | "light";

export interface ThemeTokens {
  name: ThemeName;
  bg: string;
  bgPanel: string;
  bgInput: string;
  text: string;
  textMuted: string;
  textFaint: string;
  border: string;
  borderSubtle: string;
  accent: string;
  /** Canvas node/spoke color RGB (no alpha) — orange for both themes */
  nodeR: number;
  nodeG: number;
  nodeB: number;
  /** Conversation bubble colors */
  bubblePatient: string;
  bubblePatientBorder: string;
  bubbleIris: string;
  bubbleIrisBorder: string;
  /** Clinician-specific */
  userMsgBg: string;
  userMsgBorder: string;
  /** Glass/blur aesthetic */
  glass: string;
  glassBorder: string;
  glassHover: string;
  glassShadow: string;
  glassBlur: number;
}

const DARK: ThemeTokens = {
  name: "dark",
  bg: "#141414",
  bgPanel: "#1A1A1A",
  bgInput: "rgba(255,255,255,0.05)",
  text: "#EBE6DC",
  textMuted: "rgba(235,230,220,0.55)",
  textFaint: "rgba(235,230,220,0.2)",
  border: "rgba(235,230,220,0.08)",
  borderSubtle: "rgba(235,230,220,0.06)",
  accent: "#FF6B00",
  nodeR: 235,
  nodeG: 230,
  nodeB: 220,
  bubblePatient: "rgba(235,230,220,0.06)",
  bubblePatientBorder: "rgba(235,230,220,0.10)",
  bubbleIris: "rgba(235,230,220,0.04)",
  bubbleIrisBorder: "rgba(235,230,220,0.07)",
  userMsgBg: "rgba(235,230,220,0.06)",
  userMsgBorder: "rgba(235,230,220,0.10)",
  glass: "rgba(20,20,20,0.80)",
  glassBorder: "rgba(235,230,220,0.08)",
  glassHover: "rgba(20,20,20,0.88)",
  glassShadow: "0 4px 24px rgba(0,0,0,0.5)",
  glassBlur: 24,
};

const LIGHT: ThemeTokens = {
  name: "light",
  bg: "#FAFAF7",
  bgPanel: "#F5F5F0",
  bgInput: "rgba(26,25,23,0.03)",
  text: "#1A1917",
  textMuted: "rgba(26,25,23,0.55)",
  textFaint: "rgba(26,25,23,0.2)",
  border: "rgba(26,25,23,0.08)",
  borderSubtle: "rgba(26,25,23,0.05)",
  accent: "#FF6B00",
  nodeR: 26,
  nodeG: 25,
  nodeB: 23,
  bubblePatient: "rgba(26,25,23,0.04)",
  bubblePatientBorder: "rgba(26,25,23,0.08)",
  bubbleIris: "rgba(26,25,23,0.025)",
  bubbleIrisBorder: "rgba(26,25,23,0.06)",
  userMsgBg: "rgba(26,25,23,0.04)",
  userMsgBorder: "rgba(26,25,23,0.08)",
  glass: "rgba(250,250,247,0.80)",
  glassBorder: "rgba(26,25,23,0.06)",
  glassHover: "rgba(250,250,247,0.90)",
  glassShadow: "0 4px 24px rgba(0,0,0,0.04)",
  glassBlur: 24,
};

export const THEMES: Record<ThemeName, ThemeTokens> = { dark: DARK, light: LIGHT };

/** Returns inline style properties for a frosted glass panel. */
export function glassStyle(t: ThemeTokens): React.CSSProperties {
  return {
    background: t.glass,
    backdropFilter: `blur(${t.glassBlur}px)`,
    WebkitBackdropFilter: `blur(${t.glassBlur}px)`,
    border: `1px solid ${t.glassBorder}`,
    boxShadow: t.glassShadow,
  };
}

interface ThemeContextValue {
  theme: ThemeTokens;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: LIGHT,
  toggleTheme: () => { },
});

function getInitialTheme(): ThemeName {
  try {
    const stored = localStorage.getItem("iris-theme");
    if (stored === "dark" || stored === "light") return stored;
  } catch { /* ignore */ }
  return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeName, setThemeName] = useState<ThemeName>(getInitialTheme);

  // Sync data-theme attribute on body for CSS selectors
  useEffect(() => {
    document.body.dataset.theme = themeName;
  }, [themeName]);

  const toggleTheme = useCallback(() => {
    setThemeName((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      try { localStorage.setItem("iris-theme", next); } catch { /* ignore */ }
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme: THEMES[themeName], toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
