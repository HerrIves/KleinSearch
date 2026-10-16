"""Data model for a Kleinanzeigen listing and its CSV representation."""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

STATUS_MATCH = "MATCH"        # all criteria of the profile found in title/description
STATUS_PARTIAL = "PARTIAL"    # some criteria missing (listed in `missing`)
STATUS_REJECTED = "REJECTED"  # excluded word or price out of range (not stored)

SHIPPING_YES = "Shipping possible"
SHIPPING_NO = "Pickup only"
UNKNOWN_LOCATION = "Unknown"
NO_PRICE = "No price"

LIST_SEPARATOR = "; "

CSV_FIELDS = [
    "added_at",
    "status",
    "profile",
    "location_scope",
    "title",
    "price",
    "location",
    "shipping",
    "posted",
    "matched",
    "missing",
    "reason",
    "note",
    "description",
    "link",
    "id",
]


def _join(values: List[str]) -> str:
    return LIST_SEPARATOR.join(values or [])


def _split(value: str) -> List[str]:
    return [v.strip() for v in (value or "").split(LIST_SEPARATOR.strip()) if v.strip()]


@dataclass
class Listing:
    id: str = ""
    title: str = ""
    description: str = ""
    price: str = NO_PRICE
    location: str = UNKNOWN_LOCATION
    shipping: str = SHIPPING_NO
    posted: str = ""
    link: str = ""
    profile: str = ""
    location_scope: str = ""
    status: str = ""
    matched: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    reason: str = ""
    note: str = ""
    added_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Listing":
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data and data[k] is not None}
        for key in ("matched", "missing"):
            if isinstance(known.get(key), str):
                known[key] = _split(known[key])
        if "id" in known:
            known["id"] = str(known["id"])
        return cls(**known)

    def to_csv_row(self) -> Dict[str, str]:
        row = {name: getattr(self, name) for name in CSV_FIELDS}
        row["matched"] = _join(self.matched)
        row["missing"] = _join(self.missing)
        return {k: ("" if v is None else str(v)) for k, v in row.items()}

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> "Listing":
        return cls.from_dict({k: v for k, v in row.items() if k in CSV_FIELDS})

    @property
    def key(self) -> str:
        return str(self.id or self.link)
