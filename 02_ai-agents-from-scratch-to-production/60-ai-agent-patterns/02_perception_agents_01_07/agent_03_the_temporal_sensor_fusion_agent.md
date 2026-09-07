# Agent 3 — The Temporal Sensor-Fusion Agent

### Agent 3 — The Temporal Sensor-Fusion Agent

*Aligns asynchronous streams into a single time-indexed percept.*

#### The Problem

When an agent's inputs come from multiple streams arriving at different rates (like a webhook here, a poll there, and a websocket feed elsewhere), the policy above will misbehave unless something has already normalized them onto a single timeline. The policy ends up reasoning about events as if their arrival order were their occurrence order, which is sometimes true, often wrong, and impossible to debug after the fact.

The general problem is **clock skew at the input boundary**. Each stream has its own clock, its own latency, its own retry semantics, and its own ordering guarantees. A single timeline has to be constructed from them, and the construction is non-trivial.

#### Why naïve approaches fail

- 

*"Just process events in arrival order."* This works until two streams contradict each other and the resolution depends on which arrived first. The resolution flips arbitrarily on retries.

- 

*"Sort by event timestamp from the source."* The timestamps from different sources are drifted against each other (sometimes by minutes, in poorly-managed systems by hours). You get an ordering that looks plausible and is wrong on edge cases that matter.

- 

*"Pick one stream as ground truth and align the others to it."* This works for two streams and breaks for three.

#### The Mechanism

The temporal sensor-fusion agent buffers incoming events, resolves their clock skew using shared landmark events, emits time-windowed percepts at a regular cadence, and handles back-pressure when a stream stalls.

![Pattern 027 — Agent 3 — The Temporal Sensor-Fusion Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5dcaf43a036859343a0d_codex-pattern-027-agent-3-the-temporal-sensor-fusion-agent-the-mechanism.png)

```python
# perception/sensor_fusion.py
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

@dataclass
class StreamEvent:
    stream_id: str
    source_timestamp: float       # the stream's own clock
    received_at: float            # local monotonic
    payload: dict
    landmark_id: str | None = None  # for skew estimation

@dataclass
class FusedObservation:
    window_start: float           # fused-clock time
    window_end: float
    events_by_stream: dict[str, list[StreamEvent]]
    skew_estimates: dict[str, float]  # per-stream offset to fused clock

class TemporalSensorFusionAgent:
    def __init__(self, streams: list[str], window_seconds: float = 1.0):
        self.streams = streams
        self.window = window_seconds
        self.buffers: dict[str, list[StreamEvent]] = defaultdict(list)
        self.skew: dict[str, float] = {s: 0.0 for s in streams}
        self.landmarks: dict[str, list[tuple[str, float]]] = defaultdict(list)
    
    def ingest(self, event: StreamEvent) -> None:
        self.buffers[event.stream_id].append(event)
        if event.landmark_id:
            self.landmarks[event.landmark_id].append(
                (event.stream_id, event.source_timestamp))
            self._update_skew()
    
    def _update_skew(self) -> None:
        """Estimate per-stream offset using shared landmark events."""
        for landmark_id, observations in self.landmarks.items():
            if len({s for s, _ in observations}) < 2:
                continue
            mean_ts = sum(ts for _, ts in observations) / len(observations)
            for stream, ts in observations:
                # Exponential moving average of skew
                old = self.skew[stream]
                self.skew[stream] = 0.9 * old + 0.1 * (ts - mean_ts)
    
    def emit(self, now: float) -> FusedObservation | None:
        """Emit a window if all streams have caught up to now - window."""
        window_end = now - self.window
        if not all(self._caught_up(s, window_end) for s in self.streams):
            return None
        events_by_stream = {}
        for s in self.streams:
            keep, drain = [], []
            for e in self.buffers[s]:
                fused_ts = e.source_timestamp - self.skew[s]
                if fused_ts < window_end:
                    drain.append(e)
                else:
                    keep.append(e)
            self.buffers[s] = keep
            events_by_stream[s] = sorted(drain, key=lambda e: e.source_timestamp - self.skew[e.stream_id])
        return FusedObservation(
            window_start=window_end - self.window,
            window_end=window_end,
            events_by_stream=events_by_stream,
            skew_estimates=dict(self.skew),
        )
    
    def _caught_up(self, stream: str, window_end: float) -> bool:
        # Has the stream produced any event past window_end? If yes, caught up.
        return any(
            (e.source_timestamp - self.skew[stream]) > window_end
            for e in self.buffers[stream]
        ) or self._stream_marked_idle(stream)
```

#### Trade-offs and Alternatives

Fusion adds latency proportional to the window size. For agents where freshness matters more than ordering correctness (a near-realtime alerter), shrink the window or accept partial windows.

For agents where ordering correctness dominates (anything that produces a decision binding multiple streams), grow the window or refuse to emit until all streams have caught up.

A simpler alternative is *eventual fusion*: buffer everything for a long window (minutes or hours), sort once, and reason over the sorted set. This is appropriate for batch agents and inappropriate for any agent that has to respond in seconds.

#### Production Failure Modes

- 

**Stuck streams:** One stream stalls and the window never closes. Mitigate with a per-stream liveness check and an explicit "stream-idle" marker so the fuser can proceed without it. Surface the missing stream to the downstream policy.

- 

**Skew estimate drift:** Landmark events become rare or noisy, and the skew estimate diverges from reality. Detect by monitoring the variance of skew over time. Trigger a recalibration when variance exceeds a threshold.

- 

**Out-of-order arrival within a stream:** Most stream interfaces eventually deliver events out of order despite their stated guarantees. Mitigate with a per-stream re-sort buffer with its own (shorter) window.

#### Case Study

A trading-floor support agent at a mid-sized broker fuses Bloomberg headlines, an internal order-management feed, and a desk-side Slack channel into per-minute situation reports for desk heads.

The fusion window is sixty seconds. Landmarks include market-open and market-close events shared across all three streams.

The downstream policy (an Anomaly-Spotter, Agent 4) reads the fused windows and surfaces anomalous combinations: a Slack mention of a counterparty paired with an OMS rejection on the same counterparty within the window, or a Bloomberg headline naming a sector paired with an unusual concentration of new orders in that sector. The fused-window approach reduced false-positive alerts by 60% compared to per-stream alerting.

**Pairs with:** Ambient Context (Agent 6), Anomaly Spotter (Agent 4), Drift Detector (Agent 59).
