"""Telegram notifications for newly found matching listings."""
from html import escape
import json
import logging
import os
from typing import Any, Dict, List, Set, Tuple
import urllib.error
import urllib.parse
import urllib.request

import config
from models import Listing, STATUS_MATCH, STATUS_PARTIAL

logger = logging.getLogger("scanner")


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    timeout: int = 10,
) -> Tuple[bool, str]:
    """Sends an HTML-formatted message via the official Telegram Bot API."""
    token = (bot_token or "").strip()
    chat = (chat_id or "").strip()
    if not token or not chat:
        return False, "Bot token or Chat ID is empty"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                return True, "OK"
            return False, str(body.get("description", "Unknown Telegram API error"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            return False, str(err_body.get("description", str(e)))
        except Exception:
            return False, str(e)
    except Exception as e:
        return False, str(e)


def format_listing_message(listing: Listing) -> str:
    """Formats a listing into a clean HTML message with link, price, and specs."""
    status_icon = "🎯" if listing.status == "MATCH" else "⚠️"
    title_esc = escape(listing.title or "Untitled ad")
    profile_esc = escape(listing.profile or "Default")
    price_esc = escape(listing.price or "No price")
    loc_esc = escape(listing.location or "Unknown")
    ship_esc = escape(listing.shipping or "")
    link = listing.link or "https://www.kleinanzeigen.de"

    lines = [
        f"{status_icon} <b>KleinSearch: {escape(listing.status)}</b>",
        f"📁 <b>Profile:</b> {profile_esc}",
        f"🏷️ <b>Title:</b> <a href=\"{link}\">{title_esc}</a>",
        f"💰 <b>Price:</b> <code>{price_esc}</code>",
        f"📍 <b>Location:</b> {loc_esc} | {ship_esc}",
    ]
    if listing.matched:
        matched_str = escape(", ".join(listing.matched))
        lines.append(f"✅ <b>Matched:</b> {matched_str}")
    if listing.missing:
        missing_str = escape(", ".join(listing.missing))
        lines.append(f"❌ <b>Missing:</b> {missing_str}")
    if listing.note:
        note_str = escape(listing.note)
        lines.append(f"📝 <b>Note:</b> {note_str}")

    return "\n".join(lines)


def load_notified_ids(path: str = config.NOTIFIED_IDS_PATH) -> Set[str]:
    """Loads previously notified listing keys to prevent duplicate messages."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except Exception as e:
        logger.warning(f"Failed to read notified IDs from {path}: {e}")
        return set()


def save_notified_ids(ids: Set[str], path: str = config.NOTIFIED_IDS_PATH) -> None:
    """Atomically saves notified keys to disk."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(ids)), f, indent=2)
    os.replace(tmp_path, path)


def notify_listings(
    listings: List[Listing],
    settings: Dict[str, Any],
    path: str = config.NOTIFIED_IDS_PATH,
) -> int:
    """Sends alerts for newly found matching listings according to user settings."""
    tg = settings.get("telegram") or {}
    if not tg.get("enabled"):
        return 0

    token = tg.get("bot_token")
    chat = tg.get("chat_id")
    if not token or not chat:
        return 0

    notify_on = set(tg.get("notify_on") or [STATUS_MATCH])
    candidates = []
    for item in listings:
        if not item.key:
            continue
        if item.status == STATUS_MATCH and STATUS_MATCH in notify_on:
            candidates.append(item)
        elif item.status == STATUS_PARTIAL and STATUS_PARTIAL in notify_on:
            # If must_have criteria exist, notify if at least one criterion matched!
            if item.matched or not item.missing:
                candidates.append(item)

    if not candidates:
        return 0

    notified = load_notified_ids(path)
    sent_count = 0

    for item in candidates:
        if item.key in notified:
            continue
        msg = format_listing_message(item)
        ok, err = send_telegram_message(token, chat, msg)
        if ok:
            notified.add(item.key)
            sent_count += 1
            logger.info(f"Telegram alert sent for: {item.title}")
        else:
            logger.error(f"Failed to send Telegram alert for {item.key}: {err}")

    if sent_count > 0:
        save_notified_ids(notified, path)

    return sent_count


def test_telegram_connection(bot_token: str, chat_id: str) -> Tuple[bool, str]:
    """Sends a verification message to confirm Bot Token and Chat ID work."""
    text = (
        "🔔 <b>KleinSearch Notification Test</b>\n\n"
        "Your Telegram bot is successfully connected to KleinSearch!\n"
        "You will receive alerts here when new matching ads are discovered."
    )
    return send_telegram_message(bot_token, chat_id, text)
