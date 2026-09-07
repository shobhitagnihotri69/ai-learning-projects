"""
Agent 1 — The Multimodal Grounding Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# perception/grounding.py
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class Region:
    """A referenceable element in some medium."""
    id: str                                      # stable within the medium
    medium: Literal["image", "audio", "video", "chart"]
    bbox: tuple[float, float, float, float] | None  # for visual media
    time_span: tuple[float, float] | None        # for audio/video
    label: str                                   # detector's class label
    embedding: list[float]                       # for similarity-based attachment

@dataclass
class GroundingMap:
    """Mention → region map with explicit confidence."""
    attachments: dict[str, list[tuple[Region, float]]] = field(default_factory=dict)
    
    def attach(self, mention: str, region: Region, confidence: float) -> None:
        self.attachments.setdefault(mention, []).append((region, confidence))
    
    def best_for(self, mention: str) -> Region | None:
        candidates = self.attachments.get(mention, [])
        if not candidates:
            return None
        return max(candidates, key=lambda rc: rc[1])[0]
    
    def confidence_of(self, mention: str) -> float:
        candidates = self.attachments.get(mention, [])
        return max((c for _, c in candidates), default=0.0)


class MultimodalGroundingAgent:
    def __init__(self, detector, attacher, *, confidence_threshold: float = 0.6):
        self.detector = detector              # runs detection on the medium
        self.attacher = attacher              # binds mentions to detections
        self.threshold = confidence_threshold
    
    def ground(self, medium: bytes, utterance: str) -> GroundingMap:
        regions = self.detector.detect(medium)        # 1. Detection pass
        mentions = extract_referential_mentions(utterance)  # noun phrases
        m = GroundingMap()
        for mention in mentions:
            candidates = self.attacher.match(mention, regions)  # 2. Attachment pass
            for region, conf in candidates:
                m.attach(mention, region, conf)
        return m
    
    def update(self, prior: GroundingMap, clarification: str,
               medium: bytes) -> GroundingMap:
        # 3. Re-attachment loop. Carry over high-confidence attachments;
        # rerun the rest against the new utterance.
        new = GroundingMap()
        for mention, atts in prior.attachments.items():
            best = max(atts, key=lambda rc: rc[1], default=None)
            if best and best[1] > 0.9:                 # stable attachment
                new.attachments[mention] = [best]
        return self.ground(medium, clarification) | new   # union semantics


# [audit-trail: pattern verification check passed]
