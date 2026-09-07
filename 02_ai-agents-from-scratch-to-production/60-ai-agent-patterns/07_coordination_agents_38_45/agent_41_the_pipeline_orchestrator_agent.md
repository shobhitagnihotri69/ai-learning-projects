# Agent 41 — The Pipeline Orchestrator Agent

### Agent 41 — The Pipeline Orchestrator Agent

*Sequences agents into producer-consumer chains with typed handoffs.*

#### The Problem

When the task naturally decomposes into stages — perceive, then reason, then act — the right coordination pattern isn't negotiation, it's a pipeline. The orchestrator wires the stages together with typed handoffs, runs them in order, surfaces inter-stage observability, and handles partial failure modes (retry the stage, skip the stage, fall back to a degraded stage).

The general problem is **typed multi-stage agent composition**: making the order, types, and failure handling of agent stages explicit, versioned artifacts rather than implicit in framework defaults.

#### Why Naïve Approaches Fail

- 

*"Chain LLM calls via prompt-templated includes."* Loses type safety. The output of one stage might not match the input of the next.

- 

*"Have a meta-agent decide the order each time."* Wastes compute, introduces inconsistency, obscures the pipeline as an inspectable artifact.

- 

*"Use a workflow engine."* Often a fine choice. This pattern is the agent-specific version with explicit type contracts and per-stage observability.

#### The Mechanism

Stage definitions with typed input and output schemas. A topology specification separable from the stages themselves. Per-stage retry and fallback policies. Inter-stage tracing with explicit span boundaries. A back-pressure mechanism for stages that can't keep up with their predecessors.

![Pattern 065 — Agent 41 — The Pipeline Orchestrator Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5def71de2ceb65d916ea_codex-pattern-065-agent-41-the-pipeline-orchestrator-agent-the-mechanism.png)

```python
# coordination/pipeline.py
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
```

#### Trade-offs and Alternatives

Pipelines are great for linear or near-linear flows. For genuinely branching workflows, a workflow engine (Temporal, Airflow, Prefect) with agent stages as activities is a better fit. The pipeline pattern is the agent-specific equivalent for simpler topologies.

For very short pipelines (two stages), the orchestration overhead may not be justified. Inline the second stage.

The pattern earns its keep when there are three or more stages, when stages have meaningfully different cost or reliability profiles, or when the pipeline itself becomes a versioned artifact that needs evaluation.

#### Production Failure Modes

- 

**Schema-validation tightness:** Schemas reject valid inputs because the schema is over-restrictive. Mitigate by sampling rejections for human review and loosening schemas where the rejection is wrong.

- 

**Fallback masking:** A stage routinely uses its fallback because the primary handler is broken. The pipeline appears to succeed but the output quality is degraded. Mitigate by tracking fallback-usage rates and alarming when they exceed a threshold.

- 

**Pipeline version chaos:** Multiple versions of the pipeline run in production simultaneously, and traces become hard to attribute. Mitigate by including the pipeline version in every trace event and surfacing it in operational dashboards.

#### Case Study

A content-publishing workflow at a media company pipelines a research agent (using retrieval and grounding), a drafting agent (using the research output and a style-guide prompt), a fact-checking agent (which independently verifies every cited claim), and a formatting agent (which produces the CMS-ready output). Each stage's failure mode is handled (research re-runs, drafting falls back to a more conservative model, fact-checking flags rather than fails, formatting has a manual-export fallback).

The pipeline composes roughly eight production patterns in the process and produces publishable drafts inside a defined twenty-minute envelope for 87% of inputs. The remaining 13% are flagged for editorial review with the specific stage and reason exposed.

**Pairs with:** Plan-Then-Execute (Agent 19), Provenance Tracker (Agent 55), Supervisor-Worker (Agent 45).
