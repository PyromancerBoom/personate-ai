# Dev 2 Plan: Vite React Report UI

## Summary

Dev 2 owns the user-facing frontend for Personate AI: setup flow, generated persona preview, blocking run start state, failed-run evidence, and final screenshot-backed report rendering.

Build Dev 2 as a separate Vite + React + TypeScript app in `frontend/`. The frontend talks to Dev 1's FastAPI backend over HTTP. In v1, `POST /api/runs/{id}/start` is a blocking request that returns the final completed or failed `SimulationRun`; do not implement live polling, streaming, or real-time step updates.

Dev 2 does not own AI provider logic, Playwright execution, run storage, screenshot capture, report generation, or backend simulation decisions.

## Runtime And Dependencies

Use Node.js with Vite React TypeScript.

Frontend structure:

```txt
frontend/
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  vitest.setup.ts
  src/
    main.tsx
    App.tsx
    styles.css
    types/simulation.ts
    lib/api.ts
    mocks/mockRun.ts
    components/
```

Required frontend packages:

```txt
react
react-dom
lucide-react
vite
typescript
vitest
jsdom
@vitejs/plugin-react
@testing-library/react
@testing-library/jest-dom
@testing-library/user-event
```

Environment variables:

```txt
VITE_API_BASE_URL=http://localhost:8000
VITE_MOCK_API=false
```

Notes:

- `VITE_API_BASE_URL` defaults to `http://localhost:8000`.
- `VITE_MOCK_API=true` enables frontend-only mock data and does not require a backend or API key.
- Real runs require Dev 1's backend to be running and configured with its server-side provider key.

## Public API Contract

Build against Dev 1's routes under `/api`.

```txt
POST /api/runs
  body: { url, goal, audience? }
  returns: SimulationRun with persona

POST /api/runs/{id}/start
  returns: final SimulationRun with status completed or failed

GET /api/runs/{id}
  returns: saved SimulationRun
```

Screenshot paths come from `JourneyStep.screenshot` and `frictionMoments[].screenshot`. Treat backend-relative paths such as `/api/runs/{runId}/screenshots/step_001.png` as canonical and resolve them against `VITE_API_BASE_URL` before rendering.

## Shared Data Models

Mirror Dev 1's camelCase JSON contract in `frontend/src/types/simulation.ts`.

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
```

Do not use `screenshotUrl`; Dev 1's actual contract uses `screenshot`.

## Frontend Behavior

State machine:

```txt
idle -> creating -> personaReady -> running -> completed
                                             -> failed
```

Setup behavior:

- Validate non-empty URL and goal before calling the backend.
- Preserve entered values across failures.
- Clear stale report evidence before creating a new run.
- Disable duplicate submissions while a run is actively executing.

Persona behavior:

- Call `POST /api/runs` to create the run and generate one persona.
- Render persona background, motivation, experience level, concerns, behavioral traits, and success criteria.
- Enable Start Simulation only after a run with a persona exists.

Start behavior:

- Call `POST /api/runs/{id}/start` once and await the blocking response.
- Show elapsed time and a neutral in-progress state while the request is open.
- Do not show fake step progress as real backend progress.
- Do not set a frontend timeout by default; allow the backend request to finish.
- If the returned run has `status: "failed"`, render the failed state and any partial evidence.
- If the returned run has `status: "completed"` but no `report`, show a clear missing-report error.

Report behavior:

- Render outcome, summary, persona narrative, recommendations, journey timeline, and friction moments.
- Render every supported `JourneyAction` variant explicitly.
- Resolve screenshots with `new URL(screenshot, API_BASE_URL).toString()`.
- Gracefully handle empty `steps`, empty `frictionMoments`, empty `recommendations`, missing `report`, and failed runs with partial evidence.

Error behavior:

- Prefer backend-provided `SimulationRun.error` when available.
- Parse FastAPI `detail` responses for 400/404/409/500 errors.
- Show a clear backend-unavailable message for network failures.
- Keep the user on a recoverable screen with the setup form still populated.

## Component Ownership

Core files:

- `src/App.tsx`: top-level state machine and API flow.
- `src/types/simulation.ts`: shared contract types.
- `src/lib/api.ts`: API client, mock mode, error parsing, screenshot URL helper.
- `src/components/SetupForm.tsx`: URL/goal/audience form.
- `src/components/PersonaPreview.tsx`: generated persona and start action.
- `src/components/RunningState.tsx`: blocking-run waiting state.
- `src/components/ReportView.tsx`: final report shell.
- `src/components/Timeline.tsx`: journey steps and screenshots.
- `src/components/FrictionCards.tsx`: screenshot-backed findings.
- `src/components/ErrorState.tsx`: failed run and partial evidence.
- `src/components/ActionText.tsx`: explicit action rendering.
- `src/components/ScreenshotImage.tsx`: screenshot rendering with fallback.

## Design Priorities

- Make the UI feel like a practical UX research tool, not a QA automation console.
- Keep screenshots large enough to inspect.
- Keep the setup form visible on desktop for fast retry.
- Use restrained labels for outcome, status, severity, and UX signals.
- Avoid decorative landing-page composition; first screen should be the usable product.
- Keep empty and failed states specific, especially when backend setup is missing.

## Test Plan

Unit and component tests with Vitest + Testing Library:

- Form validation blocks empty URL and goal.
- API client builds correct URLs.
- Screenshot helper handles backend-relative and absolute URLs.
- Persona preview renders returned persona.
- Action renderer covers every `JourneyAction` variant.
- Report view renders timeline, friction moments, recommendations, and empty states.
- Failed state renders backend `error`.
- Running state disables duplicate starts and setup submission.
- Creating a new run clears stale report evidence.

Manual scenarios:

- Mock happy path with `VITE_MOCK_API=true`.
- Mock failed path.
- Backend unavailable.
- Real backend create + blocking start + final report.
- Backend-relative screenshot rendering.
- Desktop and mobile viewport checks.

## Integration Checkpoints

### Checkpoint 1

Dev 2 can run `npm run dev` from `frontend/`, create a mock run, and render the complete report without Dev 1's backend.

### Checkpoint 2

Dev 2 can point `VITE_API_BASE_URL` at Dev 1's backend, call `POST /api/runs`, and render the generated persona.

### Checkpoint 3

Dev 2 can call blocking `POST /api/runs/{id}/start`, wait for the returned final run, and render completed or failed evidence without polling.

## Assumptions

- Dev 1 backend runs separately at `http://localhost:8000`.
- The frontend does not receive or store provider API keys.
- Real provider credentials live only in Dev 1's backend environment.
- Live progress, polling, and streaming are out of scope for v1.
- Complex authentication flows and mobile-native products are out of MVP scope.
