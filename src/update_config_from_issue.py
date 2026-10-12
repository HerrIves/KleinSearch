"""Utility to parse and validate search settings from a GitHub Issue body and update config.json."""
import json
import os
import re
import sys
from typing import Any, Dict

import config


def extract_json_from_body(body: str) -> Dict[str, Any]:
    """Finds JSON inside code blocks or parses raw text."""
    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", body, re.IGNORECASE)
    raw = code_match.group(1) if code_match else body.strip()
    return json.loads(raw)


def update_from_issue_body(body: str, target_path: str = config.ROOT_CONFIG_PATH) -> Dict[str, Any]:
    """Extracts, normalizes, sanitizes and saves settings from an issue body."""
    raw = extract_json_from_body(body)
    normalized = config.normalize_settings(raw)
    if "telegram" in normalized:
        normalized["telegram"]["bot_token"] = ""
    config.save_settings(normalized, target_path)
    return normalized


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python src/update_config_from_issue.py <body_or_path>")
        sys.exit(1)

    arg = sys.argv[1]
    if os.path.exists(arg):
        with open(arg, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = arg

    try:
        updated = update_from_issue_body(content)
        print(f"SUCCESS: Updated config with {len(updated['profiles'])} profiles.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
