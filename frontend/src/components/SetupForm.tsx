import { Play, SlidersHorizontal } from "lucide-react";
import { FormEvent, useId, useState } from "react";
import type { SimulationInput } from "../types/simulation";

type SetupFormProps = {
  initialValues: SimulationInput;
  isCreating: boolean;
  isDisabled?: boolean;
  onSubmit: (input: SimulationInput) => void;
};

const GOAL_MAX = 400;

export function SetupForm({ initialValues, isCreating, isDisabled = false, onSubmit }: SetupFormProps) {
  const [url, setUrl] = useState(initialValues.url);
  const [goal, setGoal] = useState(initialValues.goal);
  const [audience, setAudience] = useState(initialValues.audience ?? "");
  const [errors, setErrors] = useState<{ url?: string; goal?: string }>({});

  const reactId = useId();
  const urlId = `${reactId}-url`;
  const goalId = `${reactId}-goal`;
  const audienceId = `${reactId}-audience`;
  const urlErrorId = `${urlId}-error`;
  const goalErrorId = `${goalId}-error`;
  const goalHintId = `${goalId}-hint`;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isDisabled) {
      return;
    }

    const nextErrors: typeof errors = {};
    if (!url.trim()) {
      nextErrors.url = "Enter a product URL.";
    }
    if (!goal.trim()) {
      nextErrors.goal = "Enter a testing goal.";
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    onSubmit({
      url: url.trim(),
      goal: goal.trim(),
      audience: audience.trim() || undefined
    });
  }

  return (
    <form className="setup-panel" onSubmit={handleSubmit} noValidate>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Run setup</p>
          <h2>Target and objective</h2>
        </div>
        <div className="heading-icon" aria-hidden="true">
          <SlidersHorizontal size={18} />
        </div>
      </div>

      <div className="field">
        <label htmlFor={urlId}>Product URL</label>
        <input
          id={urlId}
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="http://localhost:3000"
          aria-invalid={Boolean(errors.url)}
          aria-describedby={errors.url ? urlErrorId : undefined}
          disabled={isDisabled}
        />
        {errors.url ? (
          <small className="field-error" id={urlErrorId}>
            {errors.url}
          </small>
        ) : null}
      </div>

      <div className="field">
        <label htmlFor={goalId}>Testing goal</label>
        <textarea
          id={goalId}
          value={goal}
          onChange={(event) => setGoal(event.target.value.slice(0, GOAL_MAX))}
          placeholder="Test whether a new user can create their first project."
          rows={5}
          aria-invalid={Boolean(errors.goal)}
          aria-describedby={[errors.goal ? goalErrorId : null, goalHintId].filter(Boolean).join(" ") || undefined}
          disabled={isDisabled}
          maxLength={GOAL_MAX}
        />
        <div className="field-hint" id={goalHintId} aria-live="polite">
          {goal.length}/{GOAL_MAX}
        </div>
        {errors.goal ? (
          <small className="field-error" id={goalErrorId}>
            {errors.goal}
          </small>
        ) : null}
      </div>

      <div className="field">
        <label htmlFor={audienceId}>Audience</label>
        <input
          id={audienceId}
          value={audience}
          onChange={(event) => setAudience(event.target.value)}
          placeholder="Non-technical small business owners"
          disabled={isDisabled}
        />
      </div>

      <button className="primary-button" type="submit" disabled={isCreating || isDisabled}>
        <Play size={18} aria-hidden="true" />
        {isDisabled ? "Simulation running..." : isCreating ? "Generating persona..." : "Generate persona"}
      </button>
    </form>
  );
}
