"""Tests for OpenAIProvider that mock the OpenAI SDK.

These keep provider wiring covered without making network calls or requiring a
real API key in CI.
"""
from __future__ import annotations

import sys
import types as pytypes

import pytest

from app.config import Settings
from app.models import DecisionOutput, PersonaOutput


class _FakeMessage:
    def __init__(self, parsed, refusal=None):
        self.parsed = parsed
        self.refusal = refusal


class _FakeChoice:
    def __init__(self, parsed):
        self.message = _FakeMessage(parsed)


class _FakeResp:
    def __init__(self, parsed):
        self.choices = [_FakeChoice(parsed)]


class _FakeCompletions:
    def __init__(self, queue):
        self.queue = queue
        self.calls: list[dict] = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        nxt = self.queue.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return _FakeResp(nxt)


class _FakeChat:
    def __init__(self, queue):
        self.completions = _FakeCompletions(queue)


class _FakeBeta:
    def __init__(self, queue):
        self.chat = _FakeChat(queue)


class _FakeOpenAIClient:
    def __init__(self, *, api_key):
        self.api_key = api_key
        self.queue: list = []
        self.beta = _FakeBeta(self.queue)


def _install_fake_openai(monkeypatch, client_holder):
    fake_openai = pytypes.ModuleType("openai")

    def AsyncOpenAI(*, api_key):
        client = _FakeOpenAIClient(api_key=api_key)
        client_holder.append(client)
        return client

    fake_openai.AsyncOpenAI = AsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)


@pytest.fixture
def settings(tmp_path):
    return Settings(
        ai_provider="openai",
        openai_api_key="fake",
        openai_model="gpt-5.5",
        runs_dir=tmp_path / "runs",
    )


@pytest.mark.asyncio
async def test_generate_persona_parses_response(monkeypatch, settings):
    from app.ai_provider import OpenAIProvider
    from app.models import SimulationInput

    holder: list[_FakeOpenAIClient] = []
    _install_fake_openai(monkeypatch, holder)
    provider = OpenAIProvider(settings)
    provider._get_client()
    holder[0].queue.append(
        PersonaOutput(
            name="Maya",
            background="bg",
            motivation="m",
            experience_level="non-technical",
            concerns=["c1"],
            behavioral_traits=["t1"],
            success_criteria="ok",
        )
    )
    persona = await provider.generate_persona(
        SimulationInput(url="http://x", goal="g", audience=None)
    )
    assert persona.name == "Maya"
    assert persona.experience_level == "non-technical"
    assert persona.id
    call = holder[0].beta.chat.completions.calls[0]
    assert call["model"] == "gpt-5.5"
    assert call["response_format"] is PersonaOutput


@pytest.mark.asyncio
async def test_decide_next_action_sends_image_and_parses(
    monkeypatch, settings, tmp_path
):
    from app.ai_provider import OpenAIProvider
    from app.models import ClickAction, Persona

    holder: list[_FakeOpenAIClient] = []
    _install_fake_openai(monkeypatch, holder)
    provider = OpenAIProvider(settings)
    provider._get_client()
    holder[0].queue.append(
        DecisionOutput(
            thought="click it",
            page_summary="a button",
            ux_signal="confidence",
            action_type="click",
            coordinates_x=100,
            coordinates_y=200,
        )
    )
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    persona = Persona(
        id="x",
        name="n",
        background="b",
        motivation="m",
        experience_level="e",
        concerns=[],
        behavioral_traits=[],
        success_criteria="s",
    )
    decision = await provider.decide_next_action(
        persona=persona,
        goal="g",
        current_step=1,
        screenshot_path=shot,
        previous_steps=[],
    )
    assert isinstance(decision.to_action(), ClickAction)
    call = holder[0].beta.chat.completions.calls[0]
    content = call["messages"][1]["content"]
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert call["response_format"] is DecisionOutput


@pytest.mark.asyncio
async def test_decide_next_action_retries_then_partial_stop(
    monkeypatch, settings, tmp_path
):
    from app.ai_provider import OpenAIProvider
    from app.models import Persona, StopAction

    holder: list[_FakeOpenAIClient] = []
    _install_fake_openai(monkeypatch, holder)
    provider = OpenAIProvider(settings)
    provider._get_client()
    holder[0].queue.extend([
        RuntimeError("schema fail #1"),
        RuntimeError("schema fail #2"),
    ])
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    persona = Persona(
        id="x",
        name="n",
        background="b",
        motivation="m",
        experience_level="e",
        concerns=[],
        behavioral_traits=[],
        success_criteria="s",
    )
    decision = await provider.decide_next_action(
        persona=persona,
        goal="g",
        current_step=1,
        screenshot_path=shot,
        previous_steps=[],
    )
    action = decision.to_action()
    assert isinstance(action, StopAction)
    assert action.outcome == "partial"
    assert "malformed" in action.reason
    assert len(holder[0].beta.chat.completions.calls) == 2
