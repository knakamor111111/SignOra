"""Known-plaintext challenge cryptography."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet


def script_commit_hash(script: str, block_hash: str = "") -> str:
    payload = f"{script.strip()}|{block_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def derive_fernet_key(master_secret: str, clip_id: str) -> bytes:
    raw = hashlib.sha256(f"{master_secret}|{clip_id}".encode()).digest()
    return base64.urlsafe_b64encode(raw)


@dataclass
class EncryptedScript:
    clip_id: str
    script_commit: str
    ciphertext_b64: str

    def to_dict(self) -> dict:
        return {
            "clip_id": self.clip_id,
            "script_commit": self.script_commit,
            "ciphertext_b64": self.ciphertext_b64,
        }


class ScriptVault:
    """Encrypt signing scripts at capture time; reveal only after DBCP window."""

    def __init__(self, master_secret: str | None = None) -> None:
        secret = master_secret or os.getenv("SIGNORA_CHALLENGE_SECRET", "")
        if not secret:
            secret = "signora-dev-secret-change-me"
        self.master_secret = secret

    def encrypt(self, clip_id: str, script: str, block_hash: str = "") -> EncryptedScript:
        key = derive_fernet_key(self.master_secret, clip_id)
        f = Fernet(key)
        token = f.encrypt(script.encode("utf-8"))
        return EncryptedScript(
            clip_id=clip_id,
            script_commit=script_commit_hash(script, block_hash),
            ciphertext_b64=base64.b64encode(token).decode("ascii"),
        )

    def decrypt(self, clip_id: str, ciphertext_b64: str) -> str:
        key = derive_fernet_key(self.master_secret, clip_id)
        f = Fernet(key)
        raw = base64.b64decode(ciphertext_b64)
        return f.decrypt(raw).decode("utf-8")

    def verify_reveal(
        self, clip_id: str, script: str, expected_commit: str, block_hash: str = ""
    ) -> bool:
        return script_commit_hash(script, block_hash) == expected_commit
