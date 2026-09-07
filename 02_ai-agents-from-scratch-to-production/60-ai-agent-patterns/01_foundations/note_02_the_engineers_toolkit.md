### Chapter 2 — The Engineer's Toolkit

The framework wars are over and nobody won. LangChain, LlamaIndex, AutoGen, CrewAI, DSPy, Haystack, Pydantic-AI, and the half-dozen serious in-house frameworks at the large labs all converge on the same five abstractions: a **model client**, a **tool registry**, a **prompt template system**, a **memory interface**, and an **orchestration loop**. They differ on which abstraction they make most pleasant and which they make most painful.

This chapter walks through those trade-offs without partisanship and gives a decision rubric for picking one. Or, more often, for picking none and building the five abstractions yourself in a few hundred lines.

#### 2.1 The five abstractions every framework converges on

When you strip a framework down to its load-bearing components, you find these five:

- 

**Model client:** A typed interface to one or more LLM providers, with the parts that matter for agents (function-calling, structured output, streaming, prompt-caching, retry, rate-limit handling) actually exposed. Frameworks differ on whether the client is leaky (you see the provider's quirks) or capping (you see a least-common-denominator interface).

- 

**Tool registry:** A catalogue of tools the policy can choose from, with structured descriptions, typed parameter schemas, invocation semantics, and (in the better frameworks) per-tool middleware for logging, retry, and authorization.

- 

**Prompt template system:** A way to compose prompts from invariant pieces, role-specific pieces, task-specific pieces, and dynamically-retrieved pieces. The frameworks that get this right treat prompts as versioned artifacts. The ones that don't treat prompts as string concatenations.

- 

**Memory interface:** A surface for reading and writing episodic events, semantic facts, retrieved documents, and prior conversations. Frameworks differ wildly on how opinionated this is, from "you decide" to "here is one giant vector store, use it."

- 

**Orchestration loop:** The actual run-the-agent loop. Frameworks differ on whether this is a fixed loop with hooks (LangChain's AgentExecutor) or a graph engine (LangGraph), or a debate harness (AutoGen), or a typed pipeline (DSPy).

If you understand these five, you can read any framework's source in an afternoon. You can also decide whether to use one. The decision rubric is: do you need to ship in two weeks (use a framework), or do you need to operate this for years (build the five abstractions, even if they sit on top of a framework as a thin internal layer)?

#### 2.2 Building the five abstractions yourself

Here's what the minimal-but-real version looks like. It's roughly two hundred lines and avoids every common mistake.

![Pattern 007 — 2.2 Building the five abstractions yourself](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca39996a5a8f7dedd3e_codex-pattern-007-2-2-building-the-five-abstractions-yourself.png)

```python
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
```

The key word in that file is *normalizes*. The provider differences matter for half the things and don't matter for the other half. Pinning them all behind a least-common-denominator interface looks clean and is wrong. Agents need access to provider-specific features (prompt caching with Anthropic, structured outputs with OpenAI, tool-use modes with Bedrock). The toolkit's job is to expose them when needed and to keep callers from depending on them when not.

![Pattern 008 — 2.2 Building the five abstractions yourself](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca39996a5a8f7dedd5e_codex-pattern-008-2-2-building-the-five-abstractions-yourself.png)

```python
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
```

![Pattern 009 — 2.2 Building the five abstractions yourself](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca39996a5a8f7dedd9f_codex-pattern-009-2-2-building-the-five-abstractions-yourself.png)

```python
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
```

The four-layer split is not cosmetic. Each layer has a different change cadence and a different cacheability profile. Treating them as one string conflates them and loses both maintainability and (with providers that support prompt caching) money.

![Pattern 010 — 2.2 Building the five abstractions yourself](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca30fad12a602ce894a_codex-pattern-010-2-2-building-the-five-abstractions-yourself.png)

```python
# toolkit/memory.py
class MemoryStore:
    """Pluggable backend; the interface stays the same."""
    def write(self, namespace: str, key: str, value: dict, ttl: int | None = None) -> None: ...
    def read(self, namespace: str, key: str) -> dict | None: ...
    def search(self, namespace: str, query: str, k: int = 10) -> list[dict]: ...
    def delete(self, namespace: str, key: str) -> None: ...
```

![Pattern 011 — 2.2 Building the five abstractions yourself](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca4c289ca370bc05fe9_codex-pattern-011-2-2-building-the-five-abstractions-yourself.png)

```python
# toolkit/loop.py
class AgentLoop:
    def __init__(self, *, policy, registry, memory, observers):
        self.policy, self.registry, self.memory, self.observers = (
            policy, registry, memory, observers)
    
    def run(self, goal: str, max_steps: int = 50) -> State:
        # The reference harness from Chapter 1, plumbed with these abstractions.
        ...
```

These five files plus the Chapter 1 harness give you a real toolkit in under 400 lines of code. It's missing nothing that production frameworks have *for production-grade work*. But it's missing many things that they have *for novice users*, which is a different problem.

#### 2.3 The components that aren't optional

Beyond the five abstractions, there are concerns no agent in production should be built without:

- 

**Vector stores and the embedding lifecycle:** This is the topic of Agent 28 in detail. For the toolkit level, treat the vector store as a first-class store with its own lifecycle (ingestion, re-embedding, sharding, eviction), not as a magic "memory" that you write to and forget.

- 

**Structured-output enforcement:** When the model is supposed to produce JSON, don't parse free text. Use the provider's structured-output mode, validate against a JSON Schema, and reject-and-retry on failure. The retry should be parameterized: if a JSON Schema is failing repeatedly, the schema is wrong, not the model.

- 

**Evaluation harnesses:** You won't pick the right model, the right prompt, or the right pattern combination without one. Build it first. It doesn't have to be sophisticated: a YAML file with cases, a function that runs them, and a pass/fail rate gets you eighty percent of the value.

- 

**Prompt-version control:** Every prompt the agent uses is a versioned artifact with a name, a version, and a hash. When a bug shows up in production, you can attribute it to the exact prompt revision that produced it.

- 

**Secret management for tool credentials:** Tools call APIs. APIs need credentials. The credentials shouldn't be in the prompt, in the trace, or in the agent's working memory. They live in a secret manager, are fetched at tool-invocation time, and never appear in any artifact the agent persists.

- 

**Observability stack:** Traces, span hierarchies, prompt diffs, tool-call inspection. The minimum bar is per-step tracing with structured data, and the higher bar is replay of any historical session.

#### 2.4 Model selection

The rule is simple: you can't pick the right model until you have a working evaluation harness, so build the harness first. Every other selection heuristic, like price-per-token, context window, function-calling support, or vendor stability, matters but is downstream of the evaluation.

Build twenty cases that represent your deployment distribution, run them against three candidate models, look at pass-rate and cost-per-pass, and decide.

A practical wrinkle: the right model often varies by step within a single agent. A small, fast model is fine for a router, while a frontier model is needed for the planner, with an even larger one (or self-consistency voting on a frontier model) for the auditor. The toolkit's model-client abstraction should make per-step model selection a one-line change, not a refactor.

#### 2.5 The gateway pattern

The single highest-leverage piece of infrastructure most teams skip is an **internal LLM gateway**. The gateway is a thin service in front of every model provider that handles:

- 

Rate limiting and provider failover.

- 

Secret rotation for provider keys.

- 

Observability injection (trace IDs, latency, cost per call).

- 

Model swaps without code changes.

- 

Per-call cost attribution to a project, a team, or a user.

- 

Audit logging of every prompt and completion that crosses an organizational boundary.

It's fifty lines of FastAPI in front of `httpx`, and it will save you a year of pain.

![Pattern 012 — 2.5 The gateway pattern](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca4c289ca370bc06070_codex-pattern-012-2-5-the-gateway-pattern.png)

```python
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
```

Every agent in your organization talks to this gateway. The gateway talks to the providers. You get an audit log, a cost-attribution surface, a rate-limit story, and a swap-the-model story for free.
