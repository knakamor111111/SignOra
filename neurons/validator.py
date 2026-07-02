#!/usr/bin/env python3
"""SignOra validator — challenge issuance, DBCP, scoring, weight setting."""

from __future__ import annotations

import asyncio
import base64
import json
import random
import time
import traceback
from pathlib import Path

import bittensor as bt

from neurons.base import base_config, get_current_block_hash
from signora.challenge.crypto import ScriptVault
from signora.challenge.store import ChallengeStore
from signora.core.types import PoseSubmission
from signora.dbcp.protocol import DBCPSession
from signora.pose.ensemble import ReferenceEnsemble
from signora.pose.extractor import synthetic_pose_submission
from signora.pose.gate import PoseQualityGate
from signora.protocol.synapses import PoseChallengeSynapse, TranslationChallengeSynapse
from signora.validation.comp_a import score_pose_submission
from signora.validation.comp_b import score_translation
from signora.validation.weight_committer import WeightCommitter
from signora.validation.weights import build_mechanism_weights


class Validator:
    EPOCH_LENGTH = 12

    def __init__(self, config: bt.Config) -> None:
        self.config = config
        self.wallet = bt.wallet(config=config)
        self.subtensor = bt.subtensor(config=config)
        self.metagraph = self.subtensor.metagraph(config.netuid)
        self.dendrite = bt.dendrite(wallet=self.wallet)
        self.gate = PoseQualityGate()
        self.reference_ensemble = ReferenceEnsemble()
        self.challenge_dir = Path("./data/challenges")
        self.challenge_store = ChallengeStore(str(self.challenge_dir / "challenges.db"))
        self.script_vault = ScriptVault()
        self.reference_dir = Path("./data/reference_poses")
        self.dbcp = DBCPSession(tempo=0, block_hash="")
        self.weight_committer = WeightCommitter(
            subtensor=self.subtensor,
            wallet=self.wallet,
            netuid=config.netuid,
            use_timelock=getattr(config.signora, "weight_timelock", True),
        )
        bt.logging.info(
            f"Reference ensemble backends: {self.reference_ensemble.pipeline_names}"
        )

    def _load_challenge_clip(self, clip_path: Path) -> tuple[str, str, int]:
        clip_id = clip_path.stem
        stage = 1
        if "_s" in clip_id:
            try:
                stage = int(clip_id.split("_s")[-1])
            except ValueError:
                stage = 1
        video_b64 = base64.b64encode(clip_path.read_bytes()).decode("ascii")
        return clip_id, video_b64, stage

    def _ground_truth(self, clip_id: str) -> str:
        record = self.challenge_store.get(clip_id)
        if record and record.revealed_script:
            return record.revealed_script
        if record:
            try:
                script = self.script_vault.decrypt(clip_id, record.ciphertext_b64)
                if self.script_vault.verify_reveal(
                    clip_id, script, record.script_commit, record.block_hash
                ):
                    return script
            except Exception:
                pass
        return f"placeholder_gt_{clip_id}"

    def _build_reference(self, clip_path: Path, clip_id: str, stage: int) -> PoseSubmission:
        ref_path = self.reference_dir / f"{clip_id}.json"
        if ref_path.exists():
            return PoseSubmission.from_dict(json.loads(ref_path.read_text()))
        try:
            return self.reference_ensemble.extract_from_path(clip_path, clip_id, stage)
        except Exception:
            return synthetic_pose_submission(clip_id, stage)

    def _sample_miner_uids(self, k: int = 16) -> list[int]:
        n = self.metagraph.n
        if n == 0:
            return []
        return random.sample(list(range(n)), min(k, n))

    async def run_epoch(self, tempo: int) -> None:
        block_hash = get_current_block_hash(self.subtensor)
        self.dbcp = DBCPSession(tempo=tempo, block_hash=block_hash)

        clips = list(self.challenge_dir.glob("*.mp4")) if self.challenge_dir.exists() else []
        if not clips:
            bt.logging.warning("No challenge clips in data/challenges — skipping epoch.")
            return

        clip_ids: list[str] = []
        references: dict[str, str] = {}
        pose_scores: dict[int, float] = {}
        translation_scores: dict[int, float] = {}

        miner_uids = self._sample_miner_uids(self.config.signora.validator_sample_size)
        if not miner_uids:
            bt.logging.warning("No miners in metagraph.")
            return

        for clip_path in clips[:5]:
            clip_id, video_b64, stage = self._load_challenge_clip(clip_path)
            clip_ids.append(clip_id)
            reference = self._build_reference(clip_path, clip_id, stage)
            references[clip_id] = self._ground_truth(clip_id)

            pose_synapse = PoseChallengeSynapse(
                clip_id=clip_id,
                stage=stage,
                video_b64=video_b64,
                tempo=tempo,
                block_hash=block_hash,
            )

            axons = [self.metagraph.axons[uid] for uid in miner_uids]
            responses = await self.dendrite.forward(
                axons=axons,
                synapse=pose_synapse,
                timeout=60,
            )

            for uid, response in zip(miner_uids, responses):
                if not response or not response.pose_submission:
                    continue
                miner_pose = PoseSubmission.from_dict(response.pose_submission)
                result = score_pose_submission(miner_pose, reference, self.gate)
                pose_scores[uid] = pose_scores.get(uid, 0.0) + result.comp_a_score

                if not result.forwarded_to_comp_b:
                    continue

                trans_synapse = TranslationChallengeSynapse(
                    clip_id=clip_id,
                    stage=stage,
                    pose_sequence=miner_pose.to_dict(),
                    gate=result.gate.to_dict(),
                    tempo=tempo,
                )
                trans_resp = await self.dendrite.forward(
                    axons=[self.metagraph.axons[uid]],
                    synapse=trans_synapse,
                    timeout=30,
                )
                if trans_resp and trans_resp[0]:
                    tr = trans_resp[0]
                    t_score = score_translation(
                        tr.translation,
                        references[clip_id],
                        stage,
                        tr.confidence,
                    )
                    translation_scores[uid] = translation_scores.get(uid, 0.0) + t_score

        vc, v_commit = self.dbcp.build_validator_commit(clip_ids, references)
        bt.logging.info(f"DBCP V_commit={v_commit}")

        uids = list(set(pose_scores) | set(translation_scores))
        mech_weights = build_mechanism_weights(uids, pose_scores, translation_scores)
        self.weight_committer.submit_all(mech_weights)

        reveal = {
            "clip_ids": vc.clip_ids,
            "reference_answers": vc.reference_answers,
            "salt": vc.salt,
            "block_hash": vc.block_hash,
            "tempo": vc.tempo,
        }
        ok = self.dbcp.verify_reveal("validator", reveal, v_commit)
        bt.logging.info(f"DBCP validator reveal verified={ok}")

    def run(self) -> None:
        bt.logging.info("SignOra validator running.")
        tempo = 0
        try:
            while True:
                self.metagraph.sync(subtensor=self.subtensor)
                tempo += 1
                asyncio.run(self.run_epoch(tempo))
                time.sleep(self.EPOCH_LENGTH)
        except KeyboardInterrupt:
            bt.logging.info("Validator stopped.")


def main() -> None:
    config = base_config("validator")
    bt.logging(config=config, logging_dir=config.full_path)
    Validator(config).run()


if __name__ == "__main__":
    main()
