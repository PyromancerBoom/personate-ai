# Personate AI Backend

FastAPI + Playwright one-persona UX simulator with selectable OpenAI or Gemini
providers.

## Setup

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate    # Windows bash
pip install -r requirements.txt
python -m playwright install chromium
```

Create a local `.env` file in `backend/`:

```bash
cp .env.example .env
```

Then set `AI_PROVIDER` and fill in the matching server-side API key.

```txt
AI_PROVIDER=openai
OPENAI_API_KEY=replace-with-your-server-side-openai-key
OPENAI_MODEL=gpt-5.5
```

Or:

```txt
AI_PROVIDER=gemini
GEMINI_API_KEY=replace-with-your-server-side-gemini-key
GEMINI_MODEL=gemini-2.0-flash-lite
```

Do not put provider keys in frontend `VITE_*` variables. Vite environment
variables are bundled into client code. Provider credentials belong only in the
backend environment, and `.env` is intentionally ignored by Git.

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

The AI provider sits behind the `AIProvider` protocol in `app/ai_provider.py`.
Use `AI_PROVIDER=openai` for `OpenAIProvider` or `AI_PROVIDER=gemini` for
`GeminiProvider`.
