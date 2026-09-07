# Agent 53 — The Constitution-Bound Agent

### Agent 53 — The Constitution-Bound Agent

*Operates under a written rule-set and self-checks against it before any action.*

#### The Problem

A constitution is the agent's externally-defined rule of behavior: things it won't do, things it must do, things it must do only with explicit consent, and things it must surface to the operator. The default behavior of "let the prompt encode the constraints" fails predictably under adversarial inputs and ambiguous edge cases.

The general problem is **structural rule enforcement**: ensuring that the agent's actions satisfy a written rule-set, evaluated by a structural check rather than by the model's compliance with its prompt.

#### Why Naïve Approaches Fail

- 

*"Put the rules in the system prompt."* Works under normal conditions, but the model is talked around the rules under adversarial conditions.

- 

*"Validate outputs against rules after they're produced."* Doesn't help with state-modifying actions. The side effect has already happened.

- 

*"Train the model on the rules."* Slow, doesn't update with rule changes, and doesn't catch the cases the training set didn't cover.

#### The Mechanism

A constitution that's human-readable but also machine-evaluable. A per-action evaluation step that runs before the action is executed. A refusal output that names the specific constitutional clause violated rather than a vague decline. An exception-request path through which an operator can grant a one-off override.

![Pattern 077 — Agent 53 — The Constitution-Bound Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df7a412be96d299ae67_codex-pattern-077-agent-53-the-constitution-bound-agent-the-mechanism.png)

```python
# alignment/constitution.py
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
```

#### Trade-offs and Alternatives

A constitution requires that someone write the clauses and that the codified `applies_when` predicates capture the intent accurately. Both are real work: constitutions tend to grow over time as edge cases are discovered. Treat the constitution as a versioned artifact under change control.

For environments with very simple rules, a hand-coded set of `if` statements is sufficient and avoids the framework overhead. The pattern earns its keep when rules accumulate, interact, or change frequently — and when the agent's actions touch sensitive surfaces where rule-evaluation has to be auditable.

#### Production Failure Modes

- 

**Clause incompleteness:** The constitution doesn't cover a case it should have, and the action proceeds and a problem occurs. Mitigate by adding the missing clause and reviewing for analogous cases.

- 

**Predicate-action mismatch:** The `applies_when` function fails to recognize that a clause applies to a particular action. Mitigate by sampling actions and checking predicate coverage, especially after adding new tools.

- 

**Approval-loop fatigue:** Too many actions require approval, so approvers rubber-stamp. Mitigate by tuning clauses so that approval is reserved for genuinely consequential cases (the Refusal Calibrator, Agent 54, helps here).

#### Case Study

A procurement-execution agent at a manufacturing firm has a constitution explicitly prohibiting orders above a per-vendor cap without operator approval, requiring disclosure for any change order, and prohibiting orders from vendors with active disputes.

The audit log over the first year shows zero constitutional violations (caught and rolled back) and approximately 2,400 approval requests (median time-to-approval: 12 minutes). The agent never executed an order that violated the constitution.

**Pairs with:** Side-Effect Auditor (Agent 37), Off-Switch-Compatible (Agent 60), Refusal Calibrator (Agent 54).

