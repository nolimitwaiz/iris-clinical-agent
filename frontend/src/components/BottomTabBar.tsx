/**
 * BottomTabBar — Mobile bottom navigation with glass aesthetic.
 * Two tabs: Patient (orb) and Dashboard (grid).
 */

import { useLocation, useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useIsMobile } from "../hooks/useMediaQuery";

export default function BottomTabBar() {
  const { theme: t } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useIsMobile();

  if (!isMobile) return null;

  const isPatient = location.pathname === "/";

  const tabs = [
    {
      label: "Patient",
      path: "/",
      active: isPatient,
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <circle cx="12" cy="12" r="4" />
        </svg>
      ),
    },
    {
      label: "Dashboard",
      path: "/clinician",
      active: !isPatient,
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
      ),
    },
  ];

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        display: "flex",
        background: t.bg,
        borderTop: `1px solid ${t.border}`,
        paddingBottom: "max(8px, env(safe-area-inset-bottom))",
      }}
    >
      {tabs.map((tab) => (
        <button
          key={tab.path}
          onClick={() => navigate(tab.path)}
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
            padding: "10px 0 6px",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            color: tab.active ? t.text : t.textMuted,
            opacity: tab.active ? 1 : 0.4,
            transition: "all 0.2s ease",
            position: "relative",
          }}
        >
          {tab.icon}
          <span style={{ fontSize: 10, fontWeight: tab.active ? 600 : 400, letterSpacing: "0.04em" }}>
            {tab.label}
          </span>
          {tab.active && (
            <span
              style={{
                position: "absolute",
                top: 4,
                width: 5,
                height: 5,
                borderRadius: "50%",
                background: t.accent,
              }}
            />
          )}
        </button>
      ))}
    </div>
  );
}
