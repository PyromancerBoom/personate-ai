import {
  Activity,
  BarChart3,
  CheckCircle2,
  Database,
  Gauge,
  History,
  LayoutDashboard,
  Loader2,
  Server,
  UserRound
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import type { RunSummary, SimulationRun } from "../types/simulation";
import { API_BASE_URL } from "../lib/api";

type DashboardShellProps = {
  state: "idle" | "creating" | "personaReady" | "running" | "completed" | "failed" | "history";
  run?: SimulationRun;
  history?: RunSummary[];
  isHistoryLoading?: boolean;
  historyError?: string;
  activeRunId?: string;
  isHistoryDisabled?: boolean;
  onSelectHistoryRun?: (runId: string) => void;
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
  },
  history: {
    label: "History",
    detail: "Viewing a saved simulation run.",
    tone: "neutral"
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

function formatHistoryTime(value: string) {
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "Unknown time";
  }

  const diffMs = Date.now() - timestamp;
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diffMs < minute) {
    return "Just now";
  }
  if (diffMs < hour) {
    return `${Math.floor(diffMs / minute)}m ago`;
  }
  if (diffMs < day) {
    return `${Math.floor(diffMs / hour)}h ago`;
  }
  if (diffMs < 7 * day) {
    return `${Math.floor(diffMs / day)}d ago`;
  }
  return new Date(value).toLocaleDateString();
}

export function DashboardShell({
  state,
  run,
  history = [],
  isHistoryLoading = false,
  historyError,
  activeRunId,
  isHistoryDisabled = false,
  onSelectHistoryRun,
  children
}: DashboardShellProps) {
  const meta = stateMeta[state];
  const [activeHref, setActiveHref] = useState("#workspace");

  useEffect(() => {
    const syncHash = () => setActiveHref(window.location.hash || "#workspace");
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  const isRunning = state === "running" || state === "creating";

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
          {navItems.map((item) => {
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

        <section className="history-panel" aria-label="Run history">
          <div className="history-heading">
            <span>
              <History size={14} aria-hidden="true" />
              History
            </span>
            {isHistoryLoading ? <Loader2 size={13} aria-hidden="true" className="spinner" /> : null}
          </div>

          {historyError ? <p className="history-message">{historyError}</p> : null}
          {!historyError && !isHistoryLoading && history.length === 0 ? (
            <p className="history-message">Previous runs will appear here.</p>
          ) : null}

          {history.length > 0 ? (
            <div className="history-list">
              {history.slice(0, 8).map((item) => (
                <button
                  className={`history-item ${activeRunId === item.id ? "active" : ""}`.trim()}
                  type="button"
                  key={item.id}
                  disabled={isHistoryDisabled}
                  onClick={() => onSelectHistoryRun?.(item.id)}
                >
                  <span className="history-item-main">
                    <strong>{item.goal || item.url}</strong>
                    <small>{formatHistoryTime(item.updatedAt)}</small>
                  </span>
                  <span className="history-item-meta">
                    <span className={`history-status history-status-${item.status}`}>{item.status}</span>
                    <span>
                      {item.steps} steps / {item.findings} findings
                    </span>
                  </span>
                </button>
              ))}
            </div>
          ) : null}
        </section>

        <div className="sidebar-footer">
          <span className="sidebar-version">personate v0.1</span>
        </div>
      </aside>

      <section className="dashboard-frame" id="main-content" tabIndex={-1}>
        <header className="topbar">
          <div>
            <p className="eyebrow">Simulation workspace</p>
            <h1>AI User Simulation</h1>
          </div>
          <div className="topbar-meta">
            <span
              className={`status-pill status-${meta.tone}`}
              aria-live="polite"
              aria-atomic="true"
            >
              {isRunning ? (
                <Loader2 size={13} aria-hidden="true" className="spinner" />
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

        <div className="run-strip" role="status" aria-label="Run statistics">
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
