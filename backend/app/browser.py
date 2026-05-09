from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .config import Settings
from .models import (
    BackAction,
    ClickAction,
    JourneyAction,
    PressKeyAction,
    ScrollDownAction,
    StopAction,
    TypeAction,
    WaitAction,
)


_KEY_MAP = {"enter": "Enter", "tab": "Tab", "escape": "Escape"}


# Stability predicate injected into the page after every action.
# Resolves when (a) the document is past `loading`, (b) body has actual
# painted content (text OR a substantial DOM), and (c) MutationObserver
# has been quiet for `quietMs`. Hard-capped at 7s so a flaky page never
# pins the agent.
#
# This replaces networkidle, which is unreliable on Google/Gmail/SPAs
# (Playwright #1497, #2515, #6536). Pattern adapted from Stagehand's
# waitForSettledDom + Skyvern's white-page detector.
_STABLE_JS = r"""
([quietMs]) => new Promise((resolve) => {
  const start = performance.now();
  const HARD = 7000;
  let lastMutation = performance.now();
  const obs = new MutationObserver(() => { lastMutation = performance.now(); });
  try {
    obs.observe(document.documentElement, {
      childList: true, subtree: true, attributes: true, characterData: true
    });
  } catch (_) { resolve(true); return; }

  const painted = () => {
    if (document.readyState === 'loading') return false;
    const b = document.body;
    if (!b) return false;
    const hasText = (b.innerText || '').trim().length > 0;
    const hasNodes = document.querySelectorAll('*').length > 50;
    return hasText || hasNodes;
  };

  const tick = () => {
    const now = performance.now();
    if (now - start > HARD) { obs.disconnect(); resolve(false); return; }
    if (painted() && (now - lastMutation) >= quietMs) {
      obs.disconnect();
      requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)));
      return;
    }
    setTimeout(tick, 50);
  };
  tick();
});
"""


# Walk the DOM, return interactable elements as {tag, type, role, name, xpath}.
# Mirrors the heuristic used by browser-use's buildDomTree.js but in ~50 lines.
INDEX_JS = r"""
() => {
  const SEL = [
    'a[href]','button','input:not([type=hidden])','textarea','select','summary',
    '[role=button]','[role=link]','[role=checkbox]','[role=radio]',
    '[role=textbox]','[role=combobox]','[role=tab]','[role=menuitem]',
    '[contenteditable=""]','[contenteditable="true"]','[onclick]',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || s.opacity === '0')
      return false;
    if (r.bottom < -200 || r.top > innerHeight + 200) return false;
    return true;
  };

  const xpathOf = (el) => {
    const seg = [];
    for (; el && el.nodeType === 1; el = el.parentNode) {
      let i = 1;
      for (let s = el.previousSibling; s; s = s.previousSibling)
        if (s.nodeType === 1 && s.nodeName === el.nodeName) i++;
      seg.unshift(el.nodeName.toLowerCase() + '[' + i + ']');
    }
    return '/' + seg.join('/');
  };

  const seen = new Set();
  const out = [];
  document.querySelectorAll(SEL).forEach((el) => {
    if (seen.has(el) || !visible(el)) return;
    seen.add(el);
    const name = (
      el.getAttribute('aria-label') ||
      (el.innerText || '').trim() ||
      el.value ||
      el.placeholder ||
      el.title ||
      el.getAttribute('name') ||
      ''
    ).replace(/\s+/g, ' ').trim().slice(0, 80);
    out.push({
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      role: el.getAttribute('role') || '',
      name: name,
      xpath: xpathOf(el),
    });
  });
  return out;
}
"""


