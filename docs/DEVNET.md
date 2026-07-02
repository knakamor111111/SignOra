# Devnet bootstrap

Run the full local stack:

```bash
pip install -e ".[pose,server,dwpose,dev]"

# One-shot: WLASL pairs → train translator → challenge smoke → subtensor check
python scripts/devnet_bootstrap.py

# Skip large DWPose download
python scripts/devnet_bootstrap.py --skip-dwpose
```

## 1. WLASL training data

Real gloss labels from [WLASL](https://github.com/dxli94/WLASL):

```bash
# Metadata bootstrap (100 glosses, synthetic poses) — works offline
python scripts/prepare_wlasl_dataset.py --metadata-only --max-samples 100

# Direct MP4 downloads + optical-flow pose (non-YouTube URLs only)
python scripts/prepare_wlasl_dataset.py --max-samples 50
```

Output: `data/training/wlasl_pairs.json`

## 2. YouTube-ASL (manifest)

Provide a JSON manifest (see `data/training/youtube_asl_sample_manifest.json`):

```bash
python scripts/prepare_youtube_asl_dataset.py \
  --manifest data/training/youtube_asl_sample_manifest.json \
  --metadata-only
```

## 3. Train Comp B

```bash
python scripts/train_translator.py \
  --dataset data/training/wlasl_pairs.json \
  --model-dir models \
  --epochs 50
```

## 4. DWPose ONNX

```bash
pip install gdown controlnet-dwpose onnxruntime
python scripts/download_dwpose_models.py
```

Creates `models/yolox_l.onnx`, `models/dw-ll_ucoco_384.onnx`, and alias `models/dwpose.onnx`.

## 5. Local subtensor + challenge server

Terminal 1 — subtensor (from subtensor-1 repo):

```bash
cd ../subtensor-1
./scripts/localnet.sh
```

Terminal 2 — challenge server:

```bash
export SIGNORA_CHALLENGE_SECRET=devnet-secret
python scripts/run_challenge_server.py --port 8787
```

Terminal 3 — miner / validator:

```bash
python neurons/miner.py --netuid 2 \
  --subtensor.chain_endpoint ws://127.0.0.1:9944 \
  --wallet.name alice --wallet.hotkey default

python neurons/validator.py --netuid 2 \
  --subtensor.chain_endpoint ws://127.0.0.1:9944 \
  --wallet.name bob --wallet.hotkey default
```

Register subnet on local chain first (see subtensor `ts-tests/suites/zombienet_subnets/`).

## Status checklist

| Step | Artifact | Command to verify |
|------|----------|-------------------|
| WLASL pairs | `data/training/wlasl_pairs.json` | `prepare_wlasl_dataset.py` |
| Translator | `models/translator.npz` | `train_translator.py` |
| DWPose | `models/dw-ll_ucoco_384.onnx` | `download_dwpose_models.py` |
| Challenge server | `/health` on :8787 | `run_challenge_server.py` |
| Subtensor | block height on :9944 | `devnet_bootstrap.py` |
