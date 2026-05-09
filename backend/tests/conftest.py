from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest

from app.config import Settings
from app.main import create_app
from app.models import (
    DecisionOutput,
    JourneyStep,
    Persona,
    SimulationInput,
    SimulationReport,
    SimulationRun,
    StopAction,
)
from app.storage import RunStorage


class StubProvider:
    """Deterministic AI provider used for unit + API tests."""

    def __init__(self, *, decisions: list[DecisionOutput] | None = None,
                 fail_persona: bool = False, fail_decision: bool = False):
        self.decisions = decisions or []
        self.fail_persona = fail_persona
        self.fail_decision = fail_decision
        self._idx = 0
        self.calls: list[str] = []

    async def generate_persona(self, input: SimulationInput) -> Persona:
        self.calls.append("persona")
        if self.fail_persona:
            raise RuntimeError("stub: persona failed")
        return Persona(
            id=uuid.uuid4().hex[:8],
            name="Maya Tester",
            background="Small-business owner exploring a new tool.",
            motivation="See if this product can save her time.",
            experience_level="non-technical",
            concerns=["complexity", "time"],
            behavioral_traits=["scans quickly", "skeptical of jargon"],
            success_criteria="Reaches the first useful screen within a few clicks.",
        )

    async def decide_next_action(self, *, persona, goal, current_step,
                                 screenshot_path, previous_steps) -> DecisionOutput:
        self.calls.append(f"decide:{current_step}")
        if self.fail_decision:
            raise RuntimeError("stub: decision failed")
        if self._idx < len(self.decisions):
            d = self.decisions[self._idx]
            self._idx += 1
            return d
        return DecisionOutput(
            thought="I think I'm done.",
            page_summary="(stub)",
            ux_signal="neutral",
            action_type="stop",
            outcome="success",
            reason="stub default stop",
        )

    async def generate_report(self, *, run: SimulationRun, persona,
                              steps: list[JourneyStep]) -> SimulationReport:
        self.calls.append("report")
        return SimulationReport(
            outcome="success",
            summary="Stub run completed.",
            persona_narrative="Maya navigated the product without major issues.",
            friction_moments=[],
            recommendations=["Keep going."],
        )


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    return Settings(
        ai_provider="gemini",
        gemini_api_key="test-key",
        gemini_model="gemini-2.5-pro",
        openai_api_key="test-openai-key",
        openai_model="gpt-5.5",
        playwright_headless=True,
        max_journey_steps=4,
        runs_dir=tmp_path / "runs",
    )


@pytest.fixture
def stub_provider() -> StubProvider:
    return StubProvider()


@pytest.fixture
def app_and_storage(tmp_settings, stub_provider):
    storage = RunStorage(tmp_settings.runs_dir)
    app = create_app(settings=tmp_settings, storage=storage, provider=stub_provider)
    return app, storage, stub_provider


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
