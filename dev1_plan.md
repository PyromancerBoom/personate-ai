# Dev 1 Plan: Python FastAPI Simulation Engine

> **Implementation note:** the shipped backend uses **Google Gemini** (env var
> `GEMINI_API_KEY`, default model `gemini-2.5-pro`) instead of OpenAI as
> originally planned. The `AIProvider` protocol is unchanged. See
> `backend/README.md` for current setup.

## Summary

Dev 1 owns the backend simulation engine for Personate AI: a one-persona UX simulator that uses OpenAI vision and Playwright to operate a live web product, save screenshots and journey logs, and return final report data Dev 2 can render.

Implement this as a Python FastAPI backend in `backend/`. For now, assume the full simulation happens in the backend. Dev 2's frontend only initializes a run and views the completed report. Keep the wire contract compatible with the shared TypeScript shapes in `dev2_plan.md`.

Dev 1 does not own app screens, visual design, report layout, dashboard polish, or frontend state management. Dev 1 does own run orchestration, browser progress, step recording, and report generation.

## Runtime And Dependencies

Use Python 3.11+.

Create this backend structure:

```txt
backend/
  app/
    __init__.py
    main.py
    config.py
    models.py
    storage.py
    ai_provider.py
    browser.py
    simulation.py
  requirements.txt
  README.md
runs/
  .gitkeep
```

Required Python packages:

```txt
fastapi
uvicorn[standard]
pydantic
pydantic-settings
playwright
openai
python-multipart
pytest
pytest-asyncio
httpx
```

After installing requirements, the developer should run:

```bash
python -m playwright install chromium
```

Environment variables:

```txt
OPENAI_API_KEY=required for create/run/report endpoints
OPENAI_MODEL=gpt-5.5
PLAYWRIGHT_HEADLESS=false
MAX_JOURNEY_STEPS=12
RUNS_DIR=../runs
```

Defaults:

- `OPENAI_MODEL` defaults to `gpt-5.5`.
- `PLAYWRIGHT_HEADLESS` defaults to `false` for demo visibility.
- `MAX_JOURNEY_STEPS` defaults to `12`.
- Browser viewport defaults to `1280x900`.
- CORS allows `http://localhost:3000`, `http://localhost:5173`, and `http://localhost:5174`.

OpenAI implementation basis:

- GPT-5.5 supports image input, Responses API, and structured outputs: https://developers.openai.com/api/docs/models/gpt-5.5
- Responses image input is documented here: https://developers.openai.com/api/docs/guides/images-vision
- Pydantic structured outputs are documented here: https://developers.openai.com/api/docs/guides/structured-outputs

## Public API Contract

Use FastAPI routes under `/api`.

### `POST /api/runs`

Creates a run, calls OpenAI to generate one persona, saves `run.json`, and returns `SimulationRun`.

Request body:

```json
{
  "url": "http://localhost:3000",
  "goal": "Test whether a new user can create their first project.",
  "audience": "Non-technical small business owners"
}
```

Behavior:

- Validate `url` as `http` or `https`; local URLs are allowed.
- Reject `file://`, empty URLs, and empty goals with `400`.
- If `OPENAI_API_KEY` is missing, return `500` with a clear error message.
- Create a run with status `draft`.
- Generate exactly one persona through `AIProvider.generate_persona`.
- Persist the run to `runs/{runId}/run.json`.
- Return the full run object.

### `POST /api/runs/{run_id}/start`

Runs the Playwright simulation end-to-end in the backend and returns the completed or failed `SimulationRun`.

Behavior:

- Return `404` if the run does not exist.
- Return `409` if the run is already `running`.
- Return `409` if the run is already `completed`.
- Set status to `running`, clear any old `error`, update `updatedAt`, and save `run.json`.
- Run the full simulation loop before returning.
- Return the final run with status `completed` and `report`, or status `failed` and `error`.
- The frontend should not render live progress in v1.

Do not implement streaming or live polling for v1.

### `GET /api/runs/{run_id}`

Returns the latest `SimulationRun` from disk. In v1 this is mainly for loading the final report or debugging a saved run, not for live progress UI.

Behavior:

- Return `404` if the run does not exist.
- Return the same camelCase JSON shape used by `POST /api/runs`.

### `GET /api/runs/{run_id}/screenshots/{file}`

Returns a screenshot image.

Behavior:

- Only serve files inside `runs/{runId}/screenshots/`.
- Reject path traversal and non-`.png` files with `400` or `404`.
- Each `JourneyStep.screenshot` must be a directly renderable URL in this form:

```txt
/api/runs/{runId}/screenshots/step_001.png
```

## Shared Data Models

Use Pydantic models in `backend/app/models.py`. Python internals can use snake_case, but all API JSON must use camelCase aliases.

Shared TypeScript contract for Dev 2:

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

Implementation notes:

- Use `Literal` types for status, outcome, severity, action types, and UX signals.
- Use discriminated unions for `JourneyAction`.
- Use `model_config = ConfigDict(populate_by_name=True, alias_generator=...)` or explicit `Field(alias=...)`.
- Always serialize responses with aliases so Dev 2 receives camelCase.

