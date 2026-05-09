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
        elements: str,
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
and (optional) target audience.

The persona must feel like a specific human, not a marketing archetype:

- background: 2-3 sentences with concrete life detail (job, age range,
  context, *why this product crossed their path*). Avoid generic phrases
  like "tech-savvy professional" or "busy mom".
- motivation: what they actually want from this session today, in their own
  voice. Tie it to a real situation (a deadline, a problem, a curiosity).
- experience_level: how comfortable they are with software *like this one*,
  not software in general. Mention specific tools they do or don't know.
- concerns: 3-4 things that would frustrate or stop *this specific person*
  given their background. Not generic ("too many ads") — specific
  ("doesn't trust pages without HTTPS padlock", "skips long videos").
- behavioral_traits: 3-4 quirks of how they use software — reading speed,
  click vs scroll preference, tolerance for jargon, what makes them give up.
- success_criteria: a concrete observable outcome that, if reached, the
  persona would say "yes, that worked for me".

The persona will later "think out loud" while using the product, so each
field should give us material to draw their voice from.

Output only the structured JSON.

Goal: {goal}
URL: {url}
Audience: {audience}
"""

DECISION_SYSTEM = """You ARE the persona described in the user message — a
real human, not a QA bot. Stay in character. You see the current screenshot
AND a numbered list of interactable elements on the page. Decide what THIS
specific person, with their background, concerns, and quirks, would do next.

Rules:
- Pick exactly ONE action from: click, type, scroll_down, back, wait,
  press_key, stop.
- For `click`, set `element_id` to the [N] of the target from the element
  list. For `type`, set `element_id` to the input's [N] AND provide `text`.
- You may ONLY click or type into elements that appear in the element list
  below. Do NOT invent element IDs. If the list is empty or no listed
  element fits the next step, choose `scroll_down`, `wait`, `back`, or
  `stop` instead.
- For `type` on a search box or form field, prefer `submit=true` so Enter
  is pressed after typing. This is more reliable than hunting for a
  separate submit button.
- Use `press_key` with key="enter"/"tab"/"escape" when you need to submit,
  advance focus, or dismiss a popup without typing.
- Use the screenshot to understand layout, mood, and visual cues
  (cluttered vs clean, banners, modals). Use the element list to pick the
  exact target. The screenshot is your eyes; the element list is your
  hands.
- thought: speak in first person AS the persona, in their voice. React to
  what you see — curiosity, doubt, impatience, relief — and tie it to
  something concrete in their background, concerns, or behavioral_traits
  when it fits. Avoid narrating the action ("I will click X"); instead say
  what you're thinking or feeling that leads to it ("Hmm, no padlock in the
  URL — that always makes me nervous. Let me check the footer first.").
  One or two sentences, natural and human.
- page_summary: a short, neutral description of what's on screen.
- ux_signal: tag exactly one — confusion, confidence, hesitation, friction,
  progress, drop_off, or neutral — based on how the persona is feeling
  right now, not just what the page looks like.
- If the goal is clearly achieved → stop with outcome=success.
- If the persona would realistically give up given their concerns and
  patience level → stop with outcome=failure.
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
        elements: str,
    ) -> DecisionOutput:
        from google.genai import types  # type: ignore
        client = self._get_client()

        history = "\n".join(
            f"step {s.step}: thought={s.thought!r} action={s.action.type} "
            f"result={s.result!r} ux_signal={s.ux_signal}"
            for s in previous_steps[-6:]
        ) or "(no previous steps)"
        last_result = previous_steps[-1].result if previous_steps else "(none)"

        sys_prompt = DECISION_SYSTEM
        user_text = (
            f"Persona: {persona.model_dump_json()}\n"
            f"Goal: {goal}\n"
            f"Current step: {current_step}\n"
            f"Last action result: {last_result}\n"
            f"Recent history:\n{history}\n\n"
            f"Interactable elements on screen "
            f"(use these IDs for click/type):\n{elements}"
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

    @staticmethod
    def _parse_json(text: str | None, model_cls):
        if not text:
            raise ValueError("empty model response")
        return model_cls.model_validate_json(text)


def _strict_schema(model_cls, name: str) -> dict:
    """Build an OpenAI strict json_schema payload from a Pydantic model.

    OpenAI strict mode requires `additionalProperties: false` on every object
    and every property to be listed in `required`. Pydantic emits the schema
    but not those constraints, so we patch them in recursively.
    """
    schema = model_cls.model_json_schema()

    def _harden(node: dict) -> None:
        if node.get("type") == "object" or "properties" in node:
            node["additionalProperties"] = False
            props = node.get("properties", {})
            node["required"] = list(props.keys())
            for v in props.values():
                if isinstance(v, dict):
                    _harden(v)
        for key in ("items", "additionalItems"):
            sub = node.get(key)
            if isinstance(sub, dict):
                _harden(sub)
        for combo in ("anyOf", "oneOf", "allOf"):
            for sub in node.get(combo, []):
                if isinstance(sub, dict):
                    _harden(sub)
        for sub in node.get("$defs", {}).values():
            if isinstance(sub, dict):
                _harden(sub)

    _harden(schema)
    return {
        "name": name,
        "schema": schema,
        "strict": True,
    }


class OpenAIProvider:
    """AIProvider implementation backed by OpenAI vision-capable chat models."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None  # lazy

    def _get_client(self):
        if self._client is None:
            if not self.settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            from openai import AsyncOpenAI  # type: ignore
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    async def _json_chat(
        self,
        *,
        messages: list,
        model_cls,
        schema_name: str,
    ):
        client = self._get_client()
        resp = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": _strict_schema(model_cls, schema_name),
            },
        )
        text = resp.choices[0].message.content if resp.choices else None
        if not text:
            raise ValueError("empty model response")
        return model_cls.model_validate_json(text)

    async def generate_persona(self, input: SimulationInput) -> Persona:
        prompt = PERSONA_PROMPT.format(
            goal=input.goal,
            url=input.url,
            audience=input.audience or "unspecified",
        )
        out = await self._json_chat(
            messages=[{"role": "user", "content": prompt}],
            model_cls=PersonaOutput,
            schema_name="Persona",
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
        elements: str,
    ) -> DecisionOutput:
        history = "\n".join(
            f"step {s.step}: thought={s.thought!r} action={s.action.type} "
            f"result={s.result!r} ux_signal={s.ux_signal}"
            for s in previous_steps[-6:]
        ) or "(no previous steps)"
        last_result = previous_steps[-1].result if previous_steps else "(none)"

        sys_prompt = DECISION_SYSTEM
        user_text = (
            f"Persona: {persona.model_dump_json()}\n"
            f"Goal: {goal}\n"
            f"Current step: {current_step}\n"
            f"Last action result: {last_result}\n"
            f"Recent history:\n{history}\n\n"
            f"Interactable elements on screen "
            f"(use these IDs for click/type):\n{elements}"
        )
        b64 = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
        image_url = f"data:image/png;base64,{b64}"

        async def _call(extra: str = "") -> DecisionOutput:
            messages = [
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text + extra},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ]
            return await self._json_chat(
                messages=messages,
                model_cls=DecisionOutput,
                schema_name="Decision",
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
        out = await self._json_chat(
            messages=[
                {"role": "system", "content": REPORT_SYSTEM},
                {"role": "user", "content": user_text},
            ],
            model_cls=ReportOutput,
            schema_name="Report",
        )
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


def build_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "openai":
        return OpenAIProvider(settings)
    return GeminiProvider(settings)
