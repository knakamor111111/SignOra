"""MediaPipe Holistic backend."""

from __future__ import annotations

from signora.core.types import PoseSubmission
from signora.pose.extractor import PoseExtractor


class MediaPipeBackend:
    name = "mediapipe_holistic"

    def __init__(self, min_hand_confidence: float = 0.5) -> None:
        self._extractor: PoseExtractor | None = None
        self._error: str | None = None
        try:
            self._extractor = PoseExtractor(min_hand_confidence=min_hand_confidence)
        except Exception as exc:  # pragma: no cover - optional dep
            self._error = str(exc)

    def available(self) -> bool:
        return self._extractor is not None

    def extract_from_path(
        self, video_path: str, clip_id: str, stage: int
    ) -> PoseSubmission:
        if not self._extractor:
            raise RuntimeError(self._error or "MediaPipe backend unavailable")
        return self._extractor.extract_from_path(video_path, clip_id, stage)
