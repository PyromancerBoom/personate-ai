import { describe, expect, it } from "vitest";
import { actionText } from "./ActionText";
import type { JourneyAction } from "../types/simulation";

describe("actionText", () => {
  const cases: [JourneyAction, string][] = [
    [{ type: "click", coordinates: [12, 34] }, "Clicked at 12, 34"],
    [{ type: "click", elementId: 5 }, "Clicked element 5"],
    [{ type: "type", text: "hello" }, 'Typed "hello"'],
    [{ type: "type", text: "hello", coordinates: [55, 66] }, 'Typed "hello" at 55, 66'],
    [{ type: "type", text: "hello", elementId: 16 }, 'Typed "hello" into element 16'],
    [{ type: "type", text: "hello", elementId: 16, submit: true }, 'Typed "hello" into element 16 + Enter'],
    [{ type: "scroll_down" }, "Scrolled down"],
    [{ type: "back" }, "Went back"],
    [{ type: "wait" }, "Waited"],
    [{ type: "press_key", key: "enter" }, "Pressed enter"],
    [{ type: "stop", outcome: "partial", reason: "No useful progress remains." }, "Stopped: partial - No useful progress remains."]
  ];

  it.each(cases)("renders %j", (action, expected) => {
    expect(actionText(action)).toBe(expected);
  });
});
