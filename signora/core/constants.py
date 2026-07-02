"""Subnet constants and stage parameters."""

from __future__ import annotations

from dataclasses import dataclass

# Subtensor mechanism IDs
MECH_POSE = 0
MECH_TRANSLATION = 1
MECH_CORPUS = 2

# Face landmarks used for grammatical non-manuals (indices into face mesh subset)
FACE_GRAMMAR_INDICES = (70, 105, 300, 334, 61, 291)

# Gate defaults per stage (testnet starting values)
STAGE_GATE_PARAMS: dict[int, dict[str, float]] = {
    1: {"tau_hand": 0.72, "theta": 0.88, "hand_coverage_min": 0.85},
    2: {"tau_hand": 0.70, "theta": 0.85, "hand_coverage_min": 0.85},
    3: {"tau_hand": 0.65, "theta": 0.82, "hand_coverage_min": 0.85},
    4: {"tau_hand": 0.65, "theta": 0.80, "hand_coverage_min": 0.85},
}

FACE_GRAMMAR_COVERAGE_MIN = 0.70
TEMPORAL_CONTINUITY_MIN = 0.90

# Comp A composite score weights
COMP_A_WEIGHTS = {"geometric": 0.6, "temporal": 0.2, "face": 0.2}

# Stage emission weights for composite miner score
STAGE_EMISSION_WEIGHTS = {1: 0.10, 2: 0.20, 3: 0.35, 4: 0.35}

# Curriculum
NUM_HAND_LANDMARKS = 21
MIN_VISIBLE_HAND_LANDMARKS = 18
VISIBILITY_THRESHOLD = 0.5

# DBCP
DBCP_REVEAL_DELAY_BLOCKS = 3


@dataclass(frozen=True)
class PhaseConfig:
    name: str
    mech_pose_share: float
    mech_translation_share: float
    mech_corpus_share: float
    m2_signer_share: float


PHASES = {
    "launch": PhaseConfig("launch", 0.50, 0.50, 0.0, 0.0),
    "phase_1b": PhaseConfig("phase_1b", 0.45, 0.45, 0.10, 0.0),
    "steady": PhaseConfig("steady", 0.35, 0.35, 0.05, 0.30),
}
