#!/usr/bin/env python3
"""Download DWPose ONNX models into models/."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"


def download_with_gdown(dest_pose: Path, dest_det: Path) -> bool:
    try:
        import gdown
    except ImportError:
        print("Install gdown: pip install gdown")
        return False

    pose_id = "12L8E2oAgZy4VACGSK9RaZBZrfgx7VTA2"
    det_id = "1w9pXC8tT0p9ndMN-CArp1__b2GbzewWI"

    print("Downloading dw-ll_ucoco_384.onnx (~200MB)...")
    gdown.download(
        f"https://drive.google.com/uc?id={pose_id}",
        str(dest_pose),
        quiet=False,
    )
    print("Downloading yolox_l.onnx (~200MB)...")
    gdown.download(
        f"https://drive.google.com/uc?id={det_id}",
        str(dest_det),
        quiet=False,
    )
    return dest_pose.exists() and dest_det.exists()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download DWPose ONNX models")
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=MODELS,
        help="Output directory (default: ./models)",
    )
    args = parser.parse_args()
    args.models_dir.mkdir(parents=True, exist_ok=True)

    pose_path = args.models_dir / "dw-ll_ucoco_384.onnx"
    det_path = args.models_dir / "yolox_l.onnx"
    alias = args.models_dir / "dwpose.onnx"

    if pose_path.exists() and det_path.exists():
        print(f"Models already present in {args.models_dir}")
    elif not download_with_gdown(pose_path, det_path):
        sys.exit(1)

    # Legacy alias expected by docs / ensemble config
    if not alias.exists():
        shutil.copy2(pose_path, alias)
        print(f"Created alias {alias}")

    print("Done.")
    print(f"  pose: {pose_path}")
    print(f"  det:  {det_path}")


if __name__ == "__main__":
    main()
