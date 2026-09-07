# Agent 48 — The Skill-Library Builder Agent

### Agent 48 — The Skill-Library Builder Agent

*Saves successful sub-procedures as reusable skills the agent can invoke directly.*

#### The Problem

The first time the agent solves a problem, it constructs the solution from primitives. The second time, it shouldn't have to. Without skill-library management, every session starts from zero — the agent rediscovers, from primitive tool calls, the procedures it has already discovered and executed many times before.

The general problem is **procedural memory accumulation**: turning successful action sequences into reusable, parameterized skills the agent can invoke as composite tools.

#### Why Naïve Approaches Fail

- 

*"Hope the model remembers."* It doesn't, across sessions.

- 

*"Hand-write common procedures."* Doesn't scale, misses procedures that emerge from agent operation.

- 

*"Log everything and hope it helps."* Logs aren't queryable as skills.

#### The Mechanism

A trace-extraction step that identifies coherent sub-procedures within longer sessions. An abstraction step that lifts concrete arguments to typed parameters. A deduplication step that catches near-duplicate skills. A usefulness ranking that prunes rarely-used skills. Exposure of the resulting skills through the tool registry so the policy treats them like any other tool.

![Pattern 072 — Agent 48 — The Skill-Library Builder Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df6e06dd9d9b178f30d_codex-pattern-072-agent-48-the-skill-library-builder-agent-the-mechanism.png)

```python
# learning/skill_library.py
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
```

#### Trade-offs and Alternatives

Skill abstraction requires an LLM call per candidate procedure. Pre-deployment, the cost is small, but on a high-traffic agent the volume can add up. Run skill extraction asynchronously, not in the request path.

For environments where successful procedures don't repeat (every problem is genuinely novel), the pattern provides no benefit. The pattern shines when the agent operates over a roughly stationary distribution of tasks.

#### Production Failure Modes

- 

**Over-abstraction:** The abstractor parameterizes too much, and the resulting skill is too general to be useful. Mitigate by validating skills against historical traces: does the skill produce the same outputs the literal traces produced?

- 

**Under-abstraction:** Parameters that should be slots are hardcoded, and the skill is too specific to reuse. Mitigate by running multiple abstraction passes with different concrete examples and merging.

- 

**Skill rot:** A skill worked when added, but the underlying tools have changed and the skill silently fails. Mitigate by including skill invocations in the evaluation harness and pruning failures.

#### Case Study

A data-engineering co-pilot at a large data-platform team accumulated a skill library of 247 typed skills covering the team's most common operations (for example, "deduplicate-by-key-and-keep-most-recent," "join-table-set-with-conflict-resolution," "publish-dashboard-to-tenant") over six months in production. Skills with success rates below 0.5 were pruned automatically. The remaining set reduced median task-completion latency by 38% on familiar tasks, and the skill names became part of the team's working vocabulary for talking about the work.

**Pairs with:** Analogical Mapping (Agent 10), Memory-of-Self (Agent 27), Feedback Loop (Agent 46).

#### Reality Check

Autonomous skill extraction from agent traces is one of the most-attempted, least-shipped patterns in the field. The hard step is *abstraction*: the difference between a useful reusable skill and a brittle copy of one specific session is subtle, and most automatic abstractors miss it.

Voyager-style research has shown the approach can work in narrow domains (Minecraft-shaped action spaces) but doesn't generalize cleanly to open-ended tool use. The most successful production-shape today is *human-in-the-loop curation*: the agent proposes candidate skills, an engineer reviews and edits, and the library grows slowly but reliably.

Pure auto-extraction at the scale implied by the catalog (hundreds of typed skills emerging unsupervised) is aspirational for most teams. So treat the pattern as a long-term investment with significant operator effort rather than as a turn-key capability.
