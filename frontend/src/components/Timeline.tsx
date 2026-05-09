import { Activity, MessageSquareText } from "lucide-react";
import type { JourneyStep, UxSignal } from "../types/simulation";
import { ActionText } from "./ActionText";
import { ScreenshotImage } from "./ScreenshotImage";

const signalLabels: Record<UxSignal, string> = {
  confusion: "Confusion",
  confidence: "Confidence",
  hesitation: "Hesitation",
  friction: "Friction",
  progress: "Progress",
  drop_off: "Drop-off",
  neutral: "Neutral"
};

export function Timeline({ steps }: { steps: JourneyStep[] }) {
  if (steps.length === 0) {
    return <p className="empty-copy">No journey steps were recorded.</p>;
  }

  return (
    <div className="timeline">
      {steps.map((step) => (
        <article className="timeline-card" key={step.step}>
          <div className="timeline-media">
            <ScreenshotImage src={step.screenshot} alt={`Step ${step.step} screenshot`} />
          </div>
          <div className="timeline-content">
            <div className="step-heading">
              <span>Step {step.step}</span>
              <span className={`signal signal-${step.uxSignal}`}>{signalLabels[step.uxSignal]}</span>
            </div>
            <p className="thought">
              <MessageSquareText size={16} />
              {step.thought}
            </p>
            <dl className="step-details">
              <div>
                <dt>Action</dt>
                <dd>
                  <ActionText action={step.action} />
                </dd>
              </div>
              <div>
                <dt>Result</dt>
                <dd>{step.result}</dd>
              </div>
              <div>
                <dt>Page summary</dt>
                <dd>{step.pageSummary}</dd>
              </div>
            </dl>
            <div className="activity-row">
              <Activity size={16} />
              <span>{step.action.type}</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
