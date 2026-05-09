# Personate AI Frontend

Dev 2 frontend for Personate AI. This is a separate Vite React TypeScript app that talks to the Python FastAPI backend.

## Setup

```bash
npm install
npm run dev
```

The API base URL defaults to `http://localhost:8000`.

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Use mock mode while the backend is unavailable:

```bash
VITE_MOCK_API=true npm run dev
```

Mock mode does not call the backend and does not need `GEMINI_API_KEY`.

## Checks

```bash
npm run build
npm run test
```
