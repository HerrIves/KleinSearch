import json
import pytest

from update_config_from_issue import extract_json_from_body, update_from_issue_body


def test_extract_json_from_body_code_block():
    body = """
    Please update my settings:
    ```json
    {
      "profiles": [{"name": "Test", "queries": ["query1"]}]
    }
    ```
    Thanks!
    """
    res = extract_json_from_body(body)
    assert res["profiles"][0]["name"] == "Test"


def test_extract_json_from_body_plain_text():
    body = '{"profiles": [{"name": "Plain"}]}'
    res = extract_json_from_body(body)
    assert res["profiles"][0]["name"] == "Plain"


def test_update_from_issue_body_sanitizes_token(tmp_path):
    body = """
    ```json
    {
      "telegram": {"enabled": true, "bot_token": "SECRET123"},
      "profiles": [{"name": "Phones", "queries": ["pixel"]}]
    }
    ```
    """
    target = str(tmp_path / "config.json")
    saved = update_from_issue_body(body, target_path=target)
    assert saved["profiles"][0]["name"] == "Phones"
    assert saved["telegram"]["bot_token"] == ""

    with open(target, "r", encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["telegram"]["bot_token"] == ""
    assert on_disk["profiles"][0]["name"] == "Phones"


def test_update_from_invalid_json():
    with pytest.raises(Exception):
        extract_json_from_body("not a json at all")
