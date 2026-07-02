"""DWPose ONNX backend using yolox + dw-ll_ucoco_384 models."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from signora.core.constants import NUM_HAND_LANDMARKS
from signora.core.types import FramePose, Landmark, PoseSubmission

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore


class DwposeOnnxBackend:
    """
    Whole-body DWPose inference via controlnet-dwpose (recommended).

    Requires models/yolox_l.onnx and models/dw-ll_ucoco_384.onnx.
    Run: python scripts/download_dwpose_models.py
    """

    name = "dwpose_onnx"

    def __init__(self, models_dir: str = "./models") -> None:
        self.models_dir = Path(models_dir)
        self.det_path = self.models_dir / "yolox_l.onnx"
        self.pose_path = self.models_dir / "dw-ll_ucoco_384.onnx"
        self._detector = None
        self._error: str | None = None

        if not self.det_path.exists() or not self.pose_path.exists():
            self._error = (
                f"Missing ONNX models in {self.models_dir}. "
                "Run: python scripts/download_dwpose_models.py"
            )
            return

        try:
            from controlnet_dwpose import DWposeDetector

            self._detector = DWposeDetector(
                model_det=str(self.det_path),
                model_pose=str(self.pose_path),
                device="cpu",
            )
        except ImportError:
            self._error = "Install controlnet-dwpose: pip install signora[dwpose]"
        except Exception as exc:  # pragma: no cover
            self._error = str(exc)

    def available(self) -> bool:
        return self._detector is not None and cv2 is not None

    def extract_from_path(
        self, video_path: str, clip_id: str, stage: int
    ) -> PoseSubmission:
        if not self.available():
            raise RuntimeError(self._error or "DWPose backend unavailable")
        if cv2 is None:
            raise RuntimeError("opencv required")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frames: list[FramePose] = []
        frame_idx = 0

        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            h, w, _ = rgb.shape

            result = self._detector(rgb)
            left, right = self._hands_from_dwpose(result, w, h)
            frames.append(
                FramePose(
                    timestamp_ms=(frame_idx / fps) * 1000.0,
                    left_hand=left,
                    right_hand=right,
                    face_grammar=[],
                    body_pose=[],
                    mean_hand_confidence=0.85 if left or right else 0.3,
                )
            )
            frame_idx += 1

        cap.release()
        conf = float(np.mean([f.mean_hand_confidence for f in frames])) if frames else 0.0
        return PoseSubmission(
            clip_id=clip_id,
            stage=stage,
            frames=frames,
            miner_confidence=conf,
            pipeline=self.name,
        )

    @staticmethod
    def _hands_from_dwpose(
        result, w: int, h: int
    ) -> tuple[list[Landmark], list[Landmark]]:
        """Parse controlnet-dwpose output to SignOra hand landmarks."""
        empty = [Landmark(0, 0, 0, 0, 0) for _ in range(NUM_HAND_LANDMARKS)]

        if result is None:
            return empty, empty

        # result: dict with 'hands' key or tuple (candidate, subset) depending on version
        hands = None
        if isinstance(result, dict):
            hands = result.get("hands") or result.get("hand")
        elif isinstance(result, (list, tuple)) and len(result) >= 1:
            body = result[0]
            if isinstance(body, dict):
                hands = body.get("hands")

        if not hands:
            return empty, empty

        def to_landmarks(points) -> list[Landmark]:
            out: list[Landmark] = []
            for i in range(NUM_HAND_LANDMARKS):
                if i < len(points):
                    p = points[i]
                    x = float(p[0]) / max(w, 1)
                    y = float(p[1]) / max(h, 1)
                    out.append(Landmark(x, y, 0.0, 0.85, 0.85))
                else:
                    out.append(Landmark(0, 0, 0, 0, 0))
            return out

        if len(hands) >= 2:
            return to_landmarks(hands[0]), to_landmarks(hands[1])
        if len(hands) == 1:
            return to_landmarks(hands[0]), empty
        return empty, empty
