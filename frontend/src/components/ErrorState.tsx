import { AlertTriangle, RefreshCw, RotateCcw } from "lucide-react";
import type { SimulationRun } from "../types/simulation";
import { Timeline } from "./Timeline";

type ErrorStateProps = {
  message: string;
  run?: SimulationRun;
  onReset: () => void;
  onRetry?: () => void;
};

export function ErrorState({ message, run, onReset, onRetry }: ErrorStateProps) {
  const hasSteps = Boolean(run?.steps.length);

  return (
    <section className="error-panel" role="alert">
      <div className="panel-title">
        <AlertTriangle size={22} aria-hidden="true" />
        <div>
          <p className="eyebrow">Simulation failed</p>
          <h2>{message}</h2>
        </div>
      </div>
      <div className="error-actions">
        {onRetry ? (
          <button className="secondary-button" type="button" onClick={onRetry}>
            <RefreshCw size={16} aria-hidden="true" />
            Try again with same inputs
          </button>
        ) : null}
        <button className="secondary-button" type="button" onClick={onReset}>
          <RotateCcw size={17} aria-hidden="true" />
          Start new simulation
        </button>
      </div>
      {hasSteps ? (
        <div className="partial-evidence" id="artifacts">
          <h3>Captured evidence</h3>
          <div id="journey">
            <Timeline steps={run?.steps ?? []} />
          </div>
        </div>
      ) : null}
    </section>
  );
}
