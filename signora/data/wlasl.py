"""WLASL metadata loading and gloss normalization."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.request import urlopen

WLASL_JSON_URL = (
    "https://raw.githubusercontent.com/dxli94/WLASL/master/start_kit/WLASL_v0.3.json"
)


def fetch_wlasl_json(cache_path: Path | None = None) -> list[dict[str, Any]]:
    if cache_path and cache_path.exists():
        return json.loads(cache_path.read_text())

    with urlopen(WLASL_JSON_URL, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2))
    return data


def gloss_to_english(gloss: str) -> str:
    """WLASL gloss token → readable English (underscores → spaces)."""
    text = gloss.replace("_", " ").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def iter_instances(
    wlasl_data: list[dict[str, Any]],
    subset: str = "WLASL100",
    split: str | None = "train",
) -> list[dict[str, Any]]:
    """Flatten WLASL JSON to per-video instances."""
    gloss_limit = 2000
    if subset.startswith("WLASL") and subset != "WLASL":
        try:
            gloss_limit = int(subset.replace("WLASL", ""))
        except ValueError:
            gloss_limit = 2000

    out: list[dict[str, Any]] = []
    for entry in wlasl_data[:gloss_limit]:
        gloss = entry.get("gloss", "")
        instances = entry.get("instances", [])
        for inst in instances:
            if split and inst.get("split") != split:
                continue
            out.append(
                {
                    "gloss": gloss,
                    "text": gloss_to_english(gloss),
                    "video_id": inst.get("video_id"),
                    "url": inst.get("url", ""),
                    "split": inst.get("split"),
                    "signer_id": inst.get("signer_id"),
                    "frame_start": inst.get("frame_start"),
                    "frame_end": inst.get("frame_end"),
                }
            )
    return out


def is_direct_video_url(url: str) -> bool:
    if not url:
        return False
    lower = url.lower()
    if "youtube.com" in lower or "youtu.be" in lower:
        return False
    return lower.endswith((".mp4", ".mov", ".webm", ".mkv")) or "mp4" in lower
