"""Tests for OpenAIProvider that mock the openai SDK.

Mirrors test_gemini_provider.py: install a fake `openai` module via sys.modules
so `from openai import AsyncOpenAI` returns our stub. Exercises real
prompt-building, schema-binding, and parsing without network calls.
"""
from __future__ import annotations

import sys
import types as pytypes

import pytest

from app.config import Settings


# ---- Fake openai SDK ----------------------------------------------------------

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResp:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, queue, calls):
        self.queue = queue
        self.calls = calls

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        nxt = self.queue.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return _FakeResp(nxt)


class _FakeChat:
    def __init__(self, queue, calls):
        self.completions = _FakeCompletions(queue, calls)


class _FakeAsyncOpenAI:
    def __init__(self, *, api_key):
        self.api_key = api_key
        self.queue: list = []
        self.calls: list[dict] = []
        self.chat = _FakeChat(self.queue, self.calls)


def _install_fake_openai(monkeypatch, holder):
    fake_mod = pytypes.ModuleType("openai")

    def AsyncOpenAI(*, api_key):
        c = _FakeAsyncOpenAI(api_key=api_key)
        holder.append(c)
        return c

    fake_mod.AsyncOpenAI = AsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_mod)


# ---- Tests --------------------------------------------------------------------

@pytest.fixture
def settings(tmp_path):
    return Settings(
        ai_provider="openai",
        openai_api_key="fake",
        openai_model="gpt-4o-mini",
        runs_dir=tmp_path / "runs",
    )


@pytest.mark.asyncio
async def test_generate_persona_parses_response(monkeypatch, settings):
    from app.ai_provider import OpenAIProvider
    from app.models import SimulationInput

    holder: list[_FakeAsyncOpenAI] = []
    _install_fake_openai(monkeypatch, holder)
    p = OpenAIProvider(settings)
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
    assert persona.id


@pytest.mark.asyncio
async def test_decide_next_action_parses_flat_schema(
    monkeypatch, settings, tmp_path
):
    from app.ai_provider import OpenAIProvider
    from app.models import ClickAction, Persona

    holder: list[_FakeAsyncOpenAI] = []
    _install_fake_openai(monkeypatch, holder)
    p = OpenAIProvider(settings)
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
    assert isinstance(action, ClickAction)
    assert action.coordinates == (100, 200)

    call = holder[0].calls[0]
    assert call["model"] == "gpt-4o-mini"
    rf = call["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"]["additionalProperties"] is False

    msgs = call["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    parts = msgs[1]["content"]
    assert parts[0]["type"] == "text"
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_decide_next_action_retries_then_partial_stop(
    monkeypatch, settings, tmp_path
):
    from app.ai_provider import OpenAIProvider
    from app.models import Persona, StopAction

    holder: list[_FakeAsyncOpenAI] = []
    _install_fake_openai(monkeypatch, holder)
    p = OpenAIProvider(settings)
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
    assert len(holder[0].calls) == 2


def test_build_provider_factory(tmp_path):
    from app.ai_provider import GeminiProvider, OpenAIProvider, build_provider

    s_gemini = Settings(ai_provider="gemini", runs_dir=tmp_path / "r1")
    assert isinstance(build_provider(s_gemini), GeminiProvider)

    s_openai = Settings(ai_provider="openai", runs_dir=tmp_path / "r2")
    assert isinstance(build_provider(s_openai), OpenAIProvider)
