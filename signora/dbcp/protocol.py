"""Dual-Blind Commitment Protocol (DBCP)."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from typing import Any


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def rotate_salt(salt: str, block_hash: str) -> str:
    return sha256_hex(f"{salt}|{block_hash}")


@dataclass
class ValidatorCommit:
    clip_ids: list[str]
    reference_answers: dict[str, str]
    salt: str
    block_hash: str
    tempo: int

    def commit_hash(self) -> str:
        payload = json.dumps(
            {
                "clip_ids": self.clip_ids,
                "reference_answers": self.reference_answers,
                "salt": self.salt,
                "block_hash": self.block_hash,
                "tempo": self.tempo,
            },
            sort_keys=True,
        )
        return sha256_hex(payload)


@dataclass
class MinerCommit:
    translations: dict[str, str]
    nonce: str
    block_hash: str
    tempo: int
    uid: int

    def commit_hash(self) -> str:
        payload = json.dumps(
            {
                "translations": self.translations,
                "nonce": self.nonce,
                "block_hash": self.block_hash,
                "tempo": self.tempo,
                "uid": self.uid,
            },
            sort_keys=True,
        )
        return sha256_hex(payload)


@dataclass
class DBCPSession:
    """In-memory DBCP state for one tempo."""

    tempo: int
    block_hash: str
    salt: str = field(default_factory=lambda: secrets.token_hex(32))
    v_commit: str = ""
    m_commits: dict[int, str] = field(default_factory=dict)
    revealed: bool = False

    def build_validator_commit(
        self, clip_ids: list[str], reference_answers: dict[str, str]
    ) -> tuple[ValidatorCommit, str]:
        vc = ValidatorCommit(
            clip_ids=clip_ids,
            reference_answers=reference_answers,
            salt=self.salt,
            block_hash=self.block_hash,
            tempo=self.tempo,
        )
        commit = vc.commit_hash()
        self.v_commit = commit
        return vc, commit

    def build_miner_commit(
        self,
        uid: int,
        translations: dict[str, str],
        nonce: str | None = None,
    ) -> tuple[MinerCommit, str]:
        mc = MinerCommit(
            translations=translations,
            nonce=nonce or secrets.token_hex(16),
            block_hash=self.block_hash,
            tempo=self.tempo,
            uid=uid,
        )
        commit = mc.commit_hash()
        self.m_commits[uid] = commit
        return mc, commit

    def verify_reveal(
        self,
        party: str,
        revealed_data: dict[str, Any],
        expected_commit: str,
    ) -> bool:
        if party == "validator":
            vc = ValidatorCommit(
                clip_ids=revealed_data["clip_ids"],
                reference_answers=revealed_data["reference_answers"],
                salt=revealed_data["salt"],
                block_hash=revealed_data["block_hash"],
                tempo=revealed_data["tempo"],
            )
            return vc.commit_hash() == expected_commit

        if party == "miner":
            mc = MinerCommit(
                translations=revealed_data["translations"],
                nonce=revealed_data["nonce"],
                block_hash=revealed_data["block_hash"],
                tempo=revealed_data["tempo"],
                uid=int(revealed_data["uid"]),
            )
            return mc.commit_hash() == expected_commit

        raise ValueError(f"Unknown party: {party}")

    def advance_salt(self, next_block_hash: str) -> None:
        self.salt = rotate_salt(self.salt, next_block_hash)
        self.block_hash = next_block_hash
