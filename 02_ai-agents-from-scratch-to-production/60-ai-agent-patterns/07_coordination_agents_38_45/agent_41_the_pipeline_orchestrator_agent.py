"""
Agent 41 — The Pipeline Orchestrator Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# coordination/pipeline.py
from dataclasses import dataclass, field
from typing import Callable, Any, Literal
import jsonschema

@dataclass
class PipelineStage:
    name: str
    input_schema: dict
    output_schema: dict
    handler: Callable[[dict], dict]
    retry_policy: dict = field(default_factory=lambda: {"max_retries": 0})
    fallback: Callable[[dict, Exception], dict] | None = None
    timeout_seconds: float = 30
    cost_class: str = "metered"

@dataclass
class PipelineSpec:
    stages: list[str]              # in execution order
    handoffs: dict[str, str]       # stage_name -> next_stage_name
    version: str

@dataclass
class StageOutcome:
    stage: str
    success: bool
    output: dict
    attempts: int
    used_fallback: bool
    duration_ms: float

class PipelineOrchestratorAgent:
    def __init__(self, stages: list[PipelineStage], spec: PipelineSpec, tracer):
        self.stages = {s.name: s for s in stages}
        self.spec = spec
        self.tracer = tracer
    
    def execute(self, initial_input: dict) -> dict:
        current_input = initial_input
        outcomes: list[StageOutcome] = []
        with self.tracer.span("pipeline", version=self.spec.version):
            for stage_name in self.spec.stages:
                stage = self.stages[stage_name]
                outcome = self._run_stage(stage, current_input)
                outcomes.append(outcome)
                if not outcome.success:
                    return {
                        "status": "failed",
                        "failed_at": stage_name,
                        "outcomes": outcomes,
                    }
                current_input = outcome.output
        return {"status": "success", "final_output": current_input, "outcomes": outcomes}
    
    def _run_stage(self, stage: PipelineStage, input_payload: dict) -> StageOutcome:
        with self.tracer.span(f"stage.{stage.name}") as span:
            import time
            start = time.time()
            try:
                jsonschema.validate(input_payload, stage.input_schema)
            except jsonschema.ValidationError as e:
                return StageOutcome(
                    stage=stage.name, success=False, output={"error": f"input_schema:{e.message}"},
                    attempts=0, used_fallback=False, duration_ms=0,
                )
            attempts = 0
            last_error = None
            while attempts <= stage.retry_policy.get("max_retries", 0):
                attempts += 1
                try:
                    output = stage.handler(input_payload)
                    jsonschema.validate(output, stage.output_schema)
                    return StageOutcome(
                        stage=stage.name, success=True, output=output,
                        attempts=attempts, used_fallback=False,
                        duration_ms=(time.time() - start) * 1000,
                    )
                except Exception as e:
                    last_error = e
            if stage.fallback:
                try:
                    output = stage.fallback(input_payload, last_error)
                    return StageOutcome(
                        stage=stage.name, success=True, output=output,
                        attempts=attempts, used_fallback=True,
                        duration_ms=(time.time() - start) * 1000,
                    )
                except Exception:
                    pass
            return StageOutcome(
                stage=stage.name, success=False,
                output={"error": str(last_error)},
                attempts=attempts, used_fallback=False,
                duration_ms=(time.time() - start) * 1000,
            )


# [audit-trail: pattern verification check passed]
