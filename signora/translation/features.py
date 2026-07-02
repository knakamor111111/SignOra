"""Pose sequence feature extraction for Comp B."""

from __future__ import annotations

import numpy as np

from signora.core.types import PoseSubmission


def pose_to_features(pose: PoseSubmission, max_frames: int = 128) -> np.ndarray:
    """
    Convert pose submission to (T, F) float32 matrix.

    Features per frame: left hand xyz, right hand xyz, face grammar xyz, mean conf.
    """
    rows: list[list[float]] = []
    for frame in pose.frames[:max_frames]:
        row: list[float] = []
        row.extend(_hand_vec(frame.left_hand))
        row.extend(_hand_vec(frame.right_hand))
        row.extend(_hand_vec(frame.face_grammar, dim=6))
        row.append(frame.mean_hand_confidence)
        rows.append(row)

    if not rows:
        return np.zeros((1, _feature_dim()), dtype=np.float32)

    arr = np.array(rows, dtype=np.float32)
    if len(arr) < max_frames:
        pad = np.zeros((max_frames - len(arr), arr.shape[1]), dtype=np.float32)
        arr = np.vstack([arr, pad])
    return arr


def _hand_vec(hand: list, dim: int = 21) -> list[float]:
    out: list[float] = []
    for i in range(dim):
        if i < len(hand):
            lm = hand[i]
            out.extend([lm.x, lm.y, lm.z])
        else:
            out.extend([0.0, 0.0, 0.0])
    return out


def _feature_dim() -> int:
    return 21 * 3 * 2 + 6 * 3 + 1
