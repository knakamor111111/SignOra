#!/usr/bin/env python3
"""Build WLASL training pairs (ASL gloss labels + optional YouTube video poses)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from signora.data.wlasl import build_wlasl_training_pairs, fetch_wlasl_metadata
from signora.data.wlasl_video import build_wlasl_video_pairs


def main() -> None:
    p = argparse.ArgumentParser(description="Prepare WLASL ASL training pairs")
    p.add_argument("--max-samples", type=int, default=100)
    p.add_argument("--out", type=Path, default=ROOT / "data" / "wlasl_pairs.json")
    p.add_argument("--output", type=Path, default=None, help="Alias for --out")
    p.add_argument(
        "--metadata-only",
        action="store_true",
        help="Skip video download (synthetic poses from WLASL gloss labels)",
    )
    p.add_argument("--metadata", type=Path, default=ROOT / "data" / "WLASL_v0.3.json")
    p.add_argument(
        "--with-youtube",
        action="store_true",
        help="Download WLASL-linked YouTube clips and extract poses (requires yt-dlp)",
    )
    p.add_argument(
        "--pose-backend",
        choices=("mediapipe", "optical_flow", "ensemble"),
        default="mediapipe",
        help="Pose backend when --with-youtube (ensemble fuses MediaPipe + optical flow + DWPose if installed)",
    )
    args = p.parse_args()
    if args.output is not None:
        args.out = args.output

    if not args.metadata.exists():
        print(f"Fetching WLASL metadata to {args.metadata} …")
        fetch_wlasl_metadata(args.metadata)

    if args.with_youtube and not args.metadata_only:
        print(
            f"ASL: downloading up to {args.max_samples} WLASL YouTube clips "
            f"(pose={args.pose_backend}) …"
        )
        pairs = build_wlasl_video_pairs(
            args.metadata,
            max_samples=args.max_samples,
            pose_backend=args.pose_backend,
        )
    else:
        print(f"ASL: metadata-only pairs (no video), max={args.max_samples} …")
        pairs = build_wlasl_training_pairs(args.metadata, max_samples=args.max_samples)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(pairs, indent=2), encoding="utf-8")
    print(f"Wrote {len(pairs)} ASL pairs → {args.out}")


if __name__ == "__main__":
    main()
