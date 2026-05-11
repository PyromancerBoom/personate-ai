import { Clock, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import type { Persona } from "../types/simulation";

const PHASES = [
  { threshold: 0, label: "Initializing browser context..." },
  { threshold: 8, label: "Navigating to target URL..." },
  { threshold: 18, label: "Analyzing page structure..." },
  { threshold: 32, label: "Simulating user interactions..." },
  { threshold: 55, label: "Capturing screenshots..." },
  { threshold: 80, label: "Evaluating UX signals..." },
  { threshold: 110, label: "Compiling friction report..." }
];

function getPhase(seconds: number) {
  let label = PHASES[0].label;
  for (const phase of PHASES) {
    if (seconds >= phase.threshold) {
      label = phase.label;
    }
  }
  return label;
}

function formatElapsed(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s < 10 ? "0" : ""}${s}s`;
}

export function RunningState({ personaName }: { personaName?: Persona["name"] }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsedSeconds((current) => current + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const phase = getPhase(elapsedSeconds);

  return (
    <section className="running-panel" aria-live="polite" aria-busy="true">
      <div className="running-progress" aria-hidden="true" />

      <div className="orb-wrap" aria-hidden="true">
        <div className="orb-inner">
          <LoaderCircle className="spinner" size={26} />
        </div>
      </div>

      <p className="eyebrow">Simulation running</p>
      <h2>{personaName ? `${personaName} is using the product` : "The persona is using the product"}</h2>
      <p>
        The backend is operating the browser, capturing screenshots, and preparing the report.
      </p>

      <p className="running-phase" aria-live="polite">
        {phase}
      </p>

      <div className="elapsed">
        <Clock size={16} aria-hidden="true" />
        <span>{formatElapsed(elapsedSeconds)} elapsed</span>
      </div>
    </section>
  );
}
