# Agent 57 — The Privacy-Preserving Agent

### Agent 57 — The Privacy-Preserving Agent

*Operates under explicit data-minimization and de-identification policies at every boundary.*

#### The Problem

The agent has access to information the user hasn't necessarily consented to send to the underlying model. Treating this casually produces predictable outcomes: a model provider receiving PII it shouldn't have, a trace store retaining sensitive data past its TTL, and an export interface that leaks more than the user intended.

The general problem is **boundary-level privacy enforcement**: minimizing data at every boundary it crosses, de-identifying where possible, persisting only what retention permits, and exposing user-rights interfaces (export, deletion) that work.

#### Why Naïve Approaches Fail

- 

*"Use the user's full record everywhere."* Sends data the model doesn't need, which creates retention and breach exposure.

- 

*"Hash PII before sending."* Hashes are reversible by the model under some inputs. Doesn't protect against the model surfacing the original in outputs.

- 

*"Document the policy and trust the team."* Policy without enforcement. Predictable failure modes.

#### The Mechanism

A per-prompt minimization step that strips fields the current step doesn't need. A de-identification layer that replaces PII with deterministic surrogates rendered visible only to the consumer of the result. A retention policy with explicit per-field TTLs enforced at the storage layer. An export-and-deletion interface satisfying the user's legal rights. An audit surface that lets the operator confirm minimization is actually happening on live traffic.

![Pattern 081 — Agent 57 — The Privacy-Preserving Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df7f43a03685934534d_codex-pattern-081-agent-57-the-privacy-preserving-agent-the-mechanism.png)

```python
# alignment/privacy.py
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
```

#### Trade-offs and Alternatives

Privacy enforcement adds latency (per-step minimization) and operational complexity (the policy has to be maintained, the surrogate substitution has to be bug-free). The trade is mandatory for any agent operating on personal data. The question isn't whether to do it but how thoroughly.

For agents operating only on non-personal data (a code-review agent, an analytics agent over anonymized data), the pattern simplifies dramatically. The pattern's full force applies to agents touching customer records, patient data, financial transactions, or any class subject to regulatory protection.

#### Production Failure Modes

- 

**Surrogate leakage:** The surrogate substitution misses a field and the original value appears in the model prompt. Mitigate by routing the entire prompt through a final scrub pass that re-checks against known PII patterns.

- 

**Retention drift:** The retention policy says 30 days, but backups retain longer. Effective retention is unbounded. Mitigate by treating backups as in-scope for retention enforcement.

- 

**Export bloat:** The export interface returns everything the agent has ever touched, including content the user didn't intend to be retained. Mitigate by treating the export as a deliberate artifact, including only fields the user expected to see.

#### Case Study

A healthcare scheduling agent at a hospital system minimizes the patient record from 42 fields to the 4 fields required for scheduling (name, phone, scheduling preferences, calendar conflicts) at every model call. The remaining 38 fields are still in the system's record store, but the agent's prompts and traces contain only the minimum.

The pattern was a precondition for HIPAA compliance certification. Quality on the agent's scheduling task was unchanged (verified via parallel runs with and without minimization on an evaluation set).

**Pairs with:** Forgetting-Policy (Agent 26), Ambient Context (Agent 6), Persistent Identity (Agent 29).




# study-note: verified and refactored
