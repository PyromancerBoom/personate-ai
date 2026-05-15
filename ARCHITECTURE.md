# Architecture

Personate AI is a local-first prototype for simulating UX journeys on live websites. The user supplies a URL, a goal, and an optional audience. The backend builds a persona, drives a real browser as that persona, records the journey, and turns the evidence into a UX report.

The core design choice: the AI does not drive the browser directly. The backend owns state, validation, screenshots, storage, and action execution. The AI only decides what the persona should try next.

## System Shape

```txt
React frontend
  -> FastAPI backend
    -> AI provider adapter
    -> Playwright browser session
    -> runs/{runId}/ artifacts
```

The frontend is a single-page React app that walks the user from setup → persona review → run → report. It does not own simulation state.

## Backend Responsibilities

Four pieces, kept separate so each one is easy to reason about:

- **API and state (`main.py`):** FastAPI validates the request, generates the persona, creates the run, runs `/start` synchronously, lists runs, and serves screenshots.
- **Simulation loop (`simulation.py`):** `run_simulation()` assumes a persona already exists and coordinates the browser, provider decisions, step recording, and the final report.
- **Browser control (`browser.py`):** `BrowserSession` wraps one Playwright Chromium page — screenshots, element indexing, page settling, action execution.
- **Persistence (`storage.py`):** `RunStorage` writes `run.json` and `report.json` atomically, plus screenshots, under `runs/{runId}/`.

This split keeps the loop inspectable. Browser code does not know about reports. Provider code does not write files. Storage does not decide what the user should do next.

## How The Browser Agent Works

### The loop

For each step, capped at `max_journey_steps` (default 12):

1. Take a screenshot.
2. Index visible interactable elements.
3. Send the persona, goal, screenshot, last 6 steps, and numbered element list to the provider.
4. Receive one structured decision: `thought`, `page_summary`, `ux_signal`, and an action.
5. Convert that decision into a typed action.
6. Execute the action.
7. Settle the page.
8. Record the step in `run.json`.

### Action vocabulary

The model can return exactly one of:

- `click(element_id)`
- `type(element_id, text, submit?)` — `submit=true` presses Enter after typing
- `scroll_down`
- `back`
- `wait`
- `press_key("enter" | "tab" | "escape")`
- `stop(outcome, reason)` — outcome is `success`, `failure`, or `partial`

### Element indexing

Injected JS walks the DOM, filters to visible interactables (anchors, buttons, inputs, textareas, contenteditables, ARIA-roled widgets like `role=button`/`combobox`/`tab`, `[onclick]`, and focusable `[tabindex]`), and returns each one with its tag, type, role, accessible name, and an xpath.

The list is numbered and shown to the model in a compact form:

```
[0]<a role="link">Pricing</a>
[1]<button>Sign up</button>
[2]<input type="email">your@email.com</input>
```

### Grounding contract

`click` and `type` may only refer to an integer index from the current list. The backend resolves index → cached xpath → Playwright locator. An index outside the list is rejected at execute time and recorded as the step result instead of crashing the run. This is what stops the model from inventing selectors.

### Page settling

After every action, the browser waits in three stages:

1. `wait_for_load_state("domcontentloaded")`.
2. A JS predicate that requires:
   - `document.readyState` past `loading`,
   - body has visible text or more than 50 elements (the "white page" guard),
   - and a 500ms quiet window from a `MutationObserver`.
3. Double `requestAnimationFrame` so the next screenshot captures painted pixels.

