import os

from scraper import parse_listings_from_html

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "search_page.html")


def _parse():
    with open(FIXTURE, encoding="utf-8") as f:
        return parse_listings_from_html(f.read())


def test_parses_all_articles():
    items = _parse()
    assert [i["id"] for i in items] == ["3534023318", "3533593879", "3533000001"]


def test_fields_of_current_markup():
    first = _parse()[0]
    assert first["title"] == "Apple MacBook Pro 16 M1 Pro 32GB RAM 512GB SSD 85% Akku TIPTOP"
    assert first["price"] == "999 € VB"
    assert first["location"] == "63067 Offenbach"
    assert first["posted"] == "Heute, 17:48"
    assert first["shipping"] == "Shipping possible"
    assert first["link"].startswith("https://www.kleinanzeigen.de/s-anzeige/apple-macbook-pro-16")
    assert "Restkapazität" in first["description"]  # from JSON-LD, not just the short <p>
    assert "\n" not in first["description"]


def test_thousands_price_and_pickup():
    second = _parse()[1]
    assert second["price"] == "1.250 €"
    assert second["shipping"] == "Pickup only"
    assert second["location"] == "10115 Berlin"


def test_missing_fields_get_defaults():
    third = _parse()[2]
    assert third["price"] == "VB"
    assert third["location"] == "Unknown"
    assert third["description"] == ""


def test_empty_page():
    assert parse_listings_from_html("<html><body>Keine Ergebnisse</body></html>") == []
