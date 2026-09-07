# Agent 26 — The Forgetting-Policy Agent

### Agent 26 — The Forgetting-Policy Agent

*Prunes memory by relevance decay rather than by storage limits.*

#### The Problem

Most agents forget by accident: a buffer rolled over, a TTL expired, or an index sharded. Deliberate forgetting is a different discipline: deciding what to forget based on a model of what is still useful, *before* the forgetting becomes a quality problem or a privacy liability.

The general problem is **principled memory pruning**: applying a retention policy that reflects what the agent actually needs, what the user has consented to retain, and what the legal/operational constraints permit.

#### Why Naïve Approaches Fail

- 

*"Keep everything forever."* Privacy violation. Storage cost. Quality erosion as stale information accumulates.

- 

*"Delete by age."* Drops valuable history along with stale data. Users complain about "forgotten" facts that were still useful.

- 

*"Delete by size budget."* Triggers only when storage is exhausted. The wrong things often get evicted. The policy is essentially LRU plus surprise.

#### The Mechanism

An explicit relevance-decay function per memory class. A forgetting cadence not driven by storage pressure. An audit trail recording what was forgotten and why so the decision can be reviewed. A recovery interface when something forgotten turns out to be needed.

![Pattern 050 — Agent 26 — The Forgetting-Policy Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5def9cbc125a9829d6a2_codex-pattern-050-agent-26-the-forgetting-policy-agent-the-mechanism.png)

```python
# memory/forgetting.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

@dataclass
class ForgettingPolicy:
    memory_class: str            # "episodic" | "semantic" | "skill" | "vector"
    retention_period: timedelta
    decay_fn: Callable[[float, timedelta], float]  # (importance, age) -> survival_score
    threshold: float             # survival score below this -> forget
    recovery_window: timedelta   # how long we can un-forget

class ForgettingPolicyAgent:
    def __init__(self, stores: dict[str, object], policies: dict[str, ForgettingPolicy]):
        self.stores = stores
        self.policies = policies
        self.audit_log = []      # what was forgotten when, and why
        self.tombstones = {}     # forgotten items still recoverable
    
    def run(self) -> dict:
        forgotten_counts = {}
        for class_name, policy in self.policies.items():
            store = self.stores[class_name]
            forgotten = []
            for item in list(store.iter_all()):
                age = datetime.utcnow() - item.created_at
                survival = policy.decay_fn(item.importance, age)
                if survival < policy.threshold:
                    self._forget(store, item, class_name, survival)
                    forgotten.append(item.id)
            forgotten_counts[class_name] = len(forgotten)
        self._prune_tombstones()
        return forgotten_counts
    
    def _forget(self, store, item, class_name: str, survival: float) -> None:
        # Move to tombstone (recoverable window)
        self.tombstones[item.id] = (item, datetime.utcnow(), class_name)
        store.delete(item.id)
        self.audit_log.append({
            "id": item.id, "class": class_name,
            "forgotten_at": datetime.utcnow(),
            "survival_score": survival,
        })
    
    def _prune_tombstones(self) -> None:
        now = datetime.utcnow()
        for tid in list(self.tombstones.keys()):
            _, forgotten_at, class_name = self.tombstones[tid]
            window = self.policies[class_name].recovery_window
            if now - forgotten_at > window:
                del self.tombstones[tid]
    
    def recover(self, item_id: str) -> object | None:
        """Un-forget within the recovery window."""
        if item_id not in self.tombstones:
            return None
        item, _, class_name = self.tombstones.pop(item_id)
        self.stores[class_name].insert(item)
        return item

# Example decay functions
def exponential_decay(importance: float, age: timedelta) -> float:
    half_life_days = 30 * max(importance, 0.1)
    days = age.total_seconds() / 86400
    return 0.5 ** (days / half_life_days)

def cliff_then_decay(importance: float, age: timedelta) -> float:
    if age < timedelta(days=7):
        return 1.0
    return exponential_decay(importance, age - timedelta(days=7))
```

#### Trade-offs and Alternatives

A forgetting policy adds operational overhead and creates real risk of forgetting something useful. The risk is justified when (a) the cost of accumulating stale data is high (privacy, storage, retrieval quality) and (b) the recovery window is wide enough that operator review can catch over-aggressive forgetting.

For agents under strict retention regulations (GDPR right-to-be-forgotten, HIPAA retention windows), the forgetting policy is mandatory, and the recovery window may itself be regulated to zero. For agents with no such constraints, default to longer windows and re-tune toward shorter ones as you observe what gets forgotten and never asked about again.

#### Production Failure Modes

- 

**Decay function mis-calibration:** Important items are forgotten too aggressively, and users notice. Mitigate by sampling forgotten items for operator review and recalibrating the importance-decay parameters.

- 

**Tombstone leakage:** Items "forgotten" remain in the tombstone for the recovery window. But from a privacy standpoint they're not actually forgotten. Mitigate by hard-deleting after the window and being clear with users about the meaning of "delete."

- 

**Forgetting cascades:** A forgotten episodic item invalidates a semantic fact that depended on it, which invalidates a derived skill, which invalidates a downstream decision. Mitigate by tracking memory provenance graphs and propagating invalidation explicitly.

#### Case Study

A personal-finance agent at a consumer-fintech vendor maintains a forgetting policy that discards transaction-level detail after thirty days while preserving aggregate semantic facts (monthly spend patterns, recurring vendors, savings-rate trends). The policy satisfies both retention regulations (the vendor's retention obligation is 30 days for raw transactions, indefinite for aggregates) and product usefulness (the agent's per-user storage stays under 50KB while supporting useful long-term insights).

**Pairs with:** Privacy-Preserving (Agent 57), Drift Detector (Agent 59), Episodic Buffer (Agent 23).

