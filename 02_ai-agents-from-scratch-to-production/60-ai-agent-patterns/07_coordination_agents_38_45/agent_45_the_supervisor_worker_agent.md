# Agent 45 — The Supervisor-Worker Agent

### Agent 45 — The Supervisor-Worker Agent

*Manages a pool of identical workers with retries, partial failure handling, and result aggregation.*

#### The Problem

When the task is "do this hundred times in parallel," the right coordination pattern is supervisor-worker. The supervisor dispatches work units to a pool of identical worker agents, monitors their progress, retries on failure, replaces stuck workers, and aggregates results.

The pattern is dull, well-understood, and absent from a surprising number of production agent systems whose elastic-scaling story therefore consists of one long sequential loop.

The general problem is **embarrassingly-parallel agent work**: making the parallelism explicit, with proper failure handling and idempotency, rather than relying on a single agent to "loop over" the work.

#### Why Naïve Approaches Fail

- 

*"Loop over the work in one agent."* No parallelism, single point of failure.

- 

*"Run N agents and hope they finish."* No retry, no progress monitoring, no aggregation.

- 

*"Use a framework's built-in 'parallel' primitive."* Often shallow, doesn't handle partial failure idiomatically.

#### The Mechanism

A work-unit schema that's independently dispatchable. A pool with explicit concurrency limits. A per-unit timeout and retry policy distinct from the pool-level policy. A partial-result aggregation strategy. An idempotency guarantee on the worker side so retries don't produce duplicate effects.

![Pattern 069 — Agent 45 — The Supervisor-Worker Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df0de598c27fe392529_codex-pattern-069-agent-45-the-supervisor-worker-agent-the-mechanism.png)

```python
# coordination/supervisor_worker.py
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Generic
import asyncio

T = TypeVar("T")
R = TypeVar("R")

@dataclass
class WorkUnit(Generic[T]):
    unit_id: str
    payload: T
    idempotency_key: str

@dataclass
class UnitResult(Generic[R]):
    unit_id: str
    success: bool
    result: R | None
    error: str | None
    attempts: int
    worker_id: str

@dataclass
class BatchResult(Generic[R]):
    total: int
    succeeded: int
    failed: int
    results: list[UnitResult[R]]

class SupervisorWorkerAgent(Generic[T, R]):
    def __init__(self, worker_fn: Callable[[WorkUnit[T]], R],
                 *, max_concurrency: int = 10, max_retries_per_unit: int = 2,
                 timeout_per_unit_s: float = 30):
        self.worker_fn = worker_fn
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries_per_unit
        self.timeout = timeout_per_unit_s
    
    async def run_batch(self, units: list[WorkUnit[T]]) -> BatchResult[R]:
        semaphore = asyncio.Semaphore(self.max_concurrency)
        results = await asyncio.gather(*[
            self._run_unit_with_concurrency(unit, semaphore) for unit in units
        ])
        succeeded = sum(1 for r in results if r.success)
        return BatchResult(
            total=len(units), succeeded=succeeded,
            failed=len(units) - succeeded, results=results,
        )
    
    async def _run_unit_with_concurrency(self, unit: WorkUnit[T],
                                         sem: asyncio.Semaphore) -> UnitResult[R]:
        async with sem:
            return await self._run_unit(unit)
    
    async def _run_unit(self, unit: WorkUnit[T]) -> UnitResult[R]:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self._invoke_worker(unit), timeout=self.timeout)
                return UnitResult(
                    unit_id=unit.unit_id, success=True, result=result,
                    error=None, attempts=attempt + 1, worker_id="pool",
                )
            except asyncio.TimeoutError:
                last_error = "timeout"
            except Exception as e:
                last_error = str(e)
        return UnitResult(
            unit_id=unit.unit_id, success=False, result=None,
            error=last_error, attempts=self.max_retries + 1, worker_id="pool",
        )
    
    async def _invoke_worker(self, unit: WorkUnit[T]) -> R:
        return await asyncio.to_thread(self.worker_fn, unit)
```

#### Trade-offs and Alternatives

The supervisor-worker pattern requires that work units be independent (no inter-unit dependencies). When dependencies exist, switch to the Pipeline Orchestrator (Agent 41) or a workflow engine. The pattern's strength is in the embarrassingly-parallel case.

For very large batches (thousands of units), the in-memory supervisor is insufficient. Instead, use a real queue (SQS, Redis Streams, a workflow engine) for durability and visibility into long-running batches.

#### Production Failure Modes

- 

**Cascading failure:** All units share a dependency (a downstream API that's rate-limited), so all units fail simultaneously. Mitigate by detecting common-failure patterns and applying backoff at the batch level, not per-unit.

- 

**Idempotency violation:** A retry produces a duplicate side effect because the worker's idempotency key wasn't honored downstream. Mitigate by enforcing idempotency at the tool/API layer (Side-Effect Auditor, Agent 37) using the unit's idempotency key.

- 

**Stuck-worker leak:** A worker hangs without timeout-triggering errors, and the unit is "in progress" forever. Mitigate by enforcing wall-time as the master constraint. Nothing escapes a wall-time kill.

#### Case Study

A document-processing agent at a tax-services firm ingests a thousand-document batch in parallel across a fifty-worker pool. The supervisor handles the dozen documents that consistently fail (typically corrupted PDFs or unusual layouts) by escalating them to a human queue rather than retrying indefinitely.

Batch completion latency dropped from 4.5 hours (sequential) to 11 minutes (parallel), with a 99.1% per-unit success rate and a structured human-escalation path for the rest.

**Pairs with:** Side-Effect Auditor (Agent 37), Pipeline Orchestrator (Agent 41), Auctioneer (Agent 44).
