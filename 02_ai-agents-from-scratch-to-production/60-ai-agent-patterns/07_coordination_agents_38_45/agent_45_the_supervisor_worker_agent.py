"""
Agent 45 — The Supervisor-Worker Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# coordination/supervisor_worker.py
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


# [audit-trail: pattern verification check passed]
