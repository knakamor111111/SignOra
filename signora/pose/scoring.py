"""Geometric scoring for Competition A (Score SN44 pattern)."""

from __future__ import annotations

import numpy as np

from signora.core.constants import COMP_A_WEIGHTS
from signora.core.types import PoseSubmission
from signora.pose.metrics import face_grammar_coverage, temporal_continuity


def _hand_xyz(hand: list) -> np.ndarray:
    if not hand:
        return np.zeros((0, 3))
    return np.array([[lm.x, lm.y, lm.z] for lm in hand])


def geometric_score(miner: PoseSubmission, reference: PoseSubmission) -> float:
    """
    Normalized 1 - MPJPE between miner and reference pose sequences.
    Returns 0..1 (higher is better).
    """
    if not miner.frames or not reference.frames:
        return 0.0

    n = min(len(miner.frames), len(reference.frames))
    errors: list[float] = []

    for i in range(n):
        mf, rf = miner.frames[i], reference.frames[i]
        for m_hand, r_hand in ((mf.left_hand, rf.left_hand), (mf.right_hand, rf.right_hand)):
            m_arr = _hand_xyz(m_hand)
            r_arr = _hand_xyz(r_hand)
            if m_arr.size == 0 or r_arr.size == 0:
                continue
            k = min(len(m_arr), len(r_arr))
            diff = m_arr[:k] - r_arr[:k]
            errors.append(float(np.sqrt((diff ** 2).sum(axis=1)).mean()))

    if not errors:
        return 0.0

    mpjpe = float(np.mean(errors))
    return float(np.clip(1.0 - (mpjpe / 0.15), 0.0, 1.0))


def score_comp_a(
    miner: PoseSubmission,
    reference: PoseSubmission,
) -> float:
    """Composite Comp A score after gate metrics computed."""
    geom = geometric_score(miner, reference)
    temporal = temporal_continuity(miner)
    face = face_grammar_coverage(miner)

    w = COMP_A_WEIGHTS
    return (
        w["geometric"] * geom
        + w["temporal"] * temporal
        + w["face"] * face
    )
