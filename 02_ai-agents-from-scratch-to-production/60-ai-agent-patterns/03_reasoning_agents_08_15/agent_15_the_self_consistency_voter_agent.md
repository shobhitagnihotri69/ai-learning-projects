# Agent 15 — The Self-Consistency Voter Agent

### Agent 15 — The Self-Consistency Voter Agent

*Runs N independent reasoning chains and aggregates them into a more reliable answer.*

#### The Problem

Sampling a model once gives you one reasoning path. Sampling it five or ten times gives you a distribution of paths, most of which arrive at the same answer when the problem has a stable answer at all.

A single sample can be confidently wrong, while a sample of ten with eight agreeing is dramatically more reliable. The disagreement rate is itself a useful signal. It tells you which problems the agent doesn't actually know how to solve.

The general problem is **stochastic confidence**: a model's surface confidence on a single sample isn't calibrated to its actual accuracy on that problem. Multiple samples expose the underlying uncertainty.

#### Why Naïve Approaches Fail

- 

*"Just sample once with low temperature."* Reduces variance but doesn't eliminate it. The failure modes that survive into low-temperature sampling are the systematic ones.

- 

*"Sample five times and take the first answer."* Doesn't use the redundancy.

- 

*"Sample five times and ensemble the answers in natural language."* Works for some tasks, but fails for tasks where "ensembling" produces an answer that's the average of two correct alternatives and is itself wrong.

#### The Mechanism

The voter agent runs the same problem through the same policy multiple times at non-zero temperature, clusters the conclusions, and reports the modal answer together with the agreement rate. Critically, agreement rate is exposed as a confidence proxy. Low agreement is an escalation signal.

![Pattern 039 — Agent 15 — The Self-Consistency Voter Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dd406b2c784575c26f6_codex-pattern-039-agent-15-the-self-consistency-voter-agent-the-mechanism.png)

```python
# reasoning/self_consistency.py
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
```

#### Trade-offs and Alternatives

N samples cost N times the inference. For an N of eight, this is an 8× multiplier on cost and latency. The trade is worth it for hard problems where single-sample accuracy is unacceptably low. But it's overhead for problems where single-sample accuracy is already high.

Pick N empirically: sample sweeps from one to sixteen on an evaluation set. The curve typically has a knee around four to eight.

The voter works only when canonicalization successfully clusters equivalent answers. For numerical answers, canonicalize to a rounded form. For free-text answers, canonicalize via a normalization model or embedding cluster. For structured answers, canonicalize by sorting / normalizing the structure.

When canonicalization fails, the voter degenerates to "pick the first sample," which is no better than not voting at all.

#### Production Failure Modes

- 

**Canonicalization too aggressive:** Different correct answers get merged into one cluster, and the voter reports false agreement. Mitigate by validating the canonicalizer against a held-out set of answers labeled as equivalent or not.

- 

**Canonicalization too lenient:** Same answers in slightly different forms appear as different clusters, and the voter under-counts agreement. Mitigate by erring on the lenient side and tuning against the labeled set.

- 

**Systematic bias:** All samples agree, all are wrong. The voter can't detect this because it has no ground truth. Mitigate by pairing the voter with an external verifier (the Chain-of-Thought Auditor, Agent 8) or a different model family.

#### Case Study

A math-tutoring agent at an edtech vendor solves every problem five times in parallel, returns the modal answer, and silently escalates any problem with fewer than four agreeing chains to a stronger model.

The escalation rate is about 8% of problems. Measured accuracy on a labeled benchmark of three thousand problems: 78% with single-sample, 91% with self-consistency voting, 96% with voting plus escalation to the stronger model. The cost increase from single-sample to voting+escalation was 3.1×, and the accuracy improvement was 18 percentage points.

**Pairs with:** Chain-of-Thought Auditor (Agent 8), Reflection (Agent 47), Debate Moderator (Agent 39).
