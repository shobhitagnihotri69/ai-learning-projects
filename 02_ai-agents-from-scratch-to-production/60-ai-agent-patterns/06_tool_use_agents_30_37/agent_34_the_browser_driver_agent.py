"""
Agent 34 — The Browser-Driver Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# tools/browser_driver.py
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

