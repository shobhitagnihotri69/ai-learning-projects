# Agent 50 — The Few-Shot Prompt Tuner Agent

### Agent 50 — The Few-Shot Prompt Tuner Agent

*Selects and orders the in-context examples that condition the model for each task.*

#### The Problem

Few-shot prompting is the easiest behavior to misuse: pick three or four examples once, hardcode them, and live with the consequences forever.

The pattern is a structural fix: for each incoming task, select examples from a pool based on similarity to the task, order them by predicted educative value, and construct the prompt dynamically.

The general problem is **per-call example selection**: making the in-context examples a dynamic property of the call, conditioned on the specific task at hand, rather than a static property of the agent.

#### Why Naïve Approaches Fail

- 

*"Hardcode three examples."* Works for the average case, but fails on cases that need different examples.

- 

*"Sample randomly from a pool."* Misses the relevance signal.

- 

*"Sort by similarity to the user's question."* Loses the *educative* signal. Sometimes the right example for teaching the model isn't the most similar one.

#### The Mechanism

A curated example pool with structured labels covering both task type and the dimension along which each example is instructive. A per-task selector that retrieves examples by structural similarity, not text similarity. An ordering rule that places the most-similar example last (or first, depending on the model's recency bias). An evaluation harness that measures the quality impact of selection against a fixed-example baseline.

![Pattern 074 — Agent 50 — The Few-Shot Prompt Tuner Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df606b2c784575c3660_codex-pattern-074-agent-50-the-few-shot-prompt-tuner-agent-the-mechanism.png)

```python
# learning/few_shot_tuner.py
from dataclasses import dataclass, field

@dataclass
class FewShotExample:
    example_id: str
    task_type: str
    instructive_dimensions: list[str]   # what this example teaches
    input: dict
    output: dict
    embedding: list[float]
    historical_inclusion_lift: float    # measured improvement when included

class FewShotPromptTunerAgent:
    def __init__(self, pool: list[FewShotExample], embedder,
                 *, examples_per_prompt: int = 3,
                 ordering: str = "similarity_last"):
        self.pool = pool
        self.embedder = embedder
        self.examples_per_prompt = examples_per_prompt
        self.ordering = ordering
    
    def select(self, task_input: dict, task_type: str) -> list[FewShotExample]:
        # 1. Filter pool by task type
        candidates = [e for e in self.pool if e.task_type == task_type]
        if not candidates:
            return []
        # 2. Score by relevance to the current task
        query_emb = self.embedder.embed(self._signature(task_input))
        scored = [(self._cosine(query_emb, e.embedding), e) for e in candidates]
        scored.sort(key=lambda se: se[0], reverse=True)
        # 3. Select with diversity: ensure different instructive_dimensions are covered
        selected = []
        covered_dimensions = set()
        for _, ex in scored:
            new_dims = set(ex.instructive_dimensions) - covered_dimensions
            if new_dims or len(selected) == 0:
                selected.append(ex)
                covered_dimensions.update(ex.instructive_dimensions)
            if len(selected) == self.examples_per_prompt:
                break
        # If still under the target, fill with top-similarity remainder
        for _, ex in scored:
            if ex in selected:
                continue
            selected.append(ex)
            if len(selected) == self.examples_per_prompt:
                break
        # 4. Order
        if self.ordering == "similarity_last":
            selected.sort(key=lambda e: self._cosine(query_emb, e.embedding))
        elif self.ordering == "similarity_first":
            selected.sort(key=lambda e: self._cosine(query_emb, e.embedding), reverse=True)
        return selected
    
    def materialize(self, examples: list[FewShotExample]) -> str:
        lines = []
        for ex in examples:
            lines.append("Example:")
            lines.append(f"  Input: {ex.input}")
            lines.append(f"  Output: {ex.output}")
            lines.append("")
        return "\n".join(lines)
    
    def record_outcome(self, examples: list[FewShotExample], succeeded: bool):
        """Update historical_inclusion_lift via EMA."""
        for ex in examples:
            signal = 1.0 if succeeded else 0.0
            ex.historical_inclusion_lift = 0.95 * ex.historical_inclusion_lift + 0.05 * signal
```

#### Trade-offs and Alternatives

Dynamic selection adds embedding-and-retrieval latency to every call. For tasks where one or two examples are sufficient and the task type is narrow, hardcoded examples are simpler and adequate.

The pattern's value scales with pool size and pool diversity. A pool of ten examples doesn't benefit much from dynamic selection. A pool of five hundred examples benefits enormously.

#### Production Failure Modes

- 

**Pool drift:** The pool is curated at launch, the production distribution shifts, and the pool's examples become unrepresentative. Mitigate by adding new examples to the pool from production feedback and pruning examples whose historical-inclusion-lift drops.

- 

**Ordering bias:** The model has a strong recency bias. Placing the most-similar example last (or first) systematically helps or hurts depending on the model. Validate ordering empirically per model.

- 

**Diversity collapse:** All selected examples come from a narrow subspace, and the model overfits to that subspace. Mitigate by enforcing instructive-dimension coverage (the code shows this).

#### Case Study

A structured-extraction agent at a healthcare-claims vendor improved its accuracy on a benchmark task by 12 percentage points purely by replacing a static three-example prompt with a dynamic-selection pool of forty examples. The selector cost per call is roughly two milliseconds, the model cost per call is unchanged, and the accuracy improvement was material enough that the vendor was able to raise the agent's confidence-threshold for auto-approval, eliminating roughly 8% of human-review work.

**Pairs with:** Analogical Mapping (Agent 10), Feedback Loop (Agent 46), Curriculum Designer (Agent 49).
