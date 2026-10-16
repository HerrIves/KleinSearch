import pytest

import evaluator
from evaluator import LocationNotResolved, make_search_url, snap_radius


@pytest.mark.parametrize("radius,expected", [(1, 5), (5, 5), (15, 20), (80, 100), (100, 100), (201, 200), (999, 200)])
def test_snap_radius(radius, expected):
    assert snap_radius(radius) == expected


def test_zip_with_radius_builds_site_filter():
    assert make_search_url("fernseher", category="175", price_max=100, location="59821", radius=100) == \
        "https://www.kleinanzeigen.de/s-preis::100/fernseher/k0c175l1811r100"


def test_url_uses_site_radius_step():
    assert make_search_url("tv", location="59821", radius=80).endswith("/k0l1811r100")


def test_radius_without_location_raises():
    with pytest.raises(LocationNotResolved):
        make_search_url("tv", radius=50)


def test_unresolved_location_raises_instead_of_nationwide_search(monkeypatch):
    def fail(req, timeout=4.0):
        raise OSError("blocked")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(LocationNotResolved):
        make_search_url("tv", location="Nirgendwostadt", radius=50)


def test_failed_lookup_is_not_cached(monkeypatch):
    calls = {"n": 0}

    def fail(req, timeout=4.0):
        calls["n"] += 1
        raise OSError("blocked")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    assert evaluator.resolve_location_id("Retrystadt") is None
    assert evaluator.resolve_location_id("Retrystadt") is None
    assert calls["n"] == 2
