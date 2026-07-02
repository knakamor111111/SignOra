"""WLASL / devnet pipeline tests."""

from pathlib import Path

from signora.data.wlasl import gloss_to_english, iter_instances


def test_gloss_to_english():
    assert gloss_to_english("thank_you") == "thank you"


def test_iter_instances_top_k():
    data = [
        {"gloss": "book", "instances": [{"split": "train", "video_id": "1", "url": ""}]},
        {"gloss": "drink", "instances": [{"split": "train", "video_id": "2", "url": ""}]},
    ]
    rows = iter_instances(data, subset="WLASL1", split="train")
    assert len(rows) == 1
    assert rows[0]["text"] == "book"


def test_wlasl_json_cached():
    cache = Path("./data/wlasl/WLASL_v0.3.json")
    if not cache.exists():
        return  # network optional in CI
    import json

    data = json.loads(cache.read_text())
    rows = iter_instances(data, subset="WLASL100", split="train")
    assert len(rows) > 0
