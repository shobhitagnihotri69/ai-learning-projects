# Agent 43 — The Negotiation Agent

### Agent 43 — The Negotiation Agent

*Bargains across agent boundaries with explicit utility functions.*

#### The Problem

When two agents have to agree on something (like a price, a schedule, or a resource allocation), and the agents represent different principals, the right coordination pattern is negotiation. Each agent holds an explicit utility function, exchanges proposals under a protocol, and updates its position based on the counterparty's signaling.

Without an explicit pattern, "agent-to-agent negotiation" degenerates into the two LLMs paraphrasing each other politely without reaching a decision.

The general problem is **inter-principal bargaining**: producing outcomes that are acceptable to each principal's interests, by agents that genuinely represent those interests rather than imitating a generic helpful tone.

#### Why Naïve Approaches Fail

- 

*"Tell the two agents to negotiate."* Without explicit utility functions and protocol, they converge to neutral, balanced statements that decide nothing.

- 

*"Have one super-agent decide for both."* Loses the principal-agent fidelity. Whichever principal trusts the super-agent more wins.

- 

*"Skip the negotiation, run an auction."* The auctioneer pattern (Agent 44) works for many-to-one matching. But for two-to-two negotiation, it forces an artificial structure.

#### The Mechanism

An explicit utility-function representation for each negotiating agent. A protocol with bounded rounds and explicit moves (propose, accept, reject, counter, reveal). A reservation-value model that prevents the agent from accepting trivially against its own interests. A transcript that is auditable by the principal afterward.

![Pattern 067 — Agent 43 — The Negotiation Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df03d68cad31e737ff7_codex-pattern-067-agent-43-the-negotiation-agent-the-mechanism.png)

```python
# coordination/negotiation.py
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum

class Move(Enum):
    PROPOSE = "propose"
    ACCEPT = "accept"
    REJECT = "reject"
    COUNTER = "counter"
    REVEAL = "reveal"
    WALK_AWAY = "walk_away"

@dataclass
class NegotiationMove:
    actor: str
    move_type: Move
    proposal: dict | None
    rationale: str
    round: int

@dataclass
class UtilityFunction:
    weights: dict[str, float]      # attribute -> weight
    
    def evaluate(self, proposal: dict) -> float:
        total = 0.0
        for attr, weight in self.weights.items():
            if attr in proposal:
                total += weight * proposal[attr]
        return total

@dataclass
class NegotiatingAgent:
    name: str
    utility: UtilityFunction
    reservation_value: float       # minimum acceptable utility
    aspiration_value: float        # opening position utility
    strategy_llm: object

@dataclass
class Negotiation:
    participants: list[NegotiatingAgent]
    moves: list[NegotiationMove]
    outcome: dict | None
    walked_away: list[str] = field(default_factory=list)

class NegotiationOrchestrator:
    def __init__(self, max_rounds: int = 10):
        self.max_rounds = max_rounds
    
    def run(self, agents: list[NegotiatingAgent], topic: str) -> Negotiation:
        negotiation = Negotiation(participants=agents, moves=[], outcome=None)
        for round_num in range(self.max_rounds):
            for agent in agents:
                move = self._take_move(agent, negotiation, round_num)
                negotiation.moves.append(move)
                if move.move_type == Move.WALK_AWAY:
                    negotiation.walked_away.append(agent.name)
                    return negotiation
                if move.move_type == Move.ACCEPT:
                    if self._all_accepted(agents, negotiation):
                        negotiation.outcome = self._last_proposal(negotiation)
                        return negotiation
        negotiation.outcome = None  # no agreement in budget
        return negotiation
    
    def _take_move(self, agent: NegotiatingAgent, negotiation: Negotiation,
                   round_num: int) -> NegotiationMove:
        last_proposal = self._last_proposal_against(agent, negotiation)
        if last_proposal:
            utility = agent.utility.evaluate(last_proposal)
            if utility < agent.reservation_value:
                # Reject or counter; never accept below reservation
                counter = self._produce_counter(agent, last_proposal, negotiation, round_num)
                return NegotiationMove(
                    actor=agent.name, move_type=Move.COUNTER,
                    proposal=counter, rationale="below_reservation",
                    round=round_num,
                )
            elif utility >= agent.aspiration_value or self._near_deadline(round_num):
                return NegotiationMove(
                    actor=agent.name, move_type=Move.ACCEPT,
                    proposal=last_proposal, rationale="acceptable",
                    round=round_num,
                )
            else:
                counter = self._produce_counter(agent, last_proposal, negotiation, round_num)
                return NegotiationMove(
                    actor=agent.name, move_type=Move.COUNTER,
                    proposal=counter, rationale="seeking_improvement",
                    round=round_num,
                )
        # No prior proposal — open with aspiration
        opening = self._produce_opening(agent)
        return NegotiationMove(
            actor=agent.name, move_type=Move.PROPOSE,
            proposal=opening, rationale="opening",
            round=round_num,
        )
    
    def _produce_counter(self, agent, opponent_proposal, negotiation, round_num):
        # The strategy LLM produces a counter that improves on the opponent's
        # proposal from the agent's perspective. Concedes more in later rounds.
        concession_factor = round_num / self.max_rounds
        ...
```

#### Trade-offs and Alternatives

Explicit negotiation requires explicit utility functions, which someone has to write. For domains where the utility is genuinely multi-attribute and the negotiation surface is rich (contract terms, scheduling, resource sharing), the investment is worthwhile. For domains where the surface is one number (price), an auctioneer (Agent 44) is simpler and sometimes better.

For negotiations where one principal is much more sophisticated than the other, mechanism design matters more than the protocol. Be explicit about which agent represents which side and what asymmetries exist.

#### Production Failure Modes

- 

**Utility mis-elicitation:** The utility function doesn't reflect the principal's actual preferences, and the agent accepts terms the principal would reject. Mitigate by calibrating the utility function against historical principal-approved outcomes and validating sample-outcomes against principal review.

- 

**Protocol gaming:** The strategy LLM finds patterns that exploit the protocol (always making maximally-aggressive counters, expecting the counterparty to relent). Mitigate by adversarial testing of the strategy against opposing strategies.

- 

**Walk-away over-use:** The agent walks away from negotiations where a deal was available. Mitigate by tracking walk-away outcomes against post-hoc analyses of what would have been acceptable to the principal.

#### Case Study

A cross-organizational scheduling agent at a venture firm negotiates meeting times between two enterprises' assistant agents under the protocol above. The pattern produces a slot that both organizations' calendars approve without either calendar's contents leaking across the boundary.

Resolution time per meeting dropped from a median of 3.4 days (human email back-and-forth) to 17 minutes (agent-to-agent), with measured participant satisfaction (post-meeting survey) unchanged or slightly higher.

**Pairs with:** Constraint-Satisfaction (Agent 11), Auctioneer (Agent 44), Provenance Tracker (Agent 55).

