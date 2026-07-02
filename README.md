# SignOra

Bittensor subnet for **ASL video → English translation** via a two-competition mining pipeline.

Repository: [github.com/knakamor111111/SignOra](https://github.com/knakamor111111/SignOra)

1. **Competition A** — skeletal pose extraction (proof-of-compute JSON)
2. **Competition B** — sequence-to-meaning translation from gate-passed pose data

## v0.7 highlights

See [docs/V07.md](./docs/V07.md) for full details.

| Feature | Command / module |
|---------|------------------|
| Reference pose ensemble | `signora/pose/ensemble.py` |
| Commit-reveal weights | `signora/validation/weight_committer.py` |
| Challenge server | `python scripts/run_challenge_server.py` |
| Train Comp B model | `python scripts/train_translator.py` |


## Quick start

```bash
cd signora
python -m venv .venv && source .venv/bin/activate
pip install -e ".[pose,server,dev]"

# Miner (Comp A + Comp B)
python neurons/miner.py \
  --netuid 0 \
  --subtensor.network local \
  --wallet.name default \
  --wallet.hotkey default \
  --axon.port 8091

# Validator
python neurons/validator.py \
  --netuid 0 \
  --subtensor.network local \
  --wallet.name default \
  --wallet.hotkey default
```

Copy `.env.example` → `.env` for local overrides.

## Repository layout

```
signora/
├── signora/
│   ├── protocol/       # Bittensor synapse definitions
│   ├── core/           # Types, constants, config
│   ├── pose/           # MediaPipe wrapper + quality gate
│   ├── translation/    # Comp B baseline model
│   ├── dbcp/           # Dual-Blind Commitment Protocol
│   └── validation/     # Validator scoring + weight builder
├── neurons/
│   ├── miner.py
│   └── validator.py
├── scripts/
│   └── calibrate_pose_gate.py
└── tests/
```

## Subtensor mechanisms

| MechId | Role |
|--------|------|
| 0 | Competition A — pose JSON |
| 1 | Competition B — translation |
| 2 | Corpus mining (Phase 1b+) |

Validators submit weights via commit-reveal / CRv3 timelock (`WeightCommitter`), with direct fallback.

## Pose quality gate

v0.6 uses a **multi-signal gate** between Comp A and Comp B (not a single 0.75 scalar). Calibrate on testnet:

```bash
python scripts/calibrate_pose_gate.py \
  --submissions-dir ./data/calibration/submissions \
  --reference-dir ./data/calibration/reference \
  --output ./data/calibration/gate_report.json
```

See [docs/pose-gate-calibration.md](./docs/pose-gate-calibration.md).

## DBCP flow

Per tempo (see `signora/dbcp/protocol.py`):

| Block | Action |
|-------|--------|
| B+0 | Validator posts `V_commit` |
| B+1 | Challenges sent to miners |
| B+2 | Miners post `M_commit` |
| B+3 | Simultaneous reveal |
| B+4 | Scoring → weights |

Task commits are off-chain; weight commits use chain CRv3.

## Development

```bash
pip install -e ".[dev]"
pytest
```

MediaPipe is optional for CI — tests use synthetic pose sequences when unavailable.

## License

MIT
