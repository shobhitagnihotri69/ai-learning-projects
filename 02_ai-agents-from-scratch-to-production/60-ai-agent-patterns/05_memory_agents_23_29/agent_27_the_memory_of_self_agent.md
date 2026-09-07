# Agent 27 — The Memory-of-Self Agent

### Agent 27 — The Memory-of-Self Agent

*Maintains a self-model of the agent's own capabilities, limits, and history.*

#### The Problem

Most agents have no idea what they themselves are good at. The agent's policy is opinionated about how to do tasks, but it has no opinion about whether *it specifically* can do this task. The result: agents that confidently attempt tasks they will fail at, agents that refuse tasks they would handle fine, and operators who can't tell from the agent's behavior which is which.

The general problem is **meta-cognitive grounding**: giving the agent an explicit, queryable model of its own capabilities, refusal classes, tool access, operational constraints, and historical performance.

#### Why Naïve Approaches Fail

- 

*"The model knows what it can do."* It doesn't, in any calibrated sense. Its self-reports are unreliable.

- 

*"List capabilities in the system prompt."* Captures intent, loses the empirical record (which tasks it actually succeeded or failed at).

- 

*"Track success metrics elsewhere."* The agent can't access them at decision time.

#### The Mechanism

A structured self-model with explicit fields. An update path triggered by post-task evaluation. A query interface used by other patterns (notably Refusal Calibrator and Skill-Library Builder). A surfaceable explanation of "what I am and am not currently configured to do."

![Pattern 051 — Agent 27 — The Memory-of-Self Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5def18437f571ad4faef_codex-pattern-051-agent-27-the-memory-of-self-agent-the-mechanism.png)

```python
# memory/self_model.py
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

@dataclass
class CapabilityRecord:
    name: str
    description: str
    declared_supported: bool         # operator-asserted
    empirical_success_rate: float    # measured
    sample_count: int
    last_evaluated: datetime
    
    @property
    def confidence(self) -> float:
        # Wilson lower bound, simplified
        if self.sample_count == 0:
            return 0.5 if self.declared_supported else 0.0
        return max(0.0, self.empirical_success_rate - 1.96 / (self.sample_count ** 0.5))

@dataclass
class SelfModel:
    agent_id: str
    agent_version: str
    capabilities: dict[str, CapabilityRecord] = field(default_factory=dict)
    refusal_classes: list[str] = field(default_factory=list)
    tool_access: list[str] = field(default_factory=list)
    operational_constraints: dict = field(default_factory=dict)
    recent_outcomes: list[dict] = field(default_factory=list)   # last 1000

class MemoryOfSelfAgent:
    def __init__(self, agent_id: str, agent_version: str):
        self.model = SelfModel(agent_id=agent_id, agent_version=agent_version)
        self._max_outcomes = 1000
    
    def declare_capability(self, name: str, description: str) -> None:
        self.model.capabilities[name] = CapabilityRecord(
            name=name, description=description,
            declared_supported=True,
            empirical_success_rate=0.5, sample_count=0,
            last_evaluated=datetime.utcnow(),
        )
    
    def record_outcome(self, capability: str, succeeded: bool,
                       task_signature: str | None = None) -> None:
        cap = self.model.capabilities.setdefault(
            capability, CapabilityRecord(
                name=capability, description="",
                declared_supported=False,
                empirical_success_rate=0.5, sample_count=0,
                last_evaluated=datetime.utcnow(),
            )
        )
        # Online update of success rate (EMA)
        alpha = 1.0 / (cap.sample_count + 1)
        cap.empirical_success_rate = (
            (1 - alpha) * cap.empirical_success_rate + alpha * (1.0 if succeeded else 0.0)
        )
        cap.sample_count += 1
        cap.last_evaluated = datetime.utcnow()
        self.model.recent_outcomes.append({
            "capability": capability, "succeeded": succeeded,
            "task_signature": task_signature, "ts": datetime.utcnow(),
        })
        if len(self.model.recent_outcomes) > self._max_outcomes:
            self.model.recent_outcomes.pop(0)
    
    def can_i(self, capability: str, *, min_confidence: float = 0.7) -> tuple[bool, str]:
        cap = self.model.capabilities.get(capability)
        if cap is None:
            return False, f"capability:{capability} not in self-model"
        if cap.confidence < min_confidence:
            return False, (
                f"capability:{capability} confidence {cap.confidence:.2f} "
                f"below threshold {min_confidence:.2f} "
                f"(empirical {cap.empirical_success_rate:.2f}, n={cap.sample_count})"
            )
        return True, f"capability:{capability} confidence {cap.confidence:.2f}"
    
    def describe(self) -> str:
        """User-facing description of what the agent can and cannot do."""
        confident = [c for c in self.model.capabilities.values() if c.confidence >= 0.7]
        uncertain = [c for c in self.model.capabilities.values() if c.confidence < 0.7]
        lines = ["I am confident I can:"]
        for c in confident:
            lines.append(f"  - {c.description} ({c.empirical_success_rate:.0%}, n={c.sample_count})")
        lines.append("I am uncertain or struggling with:")
        for c in uncertain:
            lines.append(f"  - {c.description} ({c.empirical_success_rate:.0%}, n={c.sample_count})")
        return "\n".join(lines)
```

#### Trade-offs and Alternatives

Maintaining a self-model requires the post-task evaluation infrastructure to feed it (Chapter 14). For agents without that infrastructure, the self-model degenerates to a declared capability list, which is better than nothing but doesn't give the empirical grounding the pattern is for.

For very simple agents with one or two capabilities, the self-model adds overhead without benefit. The capabilities are obvious from the toolset. The pattern earns its keep when the agent has more than a handful of distinct capability classes, when performance varies across them, or when the agent is regularly asked to do things outside its declared scope.

#### Production Failure Modes

- 

**Capability mis-classification:** The post-task evaluator labels a "success" as a "failure" or vice versa. The self-model drifts away from reality. Mitigate by sampling evaluator labels for human review and recalibrating.

- 

**Out-of-distribution overconfidence:** The agent has a 95% success rate on a capability but the incoming task differs from prior tasks. The self-model's confidence is misleading. Mitigate by classifying tasks into sub-types and tracking per-sub-type success.

- 

**Self-deprecation spiral.** A bad week of tasks pulls the self-model into pessimism. The agent starts refusing tasks it could have handled. Mitigate by bounding the influence of any single sample on the rolling success rate.

#### Case Study

A developer-tooling agent at a code-vendor maintains capability records for fifty distinct refactor classes (extract-method, inline-variable, rename-with-references, and so on) with per-class empirical success rates measured against a test suite. When asked to perform a class with confidence below 0.7, the agent declines and explains why, pointing to its own recorded performance.

The pattern reduces "agent did something wrong and we didn't catch it" reports by approximately 60%. The false-refusal rate is acceptable to operators because the agent's explanation makes the basis for declining clear.

**Pairs with:** Refusal Calibrator (Agent 54), Skill-Library Builder (Agent 48), Provenance Tracker (Agent 55).

#### Reality Check:

The self-model is downstream of an *evaluation harness* that can label tasks as succeeded or failed. Most teams don't have such a harness. The Memory-of-Self pattern is therefore aspirational unless and until the harness exists.

This book treats post-task evaluation as solved. But in practice it's the hardest infrastructure problem in deployment-time agent engineering (see Chapter 14).

The right order of construction is: evaluation harness first, then self-model populated from it. Reversing this (building the self-model machinery and hoping evaluation appears) produces a record of capabilities the agent doesn't actually have, which is worse than no self-model.