## Module Responsibilities

### `config.py`

Own settings and environment parsing.

Required settings:

- `openai_api_key`
- `openai_model`
- `playwright_headless`
- `max_journey_steps`
- `runs_dir`
- `allowed_origins`

### `models.py`

Own all request, response, storage, and OpenAI structured-output models.

Include separate OpenAI output models if needed:

- `PersonaOutput`
- `DecisionOutput`
- `ReportOutput`

Convert these into the public API models before saving.

### `storage.py`

Own local file storage.

Responsibilities:

- Create `runs/{runId}/`.
- Create `runs/{runId}/screenshots/`.
- Read and write `run.json`.
- Write `report.json`.
- Resolve screenshot paths safely.
- Perform atomic JSON writes by writing a temporary file and replacing the target.

Storage layout:

```txt
runs/
  {runId}/
    run.json
    report.json
    screenshots/
      step_001.png
      step_002.png
```

`run.json` is the source of truth for saved run state. It must include the latest status, persona, steps, report, error, `createdAt`, and `updatedAt`.

### `ai_provider.py`

Own model-specific behavior behind a small provider protocol.

Provider contract:

```py
class AIProvider(Protocol):
    async def generate_persona(self, input: SimulationInput) -> Persona: ...

    async def decide_next_action(
        self,
        *,
        persona: Persona,
        goal: str,
        current_step: int,
        screenshot_path: Path,
        previous_steps: list[JourneyStep],
    ) -> DecisionOutput: ...

    async def generate_report(
        self,
        *,
        run: SimulationRun,
        persona: Persona,
        steps: list[JourneyStep],
    ) -> SimulationReport: ...
```

Default implementation:

- `OpenAIGPT55Provider`
- Uses `AsyncOpenAI`.
- Uses the Responses API.
- Sends screenshots as image input for `decide_next_action`.
- Uses structured outputs with Pydantic schemas for persona, decision, and report generation.

Prompting rules:

- The model is simulating a realistic user persona, not a QA automation bot.
- The model must decide from screenshots and visible context.
- The model must not rely on DOM selectors.
- The model must choose exactly one supported action.
- The model should stop when the task is clearly complete, clearly blocked, or no useful progress remains.
- The model must include a concise user-like thought, a page summary, and one UX signal.

Malformed response handling:

- Validate every OpenAI response through Pydantic.
- If validation fails, retry once with a repair prompt.
- If it fails again, create a `stop` action with `outcome: "partial"` and a clear reason.

### `browser.py`

Own Playwright browser lifecycle and action execution.

Responsibilities:

- Launch Chromium through `async_playwright`.
- Open the target URL.
- Set viewport to `1280x900`.
- Capture screenshots to the path provided by `storage.py`.
- Execute supported actions.
- Return a human-readable `result` for every action.

Supported actions:

```txt
click(x, y)
type(text)
scroll_down()
back()
wait()
stop(success/failure/partial)
```

Action rules:

- Clamp click and type coordinates to the viewport.
- For `click`, use `page.mouse.click(x, y)`.
- For `type`, click coordinates first if provided, then use `page.keyboard.type(text)`.
- For `scroll_down`, scroll by roughly 70 percent of viewport height.
- For `back`, use browser history and record whether navigation happened.
- For `wait`, wait about 1000 ms.
- For `stop`, do not perform browser interaction.
- DOM access is allowed only for technical safety checks, never for AI decision-making.

### `simulation.py`

Own the end-to-end simulation loop.

Target behavior:

```txt
load run
ensure persona exists
open URL with Playwright
for each step up to MAX_JOURNEY_STEPS:
  take screenshot
  ask AI provider for thought, action, UX signal, and page summary
  validate and execute action
  append step
  save run.json
  stop if action is stop
generate report
save report.json
save completed run
```

Failure behavior:

- If browser launch or navigation fails, mark run `failed`, set `error`, save `run.json`, and stop.
- If OpenAI fails before any useful decision, mark run `failed`, set `error`, save `run.json`, and stop.
- If a later OpenAI decision is malformed twice, append a partial stop step and continue to report generation.
- If max steps is reached without explicit stop, generate a partial report.
- Always close the browser context.

Step persistence:

- Screenshot before each AI decision.
- Save screenshots as `step_001.png`, `step_002.png`, etc.
- Store the API screenshot URL in `JourneyStep.screenshot`.
- Save `run.json` after every appended step so backend failures are recoverable and the final report has complete evidence.

Report rules:

- `frictionMoments[].screenshot` must reference screenshots from real journey steps.
- `frictionMoments[].step` must match an existing step number.
- `outcome` must be `success`, `failure`, or `partial`.
- A completed run must include `report`.

### `main.py`

Own FastAPI app setup and routes.

Responsibilities:

- Configure CORS.
- Create one `Settings` instance.
- Create one `RunStorage` instance.
- Create one `OpenAIGPT55Provider` instance per app process.
- Register API routes.
- Run `POST /api/runs/{run_id}/start` as an awaited end-to-end backend operation for v1.
- Return Pydantic models serialized with aliases.

## Build Phases

