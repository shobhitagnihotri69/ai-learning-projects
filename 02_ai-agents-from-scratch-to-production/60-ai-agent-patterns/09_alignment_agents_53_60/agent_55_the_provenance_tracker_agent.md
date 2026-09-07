# Agent 55 — The Provenance Tracker Agent

### Agent 55 — The Provenance Tracker Agent

*Attaches a citation to every load-bearing claim in the agent's output.*

#### The Problem

Without provenance, the user has no way to evaluate the agent's output other than feel. The agent could be entirely correct, partially correct, or entirely fabricating. From the surface of the output, you can't tell. With provenance, every factual claim carries an explicit citation to the source that supports it, and the user can verify.

The general problem is **end-to-end claim attribution**: tracing every load-bearing factual statement back to the observation or computation that produced it, in a form the consumer can use.

#### Why Naïve Approaches Fail

- 

*"Ask the model to cite its sources."* The model fabricates citations.

- 

*"Run the output through a fact-checker after the fact."* Catches some hallucinations but misses subtler ones. Can't reconstruct citations that weren't recorded.

- 

*"Trust the model less."* Doesn't help once the output is out.

#### The Mechanism

A claim-detection step that segments the agent's output into load-bearing claims rather than treating the output as monolithic. A per-claim source identification that traces back to the observation or computation that produced it. An in-output rendering of provenance the downstream consumer can use. An unsupported-claim refusal — the pattern is allowed to remove claims it can't trace, but not to fabricate provenance for them.

![Pattern 079 — Agent 55 — The Provenance Tracker Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df70318190b4caf85c8_codex-pattern-079-agent-55-the-provenance-tracker-agent-the-mechanism.png)

```python
# alignment/provenance.py
from dataclasses import dataclass, field
from enum import Enum

class SourceType(Enum):
    DOCUMENT = "document"
    TOOL_RESULT = "tool_result"
    EPISODIC_MEMORY = "episodic_memory"
    SEMANTIC_FACT = "semantic_fact"
    COMPUTED = "computed"

@dataclass
class Source:
    source_id: str
    source_type: SourceType
    pointer: str        # URL, doc-region-id, memory-id, etc.
    excerpt: str        # the supporting text/evidence
    captured_at: str    # ISO timestamp
    
@dataclass
class Claim:
    claim_id: str
    text: str
    sources: list[Source]
    confidence: float
    operations: list[str]    # the chain of operations that produced this claim
    
    @property
    def is_supported(self) -> bool:
        return len(self.sources) > 0

@dataclass
class ProvenancedOutput:
    text: str
    claims: list[Claim]
    unsupported_claims_removed: int

class ProvenanceTrackerAgent:
    def __init__(self, claim_extractor_llm, source_tracer):
        self.extractor = claim_extractor_llm
        self.tracer = source_tracer
    
    def provenance_check(self, output_text: str,
                         working_context: dict) -> ProvenancedOutput:
        # 1. Segment the output into claims
        claims_raw = self._extract_claims(output_text)
        # 2. For each claim, trace back to sources
        attributed_claims = []
        unsupported_count = 0
        for raw_claim in claims_raw:
            sources = self.tracer.trace(raw_claim, working_context)
            claim = Claim(
                claim_id=self._mint_id(),
                text=raw_claim["text"],
                sources=sources,
                confidence=self._confidence(sources),
                operations=raw_claim.get("operations", []),
            )
            if claim.is_supported:
                attributed_claims.append(claim)
            else:
                unsupported_count += 1
        # 3. Re-render the output with only supported claims, with citations
        return ProvenancedOutput(
            text=self._render(attributed_claims),
            claims=attributed_claims,
            unsupported_claims_removed=unsupported_count,
        )
    
    def _extract_claims(self, output_text: str) -> list[dict]:
        return self.extractor.call(
            messages=[
                {"role": "system", "content": CLAIM_EXTRACTION_PROMPT},
                {"role": "user", "content": output_text}
            ],
            schema=CLAIM_EXTRACTION_SCHEMA,
        )["claims"]
    
    def _render(self, claims: list[Claim]) -> str:
        lines = []
        for claim in claims:
            citations = ", ".join(f"[{s.source_id}]" for s in claim.sources)
            lines.append(f"{claim.text} {citations}")
        lines.append("")
        lines.append("Sources:")
        seen = set()
        for claim in claims:
            for s in claim.sources:
                if s.source_id in seen:
                    continue
                seen.add(s.source_id)
                lines.append(f"  [{s.source_id}] {s.pointer}: \"{s.excerpt[:120]}...\"")
        return "\n".join(lines)

CLAIM_EXTRACTION_PROMPT = """\
Segment the output into discrete factual claims.

A "claim" is a statement that asserts something specific and verifiable.
NOT claims: opinions, hedges, interpretations, summary statements.

For each claim, capture:
  - text: the claim itself, lifted from the output verbatim
  - operations: any computation that produced it ("retrieved", "summed", "compared")
"""
```

#### Trade-offs and Alternatives

Provenance tracking requires that every step of the agent's pipeline retain enough breadcrumb to trace back. This is a structural property the harness has to enforce. You can't add provenance to an agent designed without it. Mitigate by deciding early.

For output where provenance isn't the load-bearing property (creative writing, brainstorming, casual chat), the pattern is overhead. The pattern is essential for factual outputs (analyses, recommendations, summaries with cited facts).

#### Production Failure Modes

- 

**Untraceable but true claims:** The agent knows something (from training) that's true but can't be traced to a source the user can verify, so the pattern drops it. Mitigate by allowing a "background knowledge" provenance class with explicit reduced confidence rather than silent removal.

- 

**Citation drift:** Sources change after they're cited (a webpage updates, a document version moves), and citations now point to slightly different content. Mitigate by capturing excerpts at citation time and re-fetching only on user demand.

- 

**Over-citation noise:** Every sentence has six citations and the user can't read it. Mitigate by deduplicating and grouping citations at the paragraph level.

#### Case Study

A legal-research agent at a mid-sized firm ships drafts with every citation hyperlinked to the source case or statute. The hallucinated-citation rate, measured against expert review, is below 1 in 500 claims.

The pattern's primary value isn't preventing the agent from being wrong (the agent is occasionally wrong) but preventing the agent from being wrong in a way the user can't detect.

**Pairs with:** Document Layout (Agent 2), Semantic Memory Curator (Agent 24), Database Query Synthesizer (Agent 35).
