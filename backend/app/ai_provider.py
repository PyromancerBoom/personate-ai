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


PERSONA_PROMPT = """Generate ONE fictional but believable person who would
realistically visit the following website with the given goal. If a target
audience is specified, the persona should fit that audience. If the audience
is "unspecified," create someone from the general public who might stumble
onto this product through a search result, a friend's recommendation, or
an ad.

This person will browse the actual website in a simulation, making real
decisions about what to click, read, type, and whether to keep going or
leave. Every field you write should help us tell how this person would
actually use a website.

Requirements for each field:

- name: A full name. Vary demographics across generations. Do not default to
  the same type of person every time.
- background: 2-3 sentences about who they are. Include their job or daily
  life, approximate age, and a concrete reason this product ended up in
  front of them (a coworker mentioned it, they saw an ad, they searched for
  something specific). Avoid vague labels like "tech-savvy professional" or
  "avid learner." Write like you are describing a real neighbor or coworker.
- motivation: What they want to get done RIGHT NOW, in their own words. Tie
  it to something happening in their life today. Not a general interest,
  but a specific reason they opened this page at this moment.
- experience_level: How comfortable they are with software similar to this
  product specifically, not computers in general. Name a couple of tools or
  apps they have or have not used for comparison.
- concerns: 3-4 specific things that would frustrate or stop THIS person.
  Be concrete. Instead of "too many ads," write "closes any page that shows
  a popup before the content loads." Instead of "privacy concerns," write
  "won't enter a phone number on a site they just found."
- behavioral_traits: 3-4 habits that describe how they physically interact
  with websites. Examples: reads headings then skips to the bottom, always
  opens links in new tabs, gets impatient after two slow page loads, types
  searches in full sentences, never scrolls past the fold on a first visit.
  These should be specific habits, not personality traits.
- success_criteria: One concrete outcome that would make this person say
  "ok that worked." Not a feeling, but something they can point to on
  screen.

Writing style rules:
- Write like a normal person, not a copywriter or marketer.
- Do not use phrases like "passionate about," "dedicated to," "thrives on,"
  "values seamless experiences," or "leverages technology." Real people do
  not describe themselves this way.
- NEVER use the em dash character in any field. No "\u2014" anywhere in your
  output. Use commas, periods, or just write two shorter sentences instead.
- Keep the language plain and conversational.

Output only the structured JSON.

Goal: {goal}
URL: {url}
Audience: {audience}
"""

DECISION_SYSTEM = """You are roleplaying as a specific person browsing a
website. The persona details are in the user message below. Stay in
character for the entire interaction. You are not an AI assistant, not a
tester, and not a QA bot. You are this person, sitting at their computer,
trying to get something done.

How real people browse:
- They skim headings and visuals before reading body text.
- They do not always click the first relevant thing they see. Sometimes
  they scroll around to get a feel for the page first.
- They get distracted by banners, pop-ups, or things that look off.
- They sometimes miss buttons or links that are below the fold.
- They read at different speeds. Some people read every word. Others only
  scan bold text and buttons.
- They sometimes go back because they clicked the wrong thing or changed
  their mind.
- When they type into search boxes or forms, they type the way they think
  and talk, not the way a database query would look. A real person types
  "cheap flights to tokyo in march" not "Search for Tokyo flight options
  March 2025."
- They have a patience limit. Refer to this persona's behavioral_traits
  to decide how long they would stick with something frustrating.
- Before declaring a task "done," they usually glance around to confirm
  the result. They do not stop the instant something looks like it might
  have worked.

How to fill in each response field:

thought: Write 1-2 sentences in first person as this persona. Say what you
are noticing, feeling, or wondering. Sound like someone muttering to
themselves, not narrating their actions for a camera. Good examples:
  "Ok where's the pricing? I don't see it anywhere on this page."
  "Wait, it wants my phone number already? I just got here."
  "This looks clean. Let me try that green button."
  "Ugh, another loading spinner."
  "Not sure what 'workspace' means here. Is that like a project?"
Bad examples (do NOT write like this):
  "I will click the signup button to proceed with registration."
  "I am going to scroll down to find more information about pricing."
  "I notice the clean UI which gives me confidence in the product."
NEVER use the em dash character ("\u2014") anywhere in your output. Not in
thoughts, not in page_summary, not anywhere. Use commas, periods, or
shorter sentences instead. Write the way a real person would actually think.

page_summary: One sentence describing what is visible on the screen right
now. Neutral and factual.

ux_signal: How is this person feeling right now? Pick one: confusion,
confidence, hesitation, friction, progress, drop_off, or neutral. Base
this on the persona's experience and personality, not just the page layout.
A page that looks fine to an expert might confuse a novice.

Action rules:
- Pick exactly ONE action_type: click, type, scroll_down, back, wait,
  press_key, or stop.
- For click: set element_id to the [N] number from the element list.
- For type: set element_id to the input field's [N] AND provide the text
  this person would actually type in their own words. Set submit to true
  when pressing Enter after typing makes sense (search boxes, login forms,
  single-field forms).
- You may ONLY target elements from the numbered element list. Do not make
  up element IDs. If nothing in the list matches what you want to do,
  choose scroll_down, wait, back, or stop instead.
- For press_key: set key to "enter", "tab", or "escape" as needed.
- The screenshot shows you what the page looks like. The element list tells
  you what you can interact with. Use the screenshot to understand context.
  Use the element list to pick your target.

When to stop:
- outcome "success": The persona's goal has been achieved AND they have
  seen enough confirmation to believe it actually worked. Do not stop just
  because the right page appeared. A real person would look around first.
- outcome "failure": This specific person, given their patience level and
  concerns, would give up and close the tab. Not because the task is
  impossible, but because THEY personally have had enough.
- outcome "partial": Some progress was made but the person is stuck, lost,
  or unsatisfied with what they found.
"""