### Phase 1: Backend Scaffold And Contracts

Goal: Dev 2 can call the backend to initialize a run and receive stable run/persona data.

Build:

- `backend/` package structure.
- Requirements file and backend README.
- Pydantic models with camelCase API serialization.
- Settings loader.
- Storage helpers.
- FastAPI app with CORS.
- `POST /api/runs`.
- `GET /api/runs/{run_id}`.
- OpenAI persona generation.

Done when:

- `uvicorn app.main:app --reload` starts from `backend/`.
- `POST /api/runs` creates `runs/{runId}/run.json`.
- Returned JSON matches Dev 2's shared contract.

### Phase 2: Playwright Runner

Goal: A run can operate a real browser and record journey evidence entirely in the backend.

Build:

- Async Playwright launcher.
- Browser navigation.
- Screenshot capture.
- Action executor.
- `POST /api/runs/{run_id}/start`.
- Step-by-step `run.json` updates for backend durability.
- Screenshot serving route.

Done when:

- A real URL opens in Chromium.
- At least 5 steps can be recorded against a simple local test page.
- Screenshots are saved and renderable through the API route.

### Phase 3: GPT-5.5 Decision Loop

Goal: OpenAI chooses browser actions from screenshots.

Build:

- `OpenAIGPT55Provider.decide_next_action`.
- Screenshot image input.
- Structured decision output.
- Action validation.
- One retry for malformed model responses.
- Partial-stop fallback after repeated malformed responses.

Done when:

- OpenAI can choose actions from screenshots.
- The simulation still works through the same API contract.
- Invalid AI output does not crash the run.

### Phase 4: Report Data

Goal: Completed runs include report data Dev 2 can render directly.

Build:

- `OpenAIGPT55Provider.generate_report`.
- Screenshot-backed friction moments.
- Outcome classification.
- Recommendations.
- `report.json` persistence.
- Failed-run error handling.

Done when:

- A completed run includes `report`.
- Report findings reference real step screenshots.
- Dev 2 can render the final report without extra transformation.

## Test Plan

### Unit Tests

Cover:

- Pydantic camelCase alias serialization and parsing.
- `SimulationRun.error` is optional and omitted when empty.
- URL validation accepts `http` and `https`, including localhost.
- URL validation rejects `file://`.
- Action validation accepts all supported actions.
- Coordinate clamping for click and type actions.
- Storage creates the expected directory layout.
- Storage reads and writes `run.json`.
- Screenshot path resolution rejects traversal.
- Malformed OpenAI response retries once, then produces a partial stop.

### API Tests

Use FastAPI test client or `httpx`.

Cover:

- `POST /api/runs` returns a run with persona.
- `GET /api/runs/{run_id}` returns saved state.
- `GET /api/runs/{missing}` returns `404`.
- `POST /api/runs/{run_id}/start` returns a completed or failed run after executing the backend simulation.
- Starting an already running run returns `409`.
- Missing OpenAI API key returns a clear error.
- Screenshot route serves `.png` files.
- Screenshot route rejects traversal.
- Failed simulation returns status `failed` and `error`.

### Playwright Smoke Test

Use a tiny local HTML page and a stub test provider.

Cover:

- Navigate to local page.
- Capture screenshot.
- Execute click.
- Execute type.
- Execute scroll.
- Append steps.
- Save screenshot-backed `run.json`.

The product runtime should use OpenAI first. The stub provider is allowed only for tests.

### Manual OpenAI Smoke Test

Run against a local demo product.

Acceptance:

- `POST /api/runs` creates a plausible persona.
- `POST /api/runs/{run_id}/start` runs the backend simulation and returns the final run.
- The run records 5 or more steps.
- Each step has screenshot, thought, action, UX signal, page summary, and result.
- The final run status is `completed`.
- The final report includes screenshot-backed findings and recommendations.

## Integration Checkpoints

### Checkpoint 1

Dev 2 can call `POST /api/runs` and render the generated persona.

### Checkpoint 2

Dev 2 can call `POST /api/runs/{run_id}/start` and receive a final completed or failed run without rendering live progress.

### Checkpoint 3

Dev 2 can render a completed report from `GET /api/runs/{run_id}` without transforming backend data.

## Demo Success Criteria

- A judge can enter a local or public web app URL and goal in Dev 2's UI.
- Dev 1 creates one believable persona through OpenAI.
- A real Chromium browser opens the target URL.
- The persona makes visible actions without manual control.
- Screenshots are saved for every decision step.
- Each step includes thought, action, UX signal, page summary, and result.
- The final report includes screenshot-backed findings.
- Dev 2 can render the final report through the public API.

## Assumptions

- Dev 2 runs as a separate frontend process and calls this backend over HTTP only to initialize runs and view completed reports.
- Live progress UI, streaming, and polling are out of scope for v1.
- Complex authentication, multi-tab flows, desktop apps, and mobile native apps remain out of MVP scope.
- The only shared contract change from the previous plans is optional `error?: string` on `SimulationRun`.
- Do not change `dev2_plan.md` until Dev 1 and Dev 2 explicitly coordinate that optional `error` field.
