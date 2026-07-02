"""Multi-signal pose quality gate (v0.6)."""

from __future__ import annotations

from signora.core.constants import (
    FACE_GRAMMAR_COVERAGE_MIN,
    STAGE_GATE_PARAMS,
    TEMPORAL_CONTINUITY_MIN,
)
from signora.core.types import GateResult, PoseSubmission
from signora.pose.metrics import (
    face_grammar_coverage,
    hand_coverage,
    mean_hand_confidence,
    temporal_continuity,
)
from signora.pose.scoring import geometric_score


class PoseQualityGate:
    """Decide whether a Comp A submission forwards to Comp B."""

    def __init__(
        self,
        stage_params: dict[int, dict[str, float]] | None = None,
        face_min: float = FACE_GRAMMAR_COVERAGE_MIN,
        temporal_min: float = TEMPORAL_CONTINUITY_MIN,
    ) -> None:
        self.stage_params = stage_params or STAGE_GATE_PARAMS
        self.face_min = face_min
        self.temporal_min = temporal_min

    def evaluate(
        self,
        submission: PoseSubmission,
        reference: PoseSubmission | None = None,
    ) -> GateResult:
        return evaluate_gate(
            submission, reference, self.stage_params, self.face_min, self.temporal_min
        )


def evaluate_gate(
    submission: PoseSubmission,
    reference: PoseSubmission | None,
    stage_params: dict[int, dict[str, float]] | None = None,
    face_min: float = FACE_GRAMMAR_COVERAGE_MIN,
    temporal_min: float = TEMPORAL_CONTINUITY_MIN,
) -> GateResult:
    params = (stage_params or STAGE_GATE_PARAMS).get(
        submission.stage, STAGE_GATE_PARAMS[1]
    )
    tau_hand = float(params["tau_hand"])
    theta = float(params["theta"])
    hand_cov_min = float(params.get("hand_coverage_min", 0.85))

    hand_cov = hand_coverage(submission)
    mean_conf = mean_hand_confidence(submission)
    face_cov = face_grammar_coverage(submission)
    temporal = temporal_continuity(submission)
    geom = geometric_score(submission, reference) if reference else 1.0

    checks = [
        (hand_cov >= hand_cov_min, f"hand_coverage {hand_cov:.3f} < {hand_cov_min}"),
        (mean_conf >= tau_hand, f"mean_hand_conf {mean_conf:.3f} < {tau_hand}"),
        (face_cov >= face_min, f"face_grammar_coverage {face_cov:.3f} < {face_min}"),
        (temporal >= temporal_min, f"temporal_continuity {temporal:.3f} < {temporal_min}"),
        (geom >= theta, f"geometric_score {geom:.3f} < {theta}"),
    ]

    failed = [msg for ok, msg in checks if not ok]
    passed = len(failed) == 0

    return GateResult(
        pass_=passed,
        hand_coverage=hand_cov,
        mean_hand_conf=mean_conf,
        face_grammar_coverage=face_cov,
        temporal_continuity=temporal,
        geometric_score=geom,
        stage=submission.stage,
        tau_hand=tau_hand,
        theta=theta,
        reason="" if passed else "; ".join(failed),
    )
