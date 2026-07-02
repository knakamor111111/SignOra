#!/usr/bin/env python3
"""Build a tiny training JSON from synthetic poses (bootstrap demo)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from signora.pose.extractor import synthetic_pose_submission


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("./data/training/pairs.json"))
    args = parser.parse_args()

    pairs = []
    for gloss in ("hello", "thank_you", "pain"):
        pose = synthetic_pose_submission(f"demo_s1_{gloss}", stage=1, num_frames=20)
        text = gloss.replace("_", " ")
        pairs.append({"pose": pose.to_dict(), "text": text})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(pairs, indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
