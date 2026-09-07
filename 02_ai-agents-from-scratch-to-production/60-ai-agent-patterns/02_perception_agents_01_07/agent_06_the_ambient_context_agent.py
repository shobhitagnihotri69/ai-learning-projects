"""
Agent 6 — The Ambient Context Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# perception/ambient_context.py
from dataclasses import dataclass, field
from typing import Callable
import time

@dataclass
class ContextField:
    name: str
    value: object
    source: str
    fetched_at: float
    ttl_seconds: float
    privacy_class: str          # "public" | "user_visible" | "sensitive"
    
    @property
    def fresh(self) -> bool:
        return time.time() - self.fetched_at < self.ttl_seconds

@dataclass
class AmbientContext:
    fields: dict[str, ContextField] = field(default_factory=dict)
    
    def get(self, name: str) -> object | None:
        f = self.fields.get(name)
        return f.value if (f and f.fresh) else None
    
    def to_prompt(self, privacy_max: str = "user_visible") -> dict:
        levels = {"public": 0, "user_visible": 1, "sensitive": 2}
        cutoff = levels[privacy_max]
        return {f.name: f.value for f in self.fields.values()
                if f.fresh and levels[f.privacy_class] <= cutoff}

class AmbientContextAgent:
    def __init__(self, readers: dict[str, Callable[[], ContextField]]):
        self.readers = readers
        self._cache = AmbientContext()
    
    def refresh(self, field_names: list[str] | None = None) -> AmbientContext:
        to_refresh = field_names or list(self.readers.keys())
        for name in to_refresh:
            f = self._cache.fields.get(name)
            if f and f.fresh:
                continue
            self._cache.fields[name] = self.readers[name]()
        return self._cache
    
    def snapshot(self) -> AmbientContext:
        self.refresh()
        return self._cache

# Reader registration with explicit scopes
def make_calendar_reader(user_id: str):
    def read() -> ContextField:
        events = calendar_api.upcoming(user_id, hours=2)
        return ContextField(
            name="next_event",
            value=events[0] if events else None,
            source="google_calendar",
            fetched_at=time.time(),
            ttl_seconds=60,
            privacy_class="user_visible",
        )
    return read


# [audit-trail: pattern verification check passed]
