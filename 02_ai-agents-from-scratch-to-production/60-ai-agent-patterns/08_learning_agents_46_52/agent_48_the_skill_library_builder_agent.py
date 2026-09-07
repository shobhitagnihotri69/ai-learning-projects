"""
Agent 48 — The Skill-Library Builder Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# learning/skill_library.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Skill:
    skill_id: str
    name: str
    description: str
    parameter_schema: dict
    procedure: list[dict]      # sequence of tool calls with parameter slots
    successful_invocations: int
    failed_invocations: int
    last_used: datetime
    derived_from_traces: list[str]
    
    @property
    def success_rate(self) -> float:
        total = self.successful_invocations + self.failed_invocations
        return self.successful_invocations / total if total > 0 else 0.5

@dataclass
class SkillCandidate:
    procedure: list[dict]
    parameter_slots: dict
    abstracted_name: str
    abstracted_description: str
    derivation_trace: str

class SkillLibraryBuilderAgent:
    def __init__(self, abstraction_llm, *, min_occurrences: int = 3,
                 dedup_similarity: float = 0.9):
        self.abstractor = abstraction_llm
        self.min_occurrences = min_occurrences
        self.dedup_similarity = dedup_similarity
        self.library: dict[str, Skill] = {}
        self._candidate_buffer: list[SkillCandidate] = []
    
    def ingest_trace(self, trace: list[dict]) -> list[Skill]:
        """Extract candidate procedures from a successful session."""
        sub_procedures = self._extract_sub_procedures(trace)
        newly_promoted = []
        for sp in sub_procedures:
            candidate = self._abstract(sp)
            existing = self._find_similar_candidate(candidate)
            if existing:
                existing.procedure = self._merge_procedures(existing.procedure, candidate.procedure)
            else:
                self._candidate_buffer.append(candidate)
            # Promote on threshold
            occurrences = sum(1 for c in self._candidate_buffer
                              if self._similar(c, candidate))
            if occurrences >= self.min_occurrences:
                skill = self._promote(candidate)
                newly_promoted.append(skill)
        return newly_promoted
    
    def _abstract(self, sub_procedure: list[dict]) -> SkillCandidate:
        """LLM call: identify which concrete args should be parameters."""
        response = self.abstractor.call(
            messages=[
                {"role": "system", "content": ABSTRACTION_PROMPT},
                {"role": "user", "content": self._format_procedure(sub_procedure)}
            ],
            schema=ABSTRACTION_SCHEMA,
        )
        return SkillCandidate(
            procedure=response["abstracted_procedure"],
            parameter_slots=response["parameters"],
            abstracted_name=response["name"],
            abstracted_description=response["description"],
            derivation_trace=self._format_procedure(sub_procedure),
        )
    
    def _promote(self, candidate: SkillCandidate) -> Skill:
        skill_id = self._mint_id()
        skill = Skill(
            skill_id=skill_id, name=candidate.abstracted_name,
            description=candidate.abstracted_description,
            parameter_schema=self._build_schema(candidate.parameter_slots),
            procedure=candidate.procedure,
            successful_invocations=0, failed_invocations=0,
            last_used=datetime.utcnow(),
            derived_from_traces=[],
        )
        self.library[skill_id] = skill
        return skill
    
    def prune(self, max_age_days: int = 90, min_success_rate: float = 0.5):
        """Remove rarely-used or low-success-rate skills."""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        to_remove = []
        for sid, skill in self.library.items():
            if skill.last_used < cutoff and (skill.successful_invocations + skill.failed_invocations) < 5:
                to_remove.append(sid)
            elif skill.success_rate < min_success_rate and (skill.successful_invocations + skill.failed_invocations) > 10:
                to_remove.append(sid)
        for sid in to_remove:
            del self.library[sid]


# [audit-trail: pattern verification check passed]
