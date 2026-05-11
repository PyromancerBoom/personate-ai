export type Persona = {
  id: string;
  name: string;
  background: string;
  motivation: string;
  experienceLevel: string;
  concerns: string[];
  behavioralTraits: string[];
  successCriteria: string;
};

export type SimulationInput = {
  url: string;
  goal: string;
  audience?: string;
};

export type JourneyAction =
  | { type: "click"; coordinates?: [number, number]; elementId?: number }
  | {
      type: "type";
      text: string;
      coordinates?: [number, number];
      elementId?: number;
      submit?: boolean;
    }
  | { type: "scroll_down" }
  | { type: "back" }
  | { type: "wait" }
  | { type: "press_key"; key: "enter" | "tab" | "escape" }
  | { type: "stop"; outcome: "success" | "failure" | "partial"; reason: string };

export type UxSignal =
  | "confusion"
  | "confidence"
  | "hesitation"
  | "friction"
  | "progress"
  | "drop_off"
  | "neutral";

export type JourneyStep = {
  step: number;
  screenshot: string;
  thought: string;
  action: JourneyAction;
  uxSignal: UxSignal;
  pageSummary: string;
  result: string;
};

export type SimulationReport = {
  outcome: "success" | "failure" | "partial";
  summary: string;
  personaNarrative: string;
  frictionMoments: {
    step: number;
    severity: "low" | "medium" | "high";
    finding: string;
    screenshot: string;
    recommendation: string;
  }[];
  recommendations: string[];
};

export type SimulationRun = {
  id: string;
  url: string;
  goal: string;
  audience?: string;
  status: "draft" | "running" | "completed" | "failed";
  persona?: Persona;
  steps: JourneyStep[];
  report?: SimulationReport;
  error?: string;
  createdAt: string;
  updatedAt: string;
};

export type RunSummary = {
  id: string;
  url: string;
  goal: string;
  audience?: string;
  status: SimulationRun["status"];
  createdAt: string;
  updatedAt: string;
  steps: number;
  findings: number;
  outcome?: SimulationReport["outcome"];
};
