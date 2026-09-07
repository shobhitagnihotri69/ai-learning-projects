"""
Agent 26 — The Forgetting-Policy Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# memory/forgetting.py
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

