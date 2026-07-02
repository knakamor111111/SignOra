"""Competition A validator scoring."""

from __future__ import annotations

from signora.core.types import ClipScore, GateResult, PoseSubmission
from signora.pose.gate import PoseQualityGate
from signora.pose.scoring import score_comp_a


def score_pose_submission(
    miner: PoseSubmission,
    reference: PoseSubmission,
    gate: PoseQualityGate | None = None,
) -> ClipScore:
    g = (gate or PoseQualityGate()).evaluate(miner, reference)
    if not g.pass_:
        return ClipScore(
            clip_id=miner.clip_id,
            comp_a_score=0.0,
            comp_b_score=0.0,
            gate=g,
            forwarded_to_comp_b=False,
        )

    comp_a = score_comp_a(miner, reference)
    return ClipScore(
        clip_id=miner.clip_id,
        comp_a_score=comp_a,
        comp_b_score=0.0,
        gate=g,
        forwarded_to_comp_b=True,
    )
