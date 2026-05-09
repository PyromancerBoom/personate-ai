import { Play, SlidersHorizontal } from "lucide-react";
import { FormEvent, useState } from "react";
import type { SimulationInput } from "../types/simulation";

type SetupFormProps = {
  initialValues: SimulationInput;
  isCreating: boolean;
  isDisabled?: boolean;
  onSubmit: (input: SimulationInput) => void;
};

export function SetupForm({ initialValues, isCreating, isDisabled = false, onSubmit }: SetupFormProps) {
  const [url, setUrl] = useState(initialValues.url);
  const [goal, setGoal] = useState(initialValues.goal);
  const [audience, setAudience] = useState(initialValues.audience ?? "");
  const [errors, setErrors] = useState<{ url?: string; goal?: string }>({});

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

      <label className="field">
        <span>Product URL</span>
        <input
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="http://localhost:3000"
          aria-invalid={Boolean(errors.url)}
          disabled={isDisabled}
        />
        {errors.url ? <small className="field-error">{errors.url}</small> : null}
      </label>

      <label className="field">
        <span>Testing goal</span>
        <textarea
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          placeholder="Test whether a new user can create their first project."
          rows={5}
          aria-invalid={Boolean(errors.goal)}
          disabled={isDisabled}
        />
        {errors.goal ? <small className="field-error">{errors.goal}</small> : null}
      </label>

      <label className="field">
        <span>Audience</span>
        <input
          value={audience}
          onChange={(event) => setAudience(event.target.value)}
          placeholder="Non-technical small business owners"
          disabled={isDisabled}
        />
      </label>

      <button className="primary-button" type="submit" disabled={isCreating || isDisabled}>
        <Play size={18} />
        {isDisabled ? "Simulation running..." : isCreating ? "Generating persona..." : "Generate persona"}
      </button>
    </form>
  );
}