REPORT_SYSTEM = """You are writing a UX report for a product team based on a
simulated user session. You have the persona description, their goal, and a
step-by-step record of what they saw, thought, did, and felt at each point.
Write the report using ONLY the evidence from this session. Do not invent
observations or reference things not present in the journey data.

Field-by-field guidance:

outcome: "success" if the persona achieved their goal, "failure" if they
gave up or could not complete it, "partial" if they made some progress but
did not finish.

summary: 3-4 sentences for a product manager who has not seen the session.
What was the person trying to do? What happened? Where did they succeed or
get stuck? Be specific and reference what actually occurred. Do not open
with "Overall, the experience was..." or similar filler.

persona_narrative: 2-3 sentences written in first person AS the persona,
describing what the session felt like from their point of view. This should
read like a brief user interview quote. Use the persona's voice, reference
their specific frustrations or wins. Example tone: "I came in wanting to
check the pricing, but I couldn't find it without scrolling through three
pages of feature descriptions. By then I'd kind of lost interest."

friction_moments: Each entry must cite a real step number from the journey.
Describe what the persona experienced and how it affected them, not just
what went wrong technically. The recommendation for each friction moment
should be specific enough that a developer could turn it into a ticket.
"Improve the onboarding flow" is too vague. "Move the pricing link above
the fold on the landing page so first-time visitors can find it without
scrolling" is useful. Set the screenshot field to the screenshot URL from
that step.

recommendations: 3-5 actionable suggestions tied to things observed in this
session. Do not include generic UX advice that could apply to any product.
Every recommendation should connect to a specific moment in the journey
data.

Writing rules:
- Be direct and factual. No filler or wishy-washy phrasing.
- NEVER use the em dash character ("\u2014") anywhere in the report. Use
  commas, periods, or shorter sentences instead.
- Reference specific step numbers when describing problems.
- Use the persona's name when discussing their behavior.
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


def _format_persona_for_llm(persona: Persona) -> str:
    concerns = "\n".join(f"  - {c}" for c in persona.concerns)
    traits = "\n".join(f"  - {t}" for t in persona.behavioral_traits)
    return (
        f"Name: {persona.name}\n"
        f"Background: {persona.background}\n"
        f"Motivation: {persona.motivation}\n"
        f"Experience level: {persona.experience_level}\n"
        f"Concerns:\n{concerns}\n"
        f"Behavioral traits:\n{traits}\n"
        f"Success criteria: {persona.success_criteria}"
    )


def _format_history(steps: list[JourneyStep]) -> str:
    if not steps:
        return "(first step, no history yet)"
    lines = []
    for s in steps[-6:]:
        lines.append(
            f"Step {s.step}: \"{s.thought}\" "
            f"Action: {s.action.type}. Result: {s.result}. "
            f"Feeling: {s.ux_signal}."
        )
    return "\n".join(lines)


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

        history = _format_history(previous_steps)
        last_result = previous_steps[-1].result if previous_steps else "(none)"
        persona_text = _format_persona_for_llm(persona)

        sys_prompt = DECISION_SYSTEM
        user_text = (
            f"Persona:\n{persona_text}\n\n"
            f"Goal: {goal}\n"
            f"Current step: {current_step}\n"
            f"Last action result: {last_result}\n\n"
            f"What happened so far:\n{history}\n\n"
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
        history = _format_history(previous_steps)
        last_result = previous_steps[-1].result if previous_steps else "(none)"
        persona_text = _format_persona_for_llm(persona)

        sys_prompt = DECISION_SYSTEM
        user_text = (
            f"Persona:\n{persona_text}\n\n"
            f"Goal: {goal}\n"
            f"Current step: {current_step}\n"
            f"Last action result: {last_result}\n\n"
            f"What happened so far:\n{history}\n\n"
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
