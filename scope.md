# Personate AI Scope

## Product Summary

Personate AI is an AI user simulator for live web products.

Teams provide a product URL, a testing goal, and optionally a target audience. The system generates one realistic user persona, lets that persona operate the live app through Playwright, records the journey, and produces UX insights plus developer-ready Playwright checks.

## Pitch

AI-generated users operate your live product like real people, simulate different journeys, reveal where each user gets stuck, and generate actionable insights plus Playwright checks.

## Core Workflow

```txt
Product URL + testing goal
->
Gemini generates 1 realistic persona
->
Each persona operates the live web app through Playwright
->
The system records screenshots, thoughts, actions, and UX signals
->
Gemini generates journey insights
->
Cursor SDK generates Playwright checks and developer handoff notes
```

## Primary Users

- Product teams validating onboarding, conversion, activation, or core workflows.
- Founders testing early product usability before formal research.
- Designers and engineers looking for quick UX friction signals.
- QA teams converting discovered issues into automated checks.

## Inputs

- Product or local app URL.
- Testing goal.
- Optional target audience.

Example:

```txt
URL: http://localhost:3000
Goal: Test whether new users can complete onboarding and create their first project.
Audience: Non-technical small business owners.
```

## MVP Features

### 1. Setup

Users can configure a simulation run.

- Enter product or local app URL.
- Enter testing goal.
- Enter optional target audience.
- Generate 1 persona.
- Review the generated persona before running.

### 2. Persona Generation

Gemini generates one realistic persona based on the goal and optional audience.

Each persona should include:

- Name.
- Background.
- Experience level.
- Motivation.
- Likely concerns.
- Behavioral traits.
- Success criteria for the goal.

### 3. Live App Operation

Each AI persona uses the live app through Playwright.

Supported actions:

```txt
click(x, y)
type(text)
scroll_down()
back()
wait()
stop(success/failure)
```

Simulation rules:

- Use screenshots and visible page context for decisions.
- Do not rely on DOM selectors for AI decision-making.
- Limit the persona journey to 10-15 steps.
- Support running the generated persona.

### 4. Journey Recording

The system records evidence at each step.

Logged fields:

```json
{
  "persona": "Maya",
  "step": 4,
  "screenshot": "step_004.png",
  "thought": "I don't know where onboarding starts.",
  "action": "click",
  "coordinates": [522, 318],
  "ux_signal": "confusion",
  "page_summary": "Dashboard with Settings, Integrations, and Reports"
}
```

Journey logs should include:

- Screenshot path.
- Persona thought.
- Action selected.
- Action result.
- UX signal.
- Page summary.
- Completion state.

### 5. Insight Generation

Gemini analyzes each journey and produces UX findings.

Insights should include:

- Persona outcome.
- Completion or failure reason.
- Key friction moments.
- Confusion, hesitation, backtracking, or drop-off signals.
- Severity ranking.
- Recommendations.
- Supporting screenshots.

### 6. Playwright Check Generation

Cursor SDK reads journey logs and insights to generate developer handoff artifacts.

Outputs:

- Suggested Playwright checks for critical issues.
- Reproduction steps.
- Developer-facing issue summary.
- Relevant screenshot references.

## UI Scope

### Screen 1: Setup

Purpose: configure a UX simulation.

Required elements:

- URL input.
- Goal input.
- Audience input.
- Generate Personas button.
- Persona preview cards.

### Screen 2: Run

Purpose: monitor AI users operating the app.

Required elements:

- Persona card with status.
- Current screenshot.
- Current thought.
- Current action.
- Current UX signal.
- Run Persona button.
- Step progress indicator.

### Screen 3: Insights

Purpose: review outcomes and export developer-ready findings.

Required elements:

- Persona outcomes.
- Journey timelines.
- Key friction moments with screenshots.
- Severity ranking.
- Recommendations.
- Generated Playwright checks.

## Technical Responsibilities

### Gemini

- Generate one persona.
- Understand screenshots.
- Decide next action.
- Simulate user thoughts.
- Tag UX signals.
- Generate journey insights.

### Playwright

- Open the product URL.
- Take screenshots.
- Execute persona actions.
- Capture journey evidence.
- Save logs and screenshots.

### Cursor SDK

- Read journey logs and insights.
- Generate Playwright checks.
- Create developer handoff notes.

## Data Model

### Run

- ID.
- URL.
- Goal.
- Audience.
- Created timestamp.
- Status.
- Personas.
- Journeys.
- Insights.

### Persona

- ID.
- Name.
- Background.
- Motivation.
- Experience level.
- Concerns.
- Success criteria.

### Journey Step

- Step number.
- Screenshot path.
- Page summary.
- Thought.
- Action.
- Coordinates or typed text.
- UX signal.
- Result.

### Insight

- Persona ID.
- Outcome.
- Severity.
- Finding.
- Evidence.
- Recommendation.
- Generated check.

## Constraints

- One persona per run.
- Maximum 10-15 steps per journey.
- Web apps only.
- Playwright execution only.
- Vision and screenshot-based decisions.
- No DOM selectors for AI simulation decisions.
- No complex authentication.
- No multi-tab flows.
- No desktop apps.
- No advanced replay view in MVP.
- No mobile app testing in MVP.

## Out Of Scope For MVP

- Browser extension.
- Hosted test infrastructure.
- Multi-user collaboration.
- Complex authenticated flows.
- Cross-browser testing.
- Mobile native app testing.
- Visual diffing.
- Accessibility audits.
- Synthetic analytics dashboards.
- Fine-grained video replay editor.
- Persona marketplace or saved persona library.

## Success Criteria

The MVP is successful if a user can:

1. Enter a local or public web app URL.
2. Describe a realistic product goal.
3. Generate 1 plausible persona.
4. Run that persona through the live app.
5. Review screenshots, thoughts, actions, and UX signals.
6. See clear findings about where users got stuck or succeeded.
7. Generate at least one useful Playwright check from a discovered issue.

## Suggested Build Phases

### Phase 1: Local Simulation Core

- Setup form.
- Persona generation.
- Playwright browser control.
- Screenshot capture.
- Step logs.
- Basic run screen.

### Phase 2: AI Decision Loop

- Screenshot-to-next-action prompting.
- Thought simulation.
- UX signal tagging.
- Stop condition handling.
- Single-persona run execution.

### Phase 3: Insights And Handoff

- Journey summarization.
- Friction detection.
- Severity ranking.
- Recommendations.
- Playwright check generation.

### Phase 4: Polish And Reliability

- Better error states.
- Safer action validation.
- Journey timeline UI.
- Exportable reports.
- More robust local app handling.

## MVP Demo Scenario

Use a local demo product such as an onboarding app.

Demo goal:

```txt
Test whether a first-time user can sign up, understand the dashboard, and create their first project.
```

Expected demo output:

- 1 generated persona.
- 10-15 recorded steps.
- Screenshots for each step.
- Persona-specific thoughts and UX signals.
- Ranked findings.
- Generated Playwright checks for the most important friction points.
