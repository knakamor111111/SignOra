#!/usr/bin/env python3
"""
Prepare WLASL training pairs for train_translator.py.

Downloads WLASL metadata, optionally fetches direct (non-YouTube) MP4 clips,
extracts pose with OpticalFlowBackend (no MediaPipe model file required),
and writes data/training/wlasl_pairs.json.

Usage:
  python scripts/prepare_wlasl_dataset.py --max-samples 50
  python scripts/prepare_wlasl_dataset.py --metadata-only --max-samples 500
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from signora.core.types import PoseSubmission
from signora.data.wlasl import (
    fetch_wlasl_json,
    gloss_to_english,
    is_direct_video_url,
    iter_instances,
)
from signora.pose.backends.optical_flow import OpticalFlowBackend
from signora.pose.extractor import synthetic_pose_submission


def download_file(url: str, dest: Path, timeout: int = 120) -> bool:
    try:
        req = Request(url, headers={"User-Agent": "SignOra/0.7"})
        with urlopen(req, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
        return dest.stat().st_size > 1000
    except Exception as exc:
        print(f"  skip download {url}: {exc}")
        return False


def metadata_pairs(instances: list[dict], max_samples: int) -> list[dict]:
    """Synthetic pose keyed by real WLASL glosses — bootstrap when videos unavailable."""
    pairs: list[dict] = []
    seen_gloss: set[str] = set()
    for inst in instances:
        gloss = inst["gloss"]
        if gloss in seen_gloss:
            continue
        seen_gloss.add(gloss)
        clip_id = f"wlasl_s2_{gloss}"
        pose = synthetic_pose_submission(clip_id, stage=2, num_frames=24)
        pose.pipeline = "wlasl_metadata_bootstrap"
        pairs.append({"pose": pose.to_dict(), "text": inst["text"]})
        if len(pairs) >= max_samples:
            break
    return pairs


def video_pairs(
    instances: list[dict],
    max_samples: int,
    cache_dir: Path,
) -> list[dict]:
    backend = OpticalFlowBackend()
    if not backend.available():
        raise RuntimeError("OpticalFlowBackend requires opencv")

    pairs: list[dict] = []
    cache_dir.mkdir(parents=True, exist_ok=True)

    for inst in instances:
        url = inst.get("url", "")
        if not is_direct_video_url(url):
            continue

        clip_id = f"wlasl_{inst['video_id']}"
        dest = cache_dir / f"{clip_id}.mp4"
        if not dest.exists() and not download_file(url, dest):
            continue

        try:
            submission: PoseSubmission = backend.extract_from_path(
                str(dest), clip_id, stage=2
            )
        except Exception as exc:
            print(f"  pose failed {clip_id}: {exc}")
            continue

        pairs.append({"pose": submission.to_dict(), "text": inst["text"]})
        print(f"  + {clip_id} → {inst['text']} ({len(submission.frames)} frames)")
        if len(pairs) >= max_samples:
            break

    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build WLASL training pairs")
    parser.add_argument("--max-samples", type=int, default=50)
    parser.add_argument(
        "--subset", default="WLASL100", help="WLASL100 | WLASL300 | WLASL1000 | WLASL2000"
    )
    parser.add_argument("--split", default="train")
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Use real gloss labels with synthetic poses (no video download)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./data/training/wlasl_pairs.json"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("./data/wlasl/videos"),
    )
    args = parser.parse_args()

    cache_json = Path("./data/wlasl/WLASL_v0.3.json")
    print("Fetching WLASL metadata...")
    wlasl = fetch_wlasl_json(cache_json)
    instances = iter_instances(wlasl, subset=args.subset, split=args.split)
    print(f"Found {len(instances)} instances in {args.subset}/{args.split}")

    if args.metadata_only:
        pairs = metadata_pairs(instances, args.max_samples)
        mode = "metadata-only"
    else:
        pairs = video_pairs(instances, args.max_samples, args.cache_dir)
        if len(pairs) < 10:
            print("Few direct MP4 downloads succeeded; merging metadata bootstrap...")
            meta = metadata_pairs(instances, args.max_samples)
            seen = {p["text"] for p in pairs}
            for row in meta:
                if row["text"] not in seen:
                    pairs.append(row)
            mode = "video+metadata"
        else:
            mode = "video"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pairs, indent=2))
    print(f"Wrote {len(pairs)} pairs ({mode}) → {args.output}")


if __name__ == "__main__":
    main()
