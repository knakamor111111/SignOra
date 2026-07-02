#!/usr/bin/env python3
"""Merge YouTube-ASL manifest into training pairs JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from signora.data.youtube_asl import load_youtube_asl_manifest, manifest_to_pairs
from signora.pose.backends.optical_flow import OpticalFlowBackend
from signora.pose.extractor import synthetic_pose_submission


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare YouTube-ASL training pairs")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("./data/training/youtube_asl_pairs.json"))
    parser.add_argument("--video-dir", type=Path, default=Path("./data/youtube_asl/videos"))
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()

    rows = load_youtube_asl_manifest(args.manifest)
    backend = OpticalFlowBackend()

    def pose_builder(clip_id: str, row: dict):
        video_path = row.get("path")
        if video_path:
            vp = Path(video_path)
            if not vp.is_absolute():
                vp = args.video_dir / vp
        else:
            vp = args.video_dir / f"{clip_id}.mp4"

        if not args.metadata_only and vp.exists() and backend.available():
            return backend.extract_from_path(str(vp), clip_id, stage=3)
        return synthetic_pose_submission(clip_id, stage=3, num_frames=30)

    pairs = manifest_to_pairs(rows, pose_builder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pairs, indent=2))
    print(f"Wrote {len(pairs)} pairs → {args.output}")


if __name__ == "__main__":
    main()
