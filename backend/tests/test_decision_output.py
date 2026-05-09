"""Tests for the flat-schema DecisionOutput → JourneyAction conversion.

This is the contract Gemini/OpenAI structured output must satisfy. If a
provider changes field handling, only these tests need to be touched.
"""
import pytest

from app.models import (
    BackAction,
    ClickAction,
    DecisionOutput,
    PressKeyAction,
    ScrollDownAction,
    StopAction,
    TypeAction,
    WaitAction,
)


def _base(**overrides):
    base = dict(
        thought="t",
        page_summary="p",
        ux_signal="neutral",
    )
    base.update(overrides)
    return DecisionOutput(**base)


def test_to_action_click():
    a = _base(action_type="click", element_id=7).to_action()
    assert isinstance(a, ClickAction)
    assert a.element_id == 7


def test_to_action_click_missing_element_defaults_zero():
    a = _base(action_type="click").to_action()
    assert isinstance(a, ClickAction)
    assert a.element_id == 0


def test_to_action_type_with_element():
    a = _base(action_type="type", text="hello", element_id=5).to_action()
    assert isinstance(a, TypeAction)
    assert a.text == "hello"
    assert a.element_id == 5


def test_to_action_type_without_element_defaults_zero():
    a = _base(action_type="type", text="hi").to_action()
    assert isinstance(a, TypeAction)
    assert a.element_id == 0


def test_to_action_scroll_down():
    assert isinstance(_base(action_type="scroll_down").to_action(), ScrollDownAction)


def test_to_action_back():
    assert isinstance(_base(action_type="back").to_action(), BackAction)


def test_to_action_wait():
    assert isinstance(_base(action_type="wait").to_action(), WaitAction)


def test_to_action_type_with_submit():
    a = _base(action_type="type", text="hello", element_id=2, submit=True).to_action()
    assert isinstance(a, TypeAction)
    assert a.text == "hello"
    assert a.submit is True


def test_to_action_press_key_enter():
    a = _base(action_type="press_key", key="enter").to_action()
    assert isinstance(a, PressKeyAction)
    assert a.key == "enter"


def test_to_action_press_key_defaults_enter_when_missing():
    a = _base(action_type="press_key").to_action()
    assert isinstance(a, PressKeyAction)
    assert a.key == "enter"


def test_to_action_press_key_tab_and_escape():
    assert _base(action_type="press_key", key="tab").to_action().key == "tab"
    assert _base(action_type="press_key", key="escape").to_action().key == "escape"


def test_to_action_stop():
    a = _base(action_type="stop", outcome="success", reason="done").to_action()
    assert isinstance(a, StopAction)
    assert a.outcome == "success"
    assert a.reason == "done"


def test_to_action_stop_missing_fields_defaults_partial():
    a = _base(action_type="stop").to_action()
    assert isinstance(a, StopAction)
    assert a.outcome == "partial"
    assert a.reason == "(no reason given)"


def test_decision_output_round_trips_via_json():
    """Schema must serialize as flat camelCase so structured output works."""
    d = _base(action_type="click", element_id=4)
    j = d.model_dump(by_alias=True)
    assert j["actionType"] == "click"
    assert j["elementId"] == 4
    parsed = DecisionOutput.model_validate(j)
    assert parsed.to_action().element_id == 4


def test_unknown_action_type_raises_at_to_action():
    with pytest.raises(Exception):
        _base(action_type="explode")
