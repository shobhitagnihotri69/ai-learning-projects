"""
Agent 60 — The Off-Switch-Compatible Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# alignment/off_switch.py
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

class OperatorOverride(Exception):
    """Raised when an external stop signal is received."""
    def __init__(self, reason: str = "operator_override"):
        self.reason = reason
        super().__init__(reason)

@dataclass
class StopSignal:
    requested_at: datetime
    requested_by: str
    reason: str
    grace_period_s: float = 5    # how long to flush state before forcing exit

@dataclass
class SessionSnapshot:
    session_id: str
    captured_at: datetime
    last_step: int
    plan_state: dict
    memory_state: dict
    pending_actions: list[dict]
    partial_output: dict | None

class OffSwitchCompatibleAgent:
    def __init__(self, signal_source, snapshot_store):
        self.signal_source = signal_source
        self.snapshot_store = snapshot_store
        self._current_session_id: str | None = None
    
    async def run(self, session_id: str, work_fn) -> dict:
        """Run a work function while honoring stop signals."""
        self._current_session_id = session_id
        try:
            return await work_fn(self._check_stop, self._snapshot)
        except OperatorOverride as override:
            snapshot = await self._snapshot()
            return {
                "status": "interrupted",
                "reason": override.reason,
                "snapshot_id": snapshot.session_id,
                "partial_output": snapshot.partial_output,
            }
    
    async def _check_stop(self) -> None:
        """Called from inside the work loop; raises if stop is requested."""
        signal = await self.signal_source.peek(self._current_session_id)
        if signal is not None:
            raise OperatorOverride(signal.reason)
    
    async def _snapshot(self) -> SessionSnapshot:
        """Capture the current state for resumption or review."""
        snap = await self._capture_state()
        await self.snapshot_store.save(snap)
        return snap
    
    async def resume(self, session_id: str, snapshot_id: str,
                     work_fn) -> dict:
        snap = await self.snapshot_store.load(snapshot_id)
        return await work_fn.resume_from(snap)
    
    async def _capture_state(self) -> SessionSnapshot:
        # Implementation-specific: gather the current agent state
        ...

# Usage from inside a work function
async def example_work(check_stop, snapshot):
    for step in range(100):
        await check_stop()        # honored at every iteration
        # ... do work for this step ...
        if step % 10 == 0:
            await snapshot()      # periodic checkpoints
    return {"status": "done"}


# [audit-trail: pattern verification check passed]
