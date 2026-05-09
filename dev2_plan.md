# Dev 2 Plan: Product UI And Report Experience

## Ownership

Dev 2 owns the user-facing product: setup flow, persona preview, live run screen, journey timeline, final screenshot-backed report, and demo polish.

The goal is to make the simulation understandable, impressive, and easy to demo, even while Dev 1 is still wiring the real engine.

Dev 2 should not own AI provider logic, Playwright browser execution, run storage internals, or backend simulation decisions. Those belong to Dev 1.

## Core Responsibilities

- Build the setup screen for URL, goal, and optional audience.
- Show the generated persona.
- Start a simulation run.
- Display live run progress.
- Show the current screenshot, thought, action, and UX signal.
- Render a step-by-step journey timeline.
- Build the final simulation report screen.
- Highlight screenshot-backed friction moments.
- Add polished empty, loading, running, completed, and failed states.
- Support fake sample data first, then connect to Dev 1's API.

## Suggested File Ownership

```txt
app/*
components/*
lib/report/*
lib/client/*
public/demo/*
```

Avoid editing `lib/ai`, `lib/simulation`, or `lib/playwright` unless coordinating with Dev 1.

## Build Priority

Prioritize a working visible product over depth.

The first useful version can run entirely from fake data as long as it shows:

- Setup form.
- Persona preview.
- Simulated run progress.
- Screenshot area.
- Journey timeline.
- Final report with screenshot-backed findings.

After that works, connect the UI to Dev 1's real APIs and improve report polish.

## Shared Types

Use these shapes from the shared contract. Coordinate with Dev 1 before changing them.

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
  createdAt: string;
  updatedAt: string;
};
```

## Primary Screens

### 1. Setup Screen

Purpose: let users define the simulation.

Required UI:

- URL input.
- Goal textarea.
- Optional audience input.
- Generate Persona button.
- Persona preview area.
- Start Simulation button after persona exists.

Behavior:

- Validate that URL and goal are present.
- Call `POST /api/runs`.
- Show the returned persona.
- Allow the user to start the simulation.

### 2. Run Screen

Purpose: make the live simulation visible.

Required UI:

- Persona card.
- Run status.
- Step progress.
- Current screenshot.
- Current thought.
- Current action.
- Current UX signal.
- Journey timeline.

Behavior:

- Call `POST /api/runs/:id/start`.
- Poll `GET /api/runs/:id` every 1-2 seconds, or consume events if Dev 1 provides streaming.
- Update the current step as new screenshots and logs arrive.
- Keep completed steps visible in the timeline.
- Show a transition to the final report when the run completes.

### 3. Insights Screen

Purpose: turn the raw journey into a clear product story.

Required UI:

- Outcome: success, failure, or partial.
- Persona journey narrative.
- Timeline with screenshots for each step.
- Key friction moments with screenshot evidence.
- Severity labels.
- Recommendations.
- Screenshot references for each finding.

Report design goal:

The report should feel like a lightweight UX research artifact, not a QA dashboard.

## API Contract

Build against these endpoints from Dev 1.

```txt
POST /api/runs
  body: { url, goal, audience? }
  returns: SimulationRun with persona

POST /api/runs/:id/start
  returns: SimulationRun

GET /api/runs/:id
  returns: SimulationRun
```

Screenshot paths in `JourneyStep.screenshot` should be directly renderable by the UI.

## Fake Data First

Do not wait for the real simulation engine.

Create a fake run object with:

- 1 persona.
- 6-8 journey steps.
- Placeholder screenshots.
- Mixed UX signals.
- 2-3 friction moments.
- A final report.

Use this to finish the UI while Dev 1 builds the engine.

Example fake scenario:

```txt
Goal: Create a first project after landing on the dashboard.
Friction: The persona does not recognize where onboarding starts.
Outcome: partial.
```

## UI States

Cover these states:

- Empty setup.
- Persona generating.
- Persona generated.
- Simulation starting.
- Simulation running.
- Step updated.
- Simulation completed.
- Simulation failed.
- Report loading.
- Report ready.

## Design Priorities

- Make screenshots large and central.
- Make the persona feel real, but keep the UI work-focused.
- Use compact cards for timeline steps and findings.
- Make UX signals easy to scan with restrained labels.
- Keep the report evidence-first: finding, screenshot, recommendation.
- Avoid making it look like a test automation tool.

## Phased Plan

### Phase 1: Working UI Skeleton

Goal: create a complete visible flow using fake data.

Build:

- Shared type imports or local matching types.
- Fake run data.
- Setup screen.
- Persona preview card.
- Run screen shell.
- Final report screen shell.

Done when:

- A user can move through setup, persona preview, run, and report without real backend data.
- The app already looks like the intended product demo.

### Phase 2: Live Run Experience

Goal: make the simulation feel alive using fake or partial backend data.

Build:

- Current screenshot panel.
- Current thought panel.
- Current action panel.
- Current UX signal display.
- Step progress indicator.
- Journey timeline.
- Loading, running, completed, and failed states.

Done when:

- The run screen visibly updates over steps.
- Screenshots are central and easy to inspect.
- The timeline clearly explains what the persona did.

### Phase 3: API Integration

Goal: connect the UI to Dev 1's engine without changing ownership boundaries.

Build:

- `POST /api/runs` integration.
- `POST /api/runs/:id/start` integration.
- `GET /api/runs/:id` polling.
- Screenshot rendering from real paths.
- Error display for failed runs.

Done when:

- The setup form creates a real run.
- The run screen renders real steps from Dev 1.
- The report screen renders real report data.

### Phase 4: Report Polish

Goal: make the final output judge-friendly and product-research oriented.

Build:

- Outcome summary.
- Persona journey narrative.
- Screenshot-backed friction cards.
- Severity labels.
- Recommendations section.
- Clean report export or shareable report view if feasible.

Done when:

- The final report can be shown as the main demo artifact.
- Every major finding has a screenshot reference.
- The report feels like UX simulation insight, not QA automation.

## Integration Checkpoints

### Checkpoint 1

The UI can show a persona returned by Dev 1.

### Checkpoint 2

The UI can render live journey steps from Dev 1's saved run state.

### Checkpoint 3

The UI can render a complete final report with real screenshots.

## Demo Success Criteria

- A judge can enter a URL and goal.
- A believable persona appears.
- The run screen visibly updates as the AI user acts.
- Screenshots appear in the timeline.
- The final report clearly explains where the persona got stuck.
- The final report includes screenshot-backed recommendations.
