# Pose Gate Calibration

Run on testnet before mainnet:

```bash
python scripts/calibrate_pose_gate.py \
  --submissions-dir ./data/calibration/submissions \
  --reference-dir ./data/calibration/reference \
  --output ./data/calibration/gate_report.json
```

## Starting τ_hand by stage

| Stage | τ_hand | θ |
|-------|--------|---|
| 1 | 0.72 | 0.88 |
| 2 | 0.70 | 0.85 |
| 3 | 0.65 | 0.82 |
| 4 | 0.65 | 0.80 |

Target pass_rate: **75–90%** for honest miners.

Implementation: `signora/pose/gate.py`
