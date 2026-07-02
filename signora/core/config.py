"""Runtime configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SignoraConfig:
    netuid: int = 0
    subtensor_network: str = "finney"
    subtensor_chain_endpoint: Optional[str] = None
    axon_port: int = 8091
    axon_external_ip: str = "127.0.0.1"
    validator_sample_size: int = 16
    weight_commit_reveal: bool = True
    dbcp_reveal_delay_blocks: int = 3
    challenge_video_dir: str = "./data/challenges"
    reference_pose_dir: str = "./data/reference_poses"
    model_dir: str = "./models"
    phase: str = "launch"

    @classmethod
    def from_env(cls) -> SignoraConfig:
        return cls(
            netuid=int(os.getenv("NETUID", "0")),
            subtensor_network=os.getenv("SUBTENSOR_NETWORK", "finney"),
            subtensor_chain_endpoint=os.getenv("SUBTENSOR_CHAIN_ENDPOINT"),
            axon_port=int(os.getenv("AXON_PORT", "8091")),
            axon_external_ip=os.getenv("AXON_EXTERNAL_IP", "127.0.0.1"),
            validator_sample_size=int(os.getenv("VALIDATOR_SAMPLE_SIZE", "16")),
            weight_commit_reveal=os.getenv("WEIGHT_COMMIT_REVEAL", "true").lower()
            == "true",
            dbcp_reveal_delay_blocks=int(os.getenv("DBCP_REVEAL_DELAY_BLOCKS", "3")),
            challenge_video_dir=os.getenv("CHALLENGE_VIDEO_DIR", "./data/challenges"),
            reference_pose_dir=os.getenv("POSE_REFERENCE_DIR", "./data/reference_poses"),
            model_dir=os.getenv("MODEL_DIR", "./models"),
            phase=os.getenv("SIGNORA_PHASE", "launch"),
        )
