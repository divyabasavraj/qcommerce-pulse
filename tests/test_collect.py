from datetime import datetime

import pandas as pd

from qpulse import collect


def row(review_id, at, text, collected):
    return {"review_id": review_id, "app": "zepto", "rating": 5, "text": text, "review_at": at, "app_version": "1",
            "thumbs_up": 0, "has_reply": False, "replied_at": None, "lang_query": "en", "collected_at": collected}


def test_edited_review_moves_to_its_new_month(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "RAW_DIR", tmp_path)
    collect.save(pd.DataFrame([row("a", datetime(2026, 9, 5), "old text", datetime(2026, 10, 20)),
                               row("b", datetime(2026, 9, 6), "other", datetime(2026, 10, 20))]))
    # Review "a" is edited in October: same ID, new date and text.
    collect.save(pd.DataFrame([row("a", datetime(2026, 10, 25), "new text", datetime(2026, 10, 28))]))
    sep = pd.read_parquet(tmp_path / "reviews_2026-09.parquet")
    oct_ = pd.read_parquet(tmp_path / "reviews_2026-10.parquet")
    assert list(sep["review_id"]) == ["b"]
    assert list(oct_["text"]) == ["new text"]


def test_to_ist_is_the_same_on_any_machine_clock():
    # 2025-10-27 21:20 UTC is 2025-10-28 02:50 IST.
    assert collect.to_ist(datetime.fromtimestamp(1761600000)) == datetime(2025, 10, 28, 2, 50)
