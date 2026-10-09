"""CSV storage for listings (Excel-friendly: UTF-8 with BOM, ';' delimiter)."""
import csv
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from config import CSV_DATABASE_PATH, LEGACY_CSV_PATH
from evaluator import evaluate_listing
from logger import logger
from models import (
    CSV_FIELDS,
    SHIPPING_NO,
    SHIPPING_YES,
    STATUS_MATCH,
    STATUS_PARTIAL,
    STATUS_REJECTED,
    UNKNOWN_LOCATION,
    Listing,
)

LEGACY_PROFILE_NAME = "Legacy (ThinkPad donor)"


# ==========================================
# LOW LEVEL
# ==========================================
def _read_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _write_csv(rows: Iterable[Dict[str, str]], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, path)


# ==========================================
# LEGACY MIGRATION (old Russian-header donor_listings.csv)
# ==========================================
def _convert_legacy_row(row: Dict[str, str]) -> Dict[str, str]:
    status = row.get("Статус", "")
    shipping = row.get("Доставка", "")
    location = row.get("Местоположение", "")
    return Listing(
        id=row.get("ID", "") or row.get("Ссылка", ""),
        title=row.get("Модель / Заголовок", ""),
        price=row.get("Цена", ""),
        location=UNKNOWN_LOCATION if not location or location == "Не указано" else location,
        shipping=SHIPPING_YES if "Доставка возможна" in shipping else SHIPPING_NO,
        link=row.get("Ссылка", ""),
        profile=LEGACY_PROFILE_NAME,
        status=STATUS_MATCH if status == "MATCH" else STATUS_PARTIAL,
        note=row.get("Комментарий", ""),
        added_at=row.get("Дата добавления", ""),
    ).to_csv_row()


def migrate_legacy_csv(legacy_path: str = LEGACY_CSV_PATH, new_path: str = CSV_DATABASE_PATH) -> int:
    """Copies rows from the old file into the new schema once. The old file is left untouched."""
    if os.path.exists(new_path) or not os.path.exists(legacy_path):
        return 0
    rows = [
        _convert_legacy_row(r)
        for r in _read_csv(legacy_path)
        if r.get("Статус") in ("MATCH", "POTENTIAL")
    ]
    _write_csv(rows, new_path)
    logger.info(f"Migrated {len(rows)} listings from {os.path.basename(legacy_path)} to {os.path.basename(new_path)}")
    return len(rows)


# ==========================================
# PUBLIC API
# ==========================================
def load_listings(path: str = CSV_DATABASE_PATH) -> List[Listing]:
    try:
        return [Listing.from_csv_row(r) for r in _read_csv(path)]
    except (OSError, csv.Error) as e:
        logger.warning(f"Warning: cannot read {path}: {e}")
        return []


def save_listings(listings: Iterable[Listing], path: str = CSV_DATABASE_PATH) -> None:
    _write_csv((listing.to_csv_row() for listing in listings), path)


def _sort_key(listing: Listing) -> Tuple[str, int]:
    return listing.added_at or "", 1 if listing.status == STATUS_MATCH else 0


def upsert_listings(
    items: Iterable[Union[Listing, Dict[str, Any]]],
    path: str = CSV_DATABASE_PATH,
    now: Optional[str] = None,
) -> Tuple[int, int]:
    """Adds new MATCH/PARTIAL listings and refreshes known ones (keeps user notes and added_at).
    Returns (added, total)."""
    existing = load_listings(path)
    by_key = {item.key: item for item in existing if item.key}
    now = now or datetime.now().strftime("%Y-%m-%d %H:%M")
    added = 0

    for raw in items:
        item = raw if isinstance(raw, Listing) else Listing.from_dict(raw)
        if item.status not in (STATUS_MATCH, STATUS_PARTIAL) or not item.key:
            continue
        old = by_key.get(item.key)
        if old:
            item.note = old.note
            item.added_at = old.added_at
            for attr in ("location", "posted", "description"):
                if not getattr(item, attr) or getattr(item, attr) == UNKNOWN_LOCATION:
                    setattr(item, attr, getattr(old, attr))
            existing[existing.index(old)] = item
        else:
            item.added_at = now
            existing.append(item)
            added += 1
        by_key[item.key] = item

    existing.sort(key=_sort_key, reverse=True)
    save_listings(existing, path)
    return added, len(existing)


def save_note(item_id: str, note: str, path: str = CSV_DATABASE_PATH) -> bool:
    listings = load_listings(path)
    for listing in listings:
        if listing.key == str(item_id):
            listing.note = (note or "").strip()
            save_listings(listings, path)
            return True
    return False


def reevaluate(settings: Dict[str, Any], path: str = CSV_DATABASE_PATH) -> Tuple[int, int]:
    """Re-checks stored listings against the current profiles (by profile name).
    Listings that are now rejected are removed. Returns (updated, removed)."""
    profiles = {p["name"]: p for p in settings.get("profiles", [])}
    global_exclude = settings.get("global_exclude", [])
    kept, updated, removed = [], 0, 0
    for listing in load_listings(path):
        profile = profiles.get(listing.profile)
        if not profile:
            kept.append(listing)
            continue
        result = evaluate_listing(listing.to_dict(), profile, global_exclude)
        if result["status"] == STATUS_REJECTED:
            removed += 1
            logger.info(f"  removed: {listing.title} ({result['reason']})")
            continue
        if (result["status"], result["missing"]) != (listing.status, listing.missing):
            updated += 1
        kept.append(Listing.from_dict(result))
    save_listings(kept, path)
    return updated, removed
