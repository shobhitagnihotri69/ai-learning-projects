"""
Agent 56 — The Red-Team Auditor Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# alignment/red_team.py
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





# study-note: verified and refactored
