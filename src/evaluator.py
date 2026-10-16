"""Product-agnostic evaluation of listings against a search profile."""
import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from logger import logger
from matcher import first_excluded, split_criteria
from models import STATUS_MATCH, STATUS_PARTIAL, STATUS_REJECTED

BASE_URL = "https://www.kleinanzeigen.de"
LOCATION_ENDPOINT = "https://www.kleinanzeigen.de/s-ort-empfehlungen.json"

# Radius steps offered by the Kleinanzeigen search form (values in between are not reliable).
ALLOWED_RADII = (5, 10, 20, 30, 50, 100, 150, 200)

_LOCATION_CACHE: Dict[str, Optional[str]] = {
    "59821": "1811",
    "arnsberg": "1810",
    "berlin": "3331",
    "10115": "9668",
    "münchen": "6411",
    "muenchen": "6411",
    "frankfurt am main": "4292",
    "köln": "945",
    "koeln": "945",
    "hamburg": "9409",
}


class LocationNotResolved(ValueError):
    """A search location was requested but could not be turned into a Kleinanzeigen location id.

    Building the URL anyway would silently search all of Germany."""


def snap_radius(radius: int) -> int:
    """Smallest radius offered by the site that is >= `radius` (capped at the largest)."""
    return next((r for r in ALLOWED_RADII if r >= radius), ALLOWED_RADII[-1])


def resolve_location_id(location: str, timeout: float = 4.0) -> Optional[str]:
    """Resolves a postal code, city name, or location string to a Kleinanzeigen location ID.

    Uses Kleinanzeigen's s-ort-empfehlungen.json autocomplete endpoint.
    Successful results are cached in-memory; failures are not, so a temporary network
    problem does not poison the rest of the run.
    If location already looks like a location ID (e.g. 'l1811' or 'L3331'), the ID is extracted.
    Returns None if location is empty or cannot be resolved.
    """
    if not location or not location.strip():
        return None
    loc_clean = location.strip()
    if re.fullmatch(r"[lL]\d+", loc_clean):
        return loc_clean[1:]

    cache_key = loc_clean.lower()
    if cache_key in _LOCATION_CACHE:
        return _LOCATION_CACHE[cache_key]

    url = f"{LOCATION_ENDPOINT}?query={urllib.parse.quote(loc_clean)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            loc_id = next((k.lstrip("_") for k in data.keys() if k != "_0" and k.startswith("_")), None)
            if loc_id:
                _LOCATION_CACHE[cache_key] = loc_id
            return loc_id
    except Exception as e:
        logger.debug(f"Failed to resolve location '{location}': {e}")
        return None


def clear_location_cache() -> None:
    """Clears the location cache (useful in tests)."""
    _LOCATION_CACHE.clear()


def make_search_url(
    query: str,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    category: str = "",
    page: int = 1,
    location: str = "",
    radius: Optional[int] = None,
) -> str:
    """Builds a Kleinanzeigen search URL.

    Format (verified against the live site):
      /s-preis:<min>:<max>/seite:<n>/<query-slug>/k0c<category>l<location_id>r<radius>

    Raises LocationNotResolved if a location is given but cannot be resolved (instead of
    quietly dropping it and searching all of Germany). The radius is only used together with
    a location and is rounded up to a step the site offers.
    """
    slug = urllib.parse.quote("-".join(query.lower().split()))
    segments = []
    if price_min is not None or price_max is not None:
        segments.append(f"preis:{'' if price_min is None else price_min}:{'' if price_max is None else price_max}")
    if page > 1:
        segments.append(f"seite:{page}")
    segments.append(slug)

    if radius and not (location and location.strip()):
        raise LocationNotResolved("Search radius requires a city or postal code")

    loc_id = None
    if location and location.strip():
        loc_id = resolve_location_id(location)
        if not loc_id:
            raise LocationNotResolved(f"Cannot resolve location '{location}'")

    category_part = f"c{category}" if category else ""
    loc_part = f"l{loc_id}" if loc_id else ""
    radius_part = f"r{snap_radius(radius)}" if (radius and loc_id) else ""
    return f"{BASE_URL}/s-{'/'.join(segments)}/k0{category_part}{loc_part}{radius_part}"


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
