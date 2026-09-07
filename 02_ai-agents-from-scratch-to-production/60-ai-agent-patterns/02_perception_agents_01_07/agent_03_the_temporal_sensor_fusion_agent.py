"""
Agent 3 — The Temporal Sensor-Fusion Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# perception/sensor_fusion.py
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

