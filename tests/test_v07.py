"""Extended tests for v0.7 features."""

import json
import tempfile
from pathlib import Path

import numpy as np

from signora.challenge.crypto import ScriptVault, script_commit_hash
from signora.challenge.store import ChallengeStore
from signora.core.types import PoseSubmission
from signora.pose.ensemble import ReferenceEnsemble
from signora.pose.extractor import synthetic_pose_submission
from signora.translation.features import pose_to_features
from signora.translation.sequence_model import PoseSequenceTranslator


def test_script_vault_roundtrip():
    vault = ScriptVault(master_secret="test-secret")
    enc = vault.encrypt("clip1", "hello world", block_hash="0xabc")
    plain = vault.decrypt("clip1", enc.ciphertext_b64)
    assert plain == "hello world"
    assert vault.verify_reveal("clip1", plain, enc.script_commit, "0xabc")


def test_challenge_store_ingest_reveal():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "c.db"
        store = ChallengeStore(str(db))
        vault = ScriptVault("secret")
        enc = vault.encrypt("c1", "thank you")
        store.ingest("c1", 2, "/tmp/c1.mp4", enc.script_commit, enc.ciphertext_b64)
        rec = store.get("c1")
        assert rec is not None
        assert rec.revealed_script is None
        script = vault.decrypt("c1", rec.ciphertext_b64)
        store.reveal_script("c1", script)
        assert store.get("c1").revealed_script == "thank you"


def test_reference_ensemble_synthetic_fallback():
    ensemble = ReferenceEnsemble(backends=[])
    sub = ensemble.extract_from_path("/nonexistent.mp4", "x", 1)
    assert sub.clip_id == "x"


def test_ensemble_fuse_two_submissions():
    ensemble = ReferenceEnsemble(backends=[])
    a = synthetic_pose_submission("clip", 2, num_frames=5)
    b = synthetic_pose_submission("clip", 2, num_frames=5)
    fused = ensemble._fuse([a, b], "clip", 2)
    assert len(fused.frames) == 5
    assert fused.pipeline.startswith("ensemble:")


def test_pose_features_shape():
    pose = synthetic_pose_submission("p", 1, num_frames=3)
    feats = pose_to_features(pose, max_frames=8)
    assert feats.shape == (8, feats.shape[1])
    assert feats.dtype == np.float32


def test_sequence_translator_train_and_infer(tmp_path):
    model_dir = tmp_path / "models"
    model = PoseSequenceTranslator(str(model_dir))
    model.build_vocab(["hello", "world"])
    model.init_weights(pose_to_features(synthetic_pose_submission("a", 1)).shape[1], len(model.vocab))

    pose = synthetic_pose_submission("demo_s1_hello", 1, num_frames=10)
    feats = pose_to_features(pose, model.max_frames)
    for _ in range(20):
        model.train_batch(feats, model.vocab["hello"], lr=0.05)
    model.save()

    loaded = PoseSequenceTranslator(str(model_dir))
    text, conf = loaded.translate(pose, "demo_s1_hello")
    assert isinstance(text, str)
    assert conf > 0


def test_script_commit_hash_changes_with_block():
    h1 = script_commit_hash("hello", "block1")
    h2 = script_commit_hash("hello", "block2")
    assert h1 != h2
