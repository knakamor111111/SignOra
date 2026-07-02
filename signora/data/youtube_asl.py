"""YouTube-ASL manifest helpers (metadata-only bootstrap)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_youtube_asl_manifest(path: Path) -> list[dict[str, Any]]:
    """
    Load a YouTube-ASL-style manifest.

    Expected format (JSON list):
      [{"video_id": "...", "text": "english sentence", "asl_gloss": "...", "path": "optional.mp4"}]
    """
    return json.loads(path.read_text())


def manifest_to_pairs(
    rows: list[dict[str, Any]],
    pose_builder,
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for row in rows:
        clip_id = row.get("video_id") or row.get("id", "yt")
        text = row.get("text") or row.get("english", "")
        if not text:
            continue
        pose = pose_builder(clip_id, row)
        pairs.append({"pose": pose.to_dict(), "text": text})
    return pairs
