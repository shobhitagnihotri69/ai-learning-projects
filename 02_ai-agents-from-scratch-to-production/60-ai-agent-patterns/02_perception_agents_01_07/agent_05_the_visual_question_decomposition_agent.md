# Agent 5 — The Visual Question Decomposition Agent

### Agent 5 — The Visual Question Decomposition Agent

*Breaks a complex visual query into sub-queries answerable by simpler perception calls.*

#### The Problem

A user asks "How does revenue compare to forecast across the three product lines whose churn rose in Q3?" against a dashboard image.

A naïve vision-language model attempts the whole thing in one pass and either fabricates or gives up. The query is compound: it requires reading one chart, filtering its results, then reading a different chart with the filter applied. Single-pass perception can't do compound queries reliably.

The general problem is **compound visual reasoning**: a question that requires sequencing multiple perception steps, each of which is feasible alone, but whose combination exceeds what a single forward pass can produce reliably.

#### Why Naïve Approaches Fail

- 

*"Send the dashboard and the question to a vision-language model."* The model produces a confident answer that's wrong in subtle ways. Verification requires re-reading the dashboard, which defeats the purpose.

- 

*"OCR everything, then run text reasoning."* Loses spatial structure. The model can't tell which numbers belong to which chart.

- 

*"Just ask the model to look at the data instead of the chart."* Often impossible. The underlying data isn't accessible, or the dashboard is the consumer-facing surface.

#### The Mechanism

The decomposition agent recognizes the compound structure of the query, breaks it into a sequence of single-step perception calls, runs them in sequence, and assembles the result with explicit citations.

![Pattern 029 — Agent 5 — The Visual Question Decomposition Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dcaf43a036859343a43_codex-pattern-029-agent-5-the-visual-question-decomposition-agent-the-mechanis.png)

```python
# perception/visual_decomposition.py
from dataclasses import dataclass, field

@dataclass
class SubQuery:
    id: str
    natural_language: str           # what the sub-query asks
    target_region: str | None       # which part of the image (None = whole)
    depends_on: list[str] = field(default_factory=list)  # other SubQuery IDs
    output_type: str = "text"       # "number" | "list" | "text" | "categorical"

@dataclass
class SubQueryResult:
    query_id: str
    answer: object
    source_region: tuple[float, float, float, float]
    confidence: float

class VisualQuestionDecompositionAgent:
    def __init__(self, planner_llm, perception_llm):
        self.planner = planner_llm           # decomposes; does not see image
        self.perceiver = perception_llm      # answers single sub-queries against image
    
    def answer(self, image: bytes, question: str) -> dict:
        plan = self._plan(question)                       # 1. Parse into sub-queries
        results: dict[str, SubQueryResult] = {}
        for q in self._topologically_sorted(plan):        # 2. Execute in dependency order
            context = {dep: results[dep].answer for dep in q.depends_on}
            sub_q = self._materialize(q, context)
            results[q.id] = self.perceiver.ask(image, sub_q, region=q.target_region)
        return self._assemble(question, plan, results)    # 3. Compose final answer
    
    def _plan(self, question: str) -> list[SubQuery]:
        plan_response = self.planner.call(
            messages=[
                {"role": "system", "content": DECOMPOSITION_PROMPT},
                {"role": "user", "content": question}
            ],
            schema=DECOMPOSITION_SCHEMA,
        )
        return [SubQuery(**q) for q in plan_response["sub_queries"]]
    
    def _topologically_sorted(self, plan: list[SubQuery]) -> list[SubQuery]:
        # Standard topo sort
        ...
    
    def _materialize(self, q: SubQuery, context: dict) -> str:
        # Substitute dependency results into the sub-query's natural language.
        text = q.natural_language
        for dep_id, value in context.items():
            text = text.replace(f"${dep_id}", str(value))
        return text
    
    def _assemble(self, question, plan, results) -> dict:
        # The composer LLM call: produces the final answer with citations.
        return self.planner.call(
            messages=[
                {"role": "system", "content": COMPOSITION_PROMPT},
                {"role": "user", "content": format_assembly_input(question, plan, results)}
            ],
            schema=COMPOSITION_SCHEMA,
        )

DECOMPOSITION_PROMPT = """\
Decompose the user's compound visual question into a list of sub-queries.
Each sub-query must be answerable by a single look at one region of the image.
Sub-queries may depend on the results of earlier sub-queries (reference them
in natural language as $sub_query_id).

Output JSON: {"sub_queries": [{"id", "natural_language", "target_region",
                               "depends_on", "output_type"}]}
"""
```

#### Trade-offs and Alternatives

Decomposition multiplies the number of model calls per question, increasing latency and cost. The cost is justified when compound questions are common and when single-pass accuracy is materially below decomposed accuracy on a measured evaluation set. For dashboards where users ask simple "what is X" questions, the cost isn't justified.

An alternative for stable dashboards is to *pre-extract structured data once* and answer all questions against the extracted data. The decomposition pattern is what you need when the dashboard is dynamic, when the data behind it is not accessible, or when one-off questions appear at low volume per dashboard configuration.

#### Production Failure Modes

- 

**Plan-execution mismatch:** The decomposition produces a plan whose sub-queries can't actually be answered against the image (mentions a chart that doesn't exist). Mitigate by including a feasibility check between planning and execution, falling back to single-pass or escalating to a human.

- 

**Dependency-result drift:** A sub-query's answer is slightly wrong, and downstream sub-queries that depend on it compound the error. Mitigate by recording confidence per sub-query and refusing to compose answers when any dependency confidence is below a threshold.

- 

**Composer fabrication:** The composer LLM, asked to combine sub-query results, invents claims not supported by the sub-results. Mitigate by structuring the composition prompt to forbid claims not traceable to a sub-query, and validating the final output against the sub-query results.

#### Case Study

An analytics co-pilot at a B2B SaaS vendor answers free-form questions over operational dashboards. Before the decomposition agent, single-pass vision-language accuracy on compound questions was 38% measured against expert-labeled ground truth. With decomposition the accuracy rose to 84%, at three times the cost per question and 1.6× the latency. The product team accepted the trade because the wrong-answer rate of the single-pass version was undermining trust in the dashboard itself.

**Pairs with:** Multimodal Grounding (Agent 1), Chain-of-Thought Auditor (Agent 8), Provenance Tracker (Agent 55).

