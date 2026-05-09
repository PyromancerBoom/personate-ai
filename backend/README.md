# Personate AI Backend

FastAPI + Playwright + Google Gemini one-persona UX simulator.

## Setup

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate    # Windows bash
pip install -r requirements.txt
python -m playwright install chromium
```

Set environment:

```
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-pro
PLAYWRIGHT_HEADLESS=false
MAX_JOURNEY_STEPS=12
RUNS_DIR=../runs
```

## Run

```bash
uvicorn app.main:app --reload
```

## API

- `POST /api/runs` — body `{ url, goal, audience? }` → `SimulationRun` with persona
- `POST /api/runs/{run_id}/start` — runs the full simulation; returns final run
- `GET /api/runs/{run_id}` — fetch saved run
- `GET /api/runs/{run_id}/screenshots/{file}` — serve PNG

## Tests

```bash
pytest
```

## Notes

The AI provider sits behind `AIProvider` protocol in `app/ai_provider.py`. Default
is `GeminiProvider`. Swap in any other provider that satisfies the protocol.
