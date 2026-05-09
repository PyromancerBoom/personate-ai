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

        elements = await b.index_elements()
        # Should find at least the input and the button.
        tags = [e["tag"] for e in elements]
        assert "input" in tags
        assert "button" in tags
        input_idx = tags.index("input")
        button_idx = tags.index("button")

        await b.execute(TypeAction(text="hi", element_id=input_idx))
        await b.execute(ClickAction(element_id=button_idx))
        await b.execute(ScrollDownAction())
        await b.execute(WaitAction())
        await b.execute(BackAction())
    finally:
        await b.close()


@pytest.mark.asyncio
async def test_index_elements_returns_visible_inputs(tmp_path, tmp_settings):
    page_html = (
        "<!doctype html><html><body>"
        "<input id='q' placeholder='Search'>"
        "<button>Go</button>"
        "<input type='hidden' value='x'>"
        "<div style='display:none'><button>Hidden</button></div>"
        "</body></html>"
    )
    page_file = tmp_path / "elems.html"
    page_file.write_text(page_html, encoding="utf-8")
    url = page_file.resolve().as_uri()

    tmp_settings.playwright_headless = True
    b = BrowserSession(tmp_settings)
    try:
        await b.start(url)
        elements = await b.index_elements()
        names = [e["name"] for e in elements]
        tags = [e["tag"] for e in elements]
        assert "input" in tags
        assert "button" in tags
        # Hidden + display:none must be filtered out.
        assert "Hidden" not in names
        assert not any(e.get("type") == "hidden" for e in elements)
        # Search input contributes its placeholder as the name.
        assert any("Search" in n for n in names)
        # LLM format renders [N]<tag>name</tag>.
        formatted = b.format_elements_for_llm()
        assert formatted.startswith("[0]<")
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
            element_id=0,
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
