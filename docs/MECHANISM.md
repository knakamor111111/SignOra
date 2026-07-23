# SignOra Mechanism v0.6

Implementation-focused summary. For the full original specification, see **[MECHANISM_PAPER_V05.md](./MECHANISM_PAPER_V05.md)** (converted from the June 2026 PDF).

## Quick reference

- **Comp A:** pose JSON from video (MediaPipe Holistic)
- **Comp B:** English translation from gate-passed pose
- **Gate:** multi-signal (hand coverage, τ_hand, face grammar, temporal, geometric)
- **DBCP:** commit-reveal for challenge answers; CRv3 for weights

## Testnet exit criteria

- Pose gate pass_rate 75–90%
- ≥3 independent validators
- DBCP + weight commit-reveal end-to-end
