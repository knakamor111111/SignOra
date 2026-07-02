"""Shared types for pose submissions and scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Landmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0
    presence: float = 1.0


@dataclass
class FramePose:
    timestamp_ms: float
    left_hand: list[Landmark] = field(default_factory=list)
    right_hand: list[Landmark] = field(default_factory=list)
    face_grammar: list[Landmark] = field(default_factory=list)
    body_pose: list[Landmark] = field(default_factory=list)
    mean_hand_confidence: float = 0.0


@dataclass
class PoseSubmission:
    clip_id: str
    stage: int
    frames: list[FramePose]
    miner_confidence: float
    pipeline: str = "mediapipe_holistic"

    def to_dict(self) -> dict[str, Any]:
        def lm_dict(lm: Landmark) -> dict[str, float]:
            return {
                "x": lm.x,
                "y": lm.y,
                "z": lm.z,
                "visibility": lm.visibility,
                "presence": lm.presence,
            }

        return {
            "clip_id": self.clip_id,
            "stage": self.stage,
            "pipeline": self.pipeline,
            "miner_confidence": self.miner_confidence,
            "frames": [
                {
                    "timestamp_ms": f.timestamp_ms,
                    "left_hand": [lm_dict(lm) for lm in f.left_hand],
                    "right_hand": [lm_dict(lm) for lm in f.right_hand],
                    "face_grammar": [lm_dict(lm) for lm in f.face_grammar],
                    "body_pose": [lm_dict(lm) for lm in f.body_pose],
                    "mean_hand_confidence": f.mean_hand_confidence,
                }
                for f in self.frames
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PoseSubmission:
        frames: list[FramePose] = []
        for raw in data.get("frames", []):
            def parse_hand(key: str) -> list[Landmark]:
                return [
                    Landmark(
                        x=p["x"],
                        y=p["y"],
                        z=p.get("z", 0.0),
                        visibility=p.get("visibility", 1.0),
                        presence=p.get("presence", 1.0),
                    )
                    for p in raw.get(key, [])
                ]

            frames.append(
                FramePose(
                    timestamp_ms=float(raw["timestamp_ms"]),
                    left_hand=parse_hand("left_hand"),
                    right_hand=parse_hand("right_hand"),
                    face_grammar=parse_hand("face_grammar"),
                    body_pose=parse_hand("body_pose"),
                    mean_hand_confidence=float(raw.get("mean_hand_confidence", 0.0)),
                )
            )
        return cls(
            clip_id=str(data.get("clip_id", "")),
            stage=int(data.get("stage", 1)),
            frames=frames,
            miner_confidence=float(data.get("miner_confidence", 0.0)),
            pipeline=str(data.get("pipeline", "unknown")),
        )


@dataclass
class GateResult:
    pass_: bool
    hand_coverage: float
    mean_hand_conf: float
    face_grammar_coverage: float
    temporal_continuity: float
    geometric_score: float
    stage: int
    tau_hand: float
    theta: float
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass": self.pass_,
            "hand_coverage": round(self.hand_coverage, 4),
            "mean_hand_conf": round(self.mean_hand_conf, 4),
            "face_grammar_coverage": round(self.face_grammar_coverage, 4),
            "temporal_continuity": round(self.temporal_continuity, 4),
            "geometric_score": round(self.geometric_score, 4),
            "stage": self.stage,
            "tau_hand": self.tau_hand,
            "theta": self.theta,
            "reason": self.reason,
        }


@dataclass
class ClipScore:
    clip_id: str
    comp_a_score: float
    comp_b_score: float
    gate: GateResult
    forwarded_to_comp_b: bool
