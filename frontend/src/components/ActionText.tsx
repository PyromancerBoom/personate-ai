import type { JourneyAction } from "../types/simulation";

export function actionText(action: JourneyAction): string {
  switch (action.type) {
    case "click":
      return `Clicked at ${action.coordinates[0]}, ${action.coordinates[1]}`;
    case "type":
      return action.coordinates
        ? `Typed "${action.text}" at ${action.coordinates[0]}, ${action.coordinates[1]}`
        : `Typed "${action.text}"`;
    case "scroll_down":
      return "Scrolled down";
    case "back":
      return "Went back";
    case "wait":
      return "Waited";
    case "stop":
      return `Stopped: ${action.outcome} - ${action.reason}`;
  }
}

export function ActionText({ action }: { action: JourneyAction }) {
  return <span>{actionText(action)}</span>;
}
