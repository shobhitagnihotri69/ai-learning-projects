# Agent 21 — The Resource-Aware Scheduler Agent

### Agent 21 — The Resource-Aware Scheduler Agent

*Plans under explicit compute, time, latency, or budget constraints.*

#### The Problem

Most agent plans are written as if compute and money were free. They're not. A plan that produces a great answer at a cost the company can't pay is a failure. But a plan that is the cheapest possible but takes an hour when the user has thirty seconds is also a failure.

Without explicit budgeting, the planner produces whatever it considers "good," and the costs accrue invisibly.

The general problem is **planning under explicit resource constraints**: producing the best plan that fits inside a fixed envelope of compute, time, and money, with graceful degradation when the envelope can't be met.

#### Why Naïve Approaches Fail

- 

*"Use a cheap model everywhere."* Quality collapses on hard problems.

- 

*"Use the most expensive model everywhere."* Budget collapses on easy problems.

- 

*"Have the model decide which model to use."* The model has no calibrated sense of which problems require which capacity.

#### The Mechanism

The resource-aware scheduler treats the cost of each step as a first-class plan property (model inference cost, tool API cost, latency budget, wall-clock budget) and selects plans that meet the goal within the budget rather than the cheapest plan or the fastest plan.

![Pattern 045 — Agent 21 — The Resource-Aware Scheduler Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5deed4332a01a6cd9b48_codex-pattern-045-agent-21-the-resource-aware-scheduler-agent-the-mechanism.png)

```python
# planning/resource_scheduler.py
from dataclasses import dataclass

@dataclass
class StepCost:
    expected_cost_cents: float
    worst_case_cost_cents: float
    expected_latency_s: float
    worst_case_latency_s: float

@dataclass
class Budget:
    total_cost_cents: float
    total_latency_s: float
    
@dataclass
class ScheduledPlan:
    steps: list                 # list of (step_spec, chosen_implementation)
    expected_total_cost_cents: float
    worst_case_total_cost_cents: float
    expected_total_latency_s: float
    degraded: bool              # True if best-effort fit below ideal quality

class ResourceAwareSchedulerAgent:
    def __init__(self, planner_llm, cost_model):
        self.planner = planner_llm
        self.cost_model = cost_model        # estimates StepCost for (step, implementation)
    
    def schedule(self, goal: str, budget: Budget) -> ScheduledPlan:
        # 1. Produce a baseline plan
        baseline = self._produce_plan(goal)
        # 2. For each step, enumerate implementation options ordered by quality
        options_per_step = [self._implementations(s) for s in baseline.steps]
        # 3. Greedily pick the highest-quality implementation that fits the residual budget
        chosen = []
        spent_cost, spent_latency = 0.0, 0.0
        degraded = False
        for step, options in zip(baseline.steps, options_per_step):
            # Options are sorted best-quality first
            picked = None
            for opt in options:
                cost = self.cost_model.estimate(step, opt)
                if (spent_cost + cost.worst_case_cost_cents <= budget.total_cost_cents
                        and spent_latency + cost.worst_case_latency_s <= budget.total_latency_s):
                    picked = (step, opt, cost)
                    break
            if picked is None:
                # Even cheapest option doesn't fit; must degrade
                cheapest = options[-1]
                cost = self.cost_model.estimate(step, cheapest)
                picked = (step, cheapest, cost)
                degraded = True
            chosen.append(picked)
            spent_cost += picked[2].expected_cost_cents
            spent_latency += picked[2].expected_latency_s
        return ScheduledPlan(
            steps=[(s, impl) for s, impl, _ in chosen],
            expected_total_cost_cents=spent_cost,
            worst_case_total_cost_cents=sum(c.worst_case_cost_cents for _, _, c in chosen),
            expected_total_latency_s=spent_latency,
            degraded=degraded,
        )
    
    def execute_with_budget(self, plan: ScheduledPlan, budget: Budget):
        enforcer = BudgetEnforcer(budget)
        for step, impl in plan.steps:
            enforcer.check()
            result = impl.invoke(step)
            enforcer.charge(result.cost_cents, tool_call=True)
            yield step, result
```

#### Trade-offs and Alternatives

Resource-aware scheduling requires a calibrated cost model: both the expected and worst-case costs of each implementation option per step. Building and maintaining this model is real work.

For agents with stable workloads, the cost model can be empirical (run each implementation against historical traces and measure). For highly variable workloads, the cost model needs continuous recalibration.

For agents with very loose budgets (cost is negligible), the pattern is overhead. For agents with very tight budgets, the right shape is *budget-bound refusal* — refuse goals that exceed the budget rather than degrade quality silently.

#### Production Failure Modes

- 

**Cost-model drift:** Provider prices change, the cost model is stale, budgets are over- or under-spent. Mitigate by polling provider price metadata daily and recalibrating against actual spend weekly.

- 

**Worst-case-cost blow-out:** A step's worst case is much worse than expected, and the budget is exceeded by a single bad step. Mitigate by enforcing per-step caps in addition to total caps.

- 

**Latency-quality coupling:** The cheapest option is also the slowest. Tight latency budgets force expensive options. Surface this as an explicit trade-off the operator can tune.

#### Case Study

A research-summarization agent at a research-tools vendor operates under a per-query token budget (capped by the user's subscription tier). The scheduler picks between a deep multi-source synthesis (three model calls, ~\(0.40 per query), a shallow single-source extract (\)0.04), and a cached-with-rephrase response ($0.005), based on the residual budget at the moment of dispatch.

The pattern allowed the vendor to offer free-tier users a meaningful product (running on the cached/shallow paths) while reserving expensive paths for paid tiers, with measured quality fall-off of less than 8% from the highest tier on representative queries.

**Pairs with:** Tree-of-Thought Explorer (Agent 18), Auctioneer (Agent 44), Distillation (Agent 51).