class BrowserSession:
    """Async wrapper around a single Playwright Chromium page."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._pw: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._elements: list[dict] = []

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

    async def index_elements(self) -> list[dict]:
        """Walk the page, cache and return the interactable element list."""
        try:
            self._elements = await self._page.evaluate(INDEX_JS)
        except Exception:
            self._elements = []
        return self._elements

    def format_elements_for_llm(self) -> str:
        if not self._elements:
            return "(no interactable elements detected)"
        lines = []
        for i, e in enumerate(self._elements):
            attrs = ""
            if e.get("type"):
                attrs += f' type="{e["type"]}"'
            if e.get("role"):
                attrs += f' role="{e["role"]}"'
            name = e.get("name") or ""
            lines.append(f'[{i}]<{e["tag"]}{attrs}>{name}</{e["tag"]}>')
        return "\n".join(lines)

    def _locator(self, idx: int):
        if idx < 0 or idx >= len(self._elements):
            raise IndexError(f"element {idx} out of range")
        xpath = self._elements[idx]["xpath"]
        return self._page.locator(f"xpath={xpath}").first

    async def _settle(self, *, max_total_ms: int = 8000, quiet_ms: int = 500) -> None:
        """Wait until the page is safe to screenshot after an arbitrary action.

        Handles full navigation, SPA route change, DOM mutation, and no-op.
        Never raises — agent loop must always make forward progress.
        """
        loop = asyncio.get_event_loop()
        deadline = loop.time() + max_total_ms / 1000

        # 1. If a navigation just started, wait for the new document to commit.
        try:
            remaining = max(250, int((deadline - loop.time()) * 1000))
            await self._page.wait_for_load_state(
                "domcontentloaded", timeout=remaining
            )
        except Exception:
            pass

        # 2. Paint + DOM-quiet predicate. The actual white-page fix.
        try:
            remaining = max(500, int((deadline - loop.time()) * 1000))
            await self._page.wait_for_function(
                _STABLE_JS, arg=[quiet_ms], timeout=remaining, polling=100
            )
        except Exception:
            pass

        # 3. Force a compositor frame so screenshots capture painted pixels.
        try:
            await self._page.evaluate(
                "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
            )
        except Exception:
            pass

    async def _type_into(self, loc, text: str) -> str:
        """Tiered text entry that handles inputs, textareas, AND rich editors.

        Mirrors browser-use's `_input_text_element_node`: focus → clear via
        JS → keyboard.type. Falls back through three strategies because
        `locator.fill()` alone fails on contenteditable widgets like Tally,
        Notion, and ProseMirror.
        """
        # Strategy 1: Native fill — fastest path, works for plain inputs.
        try:
            tag = (await loc.evaluate("el => el.tagName.toLowerCase()")) or ""
            is_editable = await loc.evaluate(
                "el => el.isContentEditable === true || "
                "el.getAttribute('contenteditable') === 'true' || "
                "el.getAttribute('contenteditable') === ''"
            )
            if tag in ("input", "textarea") and not is_editable:
                await loc.fill(text, timeout=3000)
                return "fill"
        except Exception:
            pass

        # Strategy 2: focus → clear via JS → keyboard.type. The browser-use
        # path. Works for contenteditable (Tally title, Notion, etc.) and
        # any rich editor that listens for real key events.
        try:
            try:
                await loc.focus(timeout=2000)
            except Exception:
                await loc.click(timeout=2000)
            await loc.evaluate(
                """el => {
                    const editable = el.isContentEditable === true ||
                        el.getAttribute('contenteditable') === 'true' ||
                        el.getAttribute('contenteditable') === '';
                    if (editable) {
                        while (el.firstChild) el.removeChild(el.firstChild);
                        el.textContent = '';
                        el.dispatchEvent(new InputEvent('input', {bubbles: true}));
                    } else if ('value' in el) {
                        const setter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ) || Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype, 'value'
                        );
                        (setter && setter.set ? setter.set : (v => el.value = v))
                            .call(el, '');
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }"""
            )
            await self._page.keyboard.type(text, delay=20)
            return "focus+type"
        except Exception:
            pass

        # Strategy 3: select-all + type. Last resort for editors that
        # don't expose a clean clear path but DO accept Ctrl+A.
        try:
            await loc.click(timeout=2000)
            await self._page.keyboard.press("Control+A")
            await self._page.keyboard.press("Delete")
            await self._page.keyboard.type(text, delay=20)
            return "selectall+type"
        except Exception as e:
            raise RuntimeError(
                f"all type strategies failed: {type(e).__name__}: {e}"
            )

    async def execute(self, action: JourneyAction) -> str:
        page = self._page
        if isinstance(action, ClickAction):
            try:
                loc = self._locator(action.element_id)
                await loc.scroll_into_view_if_needed(timeout=2000)
                await loc.click(timeout=5000)
            except IndexError:
                return f"element {action.element_id} not in current list"
            except Exception as e:
                return (
                    f"click on element {action.element_id} failed: "
                    f"{type(e).__name__}"
                )
            await self._settle()
            return f"clicked element {action.element_id}"
        if isinstance(action, TypeAction):
            try:
                loc = self._locator(action.element_id)
                await loc.scroll_into_view_if_needed(timeout=2000)
                typed_via = await self._type_into(loc, action.text)
            except IndexError:
                return f"element {action.element_id} not in current list"
            except Exception as e:
                return (
                    f"type into element {action.element_id} failed: "
                    f"{type(e).__name__}: {e}"
                )
            if action.submit:
                try:
                    await page.keyboard.press("Enter")
                except Exception:
                    pass
            await self._settle()
            suffix = " + Enter" if action.submit else ""
            return (
                f"typed {action.text!r} into element {action.element_id} "
                f"via {typed_via}{suffix}"
            )
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
        if isinstance(action, PressKeyAction):
            key = _KEY_MAP[action.key]
            await page.keyboard.press(key)
            await self._settle()
            return f"pressed {key}"
        if isinstance(action, StopAction):
            return f"stopped: {action.outcome} - {action.reason}"
        return "unknown action"
