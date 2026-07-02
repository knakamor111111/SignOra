#!/usr/bin/env python3
"""
Sweep τ_hand and report pass_rate / geometric scores for testnet calibration.

Usage:
  python scripts/calibrate_pose_gate.py \\
    --submissions-dir ./data/calibration/submissions \\
    --reference-dir ./data/calibration/reference \\
    --output ./data/calibration/gate_report.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from signora.core.types import PoseSubmission
from signora.pose.gate import evaluate_gate
from signora.pose.scoring import geometric_score


def load_poses(directory: Path) -> dict[str, PoseSubmission]:
    poses: dict[str, PoseSubmission] = {}
    for path in directory.glob("*.json"):
        data = json.loads(path.read_text())
        sub = PoseSubmission.from_dict(data)
        poses[sub.clip_id or path.stem] = sub
    return poses


def sweep_tau(
    submissions: dict[str, PoseSubmission],
    references: dict[str, PoseSubmission],
    tau_values: list[float],
) -> list[dict]:
    results = []
    for tau in tau_values:
        passed = 0
        geom_scores: list[float] = []
        for clip_id, sub in submissions.items():
            ref = references.get(clip_id)
            stage_params = {
                sub.stage: {
                    "tau_hand": tau,
                    "theta": 0.80,
                    "hand_coverage_min": 0.85,
                }
            }
            gate = evaluate_gate(sub, ref, stage_params=stage_params)
            if gate.pass_:
                passed += 1
                if ref:
                    geom_scores.append(geometric_score(sub, ref))
        n = len(submissions) or 1
        results.append(
            {
                "tau_hand": tau,
                "pass_rate": passed / n,
                "mean_geometric_score": sum(geom_scores) / len(geom_scores)
                if geom_scores
                else 0.0,
                "n_clips": len(submissions),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="SignOra pose gate calibration")
    parser.add_argument("--submissions-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("gate_report.json"))
    args = parser.parse_args()

    submissions = load_poses(args.submissions_dir)
    references = load_poses(args.reference_dir)

    if not submissions:
        raise SystemExit(f"No submissions found in {args.submissions_dir}")

    tau_values = [round(0.55 + 0.05 * i, 2) for i in range(7)]  # 0.55 .. 0.85
    report = {
        "sweep": sweep_tau(submissions, references, tau_values),
        "recommendation": "Select τ where pass_rate is 0.75-0.90",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
