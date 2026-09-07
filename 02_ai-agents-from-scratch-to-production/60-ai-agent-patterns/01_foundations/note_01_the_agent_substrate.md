### Chapter 1 — The Agent Substrate

An agent is a program with three properties: it observes an environment, it maintains some persistent state across observations, and it emits actions whose effects on that environment feed back into its next observation.

The interesting word in that sentence is *environment*. For the agents in this book, the environment is almost never the physical world. Instead, it's a software surface: an API, a database, a web page, a filesystem, a chat history, or a stream of events. Treating the environment as a software surface is what makes agent engineering tractable. Treating it as a fuzzy social or physical reality is what makes agent engineering pseudoscience.

#### 1.1 The observation-action loop

The simplest agent is a loop:

![Pattern 001 — 1.1 The observation-action loop](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5bfd6e9a9fe71f56ee81_codex-pattern-001-1-1-the-observation-action-loop.png)

```python
def run_agent(goal: str, env: Environment, max_steps: int = 50) -> Result:
    state = State(goal=goal, history=[])
    for step in range(max_steps):
        observation = env.observe()
        state.history.append(observation)

        action = policy(state)               # the LLM-driven choice
        if action.type == "terminate":
            return Result(success=True, state=state)

        outcome = env.act(action)            # mutates the world; returns observation-like
        state.history.append(outcome)

    return Result(success=False, state=state, reason="step_budget_exhausted")
```

This is the entire abstraction. Every agent in the book is a refinement of this loop. The refinements take the form of:

- 

**Replacing the policy:** From a single model call to a planner, a debate, a constraint solver, or a composition of all three.

- 

**Replacing the state:** From a flat history to typed memories, hierarchical plans, belief distributions, or skill libraries.

- 

**Replacing the environment:** From a single tool to a curated toolset, a sandboxed shell, a browser, a multi-agent surface, or a human-in-the-loop.

- 

**Replacing the termination condition:** From step-budget exhaustion to goal-check verification, plan-completion, constitutional refusal, or operator override.

The discipline of this book is that *each replacement is named*: it gets a pattern, a code shape, a failure profile, and a case study. There's no such thing as a generic "more sophisticated agent." There are agents with specific patterns in specific slots of the loop.

#### 1.2 Policy versus tool

The distinction between *policy* and *tool* is the most-confused boundary in agent engineering. The policy is the deciding component. It reads the state and chooses what to do next. The tool is the acting component. It carries out the chosen action against the environment. The two are not the same and should never share an implementation.

A policy without tools is a chatbot. A tool without a policy is a function call. An agent is the combination, mediated by a loop. Every pattern in this book either modifies the policy, modifies the tool surface, or modifies the loop that combines them — never all three simultaneously, because patterns that modify all three are usually two patterns in a trench coat.

![Pattern 002 — 1.2 Policy versus tool](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca2cd945e9ae18d8584_codex-pattern-002-1-2-policy-versus-tool.png)

```python
class Policy(Protocol):
    """Reads state, returns the next action."""
    def __call__(self, state: State) -> Action: ...

class Tool(Protocol):
    """Executes one action, returns the outcome."""
    name: str
    description: str
    parameters: dict        # JSON Schema for arguments
    def invoke(self, args: dict) -> Outcome: ...
```

These two interfaces are the type signature of agent engineering. If your code doesn't cleanly separate them, or something equivalent, you'll end up building the separation anyway, under pressure, the first time a policy change and a tool change collide in the same bug.

#### 1.3 The role of the planner

The policy in a sophisticated agent is rarely a single model call. It's typically a planner that produces a multi-step plan and an executor that runs the plan. The split matters because the failure modes of planning are different from the failure modes of execution.

A planner fails by being wrong about the world. It produces a plan whose steps don't connect, don't respect the constraints, or don't lead to the goal. An executor fails by mis-binding parameters, mis-handling tool errors, or failing to detect that the plan has gone off the rails. Treating these as the same component conflates the failures and makes neither addressable.

![Pattern 003 — 1.3 The role of the planner](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca271de2ceb65d85d33_codex-pattern-003-1-3-the-role-of-the-planner.png)

```python
class Planner(Protocol):
    def plan(self, goal: Goal, state: State) -> Plan: ...

class Executor(Protocol):
    def run(self, plan: Plan, state: State, env: Environment) -> ExecutionResult: ...

class Agent:
    def __init__(self, planner: Planner, executor: Executor):
        self.planner = planner
        self.executor = executor

    def run(self, goal: Goal, env: Environment) -> Result:
        state = State(goal=goal)
        while not state.terminated:
            plan = self.planner.plan(goal, state)
            outcome = self.executor.run(plan, state, env)
            state = state.update(outcome)
            if outcome.replan_required:
                continue          # the executor noticed the plan was wrong
            if outcome.complete:
                state.terminated = True
        return Result(state=state)
```

