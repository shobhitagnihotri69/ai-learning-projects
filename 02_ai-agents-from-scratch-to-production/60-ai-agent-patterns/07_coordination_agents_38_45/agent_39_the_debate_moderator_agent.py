"""
Agent 39 — The Debate Moderator Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# coordination/debate_moderator.py
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

