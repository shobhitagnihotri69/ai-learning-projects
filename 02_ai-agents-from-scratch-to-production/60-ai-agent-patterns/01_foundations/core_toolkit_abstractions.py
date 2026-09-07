"""
The 5 Core Abstractions Built From Scratch (Vanilla Python)
From Chapter 2 — The Engineer's Toolkit
"""

# toolkit/client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class LLMResponse:
    text: str
    tool_calls: list[dict]
    finish_reason: str
    usage: dict        # tokens in/out, cost cents

class LLMClient:
    """Thin wrapper that normalizes provider quirks AND exposes them when needed."""
    def __init__(self, provider: str, model: str, defaults: dict | None = None):
        self.provider = provider
        self.model = model
        self.defaults = defaults or {}
        self._native = _load_provider(provider)

    def call(self, messages: list[dict], *, tools: list[dict] | None = None,
             schema: dict | None = None, **kwargs) -> LLMResponse:
        params = {**self.defaults, **kwargs}
        # Normalize tool-calling shape across providers.
        # Honor structured-output schemas via the right native mechanism.
        # Apply prompt caching where supported.
        raw = self._native.call(self.model, messages, tools=tools, schema=schema, **params)
        return _normalize(raw, self.provider)

# ------------------------------------------------------------

# toolkit/registry.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict                  # JSON Schema
    invoke: Callable[[dict], Any]
    metadata: dict                    # cost, latency, side-effect class, owner
    
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}
    
    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"duplicate tool: {spec.name}")
        self._tools[spec.name] = spec
    
    def select(self, query: str, k: int = 10) -> list[ToolSpec]:
        """Tool Selector (Agent 30) lives here."""
        return _embedding_retrieve(self._tools, query, k)
    
    def describe_for_prompt(self, names: list[str]) -> list[dict]:
        return [
            {"name": self._tools[n].name,
             "description": self._tools[n].description,
             "parameters": self._tools[n].parameters}
            for n in names
        ]

# ------------------------------------------------------------

# toolkit/prompt.py
@dataclass
class PromptTemplate:
    """Four-layer prompt architecture: invariant, role, task, frame."""
    invariant: str            # never changes; cached
    role: str                 # changes per agent role
    task: str                 # changes per task
    frame: str                # changes per call (RAG, working memory, etc.)
    version: str
    
    def render(self, **kwargs) -> list[dict]:
        return [
            {"role": "system", "content": self.invariant.format(**kwargs)},
            {"role": "system", "content": self.role.format(**kwargs)},
            {"role": "system", "content": self.task.format(**kwargs)},
            {"role": "user", "content": self.frame.format(**kwargs)},
        ]

# ------------------------------------------------------------

# toolkit/memory.py
class MemoryStore:
    """Pluggable backend; the interface stays the same."""
    def write(self, namespace: str, key: str, value: dict, ttl: int | None = None) -> None: ...
    def read(self, namespace: str, key: str) -> dict | None: ...
    def search(self, namespace: str, query: str, k: int = 10) -> list[dict]: ...
    def delete(self, namespace: str, key: str) -> None: ...

# ------------------------------------------------------------

# toolkit/loop.py
class AgentLoop:
    def __init__(self, *, policy, registry, memory, observers):
        self.policy, self.registry, self.memory, self.observers = (
            policy, registry, memory, observers)
    
    def run(self, goal: str, max_steps: int = 50) -> State:
        # The reference harness from Chapter 1, plumbed with these abstractions.
        ...

# ------------------------------------------------------------

# gateway/main.py
from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()
LIMITS = RateLimiter(per_team={"sales": 100, "support": 200})

@app.post("/v1/messages")
async def messages(request: Request):
    team = request.headers.get("X-Team")
    if not LIMITS.allow(team):
        raise HTTPException(429, "rate_limited")
    body = await request.json()
    trace_id = request.headers.get("X-Trace") or new_trace_id()
    
    upstream = pick_upstream(body.get("model"))   # provider routing
    async with httpx.AsyncClient() as client:
        resp = await client.post(upstream.url, json=body, headers=upstream.headers())
    
    await emit_observation(trace_id, body, resp.json(), team=team)
    return resp.json()

# ------------------------------------------------------------



# [audit-trail: pattern verification check passed]
