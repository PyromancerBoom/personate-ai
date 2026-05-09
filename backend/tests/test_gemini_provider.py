"""Tests for GeminiProvider that mock the google-genai SDK.

These exercise the real prompt-building, schema-binding, and parsing code so we
catch breakage if google-genai changes its surface, without making network
calls or requiring a real API key.
"""
from __future__ import annotations

import sys
import types as pytypes
from pathlib import Path

import pytest

from app.config import Settings


# ---- Fake google.genai SDK -----------------------------------------------------

class _FakePart:
    def __init__(self, *, data, mime_type):
        self.data = data
        self.mime_type = mime_type

    @classmethod
    def from_bytes(cls, *, data, mime_type):
        return cls(data=data, mime_type=mime_type)


class _FakeTypesModule:
    Part = _FakePart

    class GenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeAioModels:
    def __init__(self, queue):
        self.queue = queue
        self.calls: list[dict] = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        nxt = self.queue.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return _FakeResp(nxt)


class _FakeAio:
    def __init__(self, queue):
        self.models = _FakeAioModels(queue)


class _FakeClient:
    def __init__(self, *, api_key):
        self.api_key = api_key
        self.queue: list = []
        self.aio = _FakeAio(self.queue)


def _install_fake_genai(monkeypatch, client_holder):
    fake_genai = pytypes.ModuleType("google.genai")
    def Client(*, api_key):
        c = _FakeClient(api_key=api_key)
        client_holder.append(c)
        return c
    fake_genai.Client = Client
    fake_types = _FakeTypesModule
    fake_genai.types = fake_types
    fake_google = pytypes.ModuleType("google")
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)


# ---- Tests ---------------------------------------------------------------------

@pytest.fixture
def settings(tmp_path):
    return Settings(
        gemini_api_key="fake",
        gemini_model="gemini-2.5-pro",
        runs_dir=tmp_path / "runs",
    )


@pytest.mark.asyncio
async def test_generate_persona_parses_response(monkeypatch, settings):
    from app.ai_provider import GeminiProvider
    from app.models import SimulationInput

    holder: list[_FakeClient] = []
    _install_fake_genai(monkeypatch, holder)
    p = GeminiProvider(settings)
    p._get_client()
    holder[0].queue.append(
        '{"name":"Maya","background":"bg","motivation":"m",'
        '"experienceLevel":"non-technical","concerns":["c1"],'
        '"behavioralTraits":["t1"],"successCriteria":"ok"}'
    )
    persona = await p.generate_persona(
        SimulationInput(url="http://x", goal="g", audience=None)
    )
    assert persona.name == "Maya"
    assert persona.experience_level == "non-technical"
    assert persona.id  # generated


@pytest.mark.asyncio
async def test_decide_next_action_parses_flat_schema(
    monkeypatch, settings, tmp_path
):
    from app.ai_provider import GeminiProvider
    from app.models import Persona

    holder: list[_FakeClient] = []
    _install_fake_genai(monkeypatch, holder)
    p = GeminiProvider(settings)
    p._get_client()
    holder[0].queue.append(
        '{"thought":"click it","pageSummary":"a button",'
        '"uxSignal":"confidence","actionType":"click",'
        '"coordinatesX":100,"coordinatesY":200}'
    )
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    persona = Persona(
        id="x", name="n", background="b", motivation="m",
        experience_level="e", concerns=[], behavioral_traits=[], success_criteria="s",
    )
    decision = await p.decide_next_action(
        persona=persona, goal="g", current_step=1,
        screenshot_path=shot, previous_steps=[],
    )
    action = decision.to_action()
    from app.models import ClickAction
    assert isinstance(action, ClickAction)
    assert action.coordinates == (100, 200)
    # Verify the SDK call used the flat DecisionOutput schema, not a union.
    call = holder[0].aio.models.calls[0]
    cfg = call["config"].kwargs
    from app.models import DecisionOutput
    assert cfg["response_schema"] is DecisionOutput
    assert cfg["response_mime_type"] == "application/json"


@pytest.mark.asyncio
async def test_decide_next_action_retries_then_partial_stop(
    monkeypatch, settings, tmp_path
):
    from app.ai_provider import GeminiProvider
    from app.models import Persona, StopAction

    holder: list[_FakeClient] = []
    _install_fake_genai(monkeypatch, holder)
    p = GeminiProvider(settings)
    p._get_client()
    holder[0].queue.extend([
        RuntimeError("schema fail #1"),
        RuntimeError("schema fail #2"),
    ])
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    persona = Persona(
        id="x", name="n", background="b", motivation="m",
        experience_level="e", concerns=[], behavioral_traits=[], success_criteria="s",
    )
    decision = await p.decide_next_action(
        persona=persona, goal="g", current_step=1,
        screenshot_path=shot, previous_steps=[],
    )
    action = decision.to_action()
    assert isinstance(action, StopAction)
    assert action.outcome == "partial"
    assert "malformed" in action.reason
    # Verify exactly two calls were made (initial + one retry).
    assert len(holder[0].aio.models.calls) == 2
