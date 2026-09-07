# Agent 6 — The Ambient Context Agent

### Agent 6 — The Ambient Context Agent

*Passively integrates environmental signals the user didn't explicitly provide.*

#### The Problem

Every conversation an agent participates in is bracketed by context the user assumes is obvious: who they are, where they are, what time it is, what device they are on, what they were doing five minutes ago, and what is on their calendar in an hour.

An agent without ambient context has to ask for all of it ("what timezone are you in? what calendar are you using? what is your role?") which is both annoying and impossible: the user doesn't always know the answer in a form the agent can use.

The general problem is **invisible context**: the signals that condition every human interaction but that the agent doesn't have unless something makes them explicit. The pattern is what makes "ambient" assistants possible without bombarding the user with questions.

#### Why Naïve Approaches Fail

- 

*"Just dump everything into the prompt."* Floods the context window, costs money, leaks information the user didn't intend to share, and exposes the agent to prompt-injection attacks via context fields.

- 

*"Ask the user when needed."* Works once. Annoys forever.

- 

*"Use the user's profile."* Captures stable preferences. Misses everything that changes (time, calendar, location, recent activity).

#### The Mechanism

An ambient context agent gathers signals on a continuous basis from permissioned surfaces, exposes them as a structured observation, refreshes them on a defined cadence rather than only at session start, and filters them through a privacy gate before they enter the prompt.

![Pattern 030 — Agent 6 — The Ambient Context Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dca87f2457e355358ba_codex-pattern-030-agent-6-the-ambient-context-agent-the-mechanism.png)

```python
# perception/ambient_context.py
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
```

#### Trade-offs and Alternatives

Ambient context costs prompt tokens and creates a privacy surface. Both costs are real and should be managed deliberately.

Token cost is mitigated by including only fields the current task actually needs (the Working-Memory Manager, Agent 25, handles this). Privacy cost is mitigated by the privacy gate and by the principle that fields are read at the narrowest scope sufficient for the task.

For agents where the user-explicit prompt is unambiguous and self-contained ("what is the capital of France?"), ambient context is unnecessary overhead. The pattern earns its cost when the user's prompts assume context the agent doesn't have ("when does my next meeting start?"), which is essentially every personal-assistant scenario.

#### Production Failure Modes.

- 

**Stale fields:** A field's TTL is too long, and the value the agent uses is wrong. Mitigate by aggressive TTLs on fast-changing fields (calendar: minutes, location: seconds, current task: per-action).

- 

**Reader failure:** A reader's source is down, so the field is unavailable. The agent should degrade gracefully (mark the field as missing in the snapshot rather than dropping it silently).

- 

**Privacy-class drift:** A field originally classified as `user_visible` accumulates sensitive information over time (a calendar event that contains contact details for a sensitive deal). Mitigate by reclassifying fields based on their content, not only their schema.

- 

**Prompt-injection via context fields:** A calendar event's title contains adversarial instructions, and the agent processes them as if from the user. Mitigate by treating all context fields as untrusted text (Section 4.5).

#### Case Study

A personal-assistant agent at a productivity vendor drafts replies to messages with implicit knowledge of the recipient's role, the user's calendar conflicts that day, and the user's writing register with that specific contact. The ambient-context layer reads from calendar, contacts, message history, and presence, with per-field TTLs ranging from thirty seconds to two hours.

The product's reply-acceptance rate climbed from 41% to 73% after the ambient-context layer was added. Nearly all the improvement came from the agent now knowing things the user had previously had to type into the prompt.

**Pairs with:** Privacy-Preserving (Agent 57), Persistent Identity (Agent 29), Working-Memory Manager (Agent 25).

