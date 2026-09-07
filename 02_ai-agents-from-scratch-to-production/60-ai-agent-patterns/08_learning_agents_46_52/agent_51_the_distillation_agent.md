# Agent 51 — The Distillation Agent

### Agent 51 — The Distillation Agent

*Compresses a large teacher's behavior into a smaller, faster student model.*

#### The Problem

When a frontier model produces high-quality outputs on a defined task class and a smaller model is cheap and fast, the natural move is to distill. Without an explicit distillation pipeline, the team either pays frontier-model prices indefinitely or maintains a separately-fine-tuned smaller model without the teacher's behavior captured.

The general problem is **production-time model compression**: turning expensive teacher behavior into cheap student behavior, continuously, as the production distribution evolves.

#### Why Naïve Approaches Fail

- 

*"Run the cheap model and hope."* Quality collapses on hard problems.

- 

*"Train the student once at launch."* Student becomes stale as the deployment distribution drifts.

- 

*"Manually curate distillation data."* Slow, and misses the distribution shifts that matter.

#### The Mechanism

A sampling policy that selects production cases representative of the deployment distribution. A teacher-output capture step that records both the answer and the reasoning trace. A filtering pass that excludes low-quality teacher outputs based on agreement with self-consistency or auditor checks. A training pipeline for the student model. An evaluation step that compares the student to the teacher on held-out cases.

![Pattern 075 — Agent 51 — The Distillation Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df606b2c784575c368d_codex-pattern-075-agent-51-the-distillation-agent-the-mechanism.png)

```python
# learning/distillation.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random

@dataclass
class DistillationSample:
    sample_id: str
    input: dict
    teacher_output: dict
    teacher_reasoning_trace: str
    teacher_confidence: float
    captured_at: datetime
    case_metadata: dict

@dataclass
class DistillationRun:
    run_id: str
    teacher_model: str
    student_model: str
    samples_used: int
    student_eval_score: float
    teacher_eval_score: float
    cost_reduction: float

class DistillationAgent:
    def __init__(self, teacher, student_trainer, evaluator,
                 *, sample_rate: float = 0.05, quality_floor: float = 0.95):
        self.teacher = teacher
        self.trainer = student_trainer
        self.evaluator = evaluator
        self.sample_rate = sample_rate
        self.quality_floor = quality_floor
        self.captured: list[DistillationSample] = []
    
    def capture_production_call(self, input: dict, output: dict,
                                reasoning_trace: str, confidence: float,
                                metadata: dict | None = None) -> None:
        """Sample production calls for the distillation set."""
        if random.random() > self.sample_rate:
            return
        sample = DistillationSample(
            sample_id=self._mint_id(), input=input, teacher_output=output,
            teacher_reasoning_trace=reasoning_trace, teacher_confidence=confidence,
            captured_at=datetime.utcnow(),
            case_metadata=metadata or {},
        )
        self.captured.append(sample)
    
    def filter_for_training(self, samples: list[DistillationSample]) -> list[DistillationSample]:
        """Keep only samples where the teacher seems reliable."""
        return [s for s in samples if s.teacher_confidence >= self.quality_floor]
    
    def run_distillation(self, eval_set: list[dict]) -> DistillationRun:
        # 1. Filter
        training_samples = self.filter_for_training(self.captured)
        # 2. Train the student
        student = self.trainer.train(
            base_model=self.trainer.base_model,
            training_data=[(s.input, s.teacher_output) for s in training_samples],
        )
        # 3. Evaluate
        student_score = self.evaluator.evaluate(student, eval_set)
        teacher_score = self.evaluator.evaluate(self.teacher, eval_set)
        # 4. Compute cost reduction
        teacher_cost = self.teacher.cost_per_call_cents
        student_cost = student.cost_per_call_cents
        cost_reduction = (teacher_cost - student_cost) / teacher_cost
        return DistillationRun(
            run_id=self._mint_id(),
            teacher_model=self.teacher.name, student_model=student.name,
            samples_used=len(training_samples),
            student_eval_score=student_score, teacher_eval_score=teacher_score,
            cost_reduction=cost_reduction,
        )
    
    def production_ready(self, run: DistillationRun, *, tolerance: float = 0.03) -> bool:
        """Is the student close enough to the teacher to ship?"""
        return (run.teacher_eval_score - run.student_eval_score) <= tolerance
```

#### Trade-offs and Alternatives

Distillation requires a training pipeline, a labeled evaluation set, and a continuous process. For agents whose volume is too low to justify the engineering, run the teacher and accept the cost.

For agents where the teacher's outputs are formatted in ways that don't compress well to a smaller model (long-form reasoning, complex tool use), distillation may not produce a usable student. Try on simpler task classes first, as structured outputs distill more reliably than free-form ones.

#### Production Failure Modes

- 

**Distribution drift:** The student was trained on last quarter's distribution, but the current quarter looks different. The student's quality degrades. Mitigate by continuous distillation: capture, train, and evaluate on a rolling schedule.

- 

**Teacher contamination:** A teacher mistake in the training set teaches the student to make the same mistake at scale. Mitigate with quality filters on teacher outputs (self-consistency check, auditor pass).

- 

**Eval-set staleness:** The evaluation set was assembled at launch, and it doesn't catch the modes the student fails on now. Mitigate by rolling production cases into the eval set with adversarial sampling.

#### Case Study

A content-moderation agent at a social platform initially deployed a frontier model at full cost. Six months later, the production state is a distilled student model running at one-eighth the cost with no measurable quality regression on the platform's labeled benchmark.

Distillation runs are quarterly, with sampling at 3% of production traffic and a quality floor of teacher-confidence 0.97. Roughly 60% of captured samples pass the filter into training. The savings (approximately $1.4M per year at the platform's volume) is the entirety of the distillation team's funding.

**Pairs with:** Curriculum Designer (Agent 49), Drift Detector (Agent 59), Self-Consistency Voter (Agent 15).




# study-note: verified and refactored
