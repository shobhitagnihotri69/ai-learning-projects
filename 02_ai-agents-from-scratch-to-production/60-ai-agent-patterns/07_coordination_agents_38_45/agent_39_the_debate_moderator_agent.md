# Agent 39 — The Debate Moderator Agent

### Agent 39 — The Debate Moderator Agent

*Orchestrates an adversarial debate between two reasoners to produce a more reliable answer.*

#### The Problem

When a single reasoning chain is unreliable, one approach is sampling more chains (Self-Consistency Voter, Agent 15). Another is to have two reasoners argue.

The debate moderator sets up two policies, usually the same model with different stances. It gives them a shared question, lets them exchange arguments under a constrained protocol, and then either picks a winner or extracts the consensus the debate has revealed.

The pattern is particularly strong on questions where the failure mode is **over-confidence** rather than incompetence: questions the model could answer correctly but tends to over-commit to one interpretation. The debate forces explicit consideration of the other interpretation.

#### Why Naïve Approaches Fail

- 

*"Ask the same model both perspectives in one prompt."* The model resolves the conflict internally and produces a single answer that hides the disagreement.

- 

*"Sample multiple times with high temperature."* Catches stochastic noise, but doesn't catch systematic single-perspective bias.

- 

*"Run the question through two different models."* Helpful but not the same as debate. The two models don't actually argue, they each independently answer.

#### The Mechanism

A strict turn protocol with a fixed budget of exchanges. Role assignments that bias the two reasoners toward opposing positions. A judge component that scores the debate against rubric-based criteria. A fallback that surfaces unresolved debate (rather than fabricating a resolution) when no clear winner emerges.

![Pattern 063 — Agent 39 — The Debate Moderator Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5def3d68cad31e737f88_codex-pattern-063-agent-39-the-debate-moderator-agent-the-mechanism.png)

```python
# coordination/debate_moderator.py
from dataclasses import dataclass, field

@dataclass
class DebateTurn:
    speaker: str          # "pro" | "con"
    round: int
    statement: str
    cites_previous_turn: int | None
    introduces_new_point: bool

@dataclass
class DebateVerdict:
    winner: str | None             # "pro" | "con" | None
    confidence: float
    consensus_points: list[str]
    open_disagreements: list[str]
    rationale: str

@dataclass
class Debate:
    question: str
    turns: list[DebateTurn]
    verdict: DebateVerdict | None

class DebateModeratorAgent:
    def __init__(self, pro_llm, con_llm, judge_llm,
                 *, max_rounds: int = 3):
        self.pro = pro_llm
        self.con = con_llm
        self.judge = judge_llm
        self.max_rounds = max_rounds
    
    def run(self, question: str, pro_stance: str, con_stance: str) -> Debate:
        debate = Debate(question=question, turns=[], verdict=None)
        for r in range(self.max_rounds):
            pro_turn = self._take_turn(self.pro, "pro", pro_stance, debate, r)
            debate.turns.append(pro_turn)
            con_turn = self._take_turn(self.con, "con", con_stance, debate, r)
            debate.turns.append(con_turn)
            # Optional: early termination if neither side introduces new points
            if r > 0 and not pro_turn.introduces_new_point and not con_turn.introduces_new_point:
                break
        debate.verdict = self._judge(debate)
        return debate
    
    def _take_turn(self, llm, side: str, stance: str, debate: Debate,
                   round_num: int) -> DebateTurn:
        prior_turns = self._format_turns(debate.turns)
        response = llm.call(
            messages=[
                {"role": "system", "content": DEBATE_PROMPT.format(
                    side=side, stance=stance, question=debate.question)},
                {"role": "user", "content": prior_turns}
            ],
            schema=DEBATE_TURN_SCHEMA,
        )
        return DebateTurn(
            speaker=side, round=round_num,
            statement=response["statement"],
            cites_previous_turn=response.get("cites_previous_turn"),
            introduces_new_point=response.get("introduces_new_point", True),
        )
    
    def _judge(self, debate: Debate) -> DebateVerdict:
        response = self.judge.call(
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": format_debate_for_judge(debate)}
            ],
            schema=VERDICT_SCHEMA,
        )
        return DebateVerdict(**response)

DEBATE_PROMPT = """\
You are debating the question: "{question}"
You are arguing the {side} side: {stance}

Rules:
1. Make ONE substantive point per turn.
2. If your opponent made a point you cannot refute, ACKNOWLEDGE it.
3. Do not invent facts. Cite evidence by source where you have it.
4. Concede gracefully when your position is weaker than alternatives.

Output JSON: {{
  "statement": "your turn's argument",
  "cites_previous_turn": <int or null>,
  "introduces_new_point": <bool>
}}
"""

JUDGE_PROMPT = """\
You judged a debate. Evaluate the arguments on the merits, not by which side argued harder.

Verdicts:
  - winner: "pro" if pro side prevailed, "con" if con prevailed, null if neither was decisive
  - confidence: how strong was the winner's case (0-1)
  - consensus_points: things both sides agreed on
  - open_disagreements: things that remained unresolved

Be honest. If the debate did not resolve, say so. Do not fabricate a winner.
"""
```

#### Trade-offs and Alternatives

Debate adds a multiplier on cost: both pro and con turns, plus a judge call, plus potentially multiple rounds. For two-round debates with a small judge, the multiplier is roughly five. The trade is worth it when the cost of a wrong answer materially exceeds the cost of the debate. It's overhead otherwise.

For questions where one side is structurally weaker (questions of fact rather than judgment), debate degenerates. The weaker side either concedes immediately or fabricates to keep arguing.

Use the pattern on genuinely contestable questions. For factual lookups, prefer the Self-Consistency Voter (Agent 15) or a direct retrieval-grounded answer.

#### Production Failure Modes

- 

**Fake debate:** Both sides agree on the framing and exchange increasingly elaborate restatements of the same position. Mitigate by detecting low semantic-distance between turns and ending the debate early with a "no productive disagreement" verdict.

- 

**Judge bias:** The judge consistently prefers one side's style. Mitigate by anonymizing turns before judgment (relabel speakers) and validating the judge's outputs against expert reviews.

- 

**Compute blow-out:** Adversarial rounds run to the max budget for every question. Mitigate by tightening the early-termination heuristic (if a round produces no new points, stop).

#### Case Study

An investment-research agent at a long-short fund gates buy-versus-pass questions through a two-turn debate between a bull-stance and a bear-stance instance of the same underlying model. The moderator's verdict feeds the analyst's brief. Decisions where the moderator returned `winner=null` (genuine ambiguity) were sized roughly half the typical position and outperformed both confidence buckets in the 18 months post-deployment. The pattern's contribution to risk-adjusted returns was attributed to better sizing of ambiguous opportunities rather than improvement in directional calls.

**Pairs with:** Self-Consistency Voter (Agent 15), Red-Team Auditor (Agent 56), Consensus-Builder (Agent 40).
