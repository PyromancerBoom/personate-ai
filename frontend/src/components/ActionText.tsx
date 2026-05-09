import type { JourneyAction } from "../types/simulation";

export function actionText(action: JourneyAction): string {
  switch (action.type) {
    case "click":
      return action.coordinates
        ? `Clicked at ${action.coordinates[0]}, ${action.coordinates[1]}`
        : `Clicked element ${action.elementId ?? "unknown"}`;
    case "type":
      if (action.coordinates) {
        return `Typed "${action.text}" at ${action.coordinates[0]}, ${action.coordinates[1]}`;
      }
      if (action.elementId !== undefined) {
        const suffix = action.submit ? " + Enter" : "";
        return `Typed "${action.text}" into element ${action.elementId}${suffix}`;
      }
      return `Typed "${action.text}"`;
    case "scroll_down":
      return "Scrolled down";
    case "back":
      return "Went back";
    case "wait":
      return "Waited";
    case "press_key":
      return `Pressed ${action.key}`;
    case "stop":
      return `Stopped: ${action.outcome} - ${action.reason}`;
  }
}

export function ActionText({ action }: { action: JourneyAction }) {
  return <span>{actionText(action)}</span>;
}
