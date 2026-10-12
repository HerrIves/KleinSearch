from io import BytesIO
import json
from unittest.mock import MagicMock, patch
import urllib.error

from models import Listing
import notifier


def _fake_response(data: dict, status: int = 200):
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode("utf-8")
    resp.status = status
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = None
    return resp


def test_send_telegram_message_validation():
    ok, err = notifier.send_telegram_message("", "123", "hello")
    assert not ok and "empty" in err

    ok, err = notifier.send_telegram_message("token", "", "hello")
    assert not ok and "empty" in err


@patch("urllib.request.urlopen")
def test_send_telegram_message_success(mock_urlopen):
    mock_urlopen.return_value = _fake_response({"ok": True, "result": {"message_id": 1}})
    ok, msg = notifier.send_telegram_message("tok123", "chat456", "<b>test</b>")
    assert ok is True
    assert msg == "OK"

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://api.telegram.org/bottok123/sendMessage"
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["chat_id"] == "chat456"
    assert payload["text"] == "<b>test</b>"
    assert payload["parse_mode"] == "HTML"


@patch("urllib.request.urlopen")
def test_send_telegram_message_api_error(mock_urlopen):
    mock_urlopen.return_value = _fake_response({"ok": False, "description": "Forbidden: bot was blocked by user"})
    ok, err = notifier.send_telegram_message("tok123", "chat456", "test")
    assert ok is False
    assert "blocked" in err


@patch("urllib.request.urlopen")
def test_send_telegram_message_http_error(mock_urlopen):
    err_body = json.dumps({"ok": False, "description": "Unauthorized"}).encode("utf-8")
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://api.telegram.org",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=BytesIO(err_body),
    )
    ok, err = notifier.send_telegram_message("tok123", "chat456", "test")
    assert ok is False
    assert "Unauthorized" in err


def test_format_listing_message_escaping():
    ad = Listing(
        id="123",
        title="MacBook <M1> & Pro",
        profile="Apple & Deals",
        price="850 €",
        location="Berlin",
        shipping="Shipping possible",
        link="https://kleinanzeigen.de/ad/123",
        status="MATCH",
        matched=["m1 pro", "32gb"],
        missing=[],
        note="Great seller <3",
    )
    msg = notifier.format_listing_message(ad)
    assert "&lt;M1&gt; &amp; Pro" in msg
    assert "Apple &amp; Deals" in msg
    assert "https://kleinanzeigen.de/ad/123" in msg
    assert "850 €" in msg
    assert "Great seller &lt;3" in msg
    assert "🎯" in msg


def test_notified_ids_persistence(tmp_path):
    path = str(tmp_path / "notified.json")
    assert notifier.load_notified_ids(path) == set()

    notifier.save_notified_ids({"item1", "item2"}, path)
    loaded = notifier.load_notified_ids(path)
    assert loaded == {"item1", "item2"}


@patch("notifier.send_telegram_message")
def test_notify_listings_skips_when_disabled(mock_send, tmp_path):
    path = str(tmp_path / "notified.json")
    ad = Listing(id="1", status="MATCH", title="MacBook")
    settings = {"telegram": {"enabled": False, "bot_token": "abc", "chat_id": "123"}}

    sent = notifier.notify_listings([ad], settings, path=path)
    assert sent == 0
    mock_send.assert_not_called()


@patch("notifier.send_telegram_message")
def test_notify_listings_sends_and_deduplicates(mock_send, tmp_path):
    mock_send.return_value = (True, "OK")
    path = str(tmp_path / "notified.json")

    ad1 = Listing(id="1", status="MATCH", title="MacBook 1", link="https://x/1")
    ad2 = Listing(id="2", status="PARTIAL", title="MacBook 2", link="https://x/2")
    ad3 = Listing(id="3", status="MATCH", title="MacBook 3", link="https://x/3")

    settings = {
        "telegram": {
            "enabled": True,
            "bot_token": "token123",
            "chat_id": "chat123",
            "notify_on": ["MATCH"],
        }
    }

    # First run: ad1 and ad3 are MATCH, ad2 is PARTIAL (ignored)
    sent = notifier.notify_listings([ad1, ad2, ad3], settings, path=path)
    assert sent == 2
    assert mock_send.call_count == 2
    assert notifier.load_notified_ids(path) == {"1", "3"}

    # Second run with same listings: should be deduplicated, 0 sent
    mock_send.reset_mock()
    sent2 = notifier.notify_listings([ad1, ad3], settings, path=path)
    assert sent2 == 0
    mock_send.assert_not_called()


@patch("notifier.send_telegram_message")
def test_test_telegram_connection(mock_send):
    mock_send.return_value = (True, "OK")
    ok, msg = notifier.test_telegram_connection("token", "chat")
    assert ok is True
    assert msg == "OK"
    assert "Test" in mock_send.call_args[0][2]


@patch("notifier.send_telegram_message")
def test_notify_listings_partial_requires_at_least_one_matched(mock_send, tmp_path):
    mock_send.return_value = (True, "OK")
    path = str(tmp_path / "notified.json")

    # Has 1 criterion matched
    ad_with_match = Listing(id="1", status="PARTIAL", title="MacBook 1", link="https://x/1", matched=["32gb"], missing=["m1 max"])
    # Has 0 criteria matched
    ad_zero_match = Listing(id="2", status="PARTIAL", title="MacBook 2", link="https://x/2", matched=[], missing=["32gb"])

    settings = {
        "telegram": {
            "enabled": True,
            "bot_token": "token123",
            "chat_id": "chat123",
            "notify_on": ["MATCH", "PARTIAL"],
        }
    }

    sent = notifier.notify_listings([ad_with_match, ad_zero_match], settings, path=path)
    assert sent == 1
    assert mock_send.call_count == 1
    assert "MacBook 1" in mock_send.call_args[0][2]
