# Personate AI Frontend

Dev 2 frontend for Personate AI. This is a separate Vite React TypeScript app that talks to the Python FastAPI backend.

## Setup

```bash
npm install
npm run dev
```

The API base URL defaults to `http://localhost:8000`. The backend must be running and configured with its server-side AI provider key.

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Checks

```bash
npm run build
npm run test
```
