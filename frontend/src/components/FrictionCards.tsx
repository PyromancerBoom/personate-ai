import { AlertCircle } from "lucide-react";
import type { SimulationReport } from "../types/simulation";
import { ScreenshotImage } from "./ScreenshotImage";

type FrictionMoment = SimulationReport["frictionMoments"][number];

const severityRank: Record<FrictionMoment["severity"], string> = {
  low: "Low",
  medium: "Medium",
  high: "High"
};

export function FrictionCards({ moments }: { moments: FrictionMoment[] }) {
  if (moments.length === 0) {
    return <p className="empty-copy">No major friction moments were identified.</p>;
  }

  return (
    <div className="friction-grid">
      {moments.map((moment) => (
        <article className="friction-card" key={`${moment.step}-${moment.finding}`}>
          <ScreenshotImage src={moment.screenshot} alt={`Friction screenshot for step ${moment.step}`} />
          <div className="friction-body">
            <div className="friction-meta">
              <span>Step {moment.step}</span>
              <span className={`severity severity-${moment.severity}`}>{severityRank[moment.severity]}</span>
            </div>
            <h3>
              <AlertCircle size={18} aria-hidden="true" />
              {moment.finding}
            </h3>
            <p>{moment.recommendation}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
