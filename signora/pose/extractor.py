"""MediaPipe Holistic pose extraction wrapper."""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

from signora.core.constants import FACE_GRAMMAR_INDICES, NUM_HAND_LANDMARKS
from signora.core.types import FramePose, Landmark, PoseSubmission

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    _MEDIAPIPE_AVAILABLE = True
except ImportError:  # pragma: no cover
    mp = None  # type: ignore
    _MEDIAPIPE_AVAILABLE = False


def _landmarks_from_list(
    points: list[dict], count: int = NUM_HAND_LANDMARKS
) -> list[Landmark]:
    out: list[Landmark] = []
    for p in points[:count]:
        out.append(
            Landmark(
                x=float(p.get("x", 0.0)),
                y=float(p.get("y", 0.0)),
                z=float(p.get("z", 0.0)),
                visibility=float(p.get("visibility", 1.0)),
                presence=float(p.get("presence", 1.0)),
            )
        )
    while len(out) < count:
        out.append(Landmark(0.0, 0.0, 0.0, 0.0, 0.0))
    return out


class PoseExtractor:
    """Extract per-frame pose JSON from video using MediaPipe HolisticLandmarker."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        min_hand_confidence: float = 0.5,
    ) -> None:
        self.min_hand_confidence = min_hand_confidence
        self._landmarker = None
        if _MEDIAPIPE_AVAILABLE and cv2 is not None:
            self._landmarker = self._build_landmarker(model_path, min_hand_confidence)

    @staticmethod
    def _build_landmarker(model_path: Optional[str], min_hand_conf: float):
        base_options = mp_python.BaseOptions(
            model_asset_path=model_path or _default_model_path()
        )
        options = mp_vision.HolisticLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            min_hand_landmarks_confidence=min_hand_conf,
            min_pose_landmarks_confidence=min_hand_conf,
            min_face_landmarks_confidence=min_hand_conf,
        )
        return mp_vision.HolisticLandmarker.create_from_options(options)

    def extract_from_path(
        self, video_path: str | Path, clip_id: str, stage: int
    ) -> PoseSubmission:
        if self._landmarker is None or cv2 is None:
            raise RuntimeError(
                "MediaPipe and opencv are required for pose extraction. "
                "Install with: pip install signora[pose]"
            )

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames: list[FramePose] = []
        frame_idx = 0

        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int((frame_idx / fps) * 1000)
            result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
            frames.append(self._result_to_frame(result, timestamp_ms))
            frame_idx += 1

        cap.release()
        miner_conf = float(np.mean([f.mean_hand_confidence for f in frames])) if frames else 0.0
        return PoseSubmission(
            clip_id=clip_id,
            stage=stage,
            frames=frames,
            miner_confidence=miner_conf,
            pipeline="mediapipe_holistic",
        )

    def _result_to_frame(self, result, timestamp_ms: float) -> FramePose:
        left = self._parse_hand(result.left_hand_landmarks)
        right = self._parse_hand(result.right_hand_landmarks)
        face = self._parse_face_grammar(result.face_landmarks)
        body = self._parse_body(result.pose_landmarks)

        confs = [lm.presence for lm in left + right if lm.presence > 0]
        mean_conf = float(np.mean(confs)) if confs else 0.0

        return FramePose(
            timestamp_ms=timestamp_ms,
            left_hand=left,
            right_hand=right,
            face_grammar=face,
            body_pose=body,
            mean_hand_confidence=mean_conf,
        )

    @staticmethod
    def _parse_hand(landmarks) -> list[Landmark]:
        if not landmarks:
            return [Landmark(0, 0, 0, 0, 0) for _ in range(NUM_HAND_LANDMARKS)]
        out: list[Landmark] = []
        for lm in landmarks[:NUM_HAND_LANDMARKS]:
            out.append(
                Landmark(
                    x=lm.x,
                    y=lm.y,
                    z=getattr(lm, "z", 0.0),
                    visibility=getattr(lm, "visibility", 1.0),
                    presence=getattr(lm, "presence", 1.0),
                )
            )
        while len(out) < NUM_HAND_LANDMARKS:
            out.append(Landmark(0, 0, 0, 0, 0))
        return out

    @staticmethod
    def _parse_face_grammar(landmarks) -> list[Landmark]:
        if not landmarks:
            return []
        all_lm = landmarks
        selected = []
        for idx in FACE_GRAMMAR_INDICES:
            if idx < len(all_lm):
                lm = all_lm[idx]
                selected.append(
                    Landmark(
                        x=lm.x,
                        y=lm.y,
                        z=getattr(lm, "z", 0.0),
                        visibility=getattr(lm, "visibility", 1.0),
                        presence=getattr(lm, "presence", 1.0),
                    )
                )
        return selected

    @staticmethod
    def _parse_body(landmarks) -> list[Landmark]:
        if not landmarks:
            return []
        return [
            Landmark(
                x=lm.x,
                y=lm.y,
                z=getattr(lm, "z", 0.0),
                visibility=getattr(lm, "visibility", 1.0),
                presence=getattr(lm, "presence", 1.0),
            )
            for lm in landmarks
        ]


def _default_model_path() -> str:
    """Return bundled model path or download hint."""
    bundled = Path(__file__).parent / "models" / "holistic_landmarker.task"
    if bundled.exists():
        return str(bundled)
    raise FileNotFoundError(
        "Holistic landmarker model not found. Download holistic_landmarker.task "
        "from https://ai.google.dev/edge/mediapipe/solutions/vision/holistic_landmarker "
        f"and place at {bundled}"
    )


def extract_pose_from_video_bytes(
    video_b64: str,
    clip_id: str,
    stage: int,
    extractor: Optional[PoseExtractor] = None,
) -> PoseSubmission:
    """Decode base64 MP4 and run pose extraction."""
    raw = base64.b64decode(video_b64)
    ext = extractor or PoseExtractor()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        tmp.write(raw)
        tmp.flush()
        return ext.extract_from_path(tmp.name, clip_id, stage)


def synthetic_pose_submission(
    clip_id: str, stage: int, num_frames: int = 30
) -> PoseSubmission:
    """Deterministic pose sequence for tests without MediaPipe."""
    frames: list[FramePose] = []
    for i in range(num_frames):
        t = i / max(num_frames - 1, 1)
        hand = [
            Landmark(x=t, y=0.5, z=0.0, visibility=0.9, presence=0.85)
            for _ in range(NUM_HAND_LANDMARKS)
        ]
        face = [
            Landmark(x=0.5, y=0.3, z=0.0, visibility=0.8, presence=0.8)
            for _ in range(6)
        ]
        frames.append(
            FramePose(
                timestamp_ms=float(i * 33),
                left_hand=hand,
                right_hand=hand,
                face_grammar=face,
                body_pose=[],
                mean_hand_confidence=0.85,
            )
        )
    return PoseSubmission(
        clip_id=clip_id,
        stage=stage,
        frames=frames,
        miner_confidence=0.85,
        pipeline="synthetic",
    )
