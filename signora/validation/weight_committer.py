"""Commit-reveal and CRv3 timelocked weight submission."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import bittensor as bt
from bittensor.core.extrinsics.weights import (
    commit_timelocked_weights_extrinsic,
    commit_weights_extrinsic,
    reveal_weights_extrinsic,
)
from bittensor.core.settings import version_as_int


@dataclass
class PendingWeightCommit:
    mech_id: int
    uids: list[int]
    weights: list[float]
    salt: list[int]
    mode: str  # "commit_reveal" | "timelocked" | "direct"


class WeightCommitter:
    """
    Submit validator weights via commit-reveal or CRv3 timelock when enabled.

    Falls back to direct set_mechanism_weights on subnets without commit-reveal.
    """

    def __init__(
        self,
        subtensor: bt.Subtensor,
        wallet: bt.Wallet,
        netuid: int,
        state_path: str = "./data/weight_commits.json",
        use_timelock: bool = True,
        block_time: float = 12.0,
    ) -> None:
        self.subtensor = subtensor
        self.wallet = wallet
        self.netuid = netuid
        self.state_path = Path(state_path)
        self.use_timelock = use_timelock
        self.block_time = block_time
        self._pending: list[PendingWeightCommit] = self._load_pending()

    def _load_pending(self) -> list[PendingWeightCommit]:
        if not self.state_path.exists():
            return []
        raw = json.loads(self.state_path.read_text())
        return [PendingWeightCommit(**item) for item in raw]

    def _save_pending(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.__dict__ for item in self._pending]
        self.state_path.write_text(json.dumps(payload, indent=2))

    def _hyperparams(self):
        return self.subtensor.get_subnet_hyperparameters(self.netuid)

    def commit_mechanism(
        self, mech_id: int, weights: list[tuple[int, float]]
    ) -> bool:
        if not weights:
            return True

        uids = [u for u, _ in weights]
        vals = [w for _, w in weights]
        hp = self._hyperparams()

        if hp.commit_reveal_weights_enabled and self.use_timelock:
            resp = commit_timelocked_weights_extrinsic(
                subtensor=self.subtensor,
                wallet=self.wallet,
                netuid=self.netuid,
                mechid=mech_id,
                uids=uids,
                weights=vals,
                block_time=self.block_time,
                wait_for_inclusion=False,
                wait_for_finalization=False,
                mev_protection=False,
            )
            bt.logging.info(f"Timelocked weight commit mech={mech_id}: {resp.message}")
            return resp.success

        if hp.commit_reveal_weights_enabled:
            salt = [random.randint(0, 2**16 - 1) for _ in range(8)]
            resp = commit_weights_extrinsic(
                subtensor=self.subtensor,
                wallet=self.wallet,
                netuid=self.netuid,
                mechid=mech_id,
                uids=uids,
                weights=vals,
                salt=salt,
                wait_for_inclusion=False,
                wait_for_finalization=False,
                mev_protection=False,
            )
            if resp.success:
                self._pending.append(
                    PendingWeightCommit(mech_id, uids, vals, salt, "commit_reveal")
                )
                self._save_pending()
            bt.logging.info(f"Weight commit mech={mech_id}: {resp.message}")
            return resp.success

        return self._set_direct(mech_id, uids, vals)

    def reveal_pending(self) -> None:
        hp = self._hyperparams()
        if not hp.commit_reveal_weights_enabled:
            return

        remaining: list[PendingWeightCommit] = []
        for item in self._pending:
            if item.mode != "commit_reveal":
                remaining.append(item)
                continue
            resp = reveal_weights_extrinsic(
                subtensor=self.subtensor,
                wallet=self.wallet,
                netuid=self.netuid,
                mechid=item.mech_id,
                uids=item.uids,
                weights=item.weights,
                salt=item.salt,
                version_key=version_as_int,
                wait_for_inclusion=False,
                wait_for_finalization=False,
                mev_protection=False,
            )
            bt.logging.info(
                f"Weight reveal mech={item.mech_id}: success={resp.success} {resp.message}"
            )
            if not resp.success:
                remaining.append(item)
        self._pending = remaining
        self._save_pending()

    def _set_direct(self, mech_id: int, uids: list[int], vals: list[float]) -> bool:
        try:
            self.subtensor.set_weights(
                wallet=self.wallet,
                netuid=self.netuid,
                uids=uids,
                weights=vals,
                mechid=mech_id,
                wait_for_inclusion=False,
                wait_for_finalization=False,
            )
            return True
        except Exception as exc:
            bt.logging.error(f"Direct set_weights failed: {exc}")
            return False

    def submit_all(
        self, mech_weights: dict[int, list[tuple[int, float]]]
    ) -> None:
        """Reveal prior epoch commits, then commit current weights."""
        self.reveal_pending()
        for mech_id, weights in mech_weights.items():
            self.commit_mechanism(mech_id, weights)
