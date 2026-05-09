import type { SimulationInput, SimulationRun } from "../types/simulation";

const now = new Date().toISOString();

const dashboardSvg =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1280' height='900'%3E%3Crect width='1280' height='900' fill='%23f7f8fb'/%3E%3Crect x='96' y='88' width='1088' height='112' rx='8' fill='%232b5c7d'/%3E%3Ctext x='136' y='155' font-family='Arial' font-size='34' fill='white'%3EDashboard%3C/text%3E%3Crect x='96' y='250' width='300' height='150' rx='8' fill='white' stroke='%23d8dee8'/%3E%3Ctext x='126' y='325' font-family='Arial' font-size='24' fill='%23243647'%3ECreate project%3C/text%3E%3C/svg%3E";
const formSvg =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1280' height='900'%3E%3Crect width='1280' height='900' fill='%23fafafa'/%3E%3Crect x='320' y='120' width='640' height='560' rx='8' fill='white' stroke='%23d8dee8'/%3E%3Ctext x='372' y='196' font-family='Arial' font-size='32' fill='%23243647'%3ENew project%3C/text%3E%3Crect x='372' y='250' width='536' height='58' rx='6' fill='%23f3f5f8'/%3E%3Ctext x='394' y='286' font-family='Arial' font-size='18' fill='%2361707f'%3EProject name%3C/text%3E%3C/svg%3E";
const frictionSvg =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1280' height='900'%3E%3Crect width='1280' height='900' fill='%23fafafa'/%3E%3Crect x='320' y='120' width='640' height='560' rx='8' fill='white' stroke='%23d8dee8'/%3E%3Ctext x='372' y='196' font-family='Arial' font-size='32' fill='%23243647'%3ENew project%3C/text%3E%3Crect x='372' y='515' width='210' height='54' rx='6' fill='%232b5c7d'/%3E%3Ctext x='421' y='549' font-family='Arial' font-size='18' fill='white'%3EContinue%3C/text%3E%3Ctext x='372' y='368' font-family='Arial' font-size='18' fill='%238a5a24'%3EWorkspace type is unclear%3C/text%3E%3C/svg%3E";
const successSvg =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1280' height='900'%3E%3Crect width='1280' height='900' fill='%23f7f8fb'/%3E%3Crect x='96' y='88' width='1088' height='112' rx='8' fill='%23345b4c'/%3E%3Ctext x='136' y='155' font-family='Arial' font-size='34' fill='white'%3EProject created%3C/text%3E%3Crect x='96' y='250' width='1088' height='210' rx='8' fill='white' stroke='%23d8dee8'/%3E%3Ctext x='136' y='330' font-family='Arial' font-size='28' fill='%23243647'%3EClient onboarding%3C/text%3E%3C/svg%3E";

export const mockCompletedRun: SimulationRun = {
  id: "run_mock_001",
  url: "http://localhost:3000",
  goal: "Create a first project after landing on the dashboard.",
  audience: "Non-technical small business owners",
  status: "completed",
  persona: {
    id: "persona_maya",
    name: "Maya Chen",
    background: "Runs a small bookkeeping firm and evaluates software between client calls.",
    motivation: "Wants a simple way to organize client projects without needing implementation help.",
    experienceLevel: "Comfortable with common SaaS tools, cautious with technical setup.",
    concerns: [
      "Unclear onboarding steps",
      "Accidentally choosing the wrong workspace settings",
      "Losing time to jargon-heavy screens"
    ],
    behavioralTraits: ["Scans headings first", "Avoids advanced settings", "Looks for explicit next steps"],
    successCriteria: "Understands the dashboard and creates a first project without help."
  },
  steps: [
    {
      step: 1,
      screenshot: dashboardSvg,
      thought: "The dashboard looks clean, and I see a project-related card.",
      action: { type: "click", coordinates: [236, 326] },
      uxSignal: "progress",
      pageSummary: "Dashboard with a prominent project creation card.",
      result: "Clicked the Create project card."
    },
    {
      step: 2,
      screenshot: formSvg,
      thought: "This looks like the right form, so I will name the project.",
      action: { type: "type", text: "Client onboarding", coordinates: [430, 280] },
      uxSignal: "confidence",
      pageSummary: "New project form with a project name field.",
      result: "Typed the project name."
    },
    {
      step: 3,
      screenshot: frictionSvg,
      thought: "I am not sure what workspace type means, but continue seems safe.",
      action: { type: "click", coordinates: [478, 542] },
      uxSignal: "hesitation",
      pageSummary: "Project form with an unclear workspace setting and a Continue button.",
      result: "Clicked Continue."
    },
    {
      step: 4,
      screenshot: successSvg,
      thought: "The project appears to be created, so my main goal is complete.",
      action: { type: "stop", outcome: "success", reason: "The first project was created." },
      uxSignal: "progress",
      pageSummary: "Project confirmation screen with the newly created project.",
      result: "Stopped after successful project creation."
    }
  ],
  report: {
    outcome: "partial",
    summary:
      "Maya completed the project creation flow, but hesitated when asked to choose settings that were not explained in plain language.",
    personaNarrative:
      "Maya moved quickly when the interface used familiar terms like project and continue. Her confidence dropped around workspace terminology because it did not connect to her goal.",
    frictionMoments: [
      {
        step: 3,
        severity: "medium",
        finding: "Workspace terminology caused hesitation before the final confirmation step.",
        screenshot: frictionSvg,
        recommendation:
          "Replace abstract workspace language with goal-oriented labels or add one-line helper text."
      }
    ],
    recommendations: [
      "Add helper text for workspace settings in the project creation form.",
      "Keep the Create project entry point prominent on first dashboard load.",
      "Show a clear project-created confirmation with the next recommended action."
    ]
  },
  createdAt: now,
  updatedAt: now
};

export function createDraftMockRun(input: SimulationInput): SimulationRun {
  return {
    ...mockCompletedRun,
    id: `run_mock_${Date.now()}`,
    url: input.url,
    goal: input.goal,
    audience: input.audience,
    status: "draft",
    steps: [],
    report: undefined,
    error: undefined,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
}

export function createFailedMockRun(draft: SimulationRun): SimulationRun {
  return {
    ...draft,
    status: "failed",
    error: "The browser could not reach the target URL. Check that the local app is running.",
    steps: mockCompletedRun.steps.slice(0, 2),
    updatedAt: new Date().toISOString()
  };
}

export function completeMockRun(draft: SimulationRun): SimulationRun {
  return {
    ...mockCompletedRun,
    id: draft.id,
    url: draft.url,
    goal: draft.goal,
    audience: draft.audience,
    persona: draft.persona ?? mockCompletedRun.persona,
    createdAt: draft.createdAt,
    updatedAt: new Date().toISOString()
  };
}
