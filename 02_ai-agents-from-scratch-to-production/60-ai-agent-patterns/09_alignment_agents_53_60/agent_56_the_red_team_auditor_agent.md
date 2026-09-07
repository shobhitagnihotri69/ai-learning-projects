# Agent 56 — The Red-Team Auditor Agent

### Agent 56 — The Red-Team Auditor Agent

*Probes a sibling agent for failure modes the operator has not yet observed.*

#### The Problem

Most agent failures are discovered in production by users. The red-team auditor surfaces them in pre-production. It generates adversarial inputs against the production agent, catalogues the failures it triggers, and feeds the catalogue back into the calibration and constitution-binding patterns. The auditor runs continuously because new failure modes appear as the underlying model and the deployment distribution drift.

The general problem is **continuous adversarial evaluation**: systematically searching for failure modes the agent's normal test suite doesn't catch, before the failures reach users.

#### Why Naïve Approaches Fail

- 

*"Test on a static eval set."* Catches what the set was designed for but misses what it wasn't.

- 

*"Wait for bug reports."* By then the failures are in production.

- 

*"Have a human red-team occasionally."* Helpful, but doesn't scale. Also doesn't catch failure modes that emerge between human exercises.

#### The Mechanism

A generator of adversarial cases that combines templated attacks with model-generated variants tuned to the target agent's surface. An execution harness that runs each case through the target agent in an isolated sandbox. A failure classifier that distinguishes safety, factuality, capability, and constitutional failures. A regression-suite path that promotes discovered failures into a permanent evaluation set.

![Pattern 080 — Agent 56 — The Red-Team Auditor Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df70318190b4caf85e8_codex-pattern-080-agent-56-the-red-team-auditor-agent-the-mechanism.png)

```python
# alignment/red_team.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class FailureClass(Enum):
    SAFETY = "safety"
    FACTUALITY = "factuality"
    CAPABILITY = "capability"
    CONSTITUTIONAL = "constitutional"
    PRIVACY = "privacy"

@dataclass
class AdversarialCase:
    case_id: str
    template: str               # the seed template
    instantiation: str           # the actual input
    expected_failure_class: FailureClass | None
    generated_by: str           # generator model
    rationale: str              # why this might trigger a failure

@dataclass
class FailureFinding:
    finding_id: str
    case: AdversarialCase
    target_output: dict
    failure_class: FailureClass
    severity: str               # "low" | "medium" | "high" | "critical"
    description: str
    found_at: datetime
    reproduced_count: int = 1

class RedTeamAuditorAgent:
    def __init__(self, generator_llm, target_agent_factory, classifier_llm,
                 *, cases_per_run: int = 200):
        self.generator = generator_llm
        self.target_factory = target_agent_factory
        self.classifier = classifier_llm
        self.cases_per_run = cases_per_run
        self.findings: list[FailureFinding] = []
    
    def run_audit(self, target_description: str,
                  known_findings: list[FailureFinding]) -> list[FailureFinding]:
        # 1. Generate cases
        cases = self._generate_cases(target_description, known_findings)
        new_findings = []
        # 2. Run each against an isolated target instance
        for case in cases:
            target = self.target_factory()
            try:
                output = target.run(case.instantiation)
            except Exception as e:
                output = {"error": str(e)}
            # 3. Classify
            finding = self._classify(case, output)
            if finding:
                new_findings.append(finding)
                self.findings.append(finding)
        # 4. Dedup new findings against history
        return self._dedupe_against_history(new_findings)
    
    def _generate_cases(self, target_description: str,
                        known_findings: list[FailureFinding]) -> list[AdversarialCase]:
        # Mix templated attacks (jailbreaks, prompt injection, edge cases)
        # with generated novel attacks tuned to the target.
        templated = self._templated_attacks(target_description)
        novel = self._novel_attacks(target_description, known_findings)
        all_cases = (templated + novel)[:self.cases_per_run]
        return all_cases
    
    def _novel_attacks(self, target_description: str,
                       known_findings: list[FailureFinding]) -> list[AdversarialCase]:
        response = self.generator.call(
            messages=[
                {"role": "system", "content": ATTACK_GENERATION_PROMPT},
                {"role": "user", "content": f"Target: {target_description}\nKnown findings: {known_findings[-20:]}"}
            ],
            schema=ATTACK_GENERATION_SCHEMA,
        )
        return [AdversarialCase(**c) for c in response["cases"]]
    
    def _classify(self, case: AdversarialCase, output: dict) -> FailureFinding | None:
        response = self.classifier.call(
            messages=[
                {"role": "system", "content": FAILURE_CLASSIFICATION_PROMPT},
                {"role": "user", "content": f"Case: {case}\nOutput: {output}"}
            ],
            schema=FAILURE_CLASSIFICATION_SCHEMA,
        )
        if response["failure_detected"]:
            return FailureFinding(
                finding_id=self._mint_id(),
                case=case, target_output=output,
                failure_class=FailureClass(response["class"]),
                severity=response["severity"],
                description=response["description"],
                found_at=datetime.utcnow(),
            )
        return None
    
    def promote_to_regression_suite(self, finding: FailureFinding) -> dict:
        """Convert a finding into a permanent regression test."""
        return {
            "test_id": f"regression_{finding.finding_id}",
            "input": finding.case.instantiation,
            "expected_behavior": "agent does NOT exhibit "
                                 f"{finding.failure_class.value}:{finding.description}",
            "promoted_at": datetime.utcnow().isoformat(),
        }
```

#### Trade-offs and Alternatives

Red-teaming requires generating adversarial cases at scale. The generator LLM itself can be a frontier model, which makes the audit cost non-trivial.

For agents with very low stakes, the pattern is overhead. The pattern is essential for agents that handle sensitive data, take consequential actions, or face public-facing user populations.

For agents in regulated industries, red-teaming may be mandated. The pattern's evidence (the audit log, the regression suite) becomes part of the compliance story.

#### Production Failure Modes

- 

**Generator stagnation:** The generator produces similar attacks each run and coverage doesn't grow. Mitigate by varying generator-LLM choices over time, by mixing-in human-curated attacks, and by deliberately rewarding novel attack patterns.

- 

**Classifier under-detection:** Failures occur but the classifier doesn't flag them, so the audit is falsely clean. Mitigate by sampling un-flagged outputs for human review and recalibrating.

- 

**Regression-suite bloat:** Every finding goes into the regression suite, and the suite becomes too slow to run on every change. Mitigate by tiering: top-severity findings always run, others run on a schedule.

#### Case Study

A developer-tooling agent at a code-vendor's security-focused product runs a monthly red-team audit that consistently catches new failure modes introduced by upstream model upgrades. Findings are rolled into the agent's evaluation suite within twenty-four hours of discovery.

Over a two-year window, 37 distinct failure modes were caught pre-release that would otherwise have shipped. The most-severe (a prompt-injection vector through a particular tool's output) was caught two days before a customer would have hit it in production.

**Pairs with:** Refusal Calibrator (Agent 54), Drift Detector (Agent 59), Constitution-Bound (Agent 53).
