# Dev 1 Plan: Simulation Engine

## Ownership

Dev 1 owns the backend simulation loop: AI persona generation, Playwright browser control, screenshot capture, action execution, journey logging, and report generation hooks.

The goal is to produce reliable journey data that the UI can display immediately.

Dev 1 should not own app screens, visual design, report layout, or dashboard polish. Those belong to Dev 2.

## Core Responsibilities

- Build the AI provider interface.
- Implement the default GPT-5.5 provider.
- Generate one realistic persona from URL, goal, and optional audience.
- Launch a Playwright browser session for the target URL.
- Take a screenshot before each AI decision.
- Ask the AI provider for the next action using persona, goal, screenshot, and previous steps.
- Execute supported actions through Playwright.
- Save every screenshot and journey step.
- Stop after success, failure, or the 10-15 step limit.
- Generate the final screenshot-backed simulation report.

## Suggested File Ownership

```txt
lib/ai/*
lib/simulation/*
lib/playwright/*
lib/storage/*
runs/*
```

If the app framework is not scaffolded yet, create these modules wherever the backend/API code naturally lives.

## Build Priority

Prioritize a working end-to-end simulation over depth.

The first useful version can use a mock AI provider and a simple generated report as long as it:

- Accepts URL, goal, and audience.
- Creates one persona.
- Opens the URL in Playwright.
- Captures screenshots.
- Produces journey steps.
- Saves run state for the UI.

After that works, improve GPT-5.5 reasoning, action quality, and report quality.

## Shared Types

Coordinate with Dev 2 before changing these shapes.

```ts
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
  | { type: "click"; coordinates: [number, number] }
  | { type: "type"; text: string; coordinates?: [number, number] }
  | { type: "scroll_down" }
  | { type: "back" }
  | { type: "wait" }
  | { type: "stop"; outcome: "success" | "failure" | "partial"; reason: string };

export type JourneyStep = {
  step: number;
  screenshot: string;
  thought: string;
  action: JourneyAction;
  uxSignal: "confusion" | "confidence" | "hesitation" | "friction" | "progress" | "drop_off" | "neutral";
  pageSummary: string;
  result: string;
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
  createdAt: string;
  updatedAt: string;
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
```

## AI Provider Interface

Keep all model-specific code behind this interface.

```ts
export interface AIProvider {
  generatePersona(input: SimulationInput): Promise<Persona>;
  decideNextAction(input: {
    persona: Persona;
    goal: string;
    currentStep: number;
    screenshotPath: string;
    previousSteps: JourneyStep[];
  }): Promise<{
    thought: string;
    action: JourneyAction;
    uxSignal: JourneyStep["uxSignal"];
    pageSummary: string;
  }>;
  generateReport(input: {
    run: SimulationRun;
    persona: Persona;
    steps: JourneyStep[];
  }): Promise<SimulationReport>;
}
```

Default implementation:

- `OpenAIGPT55Provider`

Do not let the rest of the app call OpenAI directly. The simulation loop should only depend on `AIProvider`.

## Simulation Loop

Target behavior:

```txt
create run
generate persona
open URL with Playwright
for each step:
  take screenshot
  ask AI provider for thought, action, UX signal, and page summary
  execute action
  save step
  stop if action is stop
generate report
save completed run
```

Supported actions:

```txt
click(x, y)
type(text)
scroll_down()
back()
wait()
stop(success/failure/partial)
```

Rules:

- Use screenshots for AI decisions.
- Do not use DOM selectors for persona decisions.
- DOM access is allowed only for technical safety checks if needed.
- Keep the run to 10-15 steps.
- Save screenshots with stable paths such as `runs/{runId}/screenshots/step_001.png`.
- Save step logs in a format Dev 2 can read while the run is active.

## Storage Contract

Minimum local storage layout:

```txt
runs/
  {runId}/
    run.json
    report.json
    screenshots/
      step_001.png
      step_002.png
```

`run.json` should include the latest run state, persona, and steps.

Dev 2 should be able to build the UI against this file structure even before real API routes are finalized.

## API Endpoints To Provide

If using Next.js or a similar web framework, expose:

```txt
POST /api/runs
  body: { url, goal, audience? }
  creates run + persona

POST /api/runs/:id/start
  starts the Playwright simulation

GET /api/runs/:id
  returns run state, persona, steps, report

GET /api/runs/:id/screenshots/:file
  returns screenshot image
```

If streaming is easy, add:

```txt
GET /api/runs/:id/events
```

Otherwise, Dev 2 can poll `GET /api/runs/:id`.

## Phased Plan

### Phase 1: Working Engine Skeleton

Goal: create a thin end-to-end backend path that Dev 2 can connect to quickly.

Build:

- Shared types.
- Local run storage helpers.
- `POST /api/runs`.
- `GET /api/runs/:id`.
- Mock AI provider.
- Mock persona generation.
- Mock journey steps if Playwright is not ready yet.

Done when:

- Dev 2 can create a run and receive a persona.
- Dev 2 can fetch a run with steps using the agreed contract.

### Phase 2: Playwright Runner

Goal: make the simulation operate a real browser.

Build:

- Playwright browser launcher.
- URL navigation.
- Screenshot capture.
- Action executor for `click`, `type`, `scroll_down`, `back`, `wait`, and `stop`.
- `POST /api/runs/:id/start`.
- Step-by-step `run.json` updates.

Done when:

- A real URL opens in Playwright.
- At least 5 steps can be recorded.
- Screenshots are saved and visible to Dev 2.

### Phase 3: GPT-5.5 Provider

Goal: replace mock decisions with real AI decisions behind the provider interface.

Build:

- `OpenAIGPT55Provider.generatePersona`.
- `OpenAIGPT55Provider.decideNextAction`.
- Prompting for screenshot-based decision-making.
- Response validation for invalid actions.
- Fallback behavior when the AI response is malformed.

Done when:

- GPT-5.5 can generate a persona.
- GPT-5.5 can choose browser actions from screenshots.
- The simulation still works through the same API contract.

### Phase 4: Report Data

Goal: produce the final report data consumed by Dev 2.

Build:

- `OpenAIGPT55Provider.generateReport`.
- Screenshot-backed friction moments.
- Outcome classification: success, failure, or partial.
- Recommendations.
- Basic run failure handling.

Done when:

- A completed run includes `report`.
- Report findings reference real step screenshots.
- Dev 2 can render the final report without extra transformation.

## Integration Checkpoints

### Checkpoint 1

Dev 2 can call `POST /api/runs` and receive a generated persona.

### Checkpoint 2

Dev 2 can call `POST /api/runs/:id/start` and see `run.json` update with screenshots and steps.

### Checkpoint 3

Dev 2 can render a completed report from `GET /api/runs/:id`.

## Demo Success Criteria

- A real browser opens a target URL.
- The persona makes at least 5 visible actions without manual control.
- Screenshots are saved for each step.
- Each step has a thought, action, UX signal, and page summary.
- The final report includes screenshot-backed findings.
