"""HTTP challenge server for known-plaintext capture workflow."""

from __future__ import annotations

import base64
import shutil
from pathlib import Path

from signora.challenge.crypto import ScriptVault
from signora.challenge.store import ChallengeStore

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field

    _FASTAPI = True
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore
    _FASTAPI = False


class IngestRequest(BaseModel):
    clip_id: str
    stage: int = Field(ge=1, le=4)
    script: str
    video_b64: str
    block_hash: str = ""


class RevealRequest(BaseModel):
    clip_id: str


def create_app(
    data_dir: str = "./data/challenges",
    master_secret: str | None = None,
) -> "FastAPI":
    if not _FASTAPI:
        raise RuntimeError("Install fastapi: pip install signora[server]")

    app = FastAPI(title="SignOra Challenge Server", version="0.7.0")
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    store = ChallengeStore(str(root / "challenges.db"))
    vault = ScriptVault(master_secret)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/ingest")
    def ingest(req: IngestRequest):
        encrypted = vault.encrypt(req.clip_id, req.script, req.block_hash)
        video_path = root / f"{req.clip_id}.mp4"
        video_path.write_bytes(base64.b64decode(req.video_b64))
        store.ingest(
            clip_id=req.clip_id,
            stage=req.stage,
            video_path=str(video_path),
            script_commit=encrypted.script_commit,
            ciphertext_b64=encrypted.ciphertext_b64,
            block_hash=req.block_hash,
        )
        return {
            "clip_id": req.clip_id,
            "script_commit": encrypted.script_commit,
            "video_path": str(video_path),
        }

    @app.get("/challenges")
    def list_challenges(limit: int = 20):
        records = store.list_unrevealed(limit=limit)
        return [
            {
                "clip_id": r.clip_id,
                "stage": r.stage,
                "video_path": r.video_path,
                "script_commit": r.script_commit,
                "block_hash": r.block_hash,
            }
            for r in records
        ]

    @app.post("/reveal")
    def reveal(req: RevealRequest):
        record = store.get(req.clip_id)
        if not record:
            raise HTTPException(status_code=404, detail="clip not found")
        script = vault.decrypt(record.clip_id, record.ciphertext_b64)
        if not vault.verify_reveal(
            record.clip_id, script, record.script_commit, record.block_hash
        ):
            raise HTTPException(status_code=400, detail="commit mismatch on reveal")
        store.reveal_script(record.clip_id, script)
        return {"clip_id": record.clip_id, "script": script}

    @app.get("/manifest")
    def manifest():
        manifest_path = root / "manifest.json"
        store.export_manifest(str(manifest_path))
        return manifest_path.read_text()

    return app
