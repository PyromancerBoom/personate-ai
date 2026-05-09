import { AlertTriangle, RotateCcw } from "lucide-react";
import type { SimulationRun } from "../types/simulation";
import { Timeline } from "./Timeline";

type ErrorStateProps = {
  message: string;
  run?: SimulationRun;
  onReset: () => void;
};

export function ErrorState({ message, run, onReset }: ErrorStateProps) {
  const hasSteps = Boolean(run?.steps.length);

  return (
    <section className="error-panel" role="alert">
      <div className="panel-title">
        <AlertTriangle size={22} />
        <div>
          <p className="eyebrow">Simulation failed</p>
          <h2>{message}</h2>
        </div>
      </div>
      <button className="secondary-button" type="button" onClick={onReset}>
        <RotateCcw size={17} />
        Start new simulation
      </button>
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
