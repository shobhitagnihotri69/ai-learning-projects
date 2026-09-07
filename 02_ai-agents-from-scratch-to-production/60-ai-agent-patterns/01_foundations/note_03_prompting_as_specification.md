### Chapter 3 — Prompting as Specification

A system prompt isn't a piece of marketing copy. It's a specification document. Read in that light, most production prompts are catastrophically under-specified: they describe a persona instead of a contract, they list a few examples instead of edge cases, they assume context the model does not have, and they leave the failure path unspecified.

This chapter reframes prompt engineering as the discipline of writing specifications that a stochastic interpreter can follow.

#### 3.1 The four-layer prompt architecture

Every well-designed prompt has four layers, in the order shown:

- 

**Invariant layer:** The parts that don't change for the life of the agent. The identity, the unconditional safety rules, the structural commitments. This layer is the same for every call. With prompt-caching providers, it should be the cached prefix.

- 

**Role layer:** What kind of agent this is — the planner, the auditor, the explainer. This layer changes when the agent is reconfigured for a different role within a larger system. It's the same for every call within a given role.

- 

**Task layer:** The current task definition. The output schema, the constraints on this particular call, the success criteria. This layer changes per task type but is often the same within a task type.

- 

**Frame layer:** The dynamic content: retrieved documents, memory contents, the user's current message. This layer changes per call.

![Pattern 013 — 3.1 The four-layer prompt architecture](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca49996a5a8f7dede73_codex-pattern-013-3-1-the-four-layer-prompt-architecture.png)

```python
# An invariant layer for an internal research assistant.
INVARIANT = """\
You are an internal research assistant for an investment-management firm.
You always cite sources. You never speculate beyond evidence. When evidence
is missing, you say so and refuse rather than guess. You output structured
JSON when called with a schema; otherwise you output plain prose with
inline citations to source IDs.
"""

# A role layer for the planner role.
ROLE_PLANNER = """\
Your role is planner. You produce a plan as JSON: an ordered list of steps,
each with a typed `action`, `inputs`, `expected_output_type`, and `success_predicate`.
You do not execute steps. You do not invoke tools. You only produce plans.
"""

# A task layer for the "answer a research question" task.
TASK_RESEARCH_QUESTION = """\
The user has a research question. Produce a plan that gathers the evidence
required to answer it, with at least two independent sources per material claim.
Use the available retrieval and computation tools listed below.
Available tools: {tool_descriptions}
Output schema: {plan_schema}
"""

# A frame layer for one specific call.
FRAME = """\
Question: {user_question}
Working memory: {working_memory_snippet}
Retrieved candidate sources: {retrieved_sources}
"""
```

The split is operationally important. With prompt caching (which Anthropic, OpenAI, and Google all now support), the invariant layer is cached at the provider, and you pay the full prompt cost only on the first call. Without the split, every call is full cost. The savings on a busy agent are in the thousands of dollars per month.

#### 3.2 The under-specified prompt — a worked example

Here's a prompt of the kind you find in nearly every "build your first agent" tutorial:

![Pattern 014 — 3.2 The under-specified prompt — a worked example](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca4531a4154e4427319_codex-pattern-014-3-2-the-under-specified-prompt-a-worked-example.png)

```plaintext
You are a helpful sales-research assistant. Given a company name, find
information about the company, summarize what they do, and produce a list
of potential pain points relevant to our product.
```

It's friendly, brief, and disastrous. It fails on every dimension that matters:

- 

**No output contract:** Is the output a paragraph? A JSON object? With what fields? When the model produces different structures on different calls, the downstream system breaks unpredictably.

- 

**No source contract:** When the model fabricates a customer list, there's no rule it has violated. Citation isn't mentioned.

- 

**No refusal path:** When the company is fictional or recently bankrupt, the model has no permitted way to say "I can't find this," so it will invent.

- 

**No bounds on the pain points:** "Potential pain points relevant to our product" is a phrase that licenses unbounded speculation.

- 

**No definition of "our product":** The model is being asked to find product-relevant pain points without being told what the product is.

Here's the same prompt re-specified:

![Pattern 015 — 3.2 The under-specified prompt — a worked example](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca492b55ea93e9385a6_codex-pattern-015-3-2-the-under-specified-prompt-a-worked-example.png)

```python
TASK_SALES_RESEARCH = """\
Task: Produce a sales-research brief on a company.

Inputs:
  - company_name: str
  - product_summary: str (the product we sell)

Output: JSON conforming to the schema below.

Output schema:
  {
    "company": {"name": str, "ticker": str | null, "industry": str},
    "summary": str,                  # 2-3 sentences, no marketing prose
    "sources": [{"id": str, "url": str, "fetched_at": str}],
    "claims": [
      {
        "text": str,
        "source_ids": [str],         # MUST be non-empty; MUST reference items in sources
        "confidence": "high" | "medium" | "low"
      }
    ],
    "potential_pain_points": [
      {
        "text": str,
        "evidence_claim_ids": [int],  # indexes into claims
        "product_relevance": str       # must explicitly connect to product_summary
      }
    ],
    "insufficient_evidence": bool      # true if you could not produce >= 3 cited claims
  }

Constraints:
  - Every claim MUST have at least one source_id. Claims without sources are forbidden.
  - Pain points MUST cite claim indexes; un-evidenced pain points are forbidden.
  - If you cannot find at least 3 cited claims, set insufficient_evidence=true
    and return empty pain_points. Do NOT fabricate to fill the structure.
  - Do not produce content about the company beyond what the cited sources support.
"""
```

