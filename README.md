# SignOra

Bittensor subnet for **ASL video → English translation** via a two-competition mining pipeline.

**Repository:** [github.com/knakamor111111/SignOra](https://github.com/knakamor111111/SignOra)

| Competition | Input | Output |
|-------------|-------|--------|
| **A — Pose extraction** | MP4 signing clip | Structured pose JSON (proof-of-compute) |
| **B — Translation** | Gate-passed pose sequence | English text |

SignOra applies the Score SN44 pattern: miners submit structured data that proves they ran real computation, not translation guesses. Known-plaintext capture, DBCP commit-reveal, and a multi-signal pose gate protect against gaming and chicken-and-egg bootstrap problems.

Mechanism spec: [docs/MECHANISM.md](./docs/MECHANISM.md) · v0.7 details: [docs/V07.md](./docs/V07.md)

---

## Install

```bash
git clone https://github.com/knakamor111111/SignOra.git
cd SignOra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[pose,server,dev]"
cp .env.example .env   # edit wallet, netuid, secrets
```

**Optional extras**

| Extra | Install | Purpose |
|-------|---------|---------|
| `pose` | `pip install -e ".[pose]"` | MediaPipe Holistic for Comp A |
| `server` | `pip install -e ".[server]"` | Challenge server (FastAPI) |
| `onnx` | `pip install -e ".[onnx]"` | DWPose ONNX reference backend |

Download `holistic_landmarker.task` from [MediaPipe Holistic Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/holistic_landmarker) → `signora/pose/models/holistic_landmarker.task`.

---

## Quick start

### Miner

```bash
python neurons/miner.py \
  --netuid 0 \
  --subtensor.network local \
  --wallet.name default \
  --wallet.hotkey default \
  --axon.port 8091 \
  --signora.model_dir ./models
```

### Validator

Drop challenge clips in `data/challenges/*.mp4`, then:

```bash
python neurons/validator.py \
  --netuid 0 \
  --subtensor.network local \
  --wallet.name default \
  --wallet.hotkey default
```

Validators score miners using a **reference pose ensemble** (not MediaPipe-only), submit weights via **commit-reveal / CRv3 timelock**, and fall back to direct `set_mechanism_weights` when commit-reveal is disabled on the subnet.

### Challenge server

Known-plaintext capture with encrypted script storage:

```bash
export SIGNORA_CHALLENGE_SECRET=change-me-before-mainnet
python scripts/run_challenge_server.py --port 8787
```

| Endpoint | Purpose |
|----------|---------|
| `POST /ingest` | Upload video + script (script encrypted, commit hash stored) |
| `GET /challenges` | List unrevealed clips for validators |
| `POST /reveal` | Decrypt script after DBCP reveal window |
| `GET /manifest` | Audit on-chain-ready commits without plaintext |

### Train Comp B translator

```bash
# Bootstrap demo pairs (synthetic poses)
python scripts/build_training_pairs.py --output ./data/training/pairs.json

# Train sequence model → models/translator.npz + models/vocab.json
python scripts/train_translator.py \
  --dataset ./data/training/pairs.json \
  --model-dir ./models \
  --epochs 100
```

Miners load the trained model automatically via `PoseSequenceTranslator`.

### Calibrate pose gate

v0.6+ uses a **multi-signal gate** between Comp A and Comp B (not a fixed 0.75 MediaPipe scalar):

```bash
python scripts/calibrate_pose_gate.py \
  --submissions-dir ./data/calibration/submissions \
  --reference-dir ./data/calibration/reference \
  --output ./data/calibration/gate_report.json
```

Target pass rate for honest miners: **75–90%**. See [docs/pose-gate-calibration.md](./docs/pose-gate-calibration.md).

---

## Architecture

```
Challenge video
      │
      ▼
┌─────────────┐     multi-signal      ┌─────────────┐
│  Comp A     │ ─── pose gate ───────▶│  Comp B     │
│  pose JSON  │                       │  English    │
└─────────────┘                       └─────────────┘
      │                                     │
      └──────────────┬──────────────────────┘
                     ▼
              Validator scores
                     │
                     ▼
         commit-reveal weights (MechId 0/1)
                     │
                     ▼
              Subtensor / Yuma
```

### Reference pose ensemble

Validators fuse independent backends to avoid circular MediaPipe scoring:

| Backend | Module |
|---------|--------|
| MediaPipe Holistic | `signora/pose/backends/mediapipe_backend.py` |
| Optical-flow pseudo-landmarks | `signora/pose/backends/optical_flow.py` |
| DWPose ONNX (optional) | `signora/pose/backends/dwpose_onnx.py` |

Fusion: per-frame median of landmarks → `signora/pose/ensemble.py`.

### Subtensor mechanisms

| MechId | Role |
|--------|------|
| 0 | Competition A — pose JSON |
| 1 | Competition B — translation |
| 2 | Corpus mining (Phase 1b+) |

Weight submission: `signora/validation/weight_committer.py` (CRv3 timelock → commit-reveal → direct fallback).

### DBCP (task answers)

| Block | Action |
|-------|--------|
| B+0 | Validator posts `V_commit` |
| B+1 | Challenges sent to miners |
| B+2 | Miners post `M_commit` |
| B+3 | Simultaneous reveal |
| B+4 | Scoring → weights |

Implementation: `signora/dbcp/protocol.py`. Weight commits use chain CRv3 separately.

---

## Repository layout

```
SignOra/
├── neurons/
│   ├── miner.py              # Comp A + Comp B axon
│   └── validator.py          # Ensemble scoring, DBCP, weight commits
├── signora/
│   ├── protocol/             # Bittensor synapses
│   ├── pose/                 # Extractor, gate, ensemble, backends
│   ├── translation/          # PoseSequenceTranslator + features
│   ├── challenge/            # Known-plaintext server + crypto + store
│   ├── dbcp/                 # Dual-Blind Commitment Protocol
│   └── validation/           # Scoring, WeightCommitter
├── scripts/
│   ├── run_challenge_server.py
│   ├── train_translator.py
│   ├── build_training_pairs.py
│   └── calibrate_pose_gate.py
├── docs/
│   ├── MECHANISM.md
│   ├── V07.md
│   └── pose-gate-calibration.md
├── models/                   # translator.npz, vocab.json, gloss_lookup.json
└── tests/
```

---

## Configuration

Copy `.env.example` → `.env`:

| Variable | Purpose |
|----------|---------|
| `NETUID` | Subnet ID |
| `SUBTENSOR_NETWORK` | `local`, `test`, or `finney` |
| `SIGNORA_CHALLENGE_SECRET` | Master key for encrypted script vault |
| `POSE_REFERENCE_DIR` | Cached reference pose JSON |
| `MODEL_DIR` | Comp B model directory |

CLI flags: `--signora.model_dir`, `--signora.validator_sample_size`, `--signora.weight_timelock`.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use synthetic pose sequences when MediaPipe is unavailable.

---

## References

- [Score SN44](https://github.com/score-technologies/score-vision) — lightweight JSON validation pattern
- [MediaPipe Holistic](https://ai.google.dev/edge/mediapipe/solutions/vision/holistic_landmarker)
- [WLASL dataset](https://github.com/dict-as/wlasl) — ASL word-level research corpus
- SignOra Mechanism Paper v0.5 / v0.6 spec

## License

MIT
