"""Redaction at ingestion (spec 3.5, 4.2 step 5).

Five fields are removed from every feed item right after schema validation, before anything is written to disk,
logged or passed to normalisation. No hash, prefix or other derivative of them is kept. Unknown fields that look
like an identifier or a URL are dropped too (spec 4.3) and only their names are reported.
"""

from __future__ import annotations

import re
from typing import Any

DISCARDED = ("vin", "komisja", "link", "kod_audi", "telefon")

VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
URL_RE = re.compile(r"https?://", re.IGNORECASE)
IDENTIFIER_KEY_RE = re.compile(r"(vin|link|url|href|phone|telefon|komisja|email|mail|nr_rej|rejestr)", re.IGNORECASE)


def looks_identifying(key: str, value: Any) -> bool:
    """An unknown field is dropped when its name or value looks like an identifier or a URL (spec 4.3)."""
    if IDENTIFIER_KEY_RE.search(key):
        return True
    return isinstance(value, str) and bool(VIN_RE.search(value) or URL_RE.search(value))


def redact_item(item: dict[str, Any], discarded: tuple[str, ...] = DISCARDED,
                known: tuple[str, ...] = ()) -> tuple[dict[str, Any], list[str]]:
    """Return the item without the discarded fields and the names of unknown fields dropped as identifying."""
    out: dict[str, Any] = {}
    dropped: list[str] = []
    for k, v in item.items():
        if k in discarded:
            continue
        if known and k not in known and looks_identifying(k, v):
            dropped.append(k)
            continue
        out[k] = v
    return out, dropped


def redact_items(items: list[dict[str, Any]], discarded: tuple[str, ...] = DISCARDED,
                 known: tuple[str, ...] = ()) -> tuple[list[dict[str, Any]], list[str]]:
    redacted = []
    dropped: set[str] = set()
    for it in items:
        r, d = redact_item(it, discarded, known)
        redacted.append(r)
        dropped.update(d)
    return redacted, sorted(dropped)
