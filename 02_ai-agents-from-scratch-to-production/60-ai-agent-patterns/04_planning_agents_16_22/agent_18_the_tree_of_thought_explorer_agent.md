# Agent 18 — The Tree-of-Thought Explorer Agent

### Agent 18 — The Tree-of-Thought Explorer Agent

*Branches plans into a search tree, evaluates partial plans, and prunes the bad branches.*

#### The Problem

When a problem has more than one plausible path forward and the cost of going down the wrong path is high, the right approach isn't a single chain of thought but a search.

ReAct commits to one branch at each step and can't recover from bad commits. But chain-of-thought (within a single call) implicitly branches and then collapses to one answer with no audit trail of the alternatives considered.

The general problem is **branch-and-evaluate planning**: maintaining multiple plausible plans in parallel, evaluating their expected value, and pruning the unpromising ones before committing.

#### Why Naïve Approaches Fail

- 

*"Sample multiple chains and vote."* The vote happens at the end, after each chain has invested in its own answer. The branches that diverged early may both be wrong. Voting can't recover.

- 

*"Run multiple ReAct loops in parallel."* Better, but expensive. Every branch costs a full ReAct execution.

- 

*"Increase temperature so a single chain explores more."* Doesn't explore, just makes the single chain noisier.

#### The Mechanism

The tree-of-thought agent expands a branching factor of plausible next moves, evaluates each branch with a value estimator (often the same model in a different role), prunes the low-value branches, and continues expansion only on the survivors. The pattern is the bridge between language-model agents and classical search.

![Pattern 042 — Agent 18 — The Tree-of-Thought Explorer Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5deea412be96d299aa48_codex-pattern-042-agent-18-the-tree-of-thought-explorer-agent-the-mechanism.png)

```python
# planning/tree_of_thought.py
from dataclasses import dataclass, field

@dataclass
class ToTNode:
    id: str
    state: str                  # natural-language description of the partial plan
    action: str | None          # action that produced this state
    parent_id: str | None
    depth: int
    value: float                # estimator score
    children: list[str] = field(default_factory=list)
    terminal: bool = False

@dataclass
class ToTResult:
    best_path: list[ToTNode]
    nodes_expanded: int
    nodes_pruned: int

class TreeOfThoughtExplorerAgent:
    def __init__(self, expander_llm, evaluator_llm, *,
                 branching: int = 4, max_depth: int = 6,
                 keep_top_k: int = 3, max_total_nodes: int = 200):
        self.expander = expander_llm
        self.evaluator = evaluator_llm
        self.branching = branching
        self.max_depth = max_depth
        self.keep_top_k = keep_top_k
        self.max_total_nodes = max_total_nodes
    
    def search(self, goal: str) -> ToTResult:
        root = ToTNode(id="root", state=goal, action=None, parent_id=None,
                       depth=0, value=0.0)
        nodes: dict[str, ToTNode] = {"root": root}
        frontier = [root]
        pruned = 0
        while frontier and len(nodes) < self.max_total_nodes:
            level_children: list[ToTNode] = []
            for node in frontier:
                if node.depth >= self.max_depth:
                    node.terminal = True
                    continue
                # 1. Expand: generate B candidate next moves
                candidates = self._expand(node)
                for action in candidates:
                    child_state = self._apply(node.state, action)
                    child = ToTNode(
                        id=f"{node.id}.{len(node.children)}",
                        state=child_state, action=action,
                        parent_id=node.id, depth=node.depth + 1,
                        value=0.0,
                    )
                    # 2. Evaluate the partial plan
                    child.value = self._evaluate(goal, child_state)
                    nodes[child.id] = child
                    node.children.append(child.id)
                    level_children.append(child)
            # 3. Prune to top-K at this level
            level_children.sort(key=lambda n: n.value, reverse=True)
            survivors = level_children[:self.keep_top_k]
            pruned += len(level_children) - len(survivors)
            frontier = [n for n in survivors if not n.terminal]
        # 4. Reconstruct the best path
        best_leaf = max(
            (n for n in nodes.values() if n.terminal or not n.children),
            key=lambda n: n.value,
        )
        path = self._path_to(nodes, best_leaf)
        return ToTResult(best_path=path, nodes_expanded=len(nodes), nodes_pruned=pruned)
    
    def _expand(self, node: ToTNode) -> list[str]:
        response = self.expander.call(
            messages=[
                {"role": "system", "content": EXPAND_PROMPT},
                {"role": "user", "content": node.state}
            ],
            schema={"type": "object", "properties": {
                "candidates": {"type": "array", "items": {"type": "string"},
                               "maxItems": self.branching}
            }}
        )
        return response["candidates"]
    
    def _evaluate(self, goal: str, state: str) -> float:
        response = self.evaluator.call(
            messages=[
                {"role": "system", "content": EVAL_PROMPT},
                {"role": "user", "content": f"Goal: {goal}\nCurrent state: {state}"}
            ],
            schema={"type": "object", "properties": {
                "value": {"type": "number", "minimum": 0, "maximum": 1}
            }}
        )
        return response["value"]
```

#### Trade-offs and Alternatives

The branching factor times depth gives the worst-case cost. For B=4 and depth=6, that is up to 4,096 expansion calls per problem (mitigated by pruning to top-K). The pattern is expensive and earns its keep on problems where the cost of the wrong path exceeds the cost of the search by a meaningful multiplier.

For problems where the value estimator is unreliable (it can't distinguish good and bad partial plans), the pruning is noisy and the pattern degenerates to expensive random search. Validate the estimator before trusting the search.

#### Production Failure Modes

- 

**Value-estimator collapse:** The evaluator gives nearly identical scores to all branches, and the pruning has no effect. Mitigate by training or prompting the evaluator on contrastive pairs (here's a good plan, here's a bad one, tell them apart) before deploying.

- 

**Expansion redundancy:** The expander produces near-identical candidates at each node. Mitigate by requiring candidates to be categorically distinct (different action types, different parameter regions).

- 

**Search budget blow-up:** On problems where the value estimator is flat, the search expands the full tree. Mitigate by hard upper bounds on total node count.

#### Case Study

A competitive-pricing agent at a B2B services firm, given a new tender, expands a tree of bidding strategies (price points, contract terms, delivery commitments) and prunes against historical win rates and margin floors. The surviving three strategies are presented to the pricing manager with their expected outcomes.

Win rate on tenders processed through the agent rose from 14% to 22% measured over six months, with no measurable change in average margin. The agent surfaced strategies the pricing team hadn't previously considered, primarily in the trade-off between price and contract length.

**Pairs with:** Counterfactual Reasoner (Agent 9), Backward Goal-Regression (Agent 22), Self-Consistency Voter (Agent 15).
