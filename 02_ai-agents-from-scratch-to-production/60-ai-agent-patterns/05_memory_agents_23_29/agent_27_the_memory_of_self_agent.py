"""
Agent 27 — The Memory-of-Self Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# memory/self_model.py
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

