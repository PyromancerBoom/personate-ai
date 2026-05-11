# Architecture

Personate AI is a local-first UX simulation system. It accepts a target website, a user goal, and an optional audience, then creates one realistic persona, drives a real browser as that persona, records the journey, and turns the evidence into a UX report.

The core design idea is simple: keep the AI responsible for judgment and interpretation, while keeping the application responsible for state, browser control, validation, persistence, and API boundaries.

## Design Goals

- **Evidence-first UX reports.** Every report is grounded in journey steps and screenshots captured during the run.
- **Provider independence.** Gemini and OpenAI sit behind the same `AIProvider` protocol so model vendors can change without rewriting the simulation loop.
- **Browser realism.** The system uses Playwright to interact with real pages instead of mocked DOMs or handcrafted flows.
- **Recoverable local persistence.** Runs are saved after every step so a process crash does not erase the journey so far.
- **Small public surface.** The frontend talks to a compact REST API, and all provider keys stay server-side.
- **Debuggability.** Each run creates human-readable JSON plus screenshots under `runs/{runId}/`.

## High-Level System

```txt
User
  |
  v
React + Vite frontend
  - setup form
  - persona preview
  - saved-run history
  - screenshot-backed report UI
  |
  | HTTP JSON
  v
FastAPI backend
  - validates inputs
  - owns run state
  - serves run JSON and screenshots
  - coordinates provider + browser
  |
  +--> AIProvider adapter
  |      - GeminiProvider
  |      - OpenAIProvider
  |      - structured JSON validation
  |
  +--> Playwright BrowserSession
  |      - Chromium page
  |      - screenshots
  |      - interactable element index
  |      - action execution
  |
  v
Filesystem storage
  - runs/{runId}/run.json
  - runs/{runId}/report.json
  - runs/{runId}/screenshots/*.png
```

## Request Lifecycle

### 1. Create Draft Run

`POST /api/runs`

1. The frontend sends `{ url, goal, audience? }`.
2. FastAPI validates that the URL is non-empty and uses `http` or `https`.
3. The backend checks that the configured provider key exists.
4. `RunStorage` creates a 12-character run ID.
5. The provider generates one persona from the URL, goal, and audience.
6. The backend saves `run.json` with status `draft`.
7. The frontend displays the persona and waits for the user to start the run.

### 2. Start Simulation

`POST /api/runs/{runId}/start`

1. The backend loads the saved run.
2. It rejects missing runs, already-running runs, and completed runs.
3. It marks the run `running` and persists that state.
4. `run_simulation()` opens Chromium through Playwright and navigates to the target URL.
5. The backend enters the step loop.

### 3. Step Loop

For each step up to `MAX_JOURNEY_STEPS`:

1. Capture `screenshots/step_NNN.png`.
2. Index visible interactable elements in the page.
3. Send persona, goal, screenshot, recent step history, and element list to the AI provider.
4. Validate the provider's structured `DecisionOutput`.
5. Convert the decision into a typed action such as `click`, `type`, `scroll_down`, or `stop`.
6. Execute the action in Playwright.
7. Append a `JourneyStep` containing thought, action, result, UX signal, page summary, and screenshot URL.
8. Save `run.json`.
9. Stop if the provider chooses `stop`.

### 4. Report Generation

After the browser loop ends:

1. The provider receives the completed journey log.
2. It returns a structured report with outcome, summary, persona narrative, friction moments, and recommendations.
3. The backend filters friction evidence to valid recorded step numbers.
4. The backend saves `report.json` and updates `run.json` with status `completed`.
5. If report generation fails, the run is marked `failed` with the error, while the recorded journey remains available.

## Simulation State Machine

```txt
draft
  |
  | POST /api/runs/{runId}/start
  v
running
  |
  +--> completed
  |      report generated successfully
  |
  +--> failed
         browser launch failed
         screenshot failed
         report generation failed
         process restarted while running
```

`POST /api/runs/{runId}/start` returns HTTP 200 for completed runs and run-level failures. The frontend must inspect `status` rather than treating every 200 as success.

Request-level problems still use normal HTTP errors:

- `400` for invalid input or invalid screenshot paths.
- `404` for missing runs or screenshots.
- `409` for invalid run transitions, such as starting an already-running run.
- `500` for missing provider configuration.
- `502` for persona generation failure.

## Backend Components

### `main.py`

Defines the FastAPI app, CORS config, dependency injection, and REST routes. It keeps HTTP concerns close to the boundary and delegates persistence to `RunStorage`, provider calls to `AIProvider`, and browser execution to `run_simulation()`.

