# Personate AI

AI-generated users for live-product UX testing.

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Node 20+](https://img.shields.io/badge/Node-20%2B-339933?logo=node.js&logoColor=white)
![License MIT](https://img.shields.io/badge/License-MIT-blue.svg)

Personate AI is a one-persona UX simulation tool for live web products. Provide a product URL, a testing goal, and an optional audience. The backend generates a persona, drives the live app through Playwright, records screenshots and journey steps, then returns a screenshot-backed UX report for the frontend to display.

## Features

- Generate a realistic user persona from a target URL, goal, and audience.
- Run that persona through a live web app with Playwright.
- Capture screenshots, thoughts, actions, UX signals, and completion status.
- Review a screenshot-backed UX report with friction moments and recommendations.
- Use Gemini or OpenAI through a small provider layer.

## Tech Stack

FastAPI, Playwright, Pydantic, React, Vite, TypeScript, Gemini, and OpenAI.

## Project Structure

```txt
backend/   FastAPI API, AI provider layer, Playwright runner, run storage
frontend/  Vite React app for setup, persona preview, run state, and reports
runs/      Generated run JSON and screenshots
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- An AI provider key for the backend
- Playwright Chromium installed for the backend environment

## Backend Setup

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies and Playwright Chromium:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Create `backend/.env` from `backend/.env.example` and set your provider key.

```txt
AI_PROVIDER=gemini

GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-pro

# Used only when AI_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

PLAYWRIGHT_HEADLESS=false
MAX_JOURNEY_STEPS=12
RUNS_DIR=../runs
```

OpenAI is also supported by the provider layer:

```txt
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

Run the backend from the `backend/` directory so `.env` is loaded correctly:

```bash
uvicorn app.main:app --reload
```

Backend URL: `http://localhost:8000`

## Frontend Setup

```bash
cd frontend
npm install
npm run dev -- --host localhost
```

Frontend URL: `http://localhost:5173`

Use `localhost`, not `127.0.0.1`, unless you also update the backend CORS `allowed_origins`. The default backend CORS config allows `http://localhost:5173`.

The frontend always talks to the real backend. There is no runtime mock simulation mode.

## Running A Simulation

1. Open `http://localhost:5173`.
2. Enter the target product URL.
3. Enter the testing goal and optional audience.
4. Generate a persona.
5. Start the simulation.
6. Review the final report with screenshots, journey steps, friction moments, and recommendations.

Generated artifacts are written under `runs/{runId}/`.

## Repository Hygiene

Local environment files, generated runs, dependency folders, Vite cache, test cache, coverage output, and local assistant/editor state are ignored by Git. Keep secrets in `backend/.env`; only commit `backend/.env.example`.

## API

- `POST /api/runs` creates a draft run and generates a persona.
- `POST /api/runs/{run_id}/start` runs the blocking Playwright simulation and returns the final run.
- `GET /api/runs/{run_id}` loads a saved run.
- `GET /api/runs/{run_id}/screenshots/{file}` serves captured screenshots.

## Checks

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm run test
npm run build
```

## Troubleshooting

- `Could not reach the backend at http://localhost:8000`: make sure the backend is running on port `8000`, and open the frontend at `http://localhost:5173`.
- `API_KEY is not configured`: set the provider key in `backend/.env` and restart the backend.
- Browser launch errors: run `python -m playwright install chromium` inside the backend environment.
- Port already in use: stop the existing process or run the service on a different port and update `VITE_API_BASE_URL` for the frontend.

## License

Personate AI is released under the [MIT License](LICENSE).
