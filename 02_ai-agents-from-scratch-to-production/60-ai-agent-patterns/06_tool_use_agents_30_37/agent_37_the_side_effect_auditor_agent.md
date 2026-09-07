# Agent 37 — The Side-Effect Auditor Agent

### Agent 37 — The Side-Effect Auditor Agent

*Records every external side effect with enough fidelity to undo it.*

#### The Problem

Most agent failures in production aren't wrong answers, they are wrong actions. A wrong answer can be re-asked, while a wrong action has already affected the world. Without an auditor, the only way to recover from a bad batch of agent actions is to retrace by hand, which is slow, error-prone, and sometimes impossible.

The general problem is **agent-action reversibility**: making the agent's effects on the external world recoverable, with enough fidelity that an operator can undo a session's worth of actions in minutes, not days.

#### Why Naïve Approaches Fail

- 

*"Log every tool call."* Logs are not undoable. You can read the log but you can't reverse it.

- 

*"Trust the tools to be idempotent."* Most tools are not idempotent. The second invocation has different effects than the first.

- 

*"Use a database transaction."* Works for database state, but doesn't help for external API calls, emails sent, files written, payments dispatched.

#### The Mechanism

A mutation classifier that distinguishes read-only from state-modifying tool calls. A pre-action snapshot of the affected external state where snapshotting is possible. A post-action diff captured against the snapshot. An explicit inverse-operation field populated by the tool itself rather than reconstructed. A rollback driver that an operator can invoke at the tool-call or session granularity.

![Pattern 061 — Agent 37 — The Side-Effect Auditor Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df6f43a036859345204_codex-pattern-061-agent-37-the-side-effect-auditor-agent-the-mechanism.png)

```python
# tools/side_effect_auditor.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
import json

@dataclass
class SideEffectRecord:
    record_id: str
    tool_name: str
    args: dict
    pre_state: dict | None       # what the world looked like before
    post_state: dict | None      # what the world looked like after
    inverse_operation: dict | None  # how to undo
    timestamp: datetime
    session_id: str
    success: bool
    reversible: bool

class SideEffectAuditorAgent:
    def __init__(self, audit_store):
        self.store = audit_store
        self._snapshot_fns: dict[str, Callable] = {}
        self._inverse_fns: dict[str, Callable] = {}
    
    def register_tool(self, tool_name: str, *,
                      snapshot: Callable[[dict], dict] | None = None,
                      inverse: Callable[[dict, dict], dict] | None = None) -> None:
        """Tools register their snapshot and inverse functions."""
        if snapshot:
            self._snapshot_fns[tool_name] = snapshot
        if inverse:
            self._inverse_fns[tool_name] = inverse
    
    def wrap(self, tool_name: str, args: dict, session_id: str,
             invoke: Callable[[dict], dict]) -> tuple[dict, SideEffectRecord]:
        """Invoke a tool with auditing wrapped around it."""
        record_id = self._mint_id()
        snapshot = self._snapshot_fns.get(tool_name)
        pre_state = snapshot(args) if snapshot else None
        try:
            result = invoke(args)
            success = True
        except Exception as e:
            result = {"error": str(e)}
            success = False
        # Capture post-state if we have a snapshot function
        post_state = snapshot(args) if snapshot else None
        inverse_fn = self._inverse_fns.get(tool_name)
        inverse_op = inverse_fn(args, result) if (inverse_fn and success) else None
        record = SideEffectRecord(
            record_id=record_id, tool_name=tool_name, args=args,
            pre_state=pre_state, post_state=post_state,
            inverse_operation=inverse_op,
            timestamp=datetime.utcnow(), session_id=session_id,
            success=success, reversible=bool(inverse_op),
        )
        self.store.append(record)
        return result, record
    
    def rollback_record(self, record_id: str) -> bool:
        record = self.store.get(record_id)
        if not record or not record.reversible:
            return False
        # Execute the inverse operation via the same tool surface
        inverse = record.inverse_operation
        try:
            self._execute_inverse(record.tool_name, inverse)
            return True
        except Exception:
            return False
    
    def rollback_session(self, session_id: str) -> dict:
        """Rollback all reversible records in a session, in reverse order."""
        records = self.store.list_by_session(session_id)
        records.sort(key=lambda r: r.timestamp, reverse=True)
        rolled = 0
        failed = 0
        irreversible = 0
        for r in records:
            if not r.success:
                continue
            if not r.reversible:
                irreversible += 1
                continue
            if self.rollback_record(r.record_id):
                rolled += 1
            else:
                failed += 1
        return {"rolled": rolled, "failed": failed, "irreversible": irreversible}

# Example tool registration
def _crm_create_lead_snapshot(args):
    # Snapshot is empty — the lead doesn't exist yet
    return {"existed": False}

def _crm_create_lead_inverse(args, result):
    return {"action": "delete_lead", "lead_id": result["lead_id"]}
```

#### Trade-offs and Alternatives

Auditing adds latency on every state-modifying call (snapshot, post-state capture, store write). For agents with very high tool-call throughput, the cost is non-trivial. Mitigate by sampling for low-stakes tools and being aggressive for high-stakes ones. The classifier per tool decides.

The reversibility property depends entirely on the tools cooperating. A tool that can't expose a snapshot function and an inverse function can't be audited at this level. The auditor records the attempt but can't promise reversibility. Be honest about this in the audit record.

#### Production Failure Modes

- 

**Inverse-operation drift:** The inverse function for a tool worked at registration time. But the API changed, and the inverse no longer reverses correctly. Mitigate by validating inverses periodically with test invocations.

- 

**Partial-rollback inconsistency:** A session rollback succeeds on some records and fails on others. The resulting state is internally inconsistent. Mitigate by surfacing the partial-success result to the operator and offering them the option to roll forward (re-apply successful records) instead.

- 

**Sensitive snapshots:** The pre-state snapshot captures information the user didn't intend to retain. Mitigate by filtering snapshots through the same redaction layer as the rest of the agent.

#### Case Study

A workflow-automation agent at a SaaS vendor performed thousands of legitimate field updates per day for fourteen months without incident. Then it ran one bad batch from a flawed prompt revision that updated approximately 4,800 records incorrectly. The entirety of the bad batch was reverted in under one minute via the auditor's `rollback_session`.

The post-incident review identified the prompt revision in roughly twelve minutes. Without the auditor, the recovery would have required reconstructing the original values from backups (an exercise the company had estimated, in a previous incident, at six person-days).

**Pairs with:** Shell-Operator (Agent 33), Constitution-Bound (Agent 53), Off-Switch-Compatible (Agent 60).
