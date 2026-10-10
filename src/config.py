"""Paths and user settings.

User settings live in data/config.json and are edited from the dashboard.
Nothing in here is specific to any product: a search is described by
"profiles" (queries + price range + criteria + exclusions).
"""
import copy
import json
import os
from typing import Any, Dict, List, Optional

# ==========================================
# PATHS
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

BROWSER_PROFILE_DIR = os.path.join(DATA_DIR, "browser_profile")
CSV_DATABASE_PATH = os.path.join(DATA_DIR, "listings.csv")
LEGACY_CSV_PATH = os.path.join(DATA_DIR, "donor_listings.csv")
HTML_DASHBOARD_PATH = os.path.join(BASE_DIR, "index.html")
LOG_FILE_PATH = os.path.join(DATA_DIR, "scanner.log")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
NOTIFIED_IDS_PATH = os.path.join(DATA_DIR, "notified_ids.json")

# ==========================================
# DEFAULTS
# ==========================================
MAX_PAGES_LIMIT = 20

# Words that mark "wanted"/"swap" ads or ads that are no longer available.
DEFAULT_GLOBAL_EXCLUDE = ["suche", "gesucht", "tausche", "reserviert", "verkauft"]

DEFAULT_TELEGRAM_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "bot_token": "",
    "chat_id": "",
    "notify_on": ["MATCH"],
}

PROFILE_TEMPLATE: Dict[str, Any] = {
    "name": "New search",
    "enabled": True,
    "queries": [],
    "price_min": None,
    "price_max": None,
    "pages": 3,
    "category": "",
    "must_have": [],
    "exclude": [],
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "global_exclude": list(DEFAULT_GLOBAL_EXCLUDE),
    "telegram": dict(DEFAULT_TELEGRAM_SETTINGS),
    "profiles": [
        {
            "name": "MacBook M1 Pro/Max 32GB",
            "enabled": True,
            "queries": ["macbook m1 pro 32gb", "macbook m1 max 32gb"],
            "price_min": 300,
            "price_max": 1200,
            "pages": 2,
            "category": "278",
            "must_have": ["m1 pro|m1 max", "32gb"],
            "exclude": ["defekt", "icloud", "gesperrt"],
        }
    ],
}


# ==========================================
# NORMALIZATION
# ==========================================
def _to_list(value: Any) -> List[str]:
    """Accepts a list or a newline/comma separated string; returns clean non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.replace("\r", "").split("\n")
    elif isinstance(value, (list, tuple)):
        parts = [str(v) for v in value]
    else:
        parts = [str(value)]
    result = []
    for part in parts:
        part = " ".join(part.split())
        if part and part not in result:
            result.append(part)
    return result


def _to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def normalize_profile(raw: Dict[str, Any]) -> Dict[str, Any]:
    raw = raw or {}
    profile = copy.deepcopy(PROFILE_TEMPLATE)
    name = " ".join(str(raw.get("name") or "").split())
    profile["name"] = name or PROFILE_TEMPLATE["name"]
    profile["enabled"] = bool(raw.get("enabled", True))
    profile["queries"] = _to_list(raw.get("queries"))
    profile["price_min"] = _to_int(raw.get("price_min"))
    profile["price_max"] = _to_int(raw.get("price_max"))
    if (
        profile["price_min"] is not None
        and profile["price_max"] is not None
        and profile["price_min"] > profile["price_max"]
    ):
        profile["price_min"], profile["price_max"] = profile["price_max"], profile["price_min"]
    pages = _to_int(raw.get("pages")) or PROFILE_TEMPLATE["pages"]
    profile["pages"] = max(1, min(MAX_PAGES_LIMIT, pages))
    profile["category"] = "".join(ch for ch in str(raw.get("category") or "") if ch.isdigit())
    profile["must_have"] = _to_list(raw.get("must_have"))
    profile["exclude"] = _to_list(raw.get("exclude"))
    return profile


def _migrate_legacy(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Converts the old flat format (DEFAULT_MAX_PRICE / MAX_PAGES / TARGET_QUERIES)."""
    queries = []
    for q in raw.get("TARGET_QUERIES") or []:
        if isinstance(q, dict):
            queries.append(q.get("query") or q.get("name") or "")
        else:
            queries.append(str(q))
    return {
        "global_exclude": list(DEFAULT_GLOBAL_EXCLUDE),
        "profiles": [
            {
                "name": "My search",
                "queries": queries,
                "price_max": raw.get("DEFAULT_MAX_PRICE"),
                "pages": raw.get("MAX_PAGES"),
            }
        ],
    }


def normalize_telegram(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = raw or {}
    notify_on = raw.get("notify_on")
    if isinstance(notify_on, str):
        notify_on = [s.strip() for s in notify_on.split(",") if s.strip()]
    elif not isinstance(notify_on, list):
        notify_on = list(DEFAULT_TELEGRAM_SETTINGS["notify_on"])
    cleaned_notify = [s.upper() for s in notify_on if isinstance(s, str) and s.upper() in ("MATCH", "PARTIAL")]
    if not cleaned_notify:
        cleaned_notify = list(DEFAULT_TELEGRAM_SETTINGS["notify_on"])

    bot_token = str(raw.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = str(raw.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    enabled = bool(raw.get("enabled", False))
    return {
        "enabled": enabled,
        "bot_token": bot_token,
        "chat_id": chat_id,
        "notify_on": cleaned_notify,
    }


def normalize_settings(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = raw or {}
    if "profiles" not in raw and ("TARGET_QUERIES" in raw or "DEFAULT_MAX_PRICE" in raw):
        raw = _migrate_legacy(raw)
    profiles = [normalize_profile(p) for p in (raw.get("profiles") or []) if isinstance(p, dict)]
    global_exclude = raw.get("global_exclude")
    telegram = normalize_telegram(raw.get("telegram"))
    return {
        "global_exclude": _to_list(global_exclude) if global_exclude is not None else list(DEFAULT_GLOBAL_EXCLUDE),
        "telegram": telegram,
        "profiles": profiles,
    }


# ==========================================
# LOAD / SAVE
# ==========================================
def load_settings(path: str = CONFIG_PATH) -> Dict[str, Any]:
    """Reads settings from disk. Missing or broken file -> defaults (file is not overwritten)."""
    if not os.path.exists(path):
        return copy.deepcopy(DEFAULT_SETTINGS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return normalize_settings(json.load(f))
    except (OSError, ValueError) as e:
        print(f"Warning: cannot read {path}: {e}. Using defaults.")
        return copy.deepcopy(DEFAULT_SETTINGS)


def save_settings(settings: Dict[str, Any], path: str = CONFIG_PATH) -> Dict[str, Any]:
    """Normalizes and writes settings atomically. Returns what was actually saved."""
    normalized = normalize_settings(settings)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    return normalized
