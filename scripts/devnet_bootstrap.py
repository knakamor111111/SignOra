#!/usr/bin/env python3
"""
End-to-end devnet bootstrap for SignOra.

Steps:
  1. Prepare WLASL training pairs
  2. Train Comp B translator
  3. (Optional) Download DWPose ONNX models
  4. Start challenge server + smoke test
  5. Print validator/miner commands for local subtensor (ws://127.0.0.1:9944)

Usage:
  python scripts/devnet_bootstrap.py
  python scripts/devnet_bootstrap.py --skip-dwpose --skip-server
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check)


def subtensor_up(endpoint: str = "ws://127.0.0.1:9944") -> bool:
    try:
        from bittensor import Subtensor

        sub = Subtensor(network=endpoint)
        block = sub.get_current_block()
        print(f"Subtensor reachable at {endpoint} — block {block}")
        return True
    except Exception as exc:
        print(f"Subtensor not reachable at {endpoint}: {exc}")
        print("Start local node from subtensor repo: ./scripts/localnet.sh")
        return False


def smoke_challenge_server(secret: str = "devnet-secret") -> bool:
    try:
        import httpx
        from signora.challenge.server import create_app
        from signora.pose.extractor import synthetic_pose_submission
    except ImportError:
        print("Install server deps: pip install signora[server]")
        return False

    import os

    os.environ["SIGNORA_CHALLENGE_SECRET"] = secret
    app = create_app(data_dir=str(ROOT / "data" / "challenges_devnet"), master_secret=secret)

    with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
        tmp.write(b"\x00" * 128)
        tmp.flush()
        video_b64 = base64.b64encode(Path(tmp.name).read_bytes()).decode()

        transport = httpx.ASGITransport(app=app)
        import asyncio

        async def _test():
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.post(
                    "/ingest",
                    json={
                        "clip_id": "devnet_s2_hello",
                        "stage": 2,
                        "script": "hello",
                        "video_b64": video_b64,
                        "block_hash": "0xdevnet",
                    },
                )
                assert r.status_code == 200, r.text
                r2 = await client.get("/challenges")
                assert r2.status_code == 200
                assert any(c["clip_id"] == "devnet_s2_hello" for c in r2.json())
                r3 = await client.post("/reveal", json={"clip_id": "devnet_s2_hello"})
                assert r3.status_code == 200
                assert r3.json()["script"] == "hello"

        asyncio.run(_test())

    print("Challenge server smoke test passed.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="SignOra devnet bootstrap")
    parser.add_argument("--skip-dwpose", action="store_true")
    parser.add_argument("--skip-server", action="store_true")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--endpoint", default="ws://127.0.0.1:9944")
    args = parser.parse_args()

    py = sys.executable

    # 1. WLASL pairs
    run(
        [
            py,
            "scripts/prepare_wlasl_dataset.py",
            "--metadata-only",
            "--max-samples",
            "100",
            "--output",
            "data/training/wlasl_pairs.json",
        ]
    )

    # 2. Train translator
    run(
        [
            py,
            "scripts/train_translator.py",
            "--dataset",
            "data/training/wlasl_pairs.json",
            "--model-dir",
            "models",
            "--epochs",
            str(args.epochs),
        ]
    )

    # 3. DWPose models (optional, large download)
    if not args.skip_dwpose:
        run([py, "scripts/download_dwpose_models.py"], check=False)

    # 4. Challenge server smoke
    if not args.skip_server:
        smoke_challenge_server()

    # 5. Subtensor check
    chain_ok = subtensor_up(args.endpoint)

    print("\n=== Devnet commands ===")
    print("Challenge server:")
    print("  export SIGNORA_CHALLENGE_SECRET=devnet-secret")
    print("  python scripts/run_challenge_server.py --port 8787")
    print("\nMiner:")
    print(
        "  python neurons/miner.py --netuid <NETUID> "
        f"--subtensor.chain_endpoint {args.endpoint} --wallet.name default --wallet.hotkey default"
    )
    print("\nValidator:")
    print(
        "  python neurons/validator.py --netuid <NETUID> "
        f"--subtensor.chain_endpoint {args.endpoint} --wallet.name default --wallet.hotkey default"
    )
    if not chain_ok:
        print("\nNote: start subtensor first (subtensor-1 repo): ./scripts/localnet.sh")

    status = {
        "wlasl_pairs": (ROOT / "data/training/wlasl_pairs.json").exists(),
        "translator": (ROOT / "models/translator.npz").exists(),
        "dwpose_pose": (ROOT / "models/dw-ll_ucoco_384.onnx").exists(),
        "dwpose_det": (ROOT / "models/yolox_l.onnx").exists(),
        "challenge_smoke": not args.skip_server,
        "subtensor": chain_ok,
    }
    print("\nStatus:", json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
