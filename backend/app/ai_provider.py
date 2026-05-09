from __future__ import annotations

import base64
import json
import uuid
from pathlib import Path
from typing import Protocol

from .config import Settings
from .models import (
    DecisionOutput,
    JourneyStep,
    Persona,
    PersonaOutput,
    ReportOutput,
    SimulationInput,
    SimulationReport,
    SimulationRun,
    StopAction,
)


class AIProvider(Protocol):
    async def generate_persona(self, input: SimulationInput) -> Persona: ...

    async def decide_next_action(
        self,
        *,
        persona: Persona,
        goal: str,
        current_step: int,
        screenshot_path: Path,
        previous_steps: list[JourneyStep],
    ) -> DecisionOutput: ...

    async def generate_report(
        self,
        *,
        run: SimulationRun,
        persona: Persona,
        steps: list[JourneyStep],
    ) -> SimulationReport: ...


PERSONA_PROMPT = """You are a UX research assistant. Generate ONE realistic
end-user persona who would plausibly try the following product, given the goal
and (optional) target audience. The persona must feel like a real human user,
not a QA tester. Output only the structured JSON.

Goal: {goal}
URL: {url}
Audience: {audience}
"""

DECISION_SYSTEM = """You ARE a realistic end user, not a QA bot. You can only
see the current screenshot and what you remember from previous steps. Decide
what a real user with the given persona and goal would do next.

Rules:
- Pick exactly ONE action from: click, type, scroll_down, back, wait, stop.
- Use ONLY visible information. No DOM selectors. No code.
- Coordinates are in screen pixels relative to the top-left of the viewport
  ({viewport_width} x {viewport_height}).
- For click and (optional) type coordinates, choose the centre of the visible
  target.
- Include a short user-like first-person thought.
- Include a short page summary describing what's on screen.
- Tag exactly one ux_signal: confusion, confidence, hesitation, friction,
  progress, drop_off, or neutral.
- If the goal is clearly achieved → stop with outcome=success.
- If the user is clearly blocked or lost → stop with outcome=failure.
- If progress stalled with mixed results → stop with outcome=partial.
"""

REPORT_SYSTEM = """You are a UX researcher writing a short evidence-backed
report for a product team. Use ONLY the recorded persona, goal, and journey
steps. Reference real step numbers and their screenshot URLs in
friction_moments. Be concrete and product-facing, not technical.
"""


def _persona_from_output(out: PersonaOutput) -> Persona:
    return Persona(
        id=uuid.uuid4().hex[:8],
        name=out.name,
        background=out.background,
        motivation=out.motivation,
        experience_level=out.experience_level,
        concerns=out.concerns,
        behavioral_traits=out.behavioral_traits,
        success_criteria=out.success_criteria,
    )


def _report_from_output(out: ReportOutput, steps: list[JourneyStep]) -> SimulationReport:
    valid_steps = {s.step: s.screenshot for s in steps}
    clean_friction = [
        fm for fm in out.friction_moments
        if fm.step in valid_steps
    ]
    for fm in clean_friction:
        fm.screenshot = valid_steps[fm.step]
    return SimulationReport(
        outcome=out.outcome,
        summary=out.summary,
        persona_narrative=out.persona_narrative,
        friction_moments=clean_friction,
        recommendations=out.recommendations,
    )


