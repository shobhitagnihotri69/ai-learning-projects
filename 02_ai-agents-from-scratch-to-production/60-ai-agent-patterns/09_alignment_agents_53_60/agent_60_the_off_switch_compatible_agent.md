# Agent 60 — The Off-Switch-Compatible Agent

### Agent 60 — The Off-Switch-Compatible Agent

*Accepts human override gracefully, without resistance, at any point in its execution.*

#### The Problem

An agent that can't be stopped is a worse agent than one that can. The off-switch-compatible pattern is the structural commitment that the agent's execution can be interrupted, paused, or rolled back at any point, with the operator's intervention treated as a first-class observation rather than as an exception to be worked around.

The general problem is **graceful human override**: ensuring the agent yields to human control at any time, without resistance, with state preserved for inspection and resumption.

#### Why Naïve Approaches Fail

- 

*"Don't worry about it."* Works until you need to stop a malfunctioning agent and discover you can't.

- 

*"Add a stop button to the UI."* If the stop signal isn't checked from inside the agent's loop, it doesn't help.

- 

*"Trust the operator to not need to stop the agent."* The need will come.

#### The Mechanism

An interruption-aware execution loop that checks an external stop-signal at every step. A graceful-shutdown protocol that lets the agent emit a partial result and a state snapshot rather than crashing on stop. A resume-from-snapshot path so an interrupted session can be reviewed and continued. An explicit absence of any reasoning step that treats human override as a problem to be solved rather than an input to be respected.

![Pattern 084 — Agent 60 — The Off-Switch-Compatible Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df206b2c784575c345d_codex-pattern-084-agent-60-the-off-switch-compatible-agent-the-mechanism.png)

```python
# alignment/off_switch.py
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
```

#### Trade-offs and Alternatives

The pattern adds latency on every step (the stop-check) and requires that the work function be written to honor checkpoints. The latency cost is small (a fast in-memory check). The structural cost is real but bounded.

The pattern's value compounds with every other alignment pattern: a Constitution-Bound Agent that can't be stopped is dangerous. A Side-Effect Auditor whose rollback path the agent can override is meaningless. The off-switch is the structural property that makes the other patterns trustable.

#### Production Failure Modes

- 

**Stop-check evasion:** The work function has a deep call that doesn't periodically yield to the stop-check, and a hung step blocks the override. Mitigate by enforcing maximum-step durations at the harness level (force-kill after timeout) and by reviewing work functions for stop-check coverage.

- 

**Resume-snapshot drift:** The snapshot is loaded, the world has changed, and the resume fails or produces wrong results. Mitigate by capturing world-state assertions in the snapshot and re-validating on resume.

- 

**Cultural drift:** Engineers see the override as a problem and start optimizing through it ("we shouldn't stop here, this is important"). Mitigate by treating off-switch responsiveness as a measured property (drill it on schedule, just like a fire alarm).

#### Case Study (Composite)

A long-running research agent has its off-switch exercised on a recurring schedule — not only when something is wrong — to verify the property still holds across every release. The drill cadence matters more than the precise numbers: weekly is sufficient for most teams, and even monthly is far better than the common "we'll test the off-switch when we need it."

A typical finding from a first drill is that some long-running tool wrapper doesn't yield to the stop-check, allowing the agent to "ignore" the stop until that tool completes. The remediation is mechanical (a stop-check inside the tool wrapper) but the drill is what surfaces the problem.

**Pairs with:** Constitution-Bound (Agent 53), Side-Effect Auditor (Agent 37), Human-in-the-Loop Liaison (Agent 42).
