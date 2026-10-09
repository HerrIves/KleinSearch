"""Renders index.html from data/listings.csv and the current settings."""
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import config
from logger import logger
from models import CSV_FIELDS
from storage import load_listings

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.html")


def _json_for_script(value: Any) -> str:
    """JSON that is safe to embed inside a <script> tag."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_dashboard(listings: list, settings: Dict[str, Any], generated_at: Optional[str] = None) -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    for_placeholder = {
        "__DATA_JSON__": _json_for_script(listings),
        "__SETTINGS_JSON__": _json_for_script(settings),
        "__CSV_FIELDS_JSON__": _json_for_script(CSV_FIELDS),
        "__GENERATED_AT__": generated_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    pattern = re.compile("|".join(re.escape(k) for k in for_placeholder))
    return pattern.sub(lambda m: for_placeholder[m.group(0)], html)


def generate_dashboard(
    csv_path: str = config.CSV_DATABASE_PATH,
    html_path: str = config.HTML_DASHBOARD_PATH,
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    settings = settings if settings is not None else config.load_settings()
    listings = [item.to_dict() for item in load_listings(csv_path)]
    html = render_dashboard(listings, settings)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Dashboard written: {html_path} ({len(listings)} listings)")
    return html_path


if __name__ == "__main__":
    generate_dashboard()
