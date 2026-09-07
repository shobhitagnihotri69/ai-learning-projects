# Agent 4 — The Anomaly-Spotter Agent

### Agent 4 — The Anomaly-Spotter Agent

*Surfaces deviations from the expected pattern in a stream of observations.*

#### The Problem

An agent's job is sometimes not to classify, label, or explain anomalies — those are downstream tasks. Its job is to decide which slices of incoming data are worth waking another agent up for.

The naïve "alert on every change" path produces an alert volume that destroys the value of alerting altogether. The naïve "alert only on hardcoded thresholds" path misses everything except the failure modes the engineer thought to encode.

The general problem is **calibrated novelty detection**: identifying observations that are interesting precisely because they're unexpected, where "unexpected" is defined against a learned baseline rather than a hand-set rule.

#### Why Naïve Approaches Fail

- 

*"Static thresholds."* Catch the failures you encoded, miss everything else. Require a human to update them every time the baseline shifts.

- 

*"Alert on every X-sigma deviation from the moving average."* Generates alerts every time the variance changes (which is constantly in real systems), drowns the operator.

- 

*"Use a generic anomaly-detection library."* Most are tuned for industrial sensor data with very different statistical properties than business signals. Out-of-the-box false-positive rates are typically 100×+ what's tolerable.

#### The Mechanism

The anomaly-spotter maintains a model of the expected distribution of each observed signal, updates the model online, and emits an anomaly observation whenever the live signal deviates by a threshold the operator can tune.

![Pattern 028 — Agent 4 — The Anomaly-Spotter Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dcaf32977bfedb0662e_codex-pattern-028-agent-4-the-anomaly-spotter-agent-the-mechanism.png)

```python
# perception/anomaly_spotter.py
from dataclasses import dataclass
import math, time

@dataclass
class Anomaly:
    signal: str
    value: float
    expected_range: tuple[float, float]
    z_score: float
    window_start: float
    window_end: float
    severity: str          # "info" | "warn" | "critical"

class OnlineDistribution:
    """Welford's online mean/variance."""
    def __init__(self, alpha: float = 0.01):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0
        self.alpha = alpha
    
    def update(self, x: float) -> None:
        # Exponential moving statistics for non-stationary signals.
        if self.n == 0:
            self.mean = x
            self.n = 1
            return
        delta = x - self.mean
        self.mean += self.alpha * delta
        self.m2 = (1 - self.alpha) * self.m2 + self.alpha * delta * delta
        self.n += 1
    
    @property
    def sigma(self) -> float:
        return math.sqrt(self.m2)

class AnomalySpotterAgent:
    def __init__(self, signals: list[str], warn_z: float = 3.0,
                 critical_z: float = 5.0, dedup_window_s: float = 300):
        self.dists = {s: OnlineDistribution() for s in signals}
        self.warn_z = warn_z
        self.critical_z = critical_z
        self.dedup_window = dedup_window_s
        self._last_alert: dict[str, float] = {}
    
    def observe(self, signal: str, value: float, t: float = None) -> Anomaly | None:
        t = t or time.time()
        d = self.dists[signal]
        # Compute z BEFORE update so the current point doesn't dilute its own deviation.
        z = (value - d.mean) / d.sigma if d.sigma > 0 and d.n > 30 else 0.0
        d.update(value)
        if abs(z) < self.warn_z:
            return None
        # Hysteresis / deduplication
        last = self._last_alert.get(signal, 0)
        if t - last < self.dedup_window:
            return None
        severity = "critical" if abs(z) >= self.critical_z else "warn"
        self._last_alert[signal] = t
        return Anomaly(
            signal=signal,
            value=value,
            expected_range=(d.mean - 2 * d.sigma, d.mean + 2 * d.sigma),
            z_score=z,
            window_start=t - 60,
            window_end=t,
            severity=severity,
        )
```

#### Trade-offs and Alternatives

Online statistical detectors are cheap and work for univariate signals with stable variance. They fail on signals with strong seasonality (a daily signal will look anomalous every Monday morning until the model has seen enough Mondays) and on multivariate anomalies (each signal looks normal but their combination is unusual).

For seasonal signals, use a forecasting model (Prophet, Holt-Winters, lightweight LSTM) as the baseline rather than a moving mean. For multivariate anomalies, project to a learned latent space and detect deviations there (an autoencoder-based detector, or an Isolation Forest). The pattern remains the same. Only the baseline implementation changes.

#### Production Failure Modes

- 

**Cold-start:** The detector hasn't seen enough data to have a meaningful baseline, so everything looks anomalous. Mitigate by requiring a minimum sample count before the detector emits any alarms.

- 

**Quiet failure:** The signal stops arriving entirely, and the detector cheerfully reports nothing wrong. Mitigate by monitoring arrival cadence per signal as a meta-signal in the same detector.

- 

**Concept drift:** The baseline shifts permanently (a system was upgraded, user behavior changed). The detector chases the shift but mid-shift produces a wave of false positives. Mitigate by detecting concept drift explicitly (Agent 59) and pausing alerts during the recalibration window.

#### Case Study

A SaaS reliability agent at an enterprise software vendor watches latency, error rate, and saturation per service across roughly four hundred internal services.

Each service gets its own Anomaly-Spotter instance with shared thresholds. When a signal deviates, a Reflection Agent (Agent 47) is invoked to draft an incident summary against the relevant trace store before a human has noticed.

The pattern moves the detection time from "user complaint" (median twenty-three minutes) to "automated alarm" (median forty-seven seconds), and reduces false-positive incidents by 80% compared to the previous static-threshold system.

**Pairs with:** Drift Detector (Agent 59), Reflection (Agent 47), Temporal Sensor-Fusion (Agent 3).

