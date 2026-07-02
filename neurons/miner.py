#!/usr/bin/env python3
"""SignOra miner — Competition A (pose) + Competition B (translation)."""

from __future__ import annotations

import traceback

import bittensor as bt

from neurons.base import base_config, get_current_block_hash
from signora.dbcp.protocol import MinerCommit
from signora.pose.extractor import (
    PoseExtractor,
    extract_pose_from_video_bytes,
    synthetic_pose_submission,
)
from signora.protocol.synapses import PoseChallengeSynapse, TranslationChallengeSynapse
from signora.translation.sequence_model import PoseSequenceTranslator


class Miner:
    def __init__(self, config: bt.Config) -> None:
        self.config = config
        self.wallet = bt.wallet(config=config)
        self.subtensor = bt.subtensor(config=config)
        self.metagraph = self.subtensor.metagraph(config.netuid)

        self.pose_extractor: PoseExtractor | None = None
        try:
            self.pose_extractor = PoseExtractor()
        except (RuntimeError, FileNotFoundError) as exc:
            bt.logging.warning(f"PoseExtractor unavailable: {exc}. Using synthetic fallback.")

        self.translator = PoseSequenceTranslator(model_dir=config.signora.model_dir)

        self.axon = bt.axon(wallet=self.wallet, config=config)
        self.axon.attach(forward_fn=self.forward_pose, blacklist_fn=self.blacklist)
        self.axon.attach(forward_fn=self.forward_translation, blacklist_fn=self.blacklist)
        self.axon.serve(netuid=config.netuid, subtensor=self.subtensor)
        self.axon.start()

    async def blacklist(self, synapse: bt.Synapse) -> bool:
        return False

    async def forward_pose(self, synapse: PoseChallengeSynapse) -> PoseChallengeSynapse:
        try:
            if self.pose_extractor and synapse.video_b64:
                submission = extract_pose_from_video_bytes(
                    synapse.video_b64,
                    synapse.clip_id,
                    synapse.stage,
                    self.pose_extractor,
                )
            else:
                submission = synthetic_pose_submission(synapse.clip_id, synapse.stage)

            synapse.pose_submission = submission.to_dict()

            block_hash = synapse.block_hash or get_current_block_hash(self.subtensor)
            uid = (
                self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
                if self.wallet.hotkey.ss58_address in self.metagraph.hotkeys
                else 0
            )
            mc = MinerCommit(
                translations={synapse.clip_id: submission.pipeline},
                nonce=submission.clip_id,
                block_hash=block_hash,
                tempo=synapse.tempo,
                uid=uid,
            )
            synapse.m_commit = mc.commit_hash()
        except Exception:
            bt.logging.error(traceback.format_exc())
        return synapse

    async def forward_translation(
        self, synapse: TranslationChallengeSynapse
    ) -> TranslationChallengeSynapse:
        try:
            from signora.core.types import PoseSubmission

            pose = PoseSubmission.from_dict(synapse.pose_sequence or {})
            text, conf = self.translator.translate(pose, synapse.clip_id)
            synapse.translation = text
            synapse.confidence = conf

            block_hash = get_current_block_hash(self.subtensor)
            mc = MinerCommit(
                translations={synapse.clip_id: text},
                nonce=synapse.clip_id,
                block_hash=block_hash,
                tempo=synapse.tempo,
                uid=0,
            )
            synapse.m_commit = mc.commit_hash()
        except Exception:
            bt.logging.error(traceback.format_exc())
        return synapse

    def run(self) -> None:
        bt.logging.info("SignOra miner running. Press Ctrl+C to stop.")
        try:
            while True:
                self.metagraph.sync(subtensor=self.subtensor)
                bt.logging.info(f"Block {self.subtensor.get_current_block()}")
                bt.logging.info("Waiting for validator challenges...")
                import time

                time.sleep(12)
        except KeyboardInterrupt:
            bt.logging.info("Shutting down miner.")
            self.axon.stop()


def main() -> None:
    config = base_config("miner")
    bt.logging(config=config, logging_dir=config.full_path)
    Miner(config).run()


if __name__ == "__main__":
    main()
