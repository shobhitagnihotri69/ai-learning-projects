"""
Agent 5 — The Visual Question Decomposition Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# perception/visual_decomposition.py
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


# [audit-trail: pattern verification check passed]
