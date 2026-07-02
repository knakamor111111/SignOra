"""Tests for SignOra core logic."""

from signora.core.types import PoseSubmission
from signora.dbcp.protocol import DBCPSession, rotate_salt, sha256_hex
from signora.pose.extractor import synthetic_pose_submission
from signora.pose.gate import evaluate_gate
from signora.pose.scoring import geometric_score, score_comp_a
from signora.translation.baseline import wer
from signora.validation.weights import build_mechanism_weights


def test_synthetic_pose_gate_passes():
    sub = synthetic_pose_submission("clip_s1_hello", stage=1)
    ref = synthetic_pose_submission("clip_s1_hello", stage=1)
    gate = evaluate_gate(sub, ref)
    assert gate.pass_ is True
    assert gate.mean_hand_conf >= 0.72


def test_gate_fails_low_confidence():
    sub = synthetic_pose_submission("clip_s3_phrase", stage=3)
    for frame in sub.frames:
        for lm in frame.left_hand + frame.right_hand:
            lm.presence = 0.3
            lm.visibility = 0.3
    ref = synthetic_pose_submission("clip_s3_phrase", stage=3)
    gate = evaluate_gate(sub, ref)
    assert gate.pass_ is False


def test_geometric_score_identical_poses():
    a = synthetic_pose_submission("a", 2)
    b = synthetic_pose_submission("a", 2)
    assert geometric_score(a, b) > 0.95


def test_dbcp_commit_verify():
    session = DBCPSession(tempo=1, block_hash="0xabc")
    vc, commit = session.build_validator_commit(
        clip_ids=["c1"],
        reference_answers={"c1": "hello"},
    )
    reveal = {
        "clip_ids": vc.clip_ids,
        "reference_answers": vc.reference_answers,
        "salt": vc.salt,
        "block_hash": vc.block_hash,
        "tempo": vc.tempo,
    }
    assert session.verify_reveal("validator", reveal, commit)


def test_dbcp_salt_rotation():
    s1 = rotate_salt("seed", "block1")
    s2 = rotate_salt(s1, "block2")
    assert s1 != s2
    assert len(sha256_hex("x")) == 64


def test_wer():
    assert wer("hello world", "hello world") == 0.0
    assert wer("hello world", "hello") == 0.5


def test_build_mechanism_weights():
    weights = build_mechanism_weights(
        uids=[0, 1, 2],
        pose_scores={0: 1.0, 1: 0.5, 2: 0.0},
        translation_scores={0: 0.8, 1: 0.8, 2: 0.1},
    )
    pose_w = dict(weights[0])
    assert abs(sum(pose_w.values()) - 1.0) < 1e-6
    assert pose_w[0] > pose_w[2]
