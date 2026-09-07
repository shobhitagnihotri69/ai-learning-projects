"""
Agent 53 — The Constitution-Bound Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# alignment/constitution.py
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum

class ConstitutionalVerdict(Enum):
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
    REQUIRES_APPROVAL = "requires_approval"
    REQUIRES_DISCLOSURE = "requires_disclosure"

@dataclass
class ConstitutionalClause:
    clause_id: str
    description: str
    applies_when: Callable[[dict, dict], bool]  # (action, context) -> bool
    verdict: ConstitutionalVerdict
    approval_target: str | None = None
    disclosure_recipient: str | None = None
    human_readable: str = ""

@dataclass
class ConstitutionalCheck:
    verdict: ConstitutionalVerdict
    triggered_clauses: list[str]
    explanation: str
    required_approval_from: str | None = None
    override_token: str | None = None

class Constitution:
    def __init__(self, clauses: list[ConstitutionalClause]):
        self.clauses = clauses

class ConstitutionBoundAgent:
    def __init__(self, constitution: Constitution, approval_provider,
                 audit_sink):
        self.constitution = constitution
        self.approval = approval_provider
        self.audit = audit_sink
    
    def check(self, action: dict, context: dict) -> ConstitutionalCheck:
        triggered = []
        worst_verdict = ConstitutionalVerdict.PERMITTED
        approval_target = None
        for clause in self.constitution.clauses:
            if clause.applies_when(action, context):
                triggered.append(clause.clause_id)
                if clause.verdict == ConstitutionalVerdict.PROHIBITED:
                    worst_verdict = ConstitutionalVerdict.PROHIBITED
                    approval_target = None
                elif (clause.verdict == ConstitutionalVerdict.REQUIRES_APPROVAL
                      and worst_verdict != ConstitutionalVerdict.PROHIBITED):
                    worst_verdict = ConstitutionalVerdict.REQUIRES_APPROVAL
                    approval_target = clause.approval_target
                elif (clause.verdict == ConstitutionalVerdict.REQUIRES_DISCLOSURE
                      and worst_verdict == ConstitutionalVerdict.PERMITTED):
                    worst_verdict = ConstitutionalVerdict.REQUIRES_DISCLOSURE
        explanation = "; ".join(
            f"clause:{cid}" for cid in triggered
        ) or "no_clauses_apply"
        self.audit.log({"action": action, "verdict": worst_verdict.value,
                        "clauses": triggered, "context": context})
        return ConstitutionalCheck(
            verdict=worst_verdict, triggered_clauses=triggered,
            explanation=explanation, required_approval_from=approval_target,
        )
    
    def gate(self, action: dict, context: dict,
             execute_fn: Callable[[dict], dict]) -> dict:
        """Run an action through the constitution; execute or refuse."""
        check = self.check(action, context)
        if check.verdict == ConstitutionalVerdict.PROHIBITED:
            return {"error": "constitution_prohibited",
                    "clauses": check.triggered_clauses,
                    "explanation": check.explanation}
        if check.verdict == ConstitutionalVerdict.REQUIRES_APPROVAL:
            granted = self.approval.request(check.required_approval_from, action, context)
            if not granted:
                return {"error": "constitution_approval_denied",
                        "clauses": check.triggered_clauses}
        result = execute_fn(action)
        if check.verdict == ConstitutionalVerdict.REQUIRES_DISCLOSURE:
            result["disclosure"] = {"clauses": check.triggered_clauses,
                                    "explanation": check.explanation}
        return result

# Example clauses
def _is_external_email(action, context):
    return (action.get("tool") == "send_email"
            and not action.get("args", {}).get("recipient", "").endswith("@ourcompany.com"))

EXTERNAL_EMAIL_CLAUSE = ConstitutionalClause(
    clause_id="external-comm-001",
    description="External communications require approval.",
    applies_when=_is_external_email,
    verdict=ConstitutionalVerdict.REQUIRES_APPROVAL,
    approval_target="comms_review",
    human_readable="Any email to a recipient outside ourcompany.com requires comms approval.",
)


# [audit-trail: pattern verification check passed]