class GeminiProvider:
    """Default AIProvider implementation backed by Google Gemini."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None  # lazy

    def _get_client(self):
        if self._client is None:
            if not self.settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured")
            from google import genai  # type: ignore
            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    async def generate_persona(self, input: SimulationInput) -> Persona:
        from google.genai import types  # type: ignore
        client = self._get_client()
        prompt = PERSONA_PROMPT.format(
            goal=input.goal,
            url=input.url,
            audience=input.audience or "unspecified",
        )
        resp = await client.aio.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PersonaOutput,
            ),
        )
        out = self._parse_json(resp.text, PersonaOutput)
        return _persona_from_output(out)

    async def decide_next_action(
        self,
        *,
        persona: Persona,
        goal: str,
        current_step: int,
        screenshot_path: Path,
        previous_steps: list[JourneyStep],
    ) -> DecisionOutput:
        from google.genai import types  # type: ignore
        client = self._get_client()

        history = "\n".join(
            f"step {s.step}: thought={s.thought!r} action={s.action.type} "
            f"result={s.result!r} ux_signal={s.ux_signal}"
            for s in previous_steps[-6:]
        ) or "(no previous steps)"

        sys_prompt = DECISION_SYSTEM.format(
            viewport_width=self.settings.viewport_width,
            viewport_height=self.settings.viewport_height,
        )
        user_text = (
            f"Persona: {persona.model_dump_json()}\n"
            f"Goal: {goal}\n"
            f"Current step: {current_step}\n"
            f"Recent history:\n{history}"
        )
        image_bytes = screenshot_path.read_bytes()

        async def _call(extra: str = "") -> DecisionOutput:
            resp = await client.aio.models.generate_content(
                model=self.settings.gemini_model,
                contents=[
                    sys_prompt,
                    user_text + extra,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DecisionOutput,
                ),
            )
            return self._parse_json(resp.text, DecisionOutput)

        try:
            return await _call()
        except Exception:
            try:
                return await _call(
                    "\n\nPrevious response was malformed. Reply ONLY with valid "
                    "JSON matching the schema."
                )
            except Exception as e:
                return DecisionOutput(
                    thought="I'm not sure how to proceed.",
                    page_summary="(unavailable)",
                    ux_signal="drop_off",
                    action_type="stop",
                    outcome="partial",
                    reason=f"AI provider returned malformed responses: {e}",
                )

    async def generate_report(
        self,
        *,
        run: SimulationRun,
        persona: Persona,
        steps: list[JourneyStep],
    ) -> SimulationReport:
        from google.genai import types  # type: ignore
        client = self._get_client()
        steps_payload = [s.model_dump(by_alias=True) for s in steps]
        user_text = json.dumps(
            {
                "persona": persona.model_dump(by_alias=True),
                "goal": run.goal,
                "url": run.url,
                "audience": run.audience,
                "steps": steps_payload,
            },
            ensure_ascii=False,
        )
        resp = await client.aio.models.generate_content(
            model=self.settings.gemini_model,
            contents=[REPORT_SYSTEM, user_text],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReportOutput,
            ),
        )
        out = self._parse_json(resp.text, ReportOutput)
        return _report_from_output(out, steps)

    @staticmethod
    def _parse_json(text: str | None, model_cls):
        if not text:
            raise ValueError("empty model response")
        return model_cls.model_validate_json(text)


class OpenAIProvider:
    """AIProvider implementation backed by OpenAI chat completions."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            from openai import AsyncOpenAI  # type: ignore

            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    async def _parse_chat(self, *, messages: list[dict], model_cls):
        client = self._get_client()
        resp = await client.beta.chat.completions.parse(
            model=self.settings.openai_model,
            messages=messages,
            response_format=model_cls,
        )
        parsed = resp.choices[0].message.parsed
        if parsed is None:
            refusal = getattr(resp.choices[0].message, "refusal", None)
            raise ValueError(refusal or "empty parsed model response")
        return parsed

    async def generate_persona(self, input: SimulationInput) -> Persona:
        prompt = PERSONA_PROMPT.format(
            goal=input.goal,
            url=input.url,
            audience=input.audience or "unspecified",
        )
        out = await self._parse_chat(
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid structured data for the requested schema.",
                },
                {"role": "user", "content": prompt},
            ],
            model_cls=PersonaOutput,
        )
        return _persona_from_output(out)

    async def decide_next_action(
        self,
        *,
        persona: Persona,
        goal: str,
        current_step: int,
        screenshot_path: Path,
        previous_steps: list[JourneyStep],
    ) -> DecisionOutput:
        history = "\n".join(
            f"step {s.step}: thought={s.thought!r} action={s.action.type} "
            f"result={s.result!r} ux_signal={s.ux_signal}"
            for s in previous_steps[-6:]
        ) or "(no previous steps)"

        sys_prompt = DECISION_SYSTEM.format(
            viewport_width=self.settings.viewport_width,
            viewport_height=self.settings.viewport_height,
        )
        user_text = (
            f"Persona: {persona.model_dump_json()}\n"
            f"Goal: {goal}\n"
            f"Current step: {current_step}\n"
            f"Recent history:\n{history}"
        )
        data_url = (
            "data:image/png;base64,"
            + base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
        )

        async def _call(extra: str = "") -> DecisionOutput:
            return await self._parse_chat(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_text + extra},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    },
                ],
                model_cls=DecisionOutput,
            )

        try:
            return await _call()
        except Exception:
            try:
                return await _call(
                    "\n\nPrevious response was malformed. Reply ONLY with valid "
                    "JSON matching the schema."
                )
            except Exception as e:
                return DecisionOutput(
                    thought="I'm not sure how to proceed.",
                    page_summary="(unavailable)",
                    ux_signal="drop_off",
                    action_type="stop",
                    outcome="partial",
                    reason=f"AI provider returned malformed responses: {e}",
                )

    async def generate_report(
        self,
        *,
        run: SimulationRun,
        persona: Persona,
        steps: list[JourneyStep],
    ) -> SimulationReport:
        steps_payload = [s.model_dump(by_alias=True) for s in steps]
        user_text = json.dumps(
            {
                "persona": persona.model_dump(by_alias=True),
                "goal": run.goal,
                "url": run.url,
                "audience": run.audience,
                "steps": steps_payload,
            },
            ensure_ascii=False,
        )
        out = await self._parse_chat(
            messages=[
                {"role": "system", "content": REPORT_SYSTEM},
                {"role": "user", "content": user_text},
            ],
            model_cls=ReportOutput,
        )
        return _report_from_output(out, steps)