The re-specified version is six times longer. It's also six times more likely to produce useful output and roughly ten times less likely to silently produce nonsense. Specification is the work.

#### 3.3 Patterns for shaping behavior under uncertainty

The four-layer architecture is a frame. Inside it, certain composable patterns recur:

- 

**Deferred-judgment prompting:** Have the model produce a candidate answer and then evaluate it against criteria in a separate model call (or in a separate role within the same prompt). Single-pass self-evaluation is unreliable, while structurally separate evaluation is dramatically better. This is the prompt-level basis of the Reflection Agent (Agent 47) and the Chain-of-Thought Auditor (Agent 8).

- 

**Structured refusal:** When the model is permitted to refuse, give it a structured way to do so, like an `insufficient_evidence: true` flag, an `unable_to_proceed: { reason: str }` block, a specific output value that means "decline." Free-text refusals get parsed back into apparent answers but structured refusals do not.

- 

**Plan-before-act:** When the model is going to take an action, have it write the plan first and the action second, in the same call. This is mechanically cheap and dramatically improves the quality of the action. The plan is the model's commitment device.

- 

**Output schemas with rationale fields:** When you require structured output, include a `rationale: str` field for each decision the structure asks the model to make. The rationale is the model's reasoning trace, written next to the decision it explains, in a place where you can audit it.

![Pattern 016 — 3.3 Patterns for shaping behavior under uncertainty](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca518437f571ad48538_codex-pattern-016-3-3-patterns-for-shaping-behavior-under-uncertainty.png)

```python
# Output schema with structured refusal and rationale fields.
DECISION_SCHEMA = {
    "decision": ["approve", "reject", "escalate", "insufficient_evidence"],
    "rationale": "str",          # the model's reasoning, captured next to the decision
    "evidence_refs": ["str"],     # claim IDs the rationale depends on
    "escalation_target": "str | null",   # required when decision==escalate
    "missing_evidence": ["str"]   # required when decision==insufficient_evidence
}
```

#### 3.4 A working method for prompt iteration

Most prompt iteration is superstition. An engineer changes three things in the prompt at once, observes that the output is better on one example, declares victory, and ships. Three weeks later they can't reproduce the win.

The discipline that fixes this is unromantic:

- 

**Hold an evaluation set fixed:** Twenty to fifty cases, labeled with the desired outcome. Don't change them. New cases go into a held-out set.

- 

**Change one variable at a time:** One section of the prompt, one schema field, one model parameter. Re-run the full evaluation. Record the result.

- 

**Version every prompt:** Tag every prompt with `agent_name:role:version`. Store the full prompt in version control, even if it includes generated content. The trace records which version produced which output.

- 

**Compare pairwise, not absolutely:** "Version 5 gets 78% pass" is less useful than "version 5 beats version 4 on cases 12, 17, and 23, loses on case 6, ties on the rest." The pairwise comparison is what tells you whether to ship.

![Pattern 017 — 3.4 A working method for prompt iteration](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5ca5b8c5c96b80f39a51_codex-pattern-017-3-4-a-working-method-for-prompt-iteration.png)

```python
# Prompt-iteration record.
@dataclass
class PromptEvalRun:
    prompt_name: str
    prompt_version: str
    eval_set: str
    cases: list[CaseResult]
    pass_rate: float
    cost_per_case_cents: float
    
def compare(a: PromptEvalRun, b: PromptEvalRun) -> dict:
    """Pairwise comparison rather than absolute scores."""
    diffs = {}
    for case_a, case_b in zip(a.cases, b.cases):
        if case_a.passed != case_b.passed:
            diffs[case_a.id] = (case_a.passed, case_b.passed)
    return {"wins_for_b": sum(1 for _, p in diffs.values() if p),
            "losses_for_b": sum(1 for _, p in diffs.values() if not p),
            "diffs": diffs}
```

#### 3.5 The ceiling of prompting

This chapter is explicit that prompting alone can't enforce safety, factuality, or reliability past a certain ceiling. The ceiling is real, it's reached early in any serious agent, and recognizing it is the difference between an agent engineer and a prompt enthusiast.

Specifically, prompting can't enforce:

- 

deterministic refusal on adversarial input (the model will be talked around the rule with sufficient cleverness)

- 

strict schema adherence (with enough provider quirks the model will produce malformed JSON eventually)

- 

citation honesty (the model will fabricate citations when its refusal path is blocked)

- 

or step-bounded behavior (the model will hallucinate completion).

Each of these requires *structural* enforcement: a validator, a runtime check, a verifier agent, and a hard bound in the harness. Prompting is the steering wheel. The structural patterns in Part II are the chassis.
