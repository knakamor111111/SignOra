# SignOra Mechanism v0.6

See the full specification in the [subtensor signora docs](https://github.com/opentensor/subtensor/tree/main/signora).

## Quick reference

- **Comp A:** pose JSON from video (MediaPipe Holistic)
- **Comp B:** English translation from gate-passed pose
- **Gate:** multi-signal (hand coverage, τ_hand, face grammar, temporal, geometric)
- **DBCP:** commit-reveal for challenge answers; CRv3 for weights

## Testnet exit criteria

- Pose gate pass_rate 75–90%
- ≥3 independent validators
- DBCP + weight commit-reveal end-to-end
