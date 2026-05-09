import {
  Activity,
  BarChart3,
  CheckCircle2,
  CircleDashed,
  ClipboardList,
  Database,
  Gauge,
  LayoutDashboard,
  Server,
  UserRound
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import type { SimulationRun } from "../types/simulation";
import { API_BASE_URL } from "../lib/api";

type DashboardShellProps = {
  state: "idle" | "creating" | "personaReady" | "running" | "completed" | "failed";
  run?: SimulationRun;
  children: ReactNode;
};

const stateMeta: Record<DashboardShellProps["state"], { label: string; detail: string; tone: string }> = {
  idle: {
    label: "Ready",
    detail: "Configure a target and generate a persona.",
    tone: "neutral"
  },
  creating: {
    label: "Generating",
    detail: "Requesting a persona from the backend.",
    tone: "warning"
  },
  personaReady: {
    label: "Persona ready",
    detail: "Review the generated persona, then start the run.",
    tone: "success"
  },
  running: {
    label: "Running",
    detail: "Browser simulation is executing on the backend.",
    tone: "warning"
  },
  completed: {
    label: "Completed",
    detail: "Report data is ready for review.",
    tone: "success"
  },
  failed: {
    label: "Failed",
    detail: "The run stopped before a completed report.",
    tone: "danger"
  }
};

const navItems = [
  { label: "Workspace", icon: LayoutDashboard, href: "#workspace" },
  { label: "Persona", icon: UserRound, href: "#persona" },
  { label: "Journey", icon: Activity, href: "#journey" },
  { label: "Findings", icon: BarChart3, href: "#findings" },
  { label: "Artifacts", icon: Database, href: "#artifacts" }
];

function apiHostLabel() {
  try {
    return new URL(API_BASE_URL).host;
  } catch {
    return API_BASE_URL;
  }
}

export function DashboardShell({ state, run, children }: DashboardShellProps) {
  const meta = stateMeta[state];
  const [activeHref, setActiveHref] = useState("#workspace");

  useEffect(() => {
    const syncHash = () => setActiveHref(window.location.hash || "#workspace");
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  return (
    <main className={`app-shell ${state === "completed" || state === "failed" ? "wide" : ""}`.trim()}>
      <a className="skip-to-content" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar" aria-label="Product navigation">
        <div className="brand-mark">
          <div className="brand-glyph" aria-hidden="true">
            <Gauge size={18} />
          </div>
          <div>
            <strong>Personate</strong>
            <span>AI Simulations</span>
          </div>
        </div>

        <nav className="side-nav" aria-label="Simulation sections">
          {navItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <a
                className={activeHref === item.href ? "active" : undefined}
                href={item.href}
                key={item.label}
                onClick={() => setActiveHref(item.href)}
              >
                <Icon size={15} />
                {item.label}
              </a>
            );
          })}
        </nav>

      </aside>

      <section className="dashboard-frame" id="main-content" tabIndex={-1}>
        <header className="topbar">
          <div>
            <p className="eyebrow">Simulation workspace</p>
            <h1>AI User Simulation Report</h1>
          </div>
          <div className="topbar-meta">
            <span className={`status-pill status-${meta.tone}`}>
              {state === "running" ? (
                <CircleDashed size={13} aria-hidden="true" />
              ) : (
                <CheckCircle2 size={13} aria-hidden="true" />
              )}
              {meta.label}
            </span>
            <span className="status-pill status-neutral">
              <Server size={13} aria-hidden="true" />
              {apiHostLabel()}
            </span>
          </div>
        </header>

        <div className="run-strip">
          <div>
            <span>Run</span>
            <strong>{run?.id ?? "not created"}</strong>
          </div>
          <div>
            <span>Status</span>
            <strong>{meta.detail}</strong>
          </div>
          <div>
            <span>Steps</span>
            <strong>{run?.steps.length ?? 0}</strong>
          </div>
          <div>
            <span>Evidence</span>
            <strong>{run?.report?.frictionMoments.length ?? 0} findings</strong>
          </div>
        </div>

        {children}
      </section>
    </main>
  );
}
