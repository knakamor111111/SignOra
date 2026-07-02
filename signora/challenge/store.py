"""Challenge clip + encrypted script persistence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChallengeRecord:
    clip_id: str
    stage: int
    video_path: str
    script_commit: str
    ciphertext_b64: str
    revealed_script: str | None = None
    block_hash: str = ""


class ChallengeStore:
    def __init__(self, db_path: str = "./data/challenges/challenges.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS challenges (
                    clip_id TEXT PRIMARY KEY,
                    stage INTEGER NOT NULL,
                    video_path TEXT NOT NULL,
                    script_commit TEXT NOT NULL,
                    ciphertext_b64 TEXT NOT NULL,
                    revealed_script TEXT,
                    block_hash TEXT DEFAULT ''
                )
                """
            )

    def ingest(
        self,
        clip_id: str,
        stage: int,
        video_path: str,
        script_commit: str,
        ciphertext_b64: str,
        block_hash: str = "",
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO challenges
                (clip_id, stage, video_path, script_commit, ciphertext_b64, block_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (clip_id, stage, video_path, script_commit, ciphertext_b64, block_hash),
            )

    def list_unrevealed(self, limit: int = 50) -> list[ChallengeRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT clip_id, stage, video_path, script_commit, ciphertext_b64,
                       revealed_script, block_hash
                FROM challenges
                WHERE revealed_script IS NULL
                ORDER BY clip_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [ChallengeRecord(*row) for row in rows]

    def reveal_script(self, clip_id: str, script: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE challenges SET revealed_script = ? WHERE clip_id = ?",
                (script, clip_id),
            )

    def get(self, clip_id: str) -> ChallengeRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT clip_id, stage, video_path, script_commit, ciphertext_b64,
                       revealed_script, block_hash
                FROM challenges WHERE clip_id = ?
                """,
                (clip_id,),
            ).fetchone()
        return ChallengeRecord(*row) if row else None

    def export_manifest(self, path: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT clip_id, stage, script_commit, block_hash FROM challenges"
            ).fetchall()
        Path(path).write_text(
            json.dumps(
                [
                    {
                        "clip_id": r[0],
                        "stage": r[1],
                        "script_commit": r[2],
                        "block_hash": r[3],
                    }
                    for r in rows
                ],
                indent=2,
            )
        )
