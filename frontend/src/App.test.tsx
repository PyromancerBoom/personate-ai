import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { ErrorState } from "./components/ErrorState";
import { PersonaPreview } from "./components/PersonaPreview";
import { ReportView } from "./components/ReportView";
import { mockCompletedRun } from "./mocks/mockRun";

vi.mock("./lib/api", async () => {
  const actual = await vi.importActual<typeof import("./lib/api")>("./lib/api");
  return {
    ...actual,
    createRun: vi.fn(),
    getRun: vi.fn(),
    listRuns: vi.fn(),
    startRun: vi.fn()
  };
});

const { createRun, getRun, listRuns, startRun } = await import("./lib/api");
const mockedCreateRun = vi.mocked(createRun);
const mockedGetRun = vi.mocked(getRun);
const mockedListRuns = vi.mocked(listRuns);
const mockedStartRun = vi.mocked(startRun);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedCreateRun.mockResolvedValue({ ...mockCompletedRun, status: "draft", steps: [], report: undefined });
    mockedGetRun.mockResolvedValue(mockCompletedRun);
    mockedListRuns.mockResolvedValue([]);
    mockedStartRun.mockResolvedValue(mockCompletedRun);
  });

  it("blocks empty url and goal submissions", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.clear(screen.getByLabelText(/product url/i));
    await user.clear(screen.getByLabelText(/testing goal/i));
    await user.click(screen.getByRole("button", { name: /generate persona/i }));

    expect(screen.getByText("Enter a product URL.")).toBeInTheDocument();
    expect(screen.getByText("Enter a testing goal.")).toBeInTheDocument();
  });

  it("disables setup while the blocking start request is running", async () => {
    const user = userEvent.setup();
    const start = deferred<typeof mockCompletedRun>();
    mockedStartRun.mockReturnValue(start.promise);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /generate persona/i }));
    expect(await screen.findByText(mockCompletedRun.persona!.name)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /start simulation/i }));
    expect(await screen.findByText(/is using the product/i)).toBeInTheDocument();

    expect(screen.getByLabelText(/product url/i)).toBeDisabled();
    expect(screen.getByLabelText(/testing goal/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /simulation running/i })).toBeDisabled();
    expect(mockedCreateRun).toHaveBeenCalledTimes(1);

    start.resolve(mockCompletedRun);
    expect(await screen.findByText(/final simulation report/i)).toBeInTheDocument();
  });

  it("clears stale run evidence when a new create request fails", async () => {
    const user = userEvent.setup();
    mockedCreateRun
      .mockResolvedValueOnce({ ...mockCompletedRun, status: "draft", steps: [], report: undefined })
      .mockRejectedValueOnce(new Error("Backend unavailable"));
    render(<App />);

    await user.click(screen.getByRole("button", { name: /generate persona/i }));
    expect(await screen.findByText(mockCompletedRun.persona!.name)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate persona/i }));
    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/captured evidence/i)).not.toBeInTheDocument();
  });

  it("loads and opens a previous run from history", async () => {
    const user = userEvent.setup();
    mockedListRuns.mockResolvedValue([
      {
        id: mockCompletedRun.id,
        url: mockCompletedRun.url,
        goal: mockCompletedRun.goal,
        audience: mockCompletedRun.audience,
        status: mockCompletedRun.status,
        createdAt: mockCompletedRun.createdAt,
        updatedAt: mockCompletedRun.updatedAt,
        steps: mockCompletedRun.steps.length,
        findings: mockCompletedRun.report!.frictionMoments.length,
        outcome: mockCompletedRun.report!.outcome
      }
    ]);
    render(<App />);

    await user.click(await screen.findByRole("button", { name: new RegExp(mockCompletedRun.goal, "i") }));

    expect(mockedGetRun).toHaveBeenCalledWith(mockCompletedRun.id);
    expect(await screen.findByText(/Final simulation report/i)).toBeInTheDocument();
    expect(screen.getByText(mockCompletedRun.report!.summary)).toBeInTheDocument();
  });
});

describe("PersonaPreview", () => {
  it("renders persona fields", () => {
    const persona = mockCompletedRun.persona!;
    render(
      <PersonaPreview
        persona={persona}
        input={{ url: mockCompletedRun.url, goal: mockCompletedRun.goal, audience: mockCompletedRun.audience }}
        isRunning={false}
        onStart={() => undefined}
      />
    );

    expect(screen.getByText(persona.name)).toBeInTheDocument();
    expect(screen.getByText(persona.background)).toBeInTheDocument();
    expect(screen.getByText(persona.successCriteria)).toBeInTheDocument();
  });
});

describe("ReportView", () => {
  it("renders timeline, friction moments, and recommendations", async () => {
    render(<ReportView run={mockCompletedRun} onReset={() => undefined} />);

    expect(screen.getByText(/Final simulation report/i)).toBeInTheDocument();
    expect(screen.getByText(/Journey timeline/i)).toBeInTheDocument();
    expect(screen.getByText(/Friction moments/i)).toBeInTheDocument();
    expect(screen.getByText(mockCompletedRun.report!.recommendations[0])).toBeInTheDocument();
    await waitFor(() => expect(screen.getByAltText("Step 1 screenshot")).toBeInTheDocument());
  });

  it("handles missing report data", () => {
    render(<ReportView run={{ ...mockCompletedRun, report: undefined }} onReset={() => undefined} />);
    expect(screen.getByText(/completed run without report data/i)).toBeInTheDocument();
  });
});

describe("ErrorState", () => {
  it("renders backend errors", () => {
    render(<ErrorState message="Backend failed" onReset={() => undefined} />);
    expect(screen.getByText("Backend failed")).toBeInTheDocument();
  });
});
