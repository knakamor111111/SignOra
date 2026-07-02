"""Shared pose metrics for gate and scoring."""

from __future__ import annotations

import numpy as np

from signora.core.constants import MIN_VISIBLE_HAND_LANDMARKS, VISIBILITY_THRESHOLD
from signora.core.types import PoseSubmission


def visible_hand_landmark_count(hand: list) -> int:
    return sum(1 for lm in hand if lm.visibility >= VISIBILITY_THRESHOLD)


def face_grammar_coverage(submission: PoseSubmission) -> float:
    if not submission.frames:
        return 0.0
    if submission.stage == 1:
        return 1.0
    good = 0
    for frame in submission.frames:
        if not frame.face_grammar:
            continue
        visible = sum(
            1 for lm in frame.face_grammar if lm.visibility >= VISIBILITY_THRESHOLD
        )
        if visible >= max(1, len(frame.face_grammar) // 2):
            good += 1
    return good / len(submission.frames)


def temporal_continuity(submission: PoseSubmission) -> float:
    if len(submission.frames) < 2:
        return 1.0

    stable_pairs = 0
    total_pairs = len(submission.frames) - 1
    max_jump = 0.08

    for prev, curr in zip(submission.frames, submission.frames[1:]):
        if not prev.left_hand or not curr.left_hand:
            continue
        p = prev.left_hand[0]
        c = curr.left_hand[0]
        jump = ((p.x - c.x) ** 2 + (p.y - c.y) ** 2) ** 0.5
        if jump <= max_jump:
            stable_pairs += 1

    return stable_pairs / total_pairs if total_pairs else 1.0


def hand_coverage(submission: PoseSubmission) -> float:
    if not submission.frames:
        return 0.0
    good = 0
    for frame in submission.frames:
        left_ok = visible_hand_landmark_count(frame.left_hand) >= MIN_VISIBLE_HAND_LANDMARKS
        right_ok = visible_hand_landmark_count(frame.right_hand) >= MIN_VISIBLE_HAND_LANDMARKS
        if left_ok and right_ok:
            good += 1
    return good / len(submission.frames)


def mean_hand_confidence(submission: PoseSubmission) -> float:
    confs: list[float] = []
    for frame in submission.frames:
        for lm in frame.left_hand + frame.right_hand:
            if lm.visibility >= VISIBILITY_THRESHOLD:
                confs.append(lm.presence)
    return float(np.mean(confs)) if confs else 0.0
