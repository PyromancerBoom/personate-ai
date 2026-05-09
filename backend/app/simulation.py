from __future__ import annotations

import logging
from datetime import datetime, timezone

from .ai_provider import AIProvider
from .browser import BrowserSession
from .config import Settings
from .models import (
    JourneyStep,
    SimulationRun,
    StopAction,
)
from .storage import RunStorage

log = logging.getLogger(__name__)


def _short_error(prefix: str, e: BaseException) -> str:
    msg = str(e).strip()
    if not msg:
        msg = "see server logs"
    return f"{prefix}: {type(e).__name__}: {msg}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _screenshot_url(run_id: str, step: int) -> str:
    return f"/api/runs/{run_id}/screenshots/step_{step:03d}.png"


async def run_simulation(
    *,
    run: SimulationRun,
    settings: Settings,
    storage: RunStorage,
    provider: AIProvider,
) -> SimulationRun:
    """Execute the full Playwright + AI loop for a single run.

    On any unrecoverable failure, marks run failed/error and persists.
    Always closes the browser. Always saves run.json after each step.
    """
    if run.persona is None:
        run.status = "failed"
        run.error = "run has no persona"
        run.updated_at = _now_iso()
        storage.save_run(run)
        return run

    browser = BrowserSession(settings)
    try:
        try:
            await browser.start(run.url)
        except Exception as e:
            log.exception("browser launch/navigation failed for run %s", run.id)
            run.status = "failed"
            run.error = _short_error("browser launch/navigation failed", e)
            run.updated_at = _now_iso()
            storage.save_run(run)
            return run

        for step_num in range(1, settings.max_journey_steps + 1):
            shot_path = storage.screenshots_dir(run.id) / f"step_{step_num:03d}.png"
            try:
                await browser.screenshot(shot_path)
            except Exception as e:
                log.exception("screenshot failed for run %s step %d", run.id, step_num)
                run.status = "failed"
                run.error = _short_error(f"screenshot failed at step {step_num}", e)
                run.updated_at = _now_iso()
                storage.save_run(run)
                return run

            await browser.index_elements()
            elements_text = browser.format_elements_for_llm()

            try:
                decision = await provider.decide_next_action(
                    persona=run.persona,
                    goal=run.goal,
                    current_step=step_num,
                    screenshot_path=shot_path,
                    previous_steps=run.steps,
                    elements=elements_text,
                )
            except Exception as e:
                log.exception("AI decision failed for run %s step %d", run.id, step_num)
                if not run.steps:
                    run.status = "failed"
                    run.error = _short_error("AI decision failed before any step", e)
                    run.updated_at = _now_iso()
                    storage.save_run(run)
                    return run
                decision_action = StopAction(
                    outcome="partial",
                    reason=_short_error("AI decision failed", e),
                )
                step = JourneyStep(
                    step=step_num,
                    screenshot=_screenshot_url(run.id, step_num),
                    thought="(unavailable)",
                    action=decision_action,
                    ux_signal="drop_off",
                    page_summary="(unavailable)",
                    result="forced stop after AI failure",
                )
                run.steps.append(step)
                run.updated_at = _now_iso()
                storage.save_run(run)
                break

            try:
                decision_action = decision.to_action()
            except Exception as e:
                decision_action = StopAction(
                    outcome="partial",
                    reason=f"AI decision was malformed: {e}",
                )

            try:
                result = await browser.execute(decision_action)
            except Exception as e:
                result = f"action raised: {e}"

            step = JourneyStep(
                step=step_num,
                screenshot=_screenshot_url(run.id, step_num),
                thought=decision.thought,
                action=decision_action,
                ux_signal=decision.ux_signal,
                page_summary=decision.page_summary,
                result=result,
            )
            run.steps.append(step)
            run.updated_at = _now_iso()
            storage.save_run(run)

            if isinstance(decision_action, StopAction):
                break

        try:
            report = await provider.generate_report(
                run=run, persona=run.persona, steps=run.steps
            )
            run.report = report
            run.status = "completed"
            run.error = None
            storage.save_report(run.id, report)
        except Exception as e:
            log.exception("report generation failed for run %s", run.id)
            run.status = "failed"
            run.error = _short_error("report generation failed", e)

        run.updated_at = _now_iso()
        storage.save_run(run)
        return run
    finally:
        await browser.close()
