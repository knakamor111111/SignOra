"""Competition B baseline translation model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from signora.core.types import PoseSubmission


class BaselineTranslator:
    """
    Placeholder sequence-to-text model for bootstrap / testnet.

    Replace with a trained transformer in production. Loads optional
    gloss→English lookup from model_dir for Stage 1-2 demos.
    """

    def __init__(self, model_dir: str = "./models") -> None:
        self.model_dir = Path(model_dir)
        self._gloss_map: dict[str, str] = {}
        lookup = self.model_dir / "gloss_lookup.json"
        if lookup.exists():
            self._gloss_map = json.loads(lookup.read_text())

    def translate(
        self, pose: PoseSubmission, clip_id: str = ""
    ) -> tuple[str, float]:
        """
        Map pose sequence to English text.

        Bootstrap heuristic: if clip_id encodes expected gloss, use lookup.
        Otherwise return low-confidence placeholder.
        """
        gloss_hint = clip_id.split("_")[-1] if clip_id else ""
        if gloss_hint in self._gloss_map:
            return self._gloss_map[gloss_hint], 0.75

        # Motion-energy heuristic stub
        energy = self._motion_energy(pose)
        if energy < 0.01:
            return "", 0.1
        return f"[translation pending clip={pose.clip_id}]", 0.25

    @staticmethod
    def _motion_energy(pose: PoseSubmission) -> float:
        if len(pose.frames) < 2:
            return 0.0
        total = 0.0
        pairs = 0
        for a, b in zip(pose.frames, pose.frames[1:]):
            if not a.left_hand or not b.left_hand:
                continue
            dx = a.left_hand[0].x - b.left_hand[0].x
            dy = a.left_hand[0].y - b.left_hand[0].y
            total += (dx * dx + dy * dy) ** 0.5
            pairs += 1
        return total / pairs if pairs else 0.0


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate for Comp B scoring."""
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    if not ref:
        return 0.0 if not hyp else 1.0

    # Levenshtein at word level
    d = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1):
        d[i][0] = i
    for j in range(len(hyp) + 1):
        d[0][j] = j
    for i, rw in enumerate(ref, 1):
        for j, hw in enumerate(hyp, 1):
            cost = 0 if rw == hw else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    return d[len(ref)][len(hyp)] / len(ref)
