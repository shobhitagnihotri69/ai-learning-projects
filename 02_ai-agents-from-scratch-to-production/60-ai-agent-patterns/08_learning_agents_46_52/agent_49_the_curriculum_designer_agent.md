# Agent 49 — The Curriculum Designer Agent

### Agent 49 — The Curriculum Designer Agent

*Sequences its own training cases for accelerated skill growth.*

#### The Problem

When the agent has a corpus of historical cases it could learn from (through feedback loops, skill extraction, or fine-tuning), the order in which it processes them matters. The curriculum designer sequences cases from easier to harder, from clearer to noisier, and from on-distribution to off-distribution. The pattern is the difference between learning that converges and learning that thrashes.

The general problem is **order-of-experience optimization**: deciding which cases to learn from next, given an estimate of the agent's current proficiency, to maximize the rate of capability gain.

#### Why Naïve Approaches Fail

- 

*"Just learn from everything in chronological order."* Hard cases early in a curriculum produce noisy signal, and the agent learns the wrong lessons.

- 

*"Sample randomly."* Equivalent to no curriculum.

- 

*"Sort by difficulty once at the start."* Wastes the second half of the curriculum (too easy now), and doesn't adapt as the agent improves.

#### The Mechanism

An explicit difficulty model for each case. An estimate of the agent's current proficiency that updates as the curriculum progresses. A scheduling policy that draws the next case from the boundary between mastered and unmastered. A checkpointing discipline so the curriculum can be rewound if the agent's proficiency regresses.

![Pattern 073 — Agent 49 — The Curriculum Designer Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df6c3c147f0711e6a52_codex-pattern-073-agent-49-the-curriculum-designer-agent-the-mechanism.png)

```python
# learning/curriculum.py
from dataclasses import dataclass, field
from datetime import datetime
import math

@dataclass
class TrainingCase:
    case_id: str
    difficulty: float           # 0-1
    case_features: dict
    expected_outcome: dict
    metadata: dict = field(default_factory=dict)

@dataclass
class ProficiencyEstimate:
    skill_class: str
    estimate: float            # 0-1
    confidence: float          # how sure are we
    sample_count: int

class CurriculumDesignerAgent:
    def __init__(self, cases: list[TrainingCase], skill_classifier,
                 *, target_difficulty_offset: float = 0.1,
                 boundary_band: float = 0.15):
        self.cases = cases
        self.classify_skill = skill_classifier
        self.target_offset = target_difficulty_offset
        self.boundary_band = boundary_band
        self.proficiency: dict[str, ProficiencyEstimate] = {}
        self._consumed: set[str] = set()
        self._results: list[dict] = []
    
    def next_case(self) -> TrainingCase | None:
        """Pick the next case from the boundary of current proficiency."""
        candidates = [c for c in self.cases if c.case_id not in self._consumed]
        if not candidates:
            return None
        # Score each candidate by how close it is to the agent's current zone of proximal development
        scored = []
        for c in candidates:
            skill = self.classify_skill(c)
            prof = self.proficiency.get(skill, ProficiencyEstimate(skill, 0.3, 0.1, 0))
            target = min(1.0, prof.estimate + self.target_offset)
            distance = abs(c.difficulty - target)
            if distance > self.boundary_band:
                continue
            # Prefer cases with lower confidence (more learning opportunity)
            score = -distance + (1 - prof.confidence) * 0.3
            scored.append((score, c))
        if not scored:
            return None
        scored.sort(key=lambda sc: sc[0], reverse=True)
        return scored[0][1]
    
    def record_outcome(self, case: TrainingCase, succeeded: bool) -> None:
        self._consumed.add(case.case_id)
        skill = self.classify_skill(case)
        prof = self.proficiency.setdefault(
            skill, ProficiencyEstimate(skill, 0.3, 0.1, 0))
        # Online proficiency update (modified EMA weighted by case difficulty)
        weight = 1.0 / (prof.sample_count + 1)
        signal = case.difficulty if succeeded else (1 - case.difficulty)
        prof.estimate = (1 - weight) * prof.estimate + weight * signal
        prof.sample_count += 1
        # Confidence grows with sample count
        prof.confidence = min(0.95, 1 - 1.0 / math.sqrt(prof.sample_count + 1))
        self._results.append({"case_id": case.case_id, "succeeded": succeeded,
                              "prof_after": prof.estimate})
    
    def checkpoint(self) -> dict:
        return {
            "consumed": list(self._consumed),
            "proficiency": {k: v.__dict__ for k, v in self.proficiency.items()},
            "results": self._results,
        }
    
    def restore(self, checkpoint: dict) -> None:
        self._consumed = set(checkpoint["consumed"])
        self.proficiency = {k: ProficiencyEstimate(**v)
                            for k, v in checkpoint["proficiency"].items()}
        self._results = checkpoint["results"]
```

#### Trade-offs and Alternatives

A curriculum designer requires per-case difficulty estimates and per-case skill classifications. Estimating these is itself work. For small case corpora the work isn't justified. The pattern earns its keep on corpora of thousands of cases or more.

For situations where you have explicit human-labeled difficulties (an educational corpus, a test suite with calibrated hardness), use those rather than learning a difficulty estimator from scratch.

#### Production Failure Modes

- 

**Difficulty-estimator bias:** The estimator confuses surface features with difficulty, and the curriculum thinks something is easy that isn't. Mitigate by calibrating the estimator against held-out outcomes and recalibrating regularly.

- 

**Proficiency overestimation:** The proficiency estimate climbs too fast, and the curriculum jumps to cases the agent can't yet handle. Learning thrashes. Mitigate with a Bayesian floor on proficiency (Wilson lower bound) so the estimate respects sample uncertainty.

- 

**Curriculum exhaustion:** The agent has mastered everything in the corpus. New cases are needed but none exist. Surface the exhaustion explicitly and request new cases from the human curator.

#### Case Study

A fine-tuning pipeline at a domain-specialist vendor produced a task-accuracy improvement equivalent to the random-order baseline with roughly 40% of the training data, via curriculum-designed case ordering. The savings on training-data acquisition (which was expert-labeled and expensive) was material — roughly $180,000 per training cycle, with three cycles per year.

**Pairs with:** Active Learner (Agent 52), Distillation (Agent 51), Memory-of-Self (Agent 27).

