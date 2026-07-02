#!/usr/bin/env python3
"""Train Comp B PoseSequenceTranslator from paired pose JSON + text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from signora.core.types import PoseSubmission
from signora.translation.features import _feature_dim, pose_to_features
from signora.translation.sequence_model import PoseSequenceTranslator


def load_dataset(path: Path) -> list[tuple[PoseSubmission, str]]:
    rows = json.loads(path.read_text())
    out: list[tuple[PoseSubmission, str]] = []
    for row in rows:
        pose = PoseSubmission.from_dict(row["pose"])
        out.append((pose, row["text"]))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Train SignOra Comp B translator")
    parser.add_argument("--dataset", type=Path, required=True, help="JSON list of pose+text")
    parser.add_argument("--model-dir", type=Path, default=Path("./models"))
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=0.02)
    args = parser.parse_args()

    data = load_dataset(args.dataset)
    if not data:
        raise SystemExit("Empty dataset")

    model = PoseSequenceTranslator(str(args.model_dir))
    model.build_vocab([text for _, text in data])
    model.init_weights(_feature_dim(), len(model.vocab))

    for epoch in range(args.epochs):
        loss_sum = 0.0
        for pose, text in data:
            feats = pose_to_features(pose, model.max_frames)
            tokens = model.tokenize(text)
            if not tokens:
                continue
            target = model.vocab.get(tokens[0], 1)
            loss_sum += model.train_batch(feats, target, lr=args.lr)
        print(f"epoch={epoch+1} avg_loss={loss_sum / max(len(data), 1):.4f}")

    model.save()
    print(f"Saved model to {args.model_dir}")


if __name__ == "__main__":
    main()
