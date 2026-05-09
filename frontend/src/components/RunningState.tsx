import { Clock, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import type { Persona } from "../types/simulation";

export function RunningState({ personaName }: { personaName?: Persona["name"] }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsedSeconds((current) => current + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section className="running-panel" aria-live="polite">
      <div className="loader-wrap">
        <LoaderCircle className="spinner" size={34} />
      </div>
      <p className="eyebrow">Simulation running</p>
      <h2>{personaName ? `${personaName} is using the product` : "The persona is using the product"}</h2>
      <p>
        The backend is operating the browser, capturing screenshots, and preparing the report. This request returns
        when the simulation is complete.
      </p>
      <div className="elapsed">
        <Clock size={18} />
        <span>{elapsedSeconds}s elapsed</span>
      </div>
    </section>
  );
}
