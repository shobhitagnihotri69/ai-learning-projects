"""
Agent 49 — The Curriculum Designer Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# learning/curriculum.py
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


# [audit-trail: pattern verification check passed]