Hard-capped at 7s. Never raises — the loop must keep moving. This replaces `networkidle`, which is unreliable on Gmail, Google, and most modern SPAs (Playwright issues #1497, #2515, #6536).

### Typing fallbacks

Many real apps use rich editors instead of plain inputs, so `type` tries three strategies in order:

1. `locator.fill()` — fast path for plain `<input>` and `<textarea>`.
2. Focus + JS-clear + `page.keyboard.type()` — works on contenteditable widgets (ProseMirror, Tally, Notion) that listen for real key events.
3. Click + `Ctrl+A` + `Delete` + `keyboard.type()` — last resort for editors that only respond to select-all.

The strategy that succeeded is recorded in the step result for debugging.

## Why Build The Agent Loop Here?

Many browser-agent frameworks aim to be general task runners. Personate AI has a narrower goal: simulate a realistic user and produce UX evidence.

Owning the loop gives control over the parts that matter for UX research:

- Persona prompts can focus on habits, concerns, patience, and success criteria.
- Actions can be constrained to visible numbered elements.
- Every step saves a screenshot, thought, result, UX signal, and page summary.
- Failed or partial runs still leave behind useful evidence.
- Reports can be shaped around friction moments and recommendations.

The goal is not the most powerful web agent. The goal is a small, readable agent loop for UX experiments.

## AI Provider Boundary

The backend talks to an `AIProvider` Protocol, not directly to a vendor. The Protocol has three methods:

- `generate_persona(input)`
- `decide_next_action(persona, goal, screenshot, last 6 steps, element list)`
- `generate_report(run, persona, steps)`

Both providers (Gemini, OpenAI) return JSON validated by Pydantic. Two specifics worth knowing:

- **Flat decision schema.** Gemini's `response_schema` does not reliably handle discriminated unions, so the model returns a flat `DecisionOutput` (one `action_type` plus optional `element_id`, `text`, `submit`, `key`, `outcome`, `reason`). `DecisionOutput.to_action()` converts it into a typed `JourneyAction`.
- **OpenAI strict mode.** OpenAI's strict JSON mode requires `additionalProperties: false` and every property `required` on every object. Pydantic's emitted schema does not include those, so we patch the schema recursively before sending it.

If a provider response fails JSON validation, the provider retries once with a stricter "reply only with valid JSON" instruction. If that fails too, it returns a synthetic `stop/partial` decision so the loop records a clean failure instead of crashing.

## API Surface

```
POST   /api/runs                              create run + persona
GET    /api/runs                              list run summaries (newest first)
GET    /api/runs/{runId}                      load a run
POST   /api/runs/{runId}/start                run simulation synchronously
GET    /api/runs/{runId}/screenshots/{file}   serve a step screenshot
```

`/start` is synchronous: it returns HTTP 200 with the final run, whose `status` is `completed` or `failed`. The frontend must inspect `status` to tell the two apart. Non-2xx is reserved for request-level errors (404 for missing run, 409 for state conflict).

## Run State And Storage

A run moves through a small state machine:

```txt
draft -> running -> completed
                 -> failed
```

- `draft` — persona exists, browser has not started.
- `running` — Playwright is executing the journey.
- `completed` — final report generated.
- `failed` — stopped because of a browser, provider, or report error.

Each run is stored on disk:

```txt
runs/{runId}/
  run.json
  report.json
  screenshots/
    step_001.png
    step_002.png
```

`run.json` is the source of truth and is saved after every step. A few details that keep this safe:

- **Atomic writes.** Each save goes through `tempfile.mkstemp` + `os.replace`, so a killed process leaves either the old file or the new one — never a half-written one.
- **Orphan sweep.** On startup, `sweep_orphaned_running` scans every `run.json` and flips `running` → `failed` with error `"orphaned: process restarted while running"`. Without this, a killed `uvicorn` would leave runs that 409 forever on `/start`.
- **Run ID and path safety.** Run IDs are 12-hex-char tokens checked by regex. Screenshot serving resolves the requested path and verifies it stays inside the run's `screenshots/` dir, which blocks path-traversal.

Filesystem storage is a deliberate prototype choice — easy to inspect, easy to commit as sample output, no database setup. A hosted version would likely move metadata to a database and screenshots to object storage.

## Failure Handling

The system tries to keep useful evidence even when a run fails.

- If browser launch or the first AI decision fails, the run becomes `failed`.
- If an AI decision fails after some steps, the loop records a forced partial `stop` and stops.
- If a provider returns malformed JSON twice in a row, the loop records a forced partial `stop` rather than crashing.
- If an action references an element index that no longer exists, the error is recorded as the step result and the loop continues.
- If an action throws, the exception message is written into the step instead of crashing the run.
- If report generation fails, the journey remains saved for debugging.
- The browser is closed in a `finally` block after each run.

Failures stay visible and inspectable instead of silent.

## Weaknesses And Limitations

- Runs execute synchronously inside the HTTP request.
- There is no job queue, cancellation, or live progress stream.
- Only one persona runs at a time.
- Only one browser page is supported.
- Complex login, multi-tab flows, file uploads, and native mobile apps are out of scope.
- The agent is only as good as the screenshot, element index, and model response.
- Some custom UI widgets may not expose clean interactable elements.
- There is no authentication, multi-tenant isolation, or hosted sandbox.
- Local screenshots can contain sensitive page data, so sample runs need manual review before publishing.

## Future Extensions

- Add a background worker queue so simulations do not block HTTP requests.
- Stream step progress to the frontend with polling, SSE, or WebSockets.
- Add cancellation and retry controls.
- Store run metadata in a database and screenshots in object storage.
- Add authenticated project spaces and access control.
- Support more browser actions, such as drag, hover, upload, and multi-tab flows.
- Add richer report exports for product, design, or engineering handoff.
- Run multiple personas against the same goal and compare friction patterns.
