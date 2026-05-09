import { CheckCircle2, ClipboardList, ListChecks, RotateCcw } from "lucide-react";
import type { SimulationRun } from "../types/simulation";
import { FrictionCards } from "./FrictionCards";
import { Timeline } from "./Timeline";
import { Card, DataTable } from "./ui";

const outcomeLabels = {
  success: "Success",
  partial: "Partial",
  failure: "Failure"
};

const outcomeTones = {
  success: "success",
  partial: "warning",
  failure: "danger"
} as const;

export function ReportView({ run, onReset }: { run: SimulationRun; onReset: () => void }) {
  const report = run.report;

  if (!report) {
    return (
      <section className="report-panel">
        <div className="panel-title">
          <ClipboardList size={22} />
          <div>
            <p className="eyebrow">Report unavailable</p>
            <h2>The backend returned a completed run without report data.</h2>
          </div>
        </div>
        <button className="secondary-button" type="button" onClick={onReset}>
          <RotateCcw size={17} />
          Start new simulation
        </button>
        <div className="report-section">
          <DataTable
            rows={[
              { label: "Run ID", value: run.id },
              { label: "Status", value: run.status, tone: run.status === "failed" ? "danger" : "warning" },
              { label: "Recorded steps", value: run.steps.length }
            ]}
          />
        </div>
        <Timeline steps={run.steps} />
      </section>
    );
  }

  return (
    <section className="report-panel">
      <div className="report-header">
        <div>
          <p className="eyebrow">Final simulation report</p>
          <h1>{outcomeLabels[report.outcome]} outcome</h1>
          <p>{report.summary}</p>
        </div>
        <button className="secondary-button" type="button" onClick={onReset}>
          <RotateCcw size={17} />
          New simulation
        </button>
      </div>

      <div className="report-grid">
        <Card className="report-card report-card-compact">
          <div className="card-heading">
            <ClipboardList size={19} />
            <h2>Run facts</h2>
          </div>
          <DataTable
            rows={[
              { label: "Run ID", value: run.id },
              { label: "Outcome", value: outcomeLabels[report.outcome], tone: outcomeTones[report.outcome] },
              { label: "Steps", value: run.steps.length },
              { label: "Findings", value: report.frictionMoments.length },
              { label: "Updated", value: new Date(run.updatedAt).toLocaleString() }
            ]}
          />
        </Card>

        <Card className="report-card report-card-compact" id="workspace">
          <div className="card-heading">
            <ClipboardList size={19} />
            <h2>Run configuration</h2>
          </div>
          <DataTable
            rows={[
              { label: "Target", value: run.url },
              { label: "Goal", value: run.goal },
              { label: "Audience", value: run.audience ?? "Unspecified" }
            ]}
          />
        </Card>

        <Card className="report-card" id="persona">
          <div className="card-heading">
            <CheckCircle2 size={19} />
            <h2>Persona narrative</h2>
          </div>
          <p>{report.personaNarrative || "No persona narrative was returned."}</p>
        </Card>

        <Card className="report-card">
          <div className="card-heading">
            <ListChecks size={19} />
            <h2>Recommendations</h2>
          </div>
          {report.recommendations.length > 0 ? (
            <ul className="recommendations">
              {report.recommendations.map((recommendation) => (
                <li key={recommendation}>{recommendation}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-copy">No recommendations were returned.</p>
          )}
        </Card>
      </div>

      <div className="report-section" id="artifacts">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Artifacts</p>
            <h2>Run outputs</h2>
          </div>
        </div>
        <Card className="report-card report-card-compact">
          <DataTable
            rows={[
              { label: "Screenshots", value: `${run.steps.filter((step) => step.screenshot).length} renderable assets` },
              { label: "Journey log", value: `${run.steps.length} recorded steps` },
              { label: "Report payload", value: run.report ? "Available" : "Missing", tone: run.report ? "success" : "danger" },
              { label: "Screenshot route", value: "/api/runs/{runId}/screenshots/{file}" }
            ]}
          />
        </Card>
      </div>

      <div className="report-section" id="journey">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Evidence</p>
            <h2>Journey timeline</h2>
          </div>
        </div>
        <Timeline steps={run.steps} />
      </div>

      <div className="report-section" id="findings">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Findings</p>
            <h2>Friction moments</h2>
          </div>
        </div>
        <FrictionCards moments={report.frictionMoments} />
      </div>
    </section>
  );
}
