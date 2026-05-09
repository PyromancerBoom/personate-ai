from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings
from .models import (
    BackAction,
    ClickAction,
    JourneyAction,
    ScrollDownAction,
    StopAction,
    TypeAction,
    WaitAction,
)


class BrowserSession:
    """Async wrapper around a single Playwright Chromium page."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._pw: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    async def start(self, url: str) -> None:
        from playwright.async_api import async_playwright  # type: ignore
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.settings.playwright_headless
        )
        self._context = await self._browser.new_context(
            viewport={
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height,
            }
        )
        self._page = await self._context.new_page()
        await self._page.goto(url, wait_until="load", timeout=30_000)

    async def close(self) -> None:
        try:
            if self._context is not None:
                await self._context.close()
        finally:
            try:
                if self._browser is not None:
                    await self._browser.close()
            finally:
                if self._pw is not None:
                    await self._pw.stop()

    async def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        await self._page.screenshot(path=str(path), full_page=False)

    def _clamp_xy(self, x: int, y: int) -> tuple[int, int]:
        w = self.settings.viewport_width
        h = self.settings.viewport_height
        return max(0, min(int(x), w - 1)), max(0, min(int(y), h - 1))

    async def _settle(self) -> None:
        """Best-effort wait for the page to quiesce after an interaction.

        Swallows timeouts so a chatty SPA never aborts the run.
        """
        try:
            await self._page.wait_for_load_state("networkidle", timeout=2000)
        except Exception:
            pass

    async def execute(self, action: JourneyAction) -> str:
        page = self._page
        if isinstance(action, ClickAction):
            x, y = self._clamp_xy(*action.coordinates)
            await page.mouse.click(x, y)
            await self._settle()
            return f"clicked ({x}, {y})"
        if isinstance(action, TypeAction):
            if action.coordinates is not None:
                x, y = self._clamp_xy(*action.coordinates)
                await page.mouse.click(x, y)
            await page.keyboard.type(action.text, delay=15)
            await self._settle()
            return f"typed {action.text!r}"
        if isinstance(action, ScrollDownAction):
            dy = int(self.settings.viewport_height * 0.7)
            await page.mouse.wheel(0, dy)
            await page.wait_for_timeout(300)
            return f"scrolled down {dy}px"
        if isinstance(action, BackAction):
            resp = await page.go_back(wait_until="load")
            await self._settle()
            return "navigated back" if resp is not None else "back had no history"
        if isinstance(action, WaitAction):
            await page.wait_for_timeout(1000)
            return "waited 1000ms"
        if isinstance(action, StopAction):
            return f"stopped: {action.outcome} - {action.reason}"
        return "unknown action"
