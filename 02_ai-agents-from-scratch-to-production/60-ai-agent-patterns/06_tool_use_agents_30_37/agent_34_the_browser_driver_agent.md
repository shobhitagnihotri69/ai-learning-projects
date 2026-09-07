# Agent 34 — The Browser-Driver Agent

### Agent 34 — The Browser-Driver Agent

*Navigates web user interfaces via accessibility trees rather than pixel inspection.*

#### The Problem

Many of the world's important interfaces are web pages with no API. The agent needs to log into vendor portals, file forms, scrape per-tenant dashboards, complete account-management flows that have never had an API and never will.

Pixel-based vision models can do this but are slow, expensive, and brittle when the site changes. Static scraping breaks on the first JavaScript-driven update.

The general problem is **structured web automation**: operating a real browser against real sites in a way that's robust, observable, and recoverable.

#### Why Naïve Approaches Fail

- 

*"Take a screenshot, ask the vision model to click."* Works once, expensive, brittle to layout changes, slow.

- 

*"Use Selenium with hand-written selectors."* Works until the page structure changes. Selectors are a maintenance nightmare across hundreds of sites.

- 

*"HTTP-only emulation of the user."* Loses everything that depends on JavaScript, which is approximately every modern site.

#### The Mechanism

An accessibility-tree extractor with fallbacks for sites whose ARIA implementation is incomplete. A tree-to-action planner that picks the smallest sequence of interactions to reach the goal. A wait-for-stability discipline before each action. A screenshot-of-record captured at each action for later debugging.

![Pattern 058 — Agent 34 — The Browser-Driver Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df571de2ceb65d919d8_codex-pattern-058-agent-34-the-browser-driver-agent-the-mechanism.png)

```python
# tools/browser_driver.py
from dataclasses import dataclass, field
from typing import Literal

ActionType = Literal["click", "type", "select", "navigate", "wait", "extract"]

@dataclass
class AccessibilityNode:
    role: str             # "button" | "textbox" | "link" | "heading" | ...
    name: str             # accessible name (label, text, alt)
    value: str | None
    enabled: bool
    bbox: tuple[float, float, float, float]
    children: list["AccessibilityNode"] = field(default_factory=list)
    css_selector: str | None = None    # backup if accessibility lookup fails

@dataclass
class BrowserAction:
    type: ActionType
    target_node_role: str | None = None
    target_node_name: str | None = None
    value: str | None = None
    url: str | None = None
    timeout_ms: int = 5000

@dataclass
class ActionResult:
    success: bool
    screenshot_path: str
    new_url: str | None
    tree_summary: str
    error: str | None = None

class BrowserDriverAgent:
    def __init__(self, browser):     # e.g., a Playwright Browser instance
        self.browser = browser
        self.page = None
    
    async def execute(self, action: BrowserAction) -> ActionResult:
        if action.type == "navigate":
            await self.page.goto(action.url)
        else:
            await self._wait_for_stability()
            tree = await self._extract_tree()
            target = self._find_node(tree, action.target_node_role, action.target_node_name)
            if target is None:
                return ActionResult(success=False, screenshot_path="",
                                    new_url=self.page.url, tree_summary=self._summarize(tree),
                                    error=f"target_not_found:{action.target_node_role}:{action.target_node_name}")
            if action.type == "click":
                await self.page.locator(target.css_selector).click()
            elif action.type == "type":
                await self.page.locator(target.css_selector).fill(action.value)
            elif action.type == "select":
                await self.page.locator(target.css_selector).select_option(action.value)
            elif action.type == "extract":
                value = await self.page.locator(target.css_selector).inner_text()
                return ActionResult(success=True,
                                    screenshot_path=await self._snapshot(),
                                    new_url=self.page.url,
                                    tree_summary=self._summarize(tree),
                                    error=None) | {"extracted": value}
        await self._wait_for_stability()
        return ActionResult(success=True, screenshot_path=await self._snapshot(),
                            new_url=self.page.url,
                            tree_summary=self._summarize(await self._extract_tree()))
    
    async def _wait_for_stability(self, *, max_wait_ms: int = 5000):
        """Wait for the DOM to stop changing."""
        await self.page.wait_for_load_state("networkidle", timeout=max_wait_ms)
    
    async def _extract_tree(self) -> AccessibilityNode:
        snapshot = await self.page.accessibility.snapshot()
        return self._convert(snapshot)
    
    def _find_node(self, root: AccessibilityNode, role: str | None,
                   name: str | None) -> AccessibilityNode | None:
        def walk(n):
            if (role is None or n.role == role) and (name is None or name.lower() in n.name.lower()):
                return n
            for c in n.children:
                hit = walk(c)
                if hit:
                    return hit
            return None
        return walk(root)
    
    async def _snapshot(self) -> str:
        path = f"/tmp/agent-screenshot-{id(self)}.png"
        await self.page.screenshot(path=path)
        return path
```

#### Trade-offs and Alternatives

Browser automation has irreducible latency (page loads are seconds, not milliseconds) and operational complexity (browsers are heavyweight, crash, and leak memory).

For tasks that can use an API, prefer the API. The browser-driver is the right pattern when no API exists or when the site's behavior depends on JavaScript-rendered state that the underlying API can't reproduce.

A pixel-based vision-language fallback (the naïve approach) is still useful as a backup for sites whose accessibility tree is incomplete or wrong. The hybrid pattern (accessibility-first, vision-fallback) is what most production browser agents look like.

#### Production Failure Modes

- 

**Accessibility-tree incompleteness:** A modal dialog renders without ARIA labels, and the agent can't find its controls. Mitigate by detecting incomplete trees and falling back to vision-based localization with a screenshot.

- 

**Anti-bot detection:** The site detects the automation and challenges it. Mitigate by using residential proxies, randomized user agents, and human-like timing. And by deciding explicitly which sites the agent is permitted to operate, with operator awareness.

- 

**State leakage across sessions:** Cookies, local storage, or login state from one user's session leaks into another's. Mitigate by per-session browser contexts and explicit cleanup between sessions.

#### Case Study

A procurement back-office agent at a logistics firm places weekly orders across nine supplier portals — none of which expose an API — by driving each portal's accessibility tree. Average wall-clock time per portal is twenty-eight seconds (vs. forty-five seconds historical human time).

The agent processes approximately 1,400 orders per week with a measured action-success rate of 96%. The 4% of failures escalate to a human operator with the screenshot and tree summary attached.

**Pairs with:** Document Layout (Agent 2), Side-Effect Auditor (Agent 37), Multimodal Grounding (Agent 1) — the vision-based fallback when the accessibility tree is incomplete.
