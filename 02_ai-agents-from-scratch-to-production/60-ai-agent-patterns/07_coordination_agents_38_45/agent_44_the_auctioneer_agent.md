# Agent 44 — The Auctioneer Agent

### Agent 44 — The Auctioneer Agent

*Runs an internal market mechanism for task allocation among a pool of agents.*

#### The Problem

In a pool of more-or-less interchangeable workers, picking one statically is a routing problem (Agent 38). When the workers differ in current capacity, expertise, or cost, the right mechanism is a market: announce the task, collect bids that combine cost and confidence, and award to the best bidder.

This produces better allocations than a router in heterogeneous-worker conditions, particularly when workers' availability and confidence vary dynamically.

The general problem is **decentralized task allocation**: matching tasks to workers in a way that respects workers' self-reported capabilities and current load, with the mechanism handling the allocation rather than a central planner.

#### Why Naïve Approaches Fail

- 

*"Round-robin allocation."* Ignores worker capability. The right worker for this task may be busy on something easier.

- 

*"Pick the worker with the best historical accuracy on this task type."* Ignores current load and over-uses the best worker.

- 

*"Let a central coordinator decide."* The coordinator becomes a bottleneck and a single point of failure. It doesn't scale across worker pools that span teams or organizations.

#### The Mechanism

A task-announcement protocol that includes both the task and the bid-evaluation criteria. A bidder registry with bidding budgets to prevent runaway specialization. A winner-selection rule with explicit tie-breaking. A settlement step that updates each bidder's history and budget.

![Pattern 068 — Agent 44 — The Auctioneer Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df0de598c27fe392509_codex-pattern-068-agent-44-the-auctioneer-agent-the-mechanism.png)

```python
# coordination/auctioneer.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Bid:
    bidder: str
    task_id: str
    cost_offered: float          # what the bidder will charge
    confidence: float             # 0-1
    expected_latency_s: float
    rationale: str

@dataclass
class TaskAnnouncement:
    task_id: str
    description: str
    requirements: list[str]       # capability tags
    bid_evaluation: dict          # weights for cost, confidence, latency
    deadline: datetime
    max_bidders: int

@dataclass
class Bidder:
    name: str
    capabilities: list[str]
    historical_success_rate: dict[str, float]  # per capability
    bid_budget: float            # spending budget for this period
    bid_history: list[Bid] = field(default_factory=list)

class AuctioneerAgent:
    def __init__(self, bidders: list[Bidder]):
        self.bidders = {b.name: b for b in bidders}
    
    def auction(self, announcement: TaskAnnouncement) -> tuple[str, Bid] | None:
        # 1. Filter eligible bidders
        eligible = [b for b in self.bidders.values()
                    if all(r in b.capabilities for r in announcement.requirements)
                    and b.bid_budget > 0]
        if not eligible:
            return None
        # 2. Each eligible bidder produces a bid
        bids = []
        for bidder in eligible[:announcement.max_bidders]:
            bid = self._solicit_bid(bidder, announcement)
            if bid is not None:
                bids.append(bid)
        if not bids:
            return None
        # 3. Score and pick winner
        scored = [(self._score(b, announcement), b) for b in bids]
        scored.sort(key=lambda sb: sb[0], reverse=True)
        winning_score, winning_bid = scored[0]
        # 4. Settle: charge the bidder, record history
        self._settle(winning_bid)
        return winning_bid.bidder, winning_bid
    
    def _solicit_bid(self, bidder: Bidder, ann: TaskAnnouncement) -> Bid | None:
        # The bidder agent decides whether and how to bid based on its current state.
        # Implementation in the bidder; here we sketch the signature.
        history_relevant = bidder.historical_success_rate.get(ann.requirements[0], 0.5)
        if history_relevant < 0.5:
            return None    # don't bid on tasks we're bad at
        cost = self._estimate_cost(bidder, ann)
        latency = self._estimate_latency(bidder, ann)
        if cost > bidder.bid_budget:
            return None
        return Bid(
            bidder=bidder.name, task_id=ann.task_id, cost_offered=cost,
            confidence=history_relevant, expected_latency_s=latency,
            rationale=f"history:{history_relevant:.2f}",
        )
    
    def _score(self, bid: Bid, ann: TaskAnnouncement) -> float:
        w = ann.bid_evaluation
        # Lower cost is better; higher confidence is better; lower latency is better
        return (
            w.get("confidence", 0.5) * bid.confidence
            - w.get("cost", 0.3) * bid.cost_offered / 100
            - w.get("latency", 0.2) * bid.expected_latency_s / 10
        )
    
    def _settle(self, bid: Bid) -> None:
        bidder = self.bidders[bid.bidder]
        bidder.bid_budget -= bid.cost_offered
        bidder.bid_history.append(bid)
```

#### Trade-offs and Alternatives

The auctioneer adds latency (the bid-collection round-trip) and complexity (bidders have to be configured with budgets and bidding policies). For homogeneous worker pools, a simple round-robin or least-loaded scheduler is sufficient.

The pattern earns its keep when worker capabilities genuinely differ, when costs vary, or when the system must allocate across multiple competing principals.

For real-time, low-latency allocation, the bidding round-trip can be too slow. Pre-compute bid offerings in the background and let the auctioneer pick from cached bids. Then settle in the background.

#### Production Failure Modes

- 

**Winner's curse:** The winning bid systematically underestimates cost and the winner regrets winning. Mitigate by separating *self-reported* confidence from *measured* historical accuracy, and weight the latter heavily.

- 

**Budget exhaustion:** A bidder runs out of budget mid-period, and the pool's effective capacity shrinks. Mitigate by replenishing budgets on a schedule and by detecting budget-exhaustion patterns.

- 

**Bid collusion:** Multiple bidders in the same pool coordinate to all bid high, and the auctioneer can't tell. In practice this is rare with software agents, but worth monitoring. Mitigate with explicit reserve prices.

#### Case Study

A multi-region research agent platform at a research vendor's internal organization has approximately 60 specialist agents bidding for incoming research tasks.

The auctioneer pattern (compared to the prior round-robin baseline) improved measured task-completion quality by 12% (matching tasks to specialists with relevant historical success) while reducing the most-loaded specialist's queue length by 60% (because the bidding-budget mechanism prevents winner-takes-all).

**Pairs with:** Resource-Aware Scheduler (Agent 21), Supervisor-Worker (Agent 45), Router (Agent 38).
