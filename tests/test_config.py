import json

import config


def test_missing_file_returns_defaults(tmp_path):
    settings = config.load_settings(str(tmp_path / "nope.json"))
    assert settings == config.DEFAULT_SETTINGS
    assert settings is not config.DEFAULT_SETTINGS  # a copy, safe to mutate


def test_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "config.json")
    saved = config.save_settings(
        {
            "global_exclude": ["suche"],
            "profiles": [
                {
                    "name": "  Bikes  ",
                    "queries": ["rennrad", "rennrad", ""],
                    "price_max": "300",
                    "pages": 2,
                    "must_have": ["shimano"],
                }
            ],
        },
        path,
    )
    assert config.load_settings(path) == saved
    profile = saved["profiles"][0]
    assert profile["name"] == "Bikes"
    assert profile["queries"] == ["rennrad"]  # de-duplicated, empty removed
    assert profile["price_max"] == 300
    assert profile["price_min"] is None
    assert profile["enabled"] is True


def test_normalize_profile_coercion():
    p = config.normalize_profile(
        {"pages": 999, "price_min": 500, "price_max": 100, "category": "c278 ", "queries": "a\nb\r\n\nc"}
    )
    assert p["pages"] == config.MAX_PAGES_LIMIT
    assert (p["price_min"], p["price_max"]) == (100, 500)  # swapped
    assert p["category"] == "278"
    assert p["queries"] == ["a", "b", "c"]
    assert p["name"] == "New search"


def test_invalid_numbers_become_none():
    p = config.normalize_profile({"price_min": "abc", "price_max": -5, "pages": "x"})
    assert p["price_min"] is None and p["price_max"] is None
    assert p["pages"] == config.PROFILE_TEMPLATE["pages"]


def test_legacy_format_is_migrated(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"DEFAULT_MAX_PRICE": 500, "MAX_PAGES": 3, "TARGET_QUERIES": [{"name": "apple m1", "query": "apple m1"}]}),
        encoding="utf-8",
    )
    settings = config.load_settings(str(path))
    assert settings["profiles"][0]["queries"] == ["apple m1"]
    assert settings["profiles"][0]["price_max"] == 500
    assert settings["profiles"][0]["pages"] == 3
    assert settings["global_exclude"] == config.DEFAULT_GLOBAL_EXCLUDE


def test_broken_json_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ not json", encoding="utf-8")
    assert config.load_settings(str(path)) == config.DEFAULT_SETTINGS


def test_normalize_telegram_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok_env")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat_env")
    monkeypatch.setenv("TELEGRAM_ENABLED", "true")
    res = config.normalize_telegram({})
    assert res["bot_token"] == "tok_env"
    assert res["chat_id"] == "chat_env"
    assert res["enabled"] is True

    monkeypatch.setenv("TELEGRAM_ENABLED", "false")
    res2 = config.normalize_telegram({})
    assert res2["enabled"] is False
