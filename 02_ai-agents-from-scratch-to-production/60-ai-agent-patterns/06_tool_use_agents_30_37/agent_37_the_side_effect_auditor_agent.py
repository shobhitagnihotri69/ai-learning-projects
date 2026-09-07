"""
Agent 37 — The Side-Effect Auditor Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# tools/side_effect_auditor.py
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


# [audit-trail: pattern verification check passed]
