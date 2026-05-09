import { Activity, ChevronDown, MessageSquareText } from "lucide-react";
import { useState } from "react";
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

const COLLAPSE_THRESHOLD = 20;
const HEAD_COUNT = 5;
const TAIL_COUNT = 5;

export function Timeline({ steps }: { steps: JourneyStep[] }) {
  const [showAll, setShowAll] = useState(false);

  if (steps.length === 0) {
    return <p className="empty-copy">No journey steps were recorded.</p>;
  }

  const shouldCollapse = !showAll && steps.length > COLLAPSE_THRESHOLD;
  const visible = shouldCollapse
    ? { head: steps.slice(0, HEAD_COUNT), tail: steps.slice(steps.length - TAIL_COUNT) }
    : { head: steps, tail: [] as JourneyStep[] };
  const hiddenCount = steps.length - HEAD_COUNT - TAIL_COUNT;

  return (
    <div className="timeline">
      {visible.head.map((step) => (
        <StepCard key={step.step} step={step} />
      ))}

      {shouldCollapse ? (
        <div className="timeline-collapse">
          <button type="button" onClick={() => setShowAll(true)}>
            <ChevronDown size={14} aria-hidden="true" /> Show {hiddenCount} more steps
          </button>
        </div>
      ) : null}

      {visible.tail.map((step) => (
        <StepCard key={step.step} step={step} />
      ))}
    </div>
  );
}

function StepCard({ step }: { step: JourneyStep }) {
  return (
    <article className="timeline-card">
      <div className="timeline-media">
        <ScreenshotImage src={step.screenshot} alt={`Step ${step.step} screenshot`} />
      </div>
      <div className="timeline-content">
        <div className="step-heading">
          <span>Step {step.step}</span>
          <span className={`signal signal-${step.uxSignal}`}>{signalLabels[step.uxSignal]}</span>
        </div>
        <p className="thought">
          <MessageSquareText size={16} aria-hidden="true" />
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
          <Activity size={16} aria-hidden="true" />
          <span>{step.action.type}</span>
        </div>
      </div>
    </article>
  );
}
