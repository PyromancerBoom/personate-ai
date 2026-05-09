from app.models import (
    ClickAction,
    JourneyStep,
    Persona,
    SimulationRun,
    StopAction,
)


def test_persona_camel_case_serialization():
    p = Persona(
        id="abc",
        name="Maya",
        background="bg",
        motivation="mot",
        experience_level="non-technical",
        concerns=["a"],
        behavioral_traits=["b"],
        success_criteria="ok",
    )
    data = p.model_dump(by_alias=True)
    assert "experienceLevel" in data
    assert "successCriteria" in data
    assert "behavioralTraits" in data
    assert "experience_level" not in data


def test_journey_step_camel_alias_round_trip():
    step = JourneyStep(
        step=1,
        screenshot="/api/runs/x/screenshots/step_001.png",
        thought="hi",
        action=ClickAction(coordinates=(10, 20)),
        ux_signal="confusion",
        page_summary="dash",
        result="clicked",
    )
    data = step.model_dump(by_alias=True)
    assert data["uxSignal"] == "confusion"
    assert data["pageSummary"] == "dash"
    assert data["action"]["type"] == "click"
    parsed = JourneyStep.model_validate(data)
    assert parsed.ux_signal == "confusion"
    assert parsed.page_summary == "dash"


def test_run_omits_error_when_none():
    run = SimulationRun(id="r1", url="http://x", goal="g")
    data = run.model_dump(by_alias=True, exclude_none=True)
    assert "error" not in data
    assert "persona" not in data
    assert "report" not in data


def test_stop_action_discrimination():
    raw = {
        "step": 1,
        "screenshot": "/x.png",
        "thought": "done",
        "action": {"type": "stop", "outcome": "success", "reason": "ok"},
        "uxSignal": "confidence",
        "pageSummary": "p",
        "result": "stopped",
    }
    step = JourneyStep.model_validate(raw)
    assert isinstance(step.action, StopAction)
    assert step.action.outcome == "success"
