import { ArrowRight, CheckCircle2, Goal, UserRound } from "lucide-react";
import type { Persona, SimulationInput } from "../types/simulation";

type PersonaPreviewProps = {
  persona: Persona;
  input: SimulationInput;
  isRunning: boolean;
  onStart: () => void;
};

export function PersonaPreview({ persona, input, isRunning, onStart }: PersonaPreviewProps) {
  return (
    <section className="persona-panel" aria-label="Generated persona" id="persona">
      <div className="persona-header">
        <div className="persona-avatar" aria-hidden="true">
          <UserRound size={22} />
        </div>
        <div className="persona-title">
          <p className="eyebrow">Generated persona</p>
          <h2>{persona.name}</h2>
          <span>{persona.experienceLevel}</span>
        </div>
        <div className="persona-status">
          <CheckCircle2 size={14} />
          Ready to run
        </div>
      </div>

      <div className="persona-context">
        <Goal size={16} />
        <div className="persona-context-rows">
          <div className="persona-context-row">
            <span>Goal</span>
            <p>{input.goal}</p>
          </div>
          <div className="persona-context-row">
            <span>Audience</span>
            <p>{input.audience ?? "Unspecified"}</p>
          </div>
        </div>
      </div>

      <div className="persona-grid">
        <div>
          <h3>Background</h3>
          <p>{persona.background}</p>
        </div>
        <div>
          <h3>Motivation</h3>
          <p>{persona.motivation}</p>
        </div>
        <div>
          <h3>Experience</h3>
          <p>{persona.experienceLevel}</p>
        </div>
        <div>
          <h3>Success criteria</h3>
          <p>{persona.successCriteria}</p>
        </div>
      </div>

      <div className="persona-signals">
        <div className="signal-list">
          <h3>Concerns</h3>
          <ul>
            {persona.concerns.map((concern) => (
              <li key={concern}>{concern}</li>
            ))}
          </ul>
        </div>
        <div className="signal-list">
          <h3>Behavioral traits</h3>
          <ul>
            {persona.behavioralTraits.map((trait) => (
              <li key={trait}>{trait}</li>
            ))}
          </ul>
        </div>
      </div>

      <button className="primary-button" type="button" onClick={onStart} disabled={isRunning}>
        <ArrowRight size={18} />
        {isRunning ? "Simulation running..." : "Start simulation"}
      </button>
    </section>
  );
}
