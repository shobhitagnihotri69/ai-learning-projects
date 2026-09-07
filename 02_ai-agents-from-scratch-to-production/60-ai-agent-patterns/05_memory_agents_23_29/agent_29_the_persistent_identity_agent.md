# Agent 29 — The Persistent Identity Agent

### Agent 29 — The Persistent Identity Agent

*Preserves user and agent identity across conversations, reboots, and version upgrades.*

#### The Problem

An agent that doesn't know which user it's talking to is a chat interface, not an agent. Most production agent failures around personalization, history, and consent reduce to identity-resolution problems. The same person appears with one email address in one channel, a different one in another, a different session token in a third, and the agent treats each as a stranger and rebuilds context from scratch.

The general problem is **identity stability across surfaces**: maintaining the right notion of "who is talking" across the inconsistent surface representations actors take in different channels, and maintaining the right notion of "who am I" for the agent itself across version upgrades.

#### Why Naïve Approaches Fail

- 

*"Use the email address as the user ID."* Breaks when the user changes email, has multiple emails, or interacts via channels without email (Slack ID, phone number, anonymous chat).

- 

*"Use the session token as the user ID."* Loses identity across sessions.

- 

*"Let the model figure out who's talking from context."* The model is bad at this and is exposed to identity spoofing.

#### The Mechanism

An identity resolver that maps surface identifiers to stable internal IDs. A privacy-respecting policy for which mappings can be persisted. A version-stable serialization of the agent's own identity so its long-term memory survives upgrades. An export-and-deletion path satisfying the user's right to take their history with them or remove it.

![Pattern 053 — Agent 29 — The Persistent Identity Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df48cc36c96237adccc_codex-pattern-053-agent-29-the-persistent-identity-agent-the-mechanism.png)

```python
# memory/identity.py
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

@dataclass
class SurfaceIdentifier:
    channel: str           # "email" | "slack" | "phone" | "session" | ...
    value: str
    verified: bool         # have we confirmed the user controls this?
    first_seen: datetime
    last_seen: datetime

@dataclass
class Identity:
    internal_id: str
    canonical_name: str | None
    surface_identifiers: list[SurfaceIdentifier]
    consent_scopes: list[str]
    created_at: datetime
    
    def has_surface(self, channel: str, value: str) -> bool:
        return any(s.channel == channel and s.value == value
                   for s in self.surface_identifiers)

class PersistentIdentityAgent:
    def __init__(self, store):
        self.store = store
    
    def resolve(self, channel: str, value: str) -> Identity | None:
        """Map a surface identifier to an internal identity."""
        for identity in self.store.iter_identities():
            if identity.has_surface(channel, value):
                return identity
        return None
    
    def assert_identity(self, channel: str, value: str,
                        verified: bool = False) -> Identity:
        existing = self.resolve(channel, value)
        if existing:
            for s in existing.surface_identifiers:
                if s.channel == channel and s.value == value:
                    s.last_seen = datetime.utcnow()
                    if verified:
                        s.verified = True
            self.store.update(existing)
            return existing
        # New identity
        identity = Identity(
            internal_id=self._mint_id(),
            canonical_name=None,
            surface_identifiers=[SurfaceIdentifier(
                channel=channel, value=value, verified=verified,
                first_seen=datetime.utcnow(), last_seen=datetime.utcnow(),
            )],
            consent_scopes=[],
            created_at=datetime.utcnow(),
        )
        self.store.insert(identity)
        return identity
    
    def link(self, identity_a: Identity, channel: str, value: str,
             verified: bool) -> Identity:
        """Add a surface identifier to an existing identity."""
        identity_a.surface_identifiers.append(SurfaceIdentifier(
            channel=channel, value=value, verified=verified,
            first_seen=datetime.utcnow(), last_seen=datetime.utcnow(),
        ))
        self.store.update(identity_a)
        return identity_a
    
    def merge(self, source: Identity, target: Identity) -> Identity:
        """Two identities turn out to be the same person."""
        for s in source.surface_identifiers:
            if not target.has_surface(s.channel, s.value):
                target.surface_identifiers.append(s)
        for c in source.consent_scopes:
            if c not in target.consent_scopes:
                target.consent_scopes.append(c)
        self.store.delete(source.internal_id)
        # Re-link all memories from source to target
        self._relink_memories(source.internal_id, target.internal_id)
        self.store.update(target)
        return target
    
    def export(self, identity: Identity) -> dict:
        """User's right to take their data."""
        return {
            "identity": identity,
            "episodes": self._fetch_episodes(identity.internal_id),
            "semantic_facts": self._fetch_facts(identity.internal_id),
        }
    
    def delete(self, identity: Identity) -> None:
        """User's right to deletion."""
        self._purge_memories(identity.internal_id)
        self.store.delete(identity.internal_id)
    
    def _mint_id(self) -> str:
        return "id_" + hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()[:16]
```

#### Trade-offs and Alternatives

Identity resolution requires a real store and a real policy for when surface identifiers can be linked. The privacy implications are non-trivial: linking identifiers without consent is a problem, refusing to link them at all is also a problem. The pattern requires the operator to think carefully about which links are permitted automatically and which require explicit user consent.

For agents that operate strictly within one channel and don't need cross-channel identity, the pattern is overhead, a per-channel user record suffices. The pattern earns its keep when the agent operates across channels (chat, email, voice) or when the user's identity has to survive sessions and reboots.

#### Production Failure Modes

- 

**False linking:** Two distinct users get merged because of a shared surface identifier (a shared family email). Mitigate by requiring verification before linking, and by allowing users to split a merged identity.

- 

**Failed linking.** A user's two surface identifiers aren't linked because verification didn't happen. The agent treats them as separate users. Mitigate by surfacing the un-linked-but-likely-same suggestion to the user with explicit consent.

- 

**Version upgrade memory loss:** The agent's own identity changes across versions. Old memories become unreachable. Mitigate by versioning the serialization format with explicit upward compatibility, and by running migration scripts on upgrade.

#### Case Study

A customer-success agent at an enterprise B2B vendor recognizes the same enterprise account whether contacted via email, Slack, in-product chat, or scheduled review meeting, and presents a unified history across all four. Linking is automatic for surface identifiers under the same email domain plus an organizational-membership check. Manual review is required to link surface identifiers across domains.

The pattern is responsible for the agent's measured 38-point improvement in customer-reported "feels like the same agent I talked to last time" satisfaction scores.

**Pairs with:** Ambient Context (Agent 6), Privacy-Preserving (Agent 57), Episodic Buffer (Agent 23).
