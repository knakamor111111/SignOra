"""Reference pose ensemble for validator scoring."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterable

import numpy as np

from signora.core.types import FramePose, Landmark, PoseSubmission
from signora.pose.backends.base import PoseBackend
from signora.pose.backends.dwpose_onnx import DwposeOnnxBackend
from signora.pose.backends.mediapipe_backend import MediaPipeBackend
from signora.pose.backends.optical_flow import OpticalFlowBackend
from signora.pose.extractor import synthetic_pose_submission


class ReferenceEnsemble:
    """
    Run multiple pose backends and fuse into a single reference submission.

    Fusion: per-frame median of available backend landmarks (Score SN44 pattern).
    """

    def __init__(self, backends: Iterable[PoseBackend] | None = None) -> None:
        if backends is None:
            backends = [
                MediaPipeBackend(),
                OpticalFlowBackend(),
                DwposeOnnxBackend(models_dir="./models"),
            ]
        self.backends = [b for b in backends if b.available()]
        if not self.backends:
            self.backends = []

    @property
    def pipeline_names(self) -> list[str]:
        return [b.name for b in self.backends]

    def extract_from_path(
        self, video_path: str | Path, clip_id: str, stage: int
    ) -> PoseSubmission:
        submissions: list[PoseSubmission] = []
        for backend in self.backends:
            try:
                submissions.append(
                    backend.extract_from_path(str(video_path), clip_id, stage)
                )
            except Exception:
                continue

        if not submissions:
            return synthetic_pose_submission(clip_id, stage)

        if len(submissions) == 1:
            fused = submissions[0]
            fused.pipeline = f"ensemble:{submissions[0].pipeline}"
            return fused

        return self._fuse(submissions, clip_id, stage)

    def extract_from_video_bytes(
        self, video_b64: str, clip_id: str, stage: int
    ) -> PoseSubmission:
        import base64

        raw = base64.b64decode(video_b64)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
            tmp.write(raw)
            tmp.flush()
            return self.extract_from_path(tmp.name, clip_id, stage)

    def _fuse(
        self, submissions: list[PoseSubmission], clip_id: str, stage: int
    ) -> PoseSubmission:
        n_frames = max(len(s.frames) for s in submissions)
        fused_frames: list[FramePose] = []

        for i in range(n_frames):
            left_sets = []
            right_sets = []
            face_sets = []
            timestamps = []
            confs = []

            for sub in submissions:
                if i >= len(sub.frames):
                    continue
                fr = sub.frames[i]
                left_sets.append(fr.left_hand)
                right_sets.append(fr.right_hand)
                face_sets.append(fr.face_grammar)
                timestamps.append(fr.timestamp_ms)
                confs.append(fr.mean_hand_confidence)

            fused_frames.append(
                FramePose(
                    timestamp_ms=float(np.median(timestamps)) if timestamps else 0.0,
                    left_hand=self._median_landmarks(left_sets),
                    right_hand=self._median_landmarks(right_sets),
                    face_grammar=self._median_landmarks(face_sets),
                    body_pose=[],
                    mean_hand_confidence=float(np.mean(confs)) if confs else 0.0,
                )
            )

        names = "+".join(s.pipeline for s in submissions)
        return PoseSubmission(
            clip_id=clip_id,
            stage=stage,
            frames=fused_frames,
            miner_confidence=float(np.mean([s.miner_confidence for s in submissions])),
            pipeline=f"ensemble:{names}",
        )

    @staticmethod
    def _median_landmarks(hand_sets: list[list[Landmark]]) -> list[Landmark]:
        if not hand_sets:
            return []
        max_len = max(len(h) for h in hand_sets)
        out: list[Landmark] = []
        for idx in range(max_len):
            xs, ys, zs, vis, pres = [], [], [], [], []
            for hand in hand_sets:
                if idx < len(hand):
                    lm = hand[idx]
                    if lm.visibility > 0.1:
                        xs.append(lm.x)
                        ys.append(lm.y)
                        zs.append(lm.z)
                        vis.append(lm.visibility)
                        pres.append(lm.presence)
            if xs:
                out.append(
                    Landmark(
                        x=float(np.median(xs)),
                        y=float(np.median(ys)),
                        z=float(np.median(zs)),
                        visibility=float(np.median(vis)),
                        presence=float(np.median(pres)),
                    )
                )
        return out
