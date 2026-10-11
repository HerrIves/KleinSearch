from unittest.mock import patch

from main import AppController, _parse_loop_interval


def test_parse_loop_interval_default_flag():
    assert _parse_loop_interval(["--no-ui", "--loop"]) == 60
    assert _parse_loop_interval(["--interval"]) == 60


def test_parse_loop_interval_explicit_minutes():
    assert _parse_loop_interval(["--no-ui", "--loop", "30"]) == 30
    assert _parse_loop_interval(["--interval", "15"]) == 15


def test_parse_loop_interval_environment_variable(monkeypatch):
    monkeypatch.setenv("SCAN_INTERVAL_MINUTES", "45")
    assert _parse_loop_interval(["--no-ui"]) == 45


def test_parse_loop_interval_none_when_interactive():
    assert _parse_loop_interval([]) is None


def test_app_controller_basics(tmp_path):
    config_file = str(tmp_path / "config.json")
    csv_file = str(tmp_path / "listings.csv")
    controller = AppController(config_path=config_file, csv_path=csv_file)

    settings = controller.get_settings()
    assert "profiles" in settings

    settings["profiles"] = [{"name": "Test Search", "enabled": True}]
    saved = controller.save_settings(settings)
    assert len(saved["profiles"]) == 1

    assert controller.request_scan() is True
    assert controller.scan_requested.is_set()


@patch("notifier.test_telegram_connection")
def test_app_controller_telegram_test(mock_test):
    mock_test.return_value = (True, "OK")
    controller = AppController()
    res = controller.test_telegram("fake_token", "fake_chat")
    assert res == {"ok": True, "message": "OK"}


@patch("subprocess.run")
def test_app_controller_sync_github(mock_run, tmp_path):
    config_file = str(tmp_path / "config.json")
    controller = AppController(config_path=config_file)
    controller.save_settings({"telegram": {"bot_token": "secret_token"}, "profiles": []})

    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = " M config.json"
    mock_run.return_value.stderr = ""

    root_file = str(tmp_path / "root_config.json")
    res = controller.sync_github(root_config_path=root_file)
    assert res["ok"] is True
    assert "synced" in res["message"].lower() or "already" in res["message"].lower()
