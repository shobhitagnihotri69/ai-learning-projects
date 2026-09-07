# Agent 42 — The Human-in-the-Loop Liaison Agent

### Agent 42 — The Human-in-the-Loop Liaison Agent

*Escalates to a human and re-injects the human's input at well-defined decision points.*

#### The Problem

The pattern is named after what it is not: it's not "add a human reviewer at the end." A liaison agent is structurally aware of the decision points at which human input is required, the form that input must take to be useful, and the boundary conditions for proceeding without it.

The default human-in-the-loop integration most teams build is broken in predictable ways. The agent presents its full transcript and asks "is this OK?" The human, faced with a wall of text and no clear question, either rubber-stamps it or rejects it without specific feedback. Decisions get made on the basis of reviewer fatigue, not reviewer judgment.

The general problem is **structured human intervention**: making human input a typed, contextualized question with a defined input format and a defined re-entry point, not an "approve/reject" on an opaque session.

#### Why Naïve Approaches Fail

- 

*"Ask the human to approve the final output."* Approval becomes a formality. The human can't meaningfully review enough to add value.

- 

*"Send the full transcript and ask 'any concerns?'"* No structure. The reviewer can't tell what specifically needs attention.

- 

*"Block on every step."* Defeats the point of automation.

#### The Mechanism

Decision-point declarations attached to plan steps or tool calls rather than to whole sessions. A structured-question template that elicits the input the agent needs. A defined waiting policy (block, time-out, default-and-flag, ask-asynchronously). A re-entry path that resumes the agent from the exact state at which the human was consulted, with the human's input bound into the resumed state.

![Pattern 066 — Agent 42 — The Human-in-the-Loop Liaison Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5def3d68cad31e737fd4_codex-pattern-066-agent-42-the-human-in-the-loop-liaison-agent-the-mechanism.png)

```python
# coordination/hitl_liaison.py
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
```

#### Trade-offs and Alternatives

The liaison adds latency at every escalation point. For agents whose decisions have very low cost-of-error, escalation is overhead. For agents with high cost-of-error or regulatory review requirements, escalation is mandatory. The pattern is what makes it tolerable.

For very high-volume agents where escalation can swamp human capacity, the right pattern is *sampled escalation*: escalate only a configurable fraction of decisions, use the sampled human feedback to recalibrate the agent's confidence, and rely on the recalibration to reduce future escalation. This is closely related to the Active Learner (Agent 52).

#### Production Failure Modes

- 

**Escalation fatigue:** Volume of questions to humans exceeds their capacity, so questions are rubber-stamped or ignored. Mitigate by per-reviewer rate-limits and by tuning the agent's confidence thresholds so only genuinely uncertain decisions escalate.

- 

**State-snapshot drift:** The agent's state at the moment of question differs from the state at the moment of resumption (other actions have happened). Mitigate with immutable snapshots and explicit re-validation of preconditions on resume.

- 

**Ambiguous questions:** The human can't tell what's being asked, so their answer is unusable. Mitigate by templating questions and reviewing the templates against actual reviewer feedback.

#### Case Study

A contract-redlining agent at a corporate-legal department escalates each non-standard clause to the appropriate human lawyer as a structured question and resumes redlining on receipt of the answer, with the lawyer's input persisted to the agent's semantic memory (Agent 24) for future contracts.

The pattern allowed the team to redline approximately 4× the contract volume per lawyer per quarter, with measured downstream-issue rates equal to or lower than the all-human baseline.

**Pairs with:** Constitution-Bound (Agent 53), Episodic Buffer (Agent 23), Active Learner (Agent 52).
