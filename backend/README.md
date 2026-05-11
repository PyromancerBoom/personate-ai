# Personate AI Backend

FastAPI + Playwright one-persona UX simulator with a pluggable AI provider.

## Setup

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate    # Windows bash
pip install -r requirements.txt
python -m playwright install chromium
```

Set environment:

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

Use `AI_PROVIDER=openai` with `OPENAI_API_KEY` and `OPENAI_MODEL` to run against OpenAI instead.

## Run

```bash
uvicorn app.main:app --reload
```

## API

- `POST /api/runs` - body `{ url, goal, audience? }` returns `SimulationRun` with persona
- `POST /api/runs/{run_id}/start` - runs the full simulation and returns the final run
- `GET /api/runs/{run_id}` - fetches a saved run
- `GET /api/runs/{run_id}/screenshots/{file}` - serves a PNG screenshot

## Tests

```bash
pytest
```

## Notes

The AI provider sits behind the `AIProvider` protocol in `app/ai_provider.py`. The default provider is `GeminiProvider`. Swap in any other provider that satisfies the protocol.
