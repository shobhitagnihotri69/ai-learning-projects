# Agent 16 — The Hierarchical Decomposer Agent

### Agent 16 — The Hierarchical Decomposer Agent

*Breaks a goal into a recursive tree of subgoals until the leaves are directly actionable.*

#### The Problem

Complex goals aren't flat lists of actions. They're trees. "Onboard a new customer" expands into "collect KYC, provision infrastructure, schedule kickoff," each of which expands further, and the actionable leaves are tool calls.

An agent that flattens this tree into a linear plan loses the structure that makes the plan revisable. But one that refuses to flatten at all collapses into a flat ReAct loop and loses sight of the goal somewhere around step thirty.

The general problem is **long-horizon coherence**: maintaining the connection between the current micro-action and the original macro-goal across many intermediate steps. Hierarchical structure is the technique that makes this tractable.

#### Why Naïve Approaches Fail

- 

*"Generate a flat list of steps."* Works for goals that decompose into five to fifteen steps. Fails for anything larger, as the model produces lists that are internally inconsistent, miss prerequisites, or repeat steps under different phrasings.

- 

*"Use a single ReAct loop."* The loop loses the goal after enough iterations. The model starts optimizing for whatever it last observed rather than for the original objective.

- 

*"Plan only at the top level, leave the rest to the executor."* The executor (typically another LLM call) has no visibility into how its step relates to the larger plan. Its choices are locally optimal and globally drift-prone.

#### The Mechanism

The decomposer expands the tree top-down, with each non-leaf node tagged with its expected output type and success predicate. It only attempts to execute when it has reached the actionable leaves.

The tree itself is the agent's plan, the policy is its expander, and the executor walks the tree depth-first.

![Pattern 040 — Agent 16 — The Hierarchical Decomposer Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd4c3c147f0711e5b55_codex-pattern-040-agent-16-the-hierarchical-decomposer-agent-the-mechanism.png)

```python
# planning/hierarchical_decomposer.py
from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal["goal", "subgoal", "action"]

@dataclass
class PlanNode:
    id: str
    kind: NodeKind
    description: str
    expected_output_type: str       # "report" | "boolean" | "record" | "file" | ...
    success_predicate: str          # natural-language condition for completion
    children: list["PlanNode"] = field(default_factory=list)
    parent_id: str | None = None
    state: Literal["pending", "in_progress", "done", "failed"] = "pending"
    result: object | None = None
    
    @property
    def is_leaf(self) -> bool:
        return self.kind == "action"

class HierarchicalDecomposerAgent:
    def __init__(self, decomposer_llm, action_executor,
                 *, max_depth: int = 4, max_children: int = 7):
        self.decomposer = decomposer_llm
        self.executor = action_executor
        self.max_depth = max_depth
        self.max_children = max_children
    
    def run(self, goal: str) -> PlanNode:
        root = PlanNode(id="root", kind="goal", description=goal,
                        expected_output_type="result",
                        success_predicate="goal achieved")
        self._expand(root, depth=0)
        self._execute(root)
        return root
    
    def _expand(self, node: PlanNode, depth: int) -> None:
        if depth >= self.max_depth:
            # Force action at max depth; if not executable, mark failed.
            node.kind = "action"
            return
        decomposition = self.decomposer.call(
            messages=[
                {"role": "system", "content": DECOMPOSE_PROMPT},
                {"role": "user", "content": format_node(node, depth)}
            ],
            schema=DECOMPOSITION_SCHEMA,
        )
        if decomposition["actionable_directly"]:
            node.kind = "action"
            return
        for child_spec in decomposition["children"][:self.max_children]:
            child = PlanNode(
                id=f"{node.id}.{len(node.children)}",
                kind="subgoal",
                description=child_spec["description"],
                expected_output_type=child_spec["expected_output_type"],
                success_predicate=child_spec["success_predicate"],
                parent_id=node.id,
            )
            node.children.append(child)
            self._expand(child, depth + 1)
    
    def _execute(self, node: PlanNode) -> None:
        if node.is_leaf:
            node.state = "in_progress"
            try:
                node.result = self.executor.execute(
                    description=node.description,
                    expected_output_type=node.expected_output_type)
                node.state = "done" if self._satisfied(node) else "failed"
            except Exception as e:
                node.state = "failed"
                node.result = {"error": str(e)}
            return
        for child in node.children:
            self._execute(child)
            if child.state == "failed":
                # Optional: re-decompose this subgoal with the failure as context.
                self._handle_subgoal_failure(node, child)
        # Aggregate child results into the parent's result
        node.result = self._aggregate([c.result for c in node.children])
        node.state = "done" if all(c.state == "done" for c in node.children) else "failed"

DECOMPOSE_PROMPT = """\
You receive a goal node from a hierarchical plan tree.
Decide whether the node is directly actionable (a single tool call resolves it)
or whether it requires further decomposition.

If decomposable, produce 2-7 children, each with:
  - description: what this child achieves
  - expected_output_type: the data shape produced
  - success_predicate: how to know it succeeded

Children should be:
  - Independently meaningful (each can be completed and verified on its own).
  - Collectively sufficient (achieving all children achieves the parent).
  - Minimally overlapping.

Output JSON: {"actionable_directly": bool, "children": [...]}
"""
```

#### Trade-offs and Alternatives

Hierarchical decomposition adds depth-times-N LLM calls before any action happens. For short goals (under ten steps), this is overhead. The pattern earns its keep on long-horizon goals — anything that would otherwise generate a flat plan of more than fifteen steps benefits, and anything beyond thirty steps essentially requires hierarchy to remain coherent.

A simpler alternative for medium-horizon goals is *two-level decomposition*: one top-level plan with a handful of milestones, each milestone executed by a small ReAct loop. This avoids the recursive overhead of the full pattern at the cost of less revisability.

#### Production Failure Modes

- 

**Decomposition explosion:** The decomposer keeps producing seven children at every level and the tree explodes. Mitigate by capping breadth and depth (the code does both) and by penalizing decompositions whose children duplicate each other.

- 

**Leaf-action mismatch:** A leaf is reached but the action that satisfies it isn't in the executor's toolset. Mitigate by passing the available toolset into the decomposer prompt so leaves are constrained to be executable.

- 

**Aggregation failure:** Child results are aggregated incorrectly, and the parent's "done" state masks subtle child failures. Mitigate by making the aggregator a structured operation (concat lists, union sets, sum numbers) rather than an LLM call that may paraphrase.

#### Case Study

An end-to-end software-issue agent at a B2B SaaS vendor takes "the dashboard is slow" and produces a tree culminating in a profiler trace, a tracked-down N+1 query, and a draft pull request.

The tree is visible to the engineer as a navigable plan. Engineers report intervening in roughly 18% of trees (typically to redirect a sub-goal that was off the mark), with the remaining 82% completing without intervention. Median time from issue creation to draft PR dropped from 14 hours (human-only baseline) to 2.3 hours (agent + reviewer).

**Pairs with:** Plan-Then-Execute (Agent 19), Adaptive (Agent 20), Memory-of-Self (Agent 27).