On Windows, it sets `WindowsProactorEventLoopPolicy` before Uvicorn creates the event loop. This matters because Playwright launches Chromium through subprocess APIs that require the Proactor loop on Windows.

### `simulation.py`

Owns the orchestration loop. It is deliberately the only place where provider decisions, browser actions, journey step creation, and run persistence meet.

Important behavior:

- Saves the run after every successful step.
- Converts provider failure after at least one step into a forced partial stop rather than discarding the journey.
- Marks the run failed for unrecoverable failures before any useful journey exists.
- Always closes the browser in a `finally` block.

### `browser.py`

Wraps one Playwright Chromium page.

Responsibilities:

- Launch a browser context with configured viewport.
- Capture viewport screenshots.
- Build a numbered list of interactable elements.
- Execute typed actions selected by the AI provider.
- Wait for the page to settle after actions.

The element index is intentionally constrained. The provider can only click or type into elements that Playwright discovered and numbered. This reduces hallucinated selectors and keeps actions tied to what is actually visible or near the viewport.

The settle logic avoids relying only on Playwright `networkidle`, which is brittle for SPAs and pages with long-lived network activity. Instead, the browser waits for document readiness, painted body content, a quiet DOM mutation window, and a compositor frame before the next screenshot.

Typing uses tiered strategies:

1. Native `fill()` for plain inputs and textareas.
2. Focus, clear through JavaScript, and keyboard typing for rich editors.
3. Select-all plus typing as a fallback.

That extra work makes sites like Tally, Notion-style editors, and contenteditable fields more likely to behave like they would for a real user.

### `ai_provider.py`

Defines the model boundary. The backend calls the protocol, not a vendor SDK directly:

```txt
generate_persona(input) -> Persona
decide_next_action(persona, goal, current_step, screenshot_path, previous_steps, elements) -> DecisionOutput
generate_report(run, persona, steps) -> SimulationReport
```

Gemini uses native structured output schemas. OpenAI uses strict JSON schema responses derived from Pydantic models. Both providers validate responses before returning application models to the rest of the backend.

The provider prompts are split by responsibility:

- Persona generation prompt creates one believable user.
- Decision prompt roleplays that user and returns one grounded browser action.
- Report prompt summarizes only recorded evidence.

### `models.py`

Contains the shared domain model.

Key models:

- `SimulationInput`: URL, goal, optional audience.
- `Persona`: generated fictional user.
- `SimulationRun`: full persisted run.
- `RunSummary`: compact saved-run list item.
- `JourneyStep`: one screenshot-backed browser step.
- `JourneyAction`: discriminated union of supported browser actions.
- `SimulationReport`: final UX report.

API JSON uses camelCase through the shared `CamelModel` base class, while Python code can use snake_case.

### `storage.py`

Persists runs on the local filesystem.

Storage choices:

- `run.json` is the main source of truth.
- `report.json` is saved separately for easier inspection.
- Screenshots are stored as PNG files.
- JSON writes are atomic, using a temporary file followed by `os.replace()`.
- Screenshot serving validates run IDs and file names to avoid path traversal.
- Startup sweeps orphaned `running` runs to `failed`, which prevents permanent 409 responses after a server restart.

## Frontend Components

The frontend is a thin stateful client over the backend API.

### `App.tsx`

Coordinates the product workflow:

- setup input
- create draft run
- persona preview
- start run
- failed/completed report states
- saved-run history
- selected historical run display

The frontend does not simulate AI locally. It always talks to the backend.

### `lib/api.ts`

Provides typed API helpers:

- `createRun`
- `startRun`
- `getRun`
- `listRuns`

It normalizes the base URL from `VITE_API_BASE_URL`, defaulting to `http://localhost:8000`.

### UI Components

`components/` contains workflow-specific UI rather than domain logic:

- `SetupForm`
- `DashboardShell`
- `PersonaPreview`
- `RunningState`
- `ReportView`
- `Timeline`
- `FrictionCards`
- `ScreenshotImage`
- `ErrorState`

This keeps backend state transitions and provider behavior out of the React components.

## Data Model

Each run has this conceptual shape:

```txt
SimulationRun
  id
  url
  goal
  audience?
  status: draft | running | completed | failed
  persona?
  steps[]
    step
    screenshot
    thought
    action
    uxSignal
    pageSummary
    result
  report?
    outcome: success | failure | partial
    summary
    personaNarrative
    frictionMoments[]
    recommendations[]
  error?
  createdAt
  updatedAt
```