This split is the topic of Chapter 7. The patterns in that chapter (Hierarchical Decomposer, Tree-of-Thought, Plan-Then-Execute, Adaptive Replanner, and Backward Goal-Regression) are all variations on which side of the split does which work.

#### 1.4 In-context state versus persistent memory

The state visible to a policy at a given moment is the union of two things: the in-context state (what is in the prompt, including tool results) and the persistent memory (what is stored in some external store the agent can read from and write to).

The mistake to avoid is conflating them. In-context state is volatile, expensive, and limited in size by the model's context window. Persistent memory is durable, cheap to expand, and limited only by what you choose to retain.

The patterns in Chapter 8 (Episodic Buffer, Semantic Curator, Working-Memory Manager, Forgetting Policy, Memory-of-Self, Vector-Store Curator, Persistent Identity) exist to manage the boundary between these two, and they all assume the boundary is explicit.

![Pattern 004 — 1.4 In-context state versus persistent memory](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca2a90f3d34d7e270a5_codex-pattern-004-1-4-in-context-state-versus-persistent-memory.png)

```python
@dataclass
class Memory:
    in_context: list[Message]               # current prompt content
    episodic: EpisodicStore                  # event log
    semantic: SemanticStore                  # promoted facts
    skills: SkillLibrary                     # learned procedures
    self_model: SelfModel                    # what the agent thinks it is

    def compose_prompt(self, step: Step) -> list[Message]:
        """The Working-Memory Manager (Agent 25) lives here."""
        ...
```

The act of composing the prompt for each step is itself an agent pattern (the Working-Memory Manager, Agent 25). Most teams discover this only after building one agent without it and watching context costs spiral.

#### 1.5 Deterministic harness, stochastic policy

A useful invariant: the harness is deterministic, the policy is stochastic. The loop, the executor, the memory layer, the tool layer, the observability layer are all deterministic Python that you wrote. The policy is the part that calls a large language model and gets a non-deterministic answer.

This separation matters for two reasons. First, it confines the non-determinism to a single point. When something goes wrong, you can rerun the harness against a recorded policy output and reproduce the failure exactly. Second, it makes the policy substitutable. You can swap a frontier model for a smaller one, a single-shot call for a self-consistency vote, an API call for a local model, or an entire model for a deterministic stub during testing — without rewriting the rest of the system.

![Pattern 005 — 1.5 Deterministic harness, stochastic policy](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca2a90f3d34d7e27123_codex-pattern-005-1-5-deterministic-harness-stochastic-policy.png)

```python
class RecordedPolicy:
    """For replay debugging: deterministic substitute for an LLM-backed policy."""
    def __init__(self, recording: list[Action]):
        self.recording = list(reversed(recording))
    def __call__(self, state: State) -> Action:
        return self.recording.pop()

# Production
agent = Agent(
    policy=LLMPolicy(provider="<your-provider>", model="<your-model>"),
    tools=production_tools,
    memory=production_memory,
)

# Debugging an incident
trace = load_trace(incident_id="incident-2026-04-19-0034")
replay_agent = Agent(
    policy=RecordedPolicy(trace.actions),
    tools=production_tools,
    memory=production_memory,
)
result = replay_agent.run(trace.goal, trace.env_snapshot)
assert result.failure == trace.failure   # the bug reproduces
```

If your agent code doesn't admit this substitution, your debugging story is much worse than it has to be.

#### 1.6 The five canonical failure modes

Every pattern in the book is, in some sense, a response to one or more of five canonical failure modes. They appear so often, across so many otherwise unrelated systems, that they deserve names. The names recur throughout the book:

- 

**Looped reasoning:** The agent thinks-acts-thinks-acts forever without progress. This is caused by the policy proposing actions that don't change the state in a way the policy can perceive. You can address it with the bounded ReAct loop (Agent 17), the Adaptive Replanner (Agent 20), and any plan-based pattern that maintains an explicit progress measure.

- 

**Tool spoofing:** The agent is talked into calling a tool against the wrong target, with the wrong arguments, or under the wrong context. It's caused by input the model treats as instruction when it should treat as data. You can address it with the Constitution-Bound Agent (Agent 53), the Side-Effect Auditor (Agent 37), and structural input/instruction separation in the prompt architecture.

