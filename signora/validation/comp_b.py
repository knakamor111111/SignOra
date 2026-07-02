"""Competition B validator scoring."""

from __future__ import annotations

from signora.core.constants import STAGE_EMISSION_WEIGHTS
from signora.translation.baseline import wer


def score_translation(
    hypothesis: str,
    reference: str,
    stage: int,
    confidence: float = 1.0,
) -> float:
    """
    Return 0..1 translation score for a single clip.

    Uses WER against known-plaintext reference, weighted by stage importance
    and miner confidence.
    """
    error = wer(reference, hypothesis)
    base = max(0.0, 1.0 - error)
    stage_w = STAGE_EMISSION_WEIGHTS.get(stage, 0.25)
    return float(base * (0.8 + 0.2 * confidence) * (0.5 + stage_w))
