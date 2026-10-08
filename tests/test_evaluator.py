import pytest

from evaluator import evaluate_listing, make_search_url, parse_price_value

PROFILE = {
    "name": "MacBook M1 Pro/Max 32GB",
    "price_min": 300,
    "price_max": 1200,
    "must_have": ["m1 pro|m1 max", "32gb"],
    "exclude": ["defekt", "icloud"],
}
GLOBAL = ["suche", "tausche"]


def ad(title, price="900 €", description=""):
    return {"id": "1", "title": title, "price": price, "description": description, "link": "https://x/1"}


def test_full_match():
    r = evaluate_listing(ad("Apple MacBook Pro 16 M1 Pro 32GB RAM 512GB SSD"), PROFILE, GLOBAL)
    assert r["status"] == "MATCH"
    assert r["matched"] == ["m1 pro|m1 max", "32gb"]
    assert r["missing"] == []
    assert r["profile"] == PROFILE["name"]


def test_criteria_found_in_description():
    r = evaluate_listing(ad("MacBook Pro 14 2021", description="M1 Max, 32 GB RAM, 1TB"), PROFILE, GLOBAL)
    assert r["status"] == "MATCH"


def test_partial_lists_missing_criteria():
    r = evaluate_listing(ad("MacBook Pro 14 M1 Pro 512GB"), PROFILE, GLOBAL)
    assert r["status"] == "PARTIAL"
    assert r["missing"] == ["32gb"]
    assert "missing: 32gb" in r["reason"]
    assert r["reason"].startswith("1/2")


def test_nothing_matched_is_still_partial_not_rejected():
    r = evaluate_listing(ad("MacBook Air 2019"), PROFILE, GLOBAL)
    assert r["status"] == "PARTIAL"
    assert r["missing"] == ["m1 pro|m1 max", "32gb"]


@pytest.mark.parametrize(
    "title,reason",
    [
        ("Suche MacBook M1 Pro 32GB", "Excluded word: suche"),
        ("MacBook M1 Pro 32GB Display defekt", "Excluded word: defekt"),
        ("MacBook M1 Pro 32GB iCloud gesperrt", "Excluded word: icloud"),
    ],
)
def test_excluded_words(title, reason):
    r = evaluate_listing(ad(title), PROFILE, GLOBAL)
    assert r["status"] == "REJECTED"
    assert r["reason"] == reason


def test_price_out_of_range():
    assert evaluate_listing(ad("M1 Pro 32GB", "1.500 €"), PROFILE, GLOBAL)["reason"] == "Price above 1200 €"
    assert evaluate_listing(ad("M1 Pro 32GB", "50 €"), PROFILE, GLOBAL)["reason"] == "Price below 300 €"


def test_unknown_price_is_not_rejected():
    assert evaluate_listing(ad("M1 Pro 32GB", "VB"), PROFILE, GLOBAL)["status"] == "MATCH"


def test_profile_without_criteria_matches_everything_not_excluded():
    r = evaluate_listing(ad("Fahrrad 28 Zoll", "80 €"), {"name": "Bike"}, GLOBAL)
    assert r["status"] == "MATCH"
    assert r["reason"] == "No criteria set"


def test_input_is_not_mutated():
    item = ad("M1 Pro 32GB")
    evaluate_listing(item, PROFILE, GLOBAL)
    assert "status" not in item


@pytest.mark.parametrize(
    "text,value",
    [("999 € VB", 999.0), ("1.250 €", 1250.0), ("120,50 €", 120.5), ("Zu verschenken", 0.0), ("VB", None), ("", None)],
)
def test_parse_price_value(text, value):
    assert parse_price_value(text) == value


@pytest.mark.parametrize(
    "kwargs,url",
    [
        ({"query": "macbook m1 pro"}, "https://www.kleinanzeigen.de/s-macbook-m1-pro/k0"),
        (
            {"query": "MacBook  M1 Pro", "price_min": 300, "price_max": 1200, "category": "278"},
            "https://www.kleinanzeigen.de/s-preis:300:1200/macbook-m1-pro/k0c278",
        ),
        ({"query": "x", "price_max": 150, "page": 2}, "https://www.kleinanzeigen.de/s-preis::150/seite:2/x/k0"),
        ({"query": "x", "price_min": 10}, "https://www.kleinanzeigen.de/s-preis:10:/x/k0"),
        ({"query": "über größe"}, "https://www.kleinanzeigen.de/s-%C3%BCber-gr%C3%B6%C3%9Fe/k0"),
    ],
)
def test_make_search_url(kwargs, url):
    assert make_search_url(**kwargs) == url
