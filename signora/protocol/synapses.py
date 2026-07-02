"""Bittensor synapse definitions for SignOra competitions."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from bittensor.core.synapse import Synapse


class PoseChallengeSynapse(Synapse):
    """Competition A: video in → pose JSON out."""

    clip_id: str = Field(default="", description="Unique challenge clip identifier")
    stage: int = Field(default=1, ge=1, le=4, description="Curriculum stage 1-4")
    video_b64: str = Field(default="", description="Base64-encoded MP4 clip")
    tempo: int = Field(default=0, description="Subnet tempo / epoch id")
    block_hash: str = Field(default="", description="Block hash at challenge issue")

    pose_submission: Optional[dict[str, Any]] = Field(
        default=None, description="Comp A structured pose JSON"
    )
    m_commit: str = Field(default="", description="Miner commit hash (DBCP)")


class TranslationChallengeSynapse(Synapse):
    """Competition B: gate-passed pose sequence in → English text out."""

    clip_id: str = Field(default="")
    stage: int = Field(default=1, ge=1, le=4)
    pose_sequence: Optional[dict[str, Any]] = Field(
        default=None, description="Gate-passed skeletal JSON from Comp A"
    )
    gate: Optional[dict[str, Any]] = Field(
        default=None, description="Pose gate audit record"
    )
    tempo: int = Field(default=0)

    translation: str = Field(default="", description="English translation")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    m_commit: str = Field(default="")


class CorpusMiningSynapse(Synapse):
    """Phase 1b: attested Signer submits signed video + pose for corpus."""

    script_id: str = Field(default="")
    stage: int = Field(default=1, ge=1, le=4)
    video_b64: str = Field(default="")
    pose_submission: Optional[dict[str, Any]] = Field(default=None)
    script_commit: str = Field(default="", description="Pre-recording script hash")
    m_commit: str = Field(default="")
