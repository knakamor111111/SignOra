"""Second reference pipeline using optical-flow hand tracking.

Independent of MediaPipe — reduces circular scoring when miners also use MediaPipe.
Maps tracked hand centroids + contour samples into 21 pseudo-landmarks per hand.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from signora.core.constants import NUM_HAND_LANDMARKS
from signora.core.types import FramePose, Landmark, PoseSubmission

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore


class OpticalFlowBackend:
    name = "optical_flow_v1"

    def available(self) -> bool:
        return cv2 is not None

    def extract_from_path(
        self, video_path: str, clip_id: str, stage: int
    ) -> PoseSubmission:
        if cv2 is None:
            raise RuntimeError("opencv required for OpticalFlowBackend")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames: list[FramePose] = []
        prev_gray = None
        prev_points: np.ndarray | None = None
        frame_idx = 0

        while True:
            ok, bgr = cap.read()
            if not ok:
                break

            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            if prev_gray is None:
                prev_gray = gray
                prev_points = self._init_points(gray)
                frame_idx += 1
                continue

            if prev_points is not None and len(prev_points) > 0:
                next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                    prev_gray, gray, prev_points, None
                )
                good = status.reshape(-1) == 1
                tracked = next_pts.reshape(-1, 2)[good]
            else:
                tracked = np.zeros((0, 2))

            left, right = self._points_to_hands(tracked, w, h)
            mean_conf = float(min(1.0, 0.55 + 0.01 * len(tracked)))

            frames.append(
                FramePose(
                    timestamp_ms=(frame_idx / fps) * 1000.0,
                    left_hand=left,
                    right_hand=right,
                    face_grammar=[],
                    body_pose=[],
                    mean_hand_confidence=mean_conf,
                )
            )

            prev_gray = gray
            prev_points = self._init_points(gray) if len(tracked) < 4 else next_pts
            frame_idx += 1

        cap.release()
        miner_conf = float(np.mean([f.mean_hand_confidence for f in frames])) if frames else 0.0
        return PoseSubmission(
            clip_id=clip_id,
            stage=stage,
            frames=frames,
            miner_confidence=miner_conf,
            pipeline=self.name,
        )

    @staticmethod
    def _init_points(gray: np.ndarray) -> np.ndarray:
        features = cv2.goodFeaturesToTrack(
            gray, maxCorners=40, qualityLevel=0.01, minDistance=8
        )
        if features is None:
            return np.zeros((0, 1, 2), dtype=np.float32)
        return features.astype(np.float32)

    @staticmethod
    def _normalize(x: float, y: float, w: int, h: int) -> tuple[float, float]:
        return x / max(w, 1), y / max(h, 1)

    def _points_to_hands(
        self, points: np.ndarray, w: int, h: int
    ) -> tuple[list[Landmark], list[Landmark]]:
        if len(points) == 0:
            empty = [Landmark(0, 0, 0, 0, 0) for _ in range(NUM_HAND_LANDMARKS)]
            return empty, empty

        xs = points[:, 0]
        mid = w / 2.0
        left_pts = points[xs < mid]
        right_pts = points[xs >= mid]

        return (
            self._pseudo_landmarks(left_pts, w, h),
            self._pseudo_landmarks(right_pts, w, h),
        )

    def _pseudo_landmarks(
        self, pts: np.ndarray, w: int, h: int
    ) -> list[Landmark]:
        if len(pts) == 0:
            return [Landmark(0, 0, 0, 0, 0) for _ in range(NUM_HAND_LANDMARKS)]

        center = pts.mean(axis=0)
        cx, cy = self._normalize(float(center[0]), float(center[1]), w, h)

        landmarks: list[Landmark] = []
        for i in range(NUM_HAND_LANDMARKS):
            if i < len(pts):
                px, py = pts[i]
                nx, ny = self._normalize(float(px), float(py), w, h)
                vis = 0.85
            else:
                # Radiate pseudo joints from center for missing points
                angle = (i / NUM_HAND_LANDMARKS) * 6.283
                nx = cx + 0.03 * np.cos(angle)
                ny = cy + 0.03 * np.sin(angle)
                vis = 0.5
            landmarks.append(
                Landmark(x=nx, y=ny, z=0.0, visibility=vis, presence=vis)
            )
        return landmarks
