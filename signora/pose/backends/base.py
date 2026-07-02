"""Pose extraction backend protocol."""

from __future__ import annotations

from typing import Protocol

from signora.core.types import PoseSubmission


class PoseBackend(Protocol):
    name: str

    def extract_from_path(
        self, video_path: str, clip_id: str, stage: int
    ) -> PoseSubmission: ...

    def available(self) -> bool: ...
