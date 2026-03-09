import type { ReactNode } from "react";
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import { IrisProvider } from "./context/IrisContext";
import { useIsMobile } from "./hooks/useMediaQuery";
import PatientView from "./views/PatientView";
import ClinicianView from "./views/ClinicianView";
import FamilyView from "./views/FamilyView";
import BottomTabBar from "./components/BottomTabBar";

function NavBar() {
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const isPatient = location.pathname === "/";

  const t = theme;

  // Hide on mobile — BottomTabBar handles nav there
  if (isMobile) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "12px 16px",
        pointerEvents: "none",
      }}
    >
      {/* Top navbar controls */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          pointerEvents: "auto",
        }}
      >
        {/* Pill toggle: Patient | Clinician — thin border style */}
        <div
          style={{
            display: "flex",
            border: `1px solid ${t.border}`,
            borderRadius: 24,
            overflow: "hidden",
            background: t.bg,
          }}
        >
          <button
            onClick={() => navigate("/")}
            style={{
              padding: "7px 22px",
              fontSize: 13,
              letterSpacing: "0.04em",
              background: isPatient ? t.accent : "transparent",
              color: isPatient ? "#fff" : t.textMuted,
              fontWeight: isPatient ? 600 : 400,
              border: "none",
              cursor: "pointer",
              transition: "all 0.3s ease",
            }}
          >
            Patient
          </button>
          <button
            onClick={() => navigate("/clinician")}
            style={{
              padding: "7px 22px",
              fontSize: 13,
              letterSpacing: "0.04em",
              background: !isPatient ? t.accent : "transparent",
              color: !isPatient ? "#fff" : t.textMuted,
              fontWeight: !isPatient ? 600 : 400,
              border: "none",
              cursor: "pointer",
              transition: "all 0.3s ease",
            }}
          >
            Dashboard
          </button>
        </div>

        {/* Theme toggle — minimal dot */}
        <button
          onClick={toggleTheme}
          title={`Switch to ${t.name === "dark" ? "light" : "dark"} theme`}
          style={{
            width: 28,
            height: 28,
            borderRadius: 14,
            border: `1px solid ${t.border}`,
            background: t.bg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            transition: "all 0.3s ease",
            padding: 0,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: t.name === "dark" ? "#EBE6DC" : "#1A1917",
              display: "block",
            }}
          />
        </button>
      </div>
    </div>
  );
}

function PageWrapper({ children }: { children: ReactNode }) {
  return (
    <div style={{ animation: "fadeInUp 0.35s ease both" }}>
      {children}
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <IrisProvider>
          <NavBar />
          <Routes>
            <Route path="/" element={<PageWrapper><PatientView /></PageWrapper>} />
            <Route path="/clinician" element={<PageWrapper><ClinicianView /></PageWrapper>} />
            <Route path="/family/:code" element={<FamilyView />} />
          </Routes>
          <BottomTabBar />
        </IrisProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
