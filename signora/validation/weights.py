"""Build Yuma weight vectors per subtensor mechanism."""

from __future__ import annotations

from typing import Optional

import numpy as np

from signora.core.constants import MECH_CORPUS, MECH_POSE, MECH_TRANSLATION


def build_mechanism_weights(
    uids: list[int],
    pose_scores: dict[int, float],
    translation_scores: dict[int, float],
    corpus_scores: Optional[dict[int, float]] = None,
    min_score: float = 1e-6,
) -> dict[int, list[tuple[int, float]]]:
    """
    Return weight assignments per MechId.

    Output format: { mech_id: [(uid, weight), ...] }
    Weights are normalized to sum to 1.0 per mechanism.
    """
    corpus_scores = corpus_scores or {}

    return {
        MECH_POSE: _normalize_weights(uids, pose_scores, min_score),
        MECH_TRANSLATION: _normalize_weights(uids, translation_scores, min_score),
        MECH_CORPUS: _normalize_weights(uids, corpus_scores, min_score),
    }


def _normalize_weights(
    uids: list[int],
    scores: dict[int, float],
    min_score: float,
) -> list[tuple[int, float]]:
    raw = np.array([max(scores.get(uid, 0.0), min_score) for uid in uids], dtype=float)
    total = raw.sum()
    if total <= 0:
        uniform = 1.0 / len(uids) if uids else 0.0
        return [(uid, uniform) for uid in uids]
    normalized = raw / total
    return [(uid, float(w)) for uid, w in zip(uids, normalized)]


def composite_uid_scores(
    pose_scores: dict[int, float],
    translation_scores: dict[int, float],
    pose_weight: float = 0.4,
    translation_weight: float = 0.6,
) -> dict[int, float]:
    """Combined score for logging / dashboards."""
    all_uids = set(pose_scores) | set(translation_scores)
    return {
        uid: pose_weight * pose_scores.get(uid, 0.0)
        + translation_weight * translation_scores.get(uid, 0.0)
        for uid in all_uids
    }
