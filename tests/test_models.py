from models import CSV_FIELDS, Listing


def test_csv_roundtrip_keeps_lists():
    listing = Listing(
        id="42",
        title="MacBook",
        status="PARTIAL",
        matched=["m1 pro|m1 max"],
        missing=["32gb", "1tb"],
        note="call tomorrow",
    )
    row = listing.to_csv_row()
    assert list(row.keys()) == CSV_FIELDS
    assert row["missing"] == "32gb; 1tb"
    back = Listing.from_csv_row(row)
    assert back == listing


def test_from_dict_ignores_unknown_keys_and_none():
    listing = Listing.from_dict({"id": 7, "title": "x", "unknown": 1, "location": None})
    assert listing.id == "7"
    assert listing.location == "Unknown"


def test_key_falls_back_to_link():
    assert Listing(link="https://x/1").key == "https://x/1"
