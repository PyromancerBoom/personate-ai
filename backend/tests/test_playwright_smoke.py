from __future__ import annotations

import asyncio

import pytest

from app.browser import BrowserSession
from app.models import (
    BackAction,
    ClickAction,
    DecisionOutput,
    ScrollDownAction,
    StopAction,
    TypeAction,
    WaitAction,
)
from app.simulation import run_simulation
from app.storage import RunStorage
from app.models import SimulationRun
from tests.conftest import StubProvider


HTML = """<!doctype html><html><body style='font-family:sans-serif'>
<h1 id='h'>Hello</h1>
<input id='inp' />
<button id='btn' onclick="document.getElementById('h').innerText='Clicked'">Go</button>
<div style='height:2000px'></div>
</body></html>"""


@pytest.mark.asyncio
async def test_browser_smoke(tmp_path, tmp_settings):
    page = tmp_path / "index.html"
    page.write_text(HTML, encoding="utf-8")
    url = page.resolve().as_uri()

    tmp_settings.playwright_headless = True
    b = BrowserSession(tmp_settings)
    try:
        await b.start(url)
        shot = tmp_path / "shot.png"
        await b.screenshot(shot)
        assert shot.exists() and shot.stat().st_size > 0
        await b.execute(ClickAction(coordinates=(10, 10)))
        await b.execute(TypeAction(text="hi", coordinates=(50, 80)))
        await b.execute(ScrollDownAction())
        await b.execute(WaitAction())
        await b.execute(BackAction())
    finally:
        await b.close()


@pytest.mark.asyncio
async def test_simulation_loop_with_stub(tmp_path, tmp_settings):
    page = tmp_path / "index.html"
    page.write_text(HTML, encoding="utf-8")
    url = page.resolve().as_uri()

    tmp_settings.playwright_headless = True
    storage = RunStorage(tmp_settings.runs_dir)
    rid = storage.new_run_id()

    decisions = [
        DecisionOutput(
            thought="I'll click the button.",
            page_summary="A button labelled Go.",
            ux_signal="confidence",
            action_type="click",
            coordinates_x=40,
            coordinates_y=60,
        ),
        DecisionOutput(
            thought="I'm done.",
            page_summary="Heading changed.",
            ux_signal="progress",
            action_type="stop",
            outcome="success",
            reason="finished",
        ),
    ]
    provider = StubProvider(decisions=decisions)
    persona = await provider.generate_persona(
        __import__("app.models", fromlist=["SimulationInput"]).SimulationInput(
            url=url, goal="click go"
        )
    )

    run = SimulationRun(id=rid, url=url, goal="click go", persona=persona, status="running")
    storage.save_run(run)
    final = await run_simulation(
        run=run, settings=tmp_settings, storage=storage, provider=provider
    )

    assert final.status == "completed"
    assert len(final.steps) >= 2
    assert final.report is not None
    assert final.report.outcome == "success"
    shots_dir = storage.screenshots_dir(rid)
    pngs = list(shots_dir.glob("*.png"))
    assert len(pngs) >= 2
