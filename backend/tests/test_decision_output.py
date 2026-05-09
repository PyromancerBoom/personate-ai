"""Tests for the flat-schema DecisionOutput → JourneyAction conversion.

This is the contract Gemini structured output must satisfy. If Gemini changes
field handling, only these tests need to be touched.
"""
import pytest

from app.models import (
    BackAction,
    ClickAction,
    DecisionOutput,
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
    a = _base(action_type="click", coordinates_x=10, coordinates_y=20).to_action()
    assert isinstance(a, ClickAction)
    assert a.coordinates == (10, 20)


def test_to_action_click_missing_coords_defaults_zero():
    a = _base(action_type="click").to_action()
    assert isinstance(a, ClickAction)
    assert a.coordinates == (0, 0)


def test_to_action_type_with_coords():
    a = _base(
        action_type="type", text="hello", coordinates_x=5, coordinates_y=6
    ).to_action()
    assert isinstance(a, TypeAction)
    assert a.text == "hello"
    assert a.coordinates == (5, 6)


def test_to_action_type_without_coords():
    a = _base(action_type="type", text="hi").to_action()
    assert isinstance(a, TypeAction)
    assert a.coordinates is None


def test_to_action_scroll_down():
    assert isinstance(_base(action_type="scroll_down").to_action(), ScrollDownAction)


def test_to_action_back():
    assert isinstance(_base(action_type="back").to_action(), BackAction)


def test_to_action_wait():
    assert isinstance(_base(action_type="wait").to_action(), WaitAction)


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
    """Schema must serialize as flat camelCase so Gemini's response_schema works."""
    d = _base(action_type="click", coordinates_x=1, coordinates_y=2)
    j = d.model_dump(by_alias=True)
    assert j["actionType"] == "click"
    assert j["coordinatesX"] == 1
    assert j["coordinatesY"] == 2
    parsed = DecisionOutput.model_validate(j)
    assert parsed.to_action().coordinates == (1, 2)


def test_unknown_action_type_raises_at_to_action():
    # Construction validates Literal, so this is the closest we can get.
    with pytest.raises(Exception):
        _base(action_type="explode")