- 

**Context exhaustion:** The agent loses track of its goal in the middle of a long session because the goal has scrolled out of context. It's caused by treating the context window as if it had infinite memory semantics. You can address it with the Working-Memory Manager (Agent 25), the Hierarchical Decomposer (Agent 16), and per-step prompt composition.

- 

**Goal drift:** The agent gradually pivots from the original objective to a related but different one. It's caused by the policy interpreting intermediate results as if they were the goal. You can address it with the Plan-Then-Execute pattern (Agent 19), the Drift Detector (Agent 59), and any pattern that maintains an explicit goal-check separate from the policy.

- 

**Silent success on the wrong task:** The agent confidently completes a task adjacent to the one it was asked. It's caused by the policy "rounding the user's intent" to something it knows how to do. You can address it with the Chain-of-Thought Auditor (Agent 8), the Reflection Agent (Agent 47), and verification patterns that compare the output to the input rather than to itself.

When something goes wrong in production, the first question is which of the five it is. The second question is which patterns the agent doesn't yet have for that failure class.

#### 1.7 A reference harness

The chapter closes with a working reference implementation in roughly three hundred lines of Python. Every later pattern in the book is described as a modification of, or addition to, this harness.

![Pattern 006 — 1.7 A reference harness](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca3a90f3d34d7e27161_codex-pattern-006-1-7-a-reference-harness.png)

```python
# agents/harness.py — the canonical reference implementation
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Callable, Optional

# ---- Core types ---------------------------------------------------------------

@dataclass
class Observation:
    source: str                       # tool name or environment channel
    payload: dict
    timestamp: float

@dataclass
class Action:
    type: str                         # "tool_call" | "terminate" | "ask_human" | ...
    tool: Optional[str] = None
    args: dict = field(default_factory=dict)
    rationale: str = ""

@dataclass
class Outcome:
    observation: Observation
    error: Optional[str] = None

@dataclass
class State:
    goal: str
    history: list = field(default_factory=list)   # interleaved Observations/Actions
    memory: "Memory" = field(default_factory=lambda: Memory())
    terminated: bool = False
    failure_reason: Optional[str] = None

@dataclass
class Memory:
    episodic: list = field(default_factory=list)
    semantic: dict = field(default_factory=dict)
    self_model: dict = field(default_factory=dict)

# ---- Protocols ----------------------------------------------------------------

class Tool(Protocol):
    name: str
    description: str
    parameters: dict
    def invoke(self, args: dict) -> Outcome: ...

class Policy(Protocol):
    def __call__(self, state: State, tools: dict[str, Tool]) -> Action: ...

class Observer(Protocol):
    """Observability hook called on every loop event."""
    def on_action(self, state: State, action: Action) -> None: ...
    def on_outcome(self, state: State, outcome: Outcome) -> None: ...
    def on_terminate(self, state: State) -> None: ...

# ---- The harness --------------------------------------------------------------

@dataclass
class Harness:
    policy: Policy
    tools: dict[str, Tool]
    observers: list[Observer] = field(default_factory=list)
    max_steps: int = 50
    goal_check: Optional[Callable[[State], bool]] = None

    def run(self, goal: str) -> State:
        state = State(goal=goal)
        for step in range(self.max_steps):
            action = self.policy(state, self.tools)
            for obs in self.observers:
                obs.on_action(state, action)
            state.history.append(action)

            if action.type == "terminate":
                state.terminated = True
                break

            outcome = self._execute(action)
            for obs in self.observers:
                obs.on_outcome(state, outcome)
            state.history.append(outcome.observation)

            if self.goal_check and self.goal_check(state):
                state.terminated = True
                break
        else:
            state.failure_reason = "step_budget_exhausted"

        for obs in self.observers:
            obs.on_terminate(state)
        return state

    def _execute(self, action: Action) -> Outcome:
        if action.type != "tool_call":
            return Outcome(observation=Observation(
                source="harness", payload={"action_type": action.type}, timestamp=0.0))
        tool = self.tools.get(action.tool)
        if tool is None:
            return Outcome(
                observation=Observation(source="harness", payload={}, timestamp=0.0),
                error=f"unknown_tool:{action.tool}")
        try:
            return tool.invoke(action.args)
        except Exception as e:
            return Outcome(
                observation=Observation(source=action.tool, payload={}, timestamp=0.0),
                error=f"tool_exception:{type(e).__name__}:{e}")
```

If you can hold this harness in your head, you can hold the rest of the book in your head. Every pattern in Part II is a refinement, replacement, or extension of one of its components.

