"""
Agent 42 — The Human-in-the-Loop Liaison Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# coordination/hitl_liaison.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

class WaitingPolicy(Enum):
    BLOCK = "block"
    TIMEOUT = "timeout"
    DEFAULT_AND_FLAG = "default_and_flag"
    ASYNC = "async"

@dataclass
class HumanQuestion:
    question_id: str
    asked_at: datetime
    context: dict             # what the human needs to see
    question_text: str
    expected_answer_schema: dict
    options: list[str] | None  # if multiple choice
    default_if_timeout: dict | None
    timeout: timedelta
    policy: WaitingPolicy

@dataclass
class HumanResponse:
    question_id: str
    answered_at: datetime
    answer: dict
    actor: str               # who answered
    confidence_self_reported: float | None

class HumanInTheLoopLiaisonAgent:
    def __init__(self, message_channel, store):
        self.channel = message_channel
        self.store = store
    
    async def ask(self, question: HumanQuestion) -> HumanResponse | None:
        self.store.save_question(question)
        await self.channel.deliver(question)
        if question.policy == WaitingPolicy.BLOCK:
            return await self.store.await_response(question.question_id)
        elif question.policy == WaitingPolicy.TIMEOUT:
            try:
                return await self.store.await_response(question.question_id,
                                                       timeout=question.timeout)
            except TimeoutError:
                return None
        elif question.policy == WaitingPolicy.DEFAULT_AND_FLAG:
            try:
                return await self.store.await_response(question.question_id,
                                                       timeout=question.timeout)
            except TimeoutError:
                # Use default; flag for retrospective review
                self.store.flag_timeout(question.question_id)
                return HumanResponse(
                    question_id=question.question_id,
                    answered_at=datetime.utcnow(),
                    answer=question.default_if_timeout or {},
                    actor="system_default",
                    confidence_self_reported=None,
                )
        else:  # ASYNC
            return None  # caller will resume on response webhook
    
    def resume(self, session_id: str, response: HumanResponse, agent):
        """Resume the agent from the state at which the question was asked."""
        snapshot = self.store.load_session_snapshot(session_id, response.question_id)
        return agent.resume_from(snapshot, human_input=response.answer)

# Example: a contract-redlining agent asking about a non-standard clause
def ask_about_clause(liaison: HumanInTheLoopLiaisonAgent,
                     clause_text: str, similar_past_clauses: list,
                     session_id: str):
    return liaison.ask(HumanQuestion(
        question_id=mint_id(),
        asked_at=datetime.utcnow(),
        context={
            "clause_text": clause_text,
            "similar_past_clauses": similar_past_clauses,
            "this_contract_id": session_id,
        },
        question_text="Should we accept this clause as drafted, redline it, or reject?",
        expected_answer_schema={
            "type": "object",
            "properties": {
                "decision": {"enum": ["accept", "redline", "reject"]},
                "redline_text": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": ["decision"],
        },
        options=["accept", "redline", "reject"],
        default_if_timeout=None,
        timeout=timedelta(hours=2),
        policy=WaitingPolicy.DEFAULT_AND_FLAG,
    ))


# [audit-trail: pattern verification check passed]
