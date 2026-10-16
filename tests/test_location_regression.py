"""Regression tests for PLZ 59821, location errors, and stale CSV results."""
import json
from unittest.mock import patch

import pytest

from evaluator import make_search_url
from models import Listing
from storage import load_listings, reevaluate, save_listings


@pytest.mark.parametrize("location,location_id", [("59821", "1811"), ("Arnsberg", "1810")])
def test_arnsberg_100km_url(location, location_id):
    url = make_search_url("macbook", location=location, radius=100)
    assert url == f"https://www.kleinanzeigen.de/s-macbook/k0l{location_id}r100"


@pytest.mark.parametrize("location,radius", [("", 100), ("  ", 100), ("not-a-known-place", 100)])
def test_radius_fails_closed_without_valid_location(location, radius):
    with patch("evaluator.resolve_location_id", return_value=None):
        with pytest.raises(ValueError):
            make_search_url("macbook", location=location, radius=radius)


def test_unresolvable_location_without_radius_also_fails_closed():
    with patch("evaluator.resolve_location_id", return_value=None):
        with pytest.raises(ValueError):
            make_search_url("macbook", location="invalid-place")


def test_repeated_transient_lookup_failure_can_retry(monkeypatch):
    from evaluator import resolve_location_id
    from unittest.mock import MagicMock

    response = MagicMock()
    response.read.return_value = b'{"_0":"Deutschland","_876543":"Sample town"}'
    response.__enter__.return_value = response
    attempts = []

    def lookup(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("temporary outage")
        return response

    monkeypatch.setattr("urllib.request.urlopen", lookup)
    assert resolve_location_id("unique-regression-test-town") is None
    assert resolve_location_id("unique-regression-test-town") == "876543"
    assert len(attempts) == 2


def test_changed_radius_removes_stale_results(tmp_path):
    path = str(tmp_path / "listings.csv")
    old = json.dumps(["59821", 200], ensure_ascii=False)
    save_listings([Listing(id="1", title="Laptop", profile="Mac", status="MATCH", location_scope=old)], path)
    settings = {"profiles": [{"name": "Mac", "location": "59821", "radius": 100}]}
    updated, removed = reevaluate(settings, path)
    assert removed == 1
    assert load_listings(path) == []


def test_same_location_radius_keeps_results(tmp_path):
    path = str(tmp_path / "listings.csv")
    scope = json.dumps(["59821", 100], ensure_ascii=False)
    save_listings([Listing(id="1", title="Laptop", profile="Mac", status="MATCH", location_scope=scope)], path)
    settings = {"profiles": [{"name": "Mac", "location": "59821", "radius": 100}]}
    _, removed = reevaluate(settings, path)
    assert removed == 0
    assert len(load_listings(path)) == 1


def test_legacy_unscoped_local_results_are_removed(tmp_path):
    path = str(tmp_path / "listings.csv")
    save_listings([Listing(id="1", title="Laptop", profile="Mac", status="MATCH")], path)
    settings = {"profiles": [{"name": "Mac", "location": "59821", "radius": 100}]}
    _, removed = reevaluate(settings, path)
    assert removed == 1


def test_legacy_unscoped_countrywide_results_are_preserved(tmp_path):
    path = str(tmp_path / "listings.csv")
    save_listings([Listing(id="1", title="Laptop", profile="Mac", status="MATCH")], path)
    settings = {"profiles": [{"name": "Mac", "location": "", "radius": None}]}
    _, removed = reevaluate(settings, path)
    assert removed == 0
    assert len(load_listings(path)) == 1
