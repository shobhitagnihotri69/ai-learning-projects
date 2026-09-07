# Agent 59 — The Drift-Detector Agent

### Agent 59 — The Drift-Detector Agent

*Monitors the agent's own input and output distributions for shift over time.*

#### The Problem

Agents in production are exposed to a distribution that doesn't stand still. User prompts evolve, upstream APIs change, the underlying model is upgraded, and the world that the agent acts in changes. Without drift detection, the resulting shift produces a quality regression that's visible only through user complaints — by which time the regression has already affected outcomes.

The general problem is **silent-quality-regression detection**: catching distribution shift in inputs or outputs before it produces a visible quality regression.

#### Why Naïve Approaches Fail

- 

*"Monitor accuracy."* Requires ground-truth labels on production data but is usually unavailable in real-time.

- 

*"Watch the error rate."* Catches obvious failures but misses subtle quality drift.

- 

*"Run the eval suite weekly."* Catches changes that happen to be in the eval suite but misses production-specific shifts.

#### The Mechanism

A reference baseline captured at deployment and re-captured on schedule. Per-feature distribution monitoring with statistically appropriate tests. A deviation-alarm policy with explicit hysteresis. An attribution step that names the most-shifted features. A hand-off contract to the recalibration patterns.

![Pattern 083 — Agent 59 — The Drift-Detector Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df10c71d87de8b6fe5f_codex-pattern-083-agent-59-the-drift-detector-agent-the-mechanism.png)

```python
# alignment/drift_detector.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math

@dataclass
class FeatureDistribution:
    feature_name: str
    histogram: list[float]      # quantized bins
    sample_count: int
    captured_at: datetime
    
    def kl_divergence(self, other: "FeatureDistribution", eps: float = 1e-9) -> float:
        """KL(self || other) — how surprising would self look from other's perspective?"""
        s_p = self._normalized(eps)
        s_q = other._normalized(eps)
        return sum(p * math.log(p / q) for p, q in zip(s_p, s_q))
    
    def _normalized(self, eps: float):
        total = sum(self.histogram) + eps * len(self.histogram)
        return [(c + eps) / total for c in self.histogram]

@dataclass
class DriftAlarm:
    feature: str
    severity: str           # "info" | "warn" | "critical"
    divergence: float
    direction: str          # "input" | "output"
    suggested_action: str

class DriftDetectorAgent:
    def __init__(self, feature_extractors: dict[str, callable],
                 *, kl_warn: float = 0.05, kl_critical: float = 0.2,
                 window_size: int = 10000):
        self.feature_extractors = feature_extractors
        self.kl_warn = kl_warn
        self.kl_critical = kl_critical
        self.window_size = window_size
        self.baseline: dict[str, FeatureDistribution] = {}
        self.windows: dict[str, list[float]] = {f: [] for f in feature_extractors}
    
    def set_baseline(self, distributions: dict[str, FeatureDistribution]) -> None:
        self.baseline = distributions
    
    def observe(self, inputs: dict, outputs: dict) -> list[DriftAlarm]:
        for feature_name, extractor in self.feature_extractors.items():
            value = extractor(inputs, outputs)
            self.windows[feature_name].append(value)
            if len(self.windows[feature_name]) > self.window_size:
                self.windows[feature_name].pop(0)
        return self.check()
    
    def check(self) -> list[DriftAlarm]:
        alarms = []
        for feature_name, baseline_dist in self.baseline.items():
            window = self.windows[feature_name]
            if len(window) < 1000:
                continue
            current_dist = self._histogram(window, baseline_dist)
            kl = current_dist.kl_divergence(baseline_dist)
            if kl > self.kl_critical:
                alarms.append(DriftAlarm(
                    feature=feature_name, severity="critical", divergence=kl,
                    direction=self._direction(feature_name),
                    suggested_action="trigger_recalibration",
                ))
            elif kl > self.kl_warn:
                alarms.append(DriftAlarm(
                    feature=feature_name, severity="warn", divergence=kl,
                    direction=self._direction(feature_name),
                    suggested_action="investigate",
                ))
        return alarms
```

#### Trade-offs and Alternatives

Drift detection requires (a) features that meaningfully capture the deployment distribution and (b) a baseline that reflects healthy operation. Both are real work. For agents in their first weeks of operation, the baseline is itself unstable. Drift detection produces noise.

For agents whose deployment distribution is well-understood and stable, simpler statistical-process-control monitors (control charts with hand-set bounds) work fine. The drift detector earns its keep when the distribution is complex enough that hand-set bounds would miss shifts.

#### Production Failure Modes

- 

**Baseline staleness:** The baseline was captured at launch. Six months later, the distribution has legitimately evolved and the baseline is no longer the reference for "healthy." Mitigate by updating the baseline on a schedule with explicit operator review.

- 

**Feature-coverage gaps:** The features the detector watches don't capture the failure mode that actually occurs. Mitigate by adding features informed by red-team findings and by user complaints.

- 

**Alarm fatigue:** Too many alarms, so the operator stops responding. Mitigate by tuning thresholds against historical operations and by summarizing related alarms.

#### Case Study

An enterprise-search agent at a B2B vendor caught a silent quality regression caused by an upstream tokenizer change in the underlying model — three days before any user complaint, and two days before the next scheduled eval run.

The drift detector noticed a 0.18 KL divergence on the output-token-distribution feature. The alarm triggered a recalibration of the prompt-version pinning that mitigated the regression within hours.

**Pairs with:** Anomaly-Spotter (Agent 4), Distillation (Agent 51), Vector-Store Curator (Agent 28).
