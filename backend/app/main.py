from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

# Playwright on Windows must spawn Chromium via subprocess_exec, which is only
# implemented on ProactorEventLoop. Uvicorn defaults to SelectorEventLoop on
# Windows, so set the policy at import — before uvicorn builds the loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from contextlib import asynccontextmanager

from .ai_provider import AIProvider, GeminiProvider
from .config import Settings, get_settings
from .models import SimulationInput, SimulationRun
from .simulation import run_simulation
from .storage import RunStorage, is_valid_run_id


class CreateRunRequest(BaseModel):
    url: str
    goal: str
    audience: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_input(req: CreateRunRequest) -> None:
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="url is required")
    if not req.goal or not req.goal.strip():
        raise HTTPException(status_code=400, detail="goal is required")
    parsed = urlparse(req.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail="url must use http or https"
        )
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="url is invalid")


def _run_response(run: SimulationRun) -> JSONResponse:
    return JSONResponse(run.model_dump(by_alias=True, exclude_none=True))


def create_app(
    settings: Settings | None = None,
    storage: RunStorage | None = None,
    provider: AIProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    storage = storage or RunStorage(settings.runs_dir)
    provider = provider or GeminiProvider(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        storage.sweep_orphaned_running()
        yield

    app = FastAPI(title="Personate AI Backend", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_storage() -> RunStorage:
        return storage

    def get_provider() -> AIProvider:
        return provider

    def get_settings_dep() -> Settings:
        return settings

    @app.post("/api/runs")
    async def create_run(
        req: CreateRunRequest,
        store: RunStorage = Depends(get_storage),
        prov: AIProvider = Depends(get_provider),
        cfg: Settings = Depends(get_settings_dep),
    ) -> JSONResponse:
        _validate_input(req)
        if not cfg.gemini_api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY is not configured",
            )
        run_id = store.new_run_id()
        run = SimulationRun(
            id=run_id,
            url=req.url,
            goal=req.goal,
            audience=req.audience,
            status="draft",
        )
        try:
            persona = await prov.generate_persona(
                SimulationInput(url=req.url, goal=req.goal, audience=req.audience)
            )
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"persona generation failed: {e}"
            )
        run.persona = persona
        run.updated_at = _now_iso()
        store.save_run(run)
        return _run_response(run)

    @app.get("/api/runs/{run_id}")
    async def get_run(
        run_id: str,
        store: RunStorage = Depends(get_storage),
    ) -> JSONResponse:
        if not is_valid_run_id(run_id):
            raise HTTPException(status_code=404, detail="run not found")
        run = store.load_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return _run_response(run)

    @app.post("/api/runs/{run_id}/start")
    async def start_run(
        run_id: str,
        store: RunStorage = Depends(get_storage),
        prov: AIProvider = Depends(get_provider),
        cfg: Settings = Depends(get_settings_dep),
    ) -> JSONResponse:
        """Run the simulation synchronously.

        Always returns HTTP 200 with the final SimulationRun on success or
        run-level failure. The frontend MUST inspect `status` to distinguish
        "completed" from "failed". Non-2xx responses are reserved for
        request-level errors (404 for missing run, 409 for state conflicts).
        """
        if not is_valid_run_id(run_id):
            raise HTTPException(status_code=404, detail="run not found")
        run = store.load_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        if run.status == "running":
            raise HTTPException(status_code=409, detail="run already running")
        if run.status == "completed":
            raise HTTPException(status_code=409, detail="run already completed")
        run.status = "running"
        run.error = None
        run.updated_at = _now_iso()
        store.save_run(run)
        final = await run_simulation(
            run=run, settings=cfg, storage=store, provider=prov
        )
        return _run_response(final)

    @app.get("/api/runs/{run_id}/screenshots/{file}")
    async def get_screenshot(
        run_id: str,
        file: str,
        store: RunStorage = Depends(get_storage),
    ) -> FileResponse:
        if not is_valid_run_id(run_id):
            raise HTTPException(status_code=404, detail="screenshot not found")
        try:
            path = store.screenshot_path(run_id, file)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid screenshot path")
        if not path.exists():
            raise HTTPException(status_code=404, detail="screenshot not found")
        return FileResponse(str(path), media_type="image/png")

    return app


app = create_app()
