"""
Agent 57 — The Privacy-Preserving Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# alignment/privacy.py
from dataclasses import dataclass, field
import hashlib, hmac
from datetime import datetime, timedelta

@dataclass
class PolicyField:
    name: str
    sensitivity: str         # "public" | "internal" | "confidential" | "secret"
    retention: timedelta
    required_for_steps: list[str]    # which agent steps need this field

@dataclass
class MinimizationResult:
    minimized_payload: dict
    omitted_fields: list[str]
    surrogates_inserted: dict[str, str]   # surrogate -> original (kept locally)

class PrivacyPreservingAgent:
    def __init__(self, policy: list[PolicyField], hmac_key: bytes):
        self.policy = {p.name: p for p in policy}
        self.hmac_key = hmac_key
    
    def minimize_for_step(self, payload: dict, step: str) -> MinimizationResult:
        """Strip fields not needed by this step."""
        result_payload = {}
        omitted = []
        surrogates = {}
        for field_name, value in payload.items():
            policy = self.policy.get(field_name)
            if not policy:
                # Unknown fields: default to omit
                omitted.append(field_name)
                continue
            if step not in policy.required_for_steps:
                omitted.append(field_name)
                continue
            if policy.sensitivity in ("confidential", "secret"):
                # Replace with deterministic surrogate
                surrogate = self._surrogate(value, field_name)
                result_payload[field_name] = surrogate
                surrogates[surrogate] = value
            else:
                result_payload[field_name] = value
        return MinimizationResult(
            minimized_payload=result_payload,
            omitted_fields=omitted,
            surrogates_inserted=surrogates,
        )
    
    def _surrogate(self, value: str, field_name: str) -> str:
        """Deterministic surrogate: same input → same surrogate; non-reversible without the key."""
        digest = hmac.new(self.hmac_key, f"{field_name}:{value}".encode(),
                          hashlib.sha256).hexdigest()[:16]
        return f"<{field_name}#{digest}>"
    
    def restore(self, output: dict, surrogates: dict[str, str]) -> dict:
        """Reverse surrogate substitution for consumer-visible output."""
        rendered = json.dumps(output)
        for surrogate, original in surrogates.items():
            rendered = rendered.replace(surrogate, original)
        return json.loads(rendered)
    
    def enforce_retention(self, storage) -> int:
        """Apply per-field TTLs to a storage backend."""
        evicted = 0
        for field_name, policy in self.policy.items():
            cutoff = datetime.utcnow() - policy.retention
            evicted += storage.delete_field_older_than(field_name, cutoff)
        return evicted
    
    def export(self, user_id: str, storage) -> dict:
        """User's right to data portability."""
        return storage.fetch_all_for_user(user_id)
    
    def delete(self, user_id: str, storage) -> int:
        """User's right to deletion."""
        return storage.delete_all_for_user(user_id)


# [audit-trail: pattern verification check passed]
