import { useCallback, useEffect, useState } from "react";
import { ApiError, createRun, getRun, listRuns, startRun } from "./lib/api";
import type { RunSummary, SimulationInput, SimulationRun } from "./types/simulation";
import { DashboardShell } from "./components/DashboardShell";
import { ErrorState } from "./components/ErrorState";
import { PersonaPreview } from "./components/PersonaPreview";
import { ReportView } from "./components/ReportView";
import { RunningState } from "./components/RunningState";
import { SetupForm } from "./components/SetupForm";

type AppState = "idle" | "creating" | "personaReady" | "running" | "completed" | "failed" | "history";

const initialInput: SimulationInput = {
  url: "http://localhost:3000",
  goal: "Test whether a new user can create their first project.",
  audience: "Non-technical small business owners"
};

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Something went wrong while running the simulation.";
}

function stateForLoadedRun(loadedRun: SimulationRun): AppState {
  if (loadedRun.status === "completed") {
    return "completed";
  }
  if (loadedRun.status === "failed") {
    return "failed";
  }
  return "history";
}

export default function App() {
  const [state, setState] = useState<AppState>("idle");
  const [input, setInput] = useState<SimulationInput>(initialInput);
  const [run, setRun] = useState<SimulationRun | undefined>();
  const [error, setError] = useState<string | undefined>();
  const [history, setHistory] = useState<RunSummary[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | undefined>();
  const [selectedHistoryRunId, setSelectedHistoryRunId] = useState<string | undefined>();

  const persona = run?.persona;
  const isViewingHistory = Boolean(selectedHistoryRunId);
  const showSetup = !isViewingHistory && state !== "completed" && !(state === "failed" && Boolean(run?.steps.length));
  const workspaceClassName = showSetup ? "workspace" : "workspace workspace-report";

  const refreshHistory = useCallback(async () => {
    setIsHistoryLoading(true);
    try {
      setHistory(await listRuns());
      setHistoryError(undefined);
    } catch (caughtError) {
      setHistoryError(errorMessage(caughtError));
    } finally {
      setIsHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  async function handleCreateRun(nextInput: SimulationInput) {
    if (state === "running") {
      return;
    }

    setSelectedHistoryRunId(undefined);
    setInput(nextInput);
    setError(undefined);
    setRun(undefined);
    setState("creating");
    try {
      const nextRun = await createRun(nextInput);
      setRun(nextRun);
      await refreshHistory();
      setState("personaReady");
    } catch (caughtError) {
      setError(errorMessage(caughtError));
      setState("failed");
    }
  }

  async function handleStartRun() {
    if (!run || state === "running") {
      return;
    }

    setError(undefined);
    setState("running");
    try {
      const finalRun = await startRun(run.id);
      setRun(finalRun);
      await refreshHistory();
      if (finalRun.status === "failed") {
        setError(finalRun.error ?? "The simulation failed.");
        setState("failed");
        return;
      }
      if (finalRun.status !== "completed") {
        setError(`The backend returned status "${finalRun.status}" instead of a final report.`);
        setState("failed");
        return;
      }
      setState("completed");
    } catch (caughtError) {
      setError(errorMessage(caughtError));
      setState("failed");
    }
  }

  async function handleSelectHistoryRun(runId: string) {
    if (state === "running" || state === "creating") {
      return;
    }

    setSelectedHistoryRunId(runId);
    setError(undefined);
    setRun(undefined);
    setState("history");
    try {
      const loadedRun = await getRun(runId);
      setRun(loadedRun);
      setInput({
        url: loadedRun.url,
        goal: loadedRun.goal,
        audience: loadedRun.audience
      });
      setState(stateForLoadedRun(loadedRun));
    } catch (caughtError) {
      setError(errorMessage(caughtError));
      setState("failed");
      void refreshHistory();
    }
  }

  function reset() {
    setSelectedHistoryRunId(undefined);
    setState("idle");
    setRun(undefined);
    setError(undefined);
  }

  return (
    <DashboardShell
      state={state}
      run={run}
      history={history}
      isHistoryLoading={isHistoryLoading}
      historyError={historyError}
      activeRunId={run?.id ?? selectedHistoryRunId}
      isHistoryDisabled={state === "creating" || state === "running"}
      onSelectHistoryRun={handleSelectHistoryRun}
    >
      <div className={workspaceClassName}>
        {showSetup ? (
          <section className="setup-column" id="workspace">
            <SetupForm
              initialValues={input}
              isCreating={state === "creating"}
              isDisabled={state === "running"}
              onSubmit={handleCreateRun}
            />
          </section>
        ) : null}

        <section className="result-column">
          {state === "idle" || state === "creating" ? (
            <div className="empty-panel">
              <p className="eyebrow">Ready</p>
              <h2>{state === "creating" ? "Generating a persona..." : "Generate a persona to begin."}</h2>
              <p>The final report will appear here after the backend simulation completes.</p>
            </div>
          ) : null}

          {state === "history" ? (
            <div className="empty-panel">
              <p className="eyebrow">Saved run</p>
              <h2>{run ? "This saved run has not produced a final report." : "Loading saved run..."}</h2>
              <p>
                {run
                  ? `Status: ${run.status}. Draft and running history entries are kept read-only here.`
                  : "The saved simulation will open here without starting a new browser run."}
              </p>
            </div>
          ) : null}

          {state === "personaReady" && persona ? (
            <PersonaPreview persona={persona} input={input} isRunning={false} onStart={handleStartRun} />
          ) : null}

          {state === "running" ? <RunningState personaName={persona?.name} /> : null}

          {state === "completed" && run ? <ReportView run={run} onReset={reset} /> : null}

          {state === "failed" ? (
            <ErrorState
              message={error ?? run?.error ?? "The simulation failed."}
              run={run}
              onReset={reset}
              onRetry={isViewingHistory ? undefined : () => handleCreateRun(input)}
            />
          ) : null}
        </section>
      </div>
    </DashboardShell>
  );
}