The report does not replace the journey. It is a derived interpretation of recorded steps, and every friction moment should point back to a real step screenshot.

## API Surface

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/runs` | Create a draft run and generated persona. |
| `GET` | `/api/runs` | List saved run summaries. |
| `GET` | `/api/runs/{runId}` | Load a full saved run. |
| `POST` | `/api/runs/{runId}/start` | Run the simulation synchronously. |
| `GET` | `/api/runs/{runId}/screenshots/{file}` | Serve a captured PNG screenshot. |

## Configuration

Important backend settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `AI_PROVIDER` | `gemini` | Selects `GeminiProvider` or `OpenAIProvider`. |
| `GEMINI_API_KEY` | empty | Server-side Gemini key. |
| `GEMINI_MODEL` | `gemini-2.5-pro` | Gemini model name. |
| `OPENAI_API_KEY` | empty | Server-side OpenAI key. |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name. |
| `PLAYWRIGHT_HEADLESS` | `false` | Whether Chromium runs headless. |
| `MAX_JOURNEY_STEPS` | `12` | Hard cap for browser steps. |
| `RUNS_DIR` | `../runs` | Filesystem location for run artifacts. |
| `VIEWPORT_WIDTH` | `1280` | Browser viewport width. |
| `VIEWPORT_HEIGHT` | `900` | Browser viewport height. |

Important frontend setting:

| Setting | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL. |

## Persistence Layout

```txt
runs/
  .gitkeep
  {runId}/
    run.json
    report.json
    screenshots/
      step_001.png
      step_002.png
```

The application can run without committed sample runs. Committed runs are only demo artifacts for readers.

## Security And Privacy Boundaries

- Provider API keys are read only by the backend from `backend/.env`.
- The frontend never receives provider keys.
- Screenshot serving is limited to validated run IDs and `.png` file names.
- The backend rejects non-HTTP URLs for new runs.
- Generated run files can contain page screenshots, typed text, target URLs, and model-generated summaries. Treat `runs/` as publishable only after manual review.
- The system is intended for trusted local use. It does not include authentication, tenant isolation, queue isolation, or sandboxed remote execution.

## Why Filesystem Storage

Filesystem storage is a good fit for the current local-first MVP:

- Easy to inspect and debug.
- No database setup for contributors.
- Screenshots and JSON stay next to each other.
- Atomic JSON writes are enough for the single-process development workflow.

A hosted version would likely replace this with a database for run metadata, object storage for screenshots, and a background job queue for simulations.

## Concurrency Model

The API supports multiple saved runs, but each `start` request runs synchronously inside the request lifecycle. There is no worker queue yet.

Implications:

- A long simulation keeps the HTTP request open.
- If the backend process dies during a run, startup marks orphaned `running` runs as `failed`.
- Two simultaneous starts for the same run are rejected once the run is marked `running`.
- Multi-user scheduling, cancellation, progress streaming, and retry queues are future work.

## Extension Points

### Add A New AI Provider

Implement the `AIProvider` protocol in `ai_provider.py`, add settings in `config.py`, and update `build_provider()`.

The provider must return validated application models, not raw vendor responses.

Note: Works best with GPT-5.5 and Opus 4.7 for vision alignment, but the structured output and validation should allow a range of models to work with varying degrees of report quality.

### Add A New Browser Action

Add a new action model in `models.py`, teach `DecisionOutput.to_action()` how to create it, update the decision prompt, and implement execution in `BrowserSession.execute()`.

### Add Hosted Execution

A production architecture would split the synchronous run endpoint into:

1. API request creates or starts a job.
2. Worker process executes Playwright and provider calls.
3. Frontend polls or subscribes for progress.
4. Artifacts are written to durable storage.

### Add Richer Reports

Reports can be expanded without changing the browser loop by extending `ReportOutput`, `SimulationReport`, and the frontend report components.

## Sample Runs

Committed runs are intended as small, reproducible examples for public readers. Prefer public, stable targets and short tasks, for example:

- `https://tally.so/`: create a simple feedback form.
- `https://demo.playwright.dev/todomvc/`: add todos and mark one complete.

Avoid committing private customer sites, authenticated sessions, local-only URLs, or screenshots that reveal personal data.

## Current Limitations

- One persona per run.
- One browser page per run.
- Web apps only.
- No complex login or multi-tab flows.
- No hosted infrastructure or background worker queue.
- No live progress streaming from the backend.
- No authentication or multi-tenant data isolation.
- No database-backed search or analytics over runs.
- Screenshots and reports are stored on local disk.
