"""Optional DWPose / ONNX pose backend."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from signora.core.constants import NUM_HAND_LANDMARKS
from signora.core.types import FramePose, Landmark, PoseSubmission

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import onnxruntime as ort

    _ORT = True
except ImportError:  # pragma: no cover
    ort = None  # type: ignore
    _ORT = False


class DwposeOnnxBackend:
    """
    Loads an exported DWPose / whole-body ONNX model when present.

    Place model at models/dwpose.onnx (see docs/MODELS.md).
    Falls back gracefully when file or onnxruntime missing.
    """

    name = "dwpose_onnx"

    def __init__(self, model_path: str = "./models/dwpose.onnx") -> None:
        self.model_path = Path(model_path)
        self._session = None
        self._error: str | None = None

        if not _ORT:
            self._error = "onnxruntime not installed"
            return
        if not self.model_path.exists():
            self._error = f"model not found: {self.model_path}"
            return
        try:
            self._session = ort.InferenceSession(
                str(self.model_path), providers=["CPUExecutionProvider"]
            )
        except Exception as exc:  # pragma: no cover
            self._error = str(exc)

    def available(self) -> bool:
        return self._session is not None and cv2 is not None

    def extract_from_path(
        self, video_path: str, clip_id: str, stage: int
    ) -> PoseSubmission:
        if not self.available():
            raise RuntimeError(self._error or "DWPose ONNX backend unavailable")
        if cv2 is None:
            raise RuntimeError("opencv required")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames: list[FramePose] = []
        frame_idx = 0
        input_name = self._session.get_inputs()[0].name

        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            h, w, _ = rgb.shape
            inp = self._preprocess(rgb)
            outputs = self._session.run(None, {input_name: inp})
            left, right = self._decode_hands(outputs[0], w, h)
            frames.append(
                FramePose(
                    timestamp_ms=(frame_idx / fps) * 1000.0,
                    left_hand=left,
                    right_hand=right,
                    face_grammar=[],
                    body_pose=[],
                    mean_hand_confidence=0.8,
                )
            )
            frame_idx += 1

        cap.release()
        return PoseSubmission(
            clip_id=clip_id,
            stage=stage,
            frames=frames,
            miner_confidence=0.8,
            pipeline=self.name,
        )

    @staticmethod
    def _preprocess(rgb: np.ndarray) -> np.ndarray:
        resized = cv2.resize(rgb, (256, 256))
        arr = resized.astype(np.float32) / 255.0
        return np.transpose(arr, (2, 0, 1))[None, ...]

    @staticmethod
    def _decode_hands(
        raw: np.ndarray, w: int, h: int
    ) -> tuple[list[Landmark], list[Landmark]]:
        """Map generic ONNX keypoint output to hand landmark lists."""
        flat = np.asarray(raw).reshape(-1)
        if flat.size < NUM_HAND_LANDMARKS * 4:
            empty = [Landmark(0, 0, 0, 0, 0) for _ in range(NUM_HAND_LANDMARKS)]
            return empty, empty

        def slice_hand(offset: int) -> list[Landmark]:
            pts = []
            for i in range(NUM_HAND_LANDMARKS):
                base = offset + i * 2
                x = float(flat[base]) / max(w, 1)
                y = float(flat[base + 1]) / max(h, 1)
                pts.append(Landmark(x, y, 0.0, 0.85, 0.85))
            return pts

        return slice_hand(0), slice_hand(NUM_HAND_LANDMARKS * 2)
