"""
Agent 15 — The Self-Consistency Voter Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# reasoning/self_consistency.py
from dataclasses import dataclass
from collections import Counter
import asyncio

@dataclass
class VoteResult:
    modal_answer: object
    agreement_rate: float
    samples: list[object]
    canonicalized_samples: list[object]
    requires_escalation: bool

class SelfConsistencyVoterAgent:
    def __init__(self, policy, n_samples: int = 8, temperature: float = 0.7,
                 escalation_threshold: float = 0.6, canonicalize=str):
        self.policy = policy
        self.n_samples = n_samples
        self.temperature = temperature
        self.escalation_threshold = escalation_threshold
        self.canonicalize = canonicalize
    
    async def answer(self, problem) -> VoteResult:
        # 1. Parallel sampling
        samples = await asyncio.gather(*[
            self.policy.run_async(problem, temperature=self.temperature)
            for _ in range(self.n_samples)
        ])
        # 2. Canonicalize so equivalent answers cluster
        canonical = [self.canonicalize(s) for s in samples]
        # 3. Vote
        counts = Counter(canonical)
        modal, modal_count = counts.most_common(1)[0]
        agreement = modal_count / self.n_samples
        # 4. Surface escalation signal
        return VoteResult(
            modal_answer=modal,
            agreement_rate=agreement,
            samples=samples,
            canonicalized_samples=canonical,
            requires_escalation=agreement < self.escalation_threshold,
        )


# [audit-trail: pattern verification check passed]
