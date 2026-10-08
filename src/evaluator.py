"""Product-agnostic evaluation of listings against a search profile."""
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from matcher import first_excluded, split_criteria
from models import STATUS_MATCH, STATUS_PARTIAL, STATUS_REJECTED

BASE_URL = "https://www.kleinanzeigen.de"


def make_search_url(
    query: str,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    category: str = "",
    page: int = 1,
) -> str:
    """Builds a Kleinanzeigen search URL.

    Format (verified against the live site):
      /s-preis:<min>:<max>/seite:<n>/<query-slug>/k0c<category>
    """
    slug = urllib.parse.quote("-".join(query.lower().split()))
    segments = []
    if price_min is not None or price_max is not None:
        segments.append(f"preis:{'' if price_min is None else price_min}:{'' if price_max is None else price_max}")
    if page > 1:
        segments.append(f"seite:{page}")
    segments.append(slug)
    category_part = f"c{category}" if category else ""
    return f"{BASE_URL}/s-{'/'.join(segments)}/k0{category_part}"


_PRICE_RE = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")


def parse_price_value(price_str: str) -> Optional[float]:
    """'1.200 € VB' -> 1200.0, '120,50 €' -> 120.5, 'Zu verschenken' -> 0.0, 'VB' -> None."""
    if not price_str:
        return None
    if "verschenken" in price_str.lower():
        return 0.0
    m = _PRICE_RE.search(price_str)
    if not m:
        return None
    try:
        return float(m.group(0).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def listing_text(item: Dict[str, Any]) -> str:
    return f"{item.get('title') or ''}\n{item.get('description') or ''}"


def evaluate_listing(
    item: Dict[str, Any],
    profile: Dict[str, Any],
    global_exclude: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Returns a copy of `item` with status / matched / missing / reason / profile set."""
    result = dict(item)
    result["profile"] = profile.get("name", "")
    result["matched"], result["missing"] = [], []
    text = listing_text(item)

    price = parse_price_value(item.get("price") or "")
    price_min, price_max = profile.get("price_min"), profile.get("price_max")
    if price is not None and price_min is not None and price < price_min:
        result.update(status=STATUS_REJECTED, reason=f"Price below {price_min} €")
        return result
    if price is not None and price_max is not None and price > price_max:
        result.update(status=STATUS_REJECTED, reason=f"Price above {price_max} €")
        return result

    excluded = first_excluded(text, list(global_exclude or []) + list(profile.get("exclude") or []))
    if excluded:
        result.update(status=STATUS_REJECTED, reason=f"Excluded word: {excluded}")
        return result

    criteria = profile.get("must_have") or []
    matched, missing = split_criteria(text, criteria)
    result["matched"], result["missing"] = matched, missing
    if not missing:
        reason = f"All criteria found ({len(matched)}/{len(matched)})" if matched else "No criteria set"
        result.update(status=STATUS_MATCH, reason=reason)
    else:
        total = len(matched) + len(missing)
        result.update(
            status=STATUS_PARTIAL,
            reason=f"{len(matched)}/{total} criteria; missing: {', '.join(missing)}",
        )
    return result
