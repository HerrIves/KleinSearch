import csv

import storage
from models import Listing


def _ad(i, status="MATCH", **kw):
    return Listing(id=str(i), title=f"Ad {i}", status=status, link=f"https://x/{i}", **kw)


def test_upsert_adds_only_match_and_partial(tmp_path):
    path = str(tmp_path / "l.csv")
    added, total = storage.upsert_listings(
        [_ad(1), _ad(2, "PARTIAL", missing=["32gb"]), _ad(3, "REJECTED")], path, now="2026-01-01 10:00"
    )
    assert (added, total) == (2, 2)
    stored = {item.id: item for item in storage.load_listings(path)}
    assert stored["2"].missing == ["32gb"]
    assert stored["1"].added_at == "2026-01-01 10:00"


def test_upsert_updates_existing_and_keeps_note(tmp_path):
    path = str(tmp_path / "l.csv")
    storage.upsert_listings([_ad(1, "PARTIAL", price="900 €")], path, now="2026-01-01 10:00")
    assert storage.save_note("1", "  seller is nice ", path)
    added, total = storage.upsert_listings([_ad(1, "MATCH", price="850 €")], path, now="2026-02-02 10:00")
    assert (added, total) == (0, 1)
    [row] = storage.load_listings(path)
    assert row.status == "MATCH"
    assert row.price == "850 €"
    assert row.note == "seller is nice"
    assert row.added_at == "2026-01-01 10:00"


def test_save_note_unknown_id(tmp_path):
    path = str(tmp_path / "l.csv")
    storage.upsert_listings([_ad(1)], path)
    assert storage.save_note("999", "x", path) is False


def test_file_is_excel_friendly(tmp_path):
    path = tmp_path / "l.csv"
    storage.upsert_listings([_ad(1)], str(path))
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM
    assert b";" in raw.splitlines()[0]


def test_reevaluate_removes_now_excluded(tmp_path):
    path = str(tmp_path / "l.csv")
    storage.upsert_listings(
        [
            Listing(id="1", title="MacBook M1 Pro 32GB", status="PARTIAL", profile="Mac"),
            Listing(id="2", title="MacBook M1 Pro defekt", status="PARTIAL", profile="Mac"),
            Listing(id="3", title="Other", status="PARTIAL", profile="Deleted profile"),
        ],
        path,
    )
    settings = {"global_exclude": [], "profiles": [{"name": "Mac", "must_have": ["32gb"], "exclude": ["defekt"]}]}
    updated, removed = storage.reevaluate(settings, path)
    assert (updated, removed) == (1, 1)
    stored = {item.id: item for item in storage.load_listings(path)}
    assert stored["1"].status == "MATCH"
    assert "2" not in stored
    assert "3" in stored  # unknown profile: kept untouched




def test_upsert_listings_detailed(tmp_path):
    path = str(tmp_path / "l.csv")
    ad1 = _ad(1, "MATCH")
    ad2 = _ad(2, "PARTIAL")
    added, total, new_items = storage.upsert_listings_detailed([ad1, ad2], path)
    assert (added, total) == (2, 2)
    assert len(new_items) == 2
    assert {item.id for item in new_items} == {"1", "2"}

    # Updating existing listing shouldn't be in new_items
    ad1_updated = _ad(1, "MATCH", price="500 €")
    added2, total2, new_items2 = storage.upsert_listings_detailed([ad1_updated], path)
    assert (added2, total2) == (0, 2)
    assert len(new_items2) == 0
