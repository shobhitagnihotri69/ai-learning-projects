"""
Agent 43 — The Negotiation Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# coordination/negotiation.py
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

