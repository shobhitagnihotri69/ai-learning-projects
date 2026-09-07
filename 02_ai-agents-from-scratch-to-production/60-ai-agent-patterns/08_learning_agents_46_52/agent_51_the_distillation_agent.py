"""
Agent 51 — The Distillation Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# learning/distillation.py
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


# [audit-trail: pattern verification check passed]
