from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


UxSignal = Literal[
    "confusion",
    "confidence",
    "hesitation",
    "friction",
    "progress",
    "drop_off",
    "neutral",
]
RunStatus = Literal["draft", "running", "completed", "failed"]
Outcome = Literal["success", "failure", "partial"]
Severity = Literal["low", "medium", "high"]


class Persona(CamelModel):
    id: str
    name: str
    background: str
    motivation: str
    experience_level: str
    concerns: list[str] = Field(default_factory=list)
    behavioral_traits: list[str] = Field(default_factory=list)
    success_criteria: str


class SimulationInput(CamelModel):
    url: str
    goal: str
    audience: str | None = None


class ClickAction(CamelModel):
    type: Literal["click"] = "click"
    coordinates: tuple[int, int]


class TypeAction(CamelModel):
    type: Literal["type"] = "type"
    text: str
    coordinates: tuple[int, int] | None = None


class ScrollDownAction(CamelModel):
    type: Literal["scroll_down"] = "scroll_down"


class BackAction(CamelModel):
    type: Literal["back"] = "back"


class WaitAction(CamelModel):
    type: Literal["wait"] = "wait"


class StopAction(CamelModel):
    type: Literal["stop"] = "stop"
    outcome: Outcome
    reason: str


JourneyAction = Annotated[
    Union[
        ClickAction,
        TypeAction,
        ScrollDownAction,
        BackAction,
        WaitAction,
        StopAction,
    ],
    Field(discriminator="type"),
]


class JourneyStep(CamelModel):
    step: int
    screenshot: str
    thought: str
    action: JourneyAction
    ux_signal: UxSignal
    page_summary: str
    result: str


class FrictionMoment(CamelModel):
    step: int
    severity: Severity
    finding: str
    screenshot: str
    recommendation: str


class SimulationReport(CamelModel):
    outcome: Outcome
    summary: str
    persona_narrative: str
    friction_moments: list[FrictionMoment] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class SimulationRun(CamelModel):
    id: str
    url: str
    goal: str
    audience: str | None = None
    status: RunStatus = "draft"
    persona: Persona | None = None
    steps: list[JourneyStep] = Field(default_factory=list)
    report: SimulationReport | None = None
    error: str | None = None
    created_at: str = Field(default_factory=_utc_now_iso)
    updated_at: str = Field(default_factory=_utc_now_iso)


# AI structured-output models. These mirror the public models but stay separate
# so we can validate provider responses before persisting them.

class PersonaOutput(CamelModel):
    name: str
    background: str
    motivation: str
    experience_level: str
    concerns: list[str]
    behavioral_traits: list[str]
    success_criteria: str


ActionType = Literal["click", "type", "scroll_down", "back", "wait", "stop"]


class DecisionOutput(CamelModel):
    """Flat schema for Gemini structured output.

    Gemini's response_schema does not reliably handle discriminated unions, so
    we receive a flat object and convert it to a real JourneyAction via
    `to_action()`. Only the fields relevant to the chosen `action_type` are
    expected to be populated.
    """

    thought: str
    page_summary: str
    ux_signal: UxSignal
    action_type: ActionType
    coordinates_x: int | None = None
    coordinates_y: int | None = None
    text: str | None = None
    outcome: Outcome | None = None
    reason: str | None = None

    def to_action(self) -> JourneyAction:
        t = self.action_type
        if t == "click":
            x, y = self.coordinates_x or 0, self.coordinates_y or 0
            return ClickAction(coordinates=(x, y))
        if t == "type":
            coords = None
            if self.coordinates_x is not None and self.coordinates_y is not None:
                coords = (self.coordinates_x, self.coordinates_y)
            return TypeAction(text=self.text or "", coordinates=coords)
        if t == "scroll_down":
            return ScrollDownAction()
        if t == "back":
            return BackAction()
        if t == "wait":
            return WaitAction()
        if t == "stop":
            return StopAction(
                outcome=self.outcome or "partial",
                reason=self.reason or "(no reason given)",
            )
        raise ValueError(f"unknown action_type: {t}")


class ReportOutput(CamelModel):
    outcome: Outcome
    summary: str
    persona_narrative: str
    friction_moments: list[FrictionMoment]
    recommendations: list[str]
