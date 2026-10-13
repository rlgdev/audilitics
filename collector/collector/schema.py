"""Schema of one get2.php item (spec 3.3), validated with pydantic (spec 4.2 step 4).

Validation checks that every known field is present, including the five fields of spec 3.5; the items are then
redacted and only the redacted fields reach the pydantic model. `FeedItem` therefore has no attribute for a
discarded field (spec 3.5).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from collector.redact import DISCARDED, redact_items

KEPT_FIELDS = (
    "model", "silnik", "silnik2", "dealer", "dealer_nr", "cena_katalogowa", "cena_vtp", "cena_historyczna",
    "cena_historyczna_katalogowa", "rata", "stara_rata", "rata_historyczna", "rok_produkcji", "rok_modelowy",
    "kod_modelowy", "id", "business_edition", "stock_cleaning", "moj_elektryk",
)
KNOWN_FIELDS = KEPT_FIELDS + DISCARDED


class FeedItem(BaseModel):
    """A redacted feed item. All fields arrive as strings; an empty string means null."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=False)

    model: str
    silnik: str
    silnik2: str
    dealer: str
    dealer_nr: str
    cena_katalogowa: str
    cena_vtp: str
    cena_historyczna: str
    cena_historyczna_katalogowa: str
    rata: str
    stara_rata: str
    rata_historyczna: str
    rok_produkcji: str
    rok_modelowy: str
    kod_modelowy: str
    id: str
    business_edition: str
    stock_cleaning: str
    moj_elektryk: str


class SchemaError(Exception):
    pass


def check_fields(items: list[dict[str, Any]], require_discarded: bool) -> list[str]:
    """Fail on a missing known field; return the sorted unknown field names."""
    required = KNOWN_FIELDS if require_discarded else KEPT_FIELDS
    unknown: set[str] = set()
    for i, raw in enumerate(items):
        missing = [f for f in required if f not in raw]
        if missing:
            raise SchemaError(f"item {i}: missing known field(s) {', '.join(missing)}")
        unknown.update(k for k in raw if k not in KNOWN_FIELDS)
    return sorted(unknown)


def validate_and_redact(items: list[dict[str, Any]], require_discarded: bool = True,
                        discarded: tuple[str, ...] = DISCARDED) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Live path (spec 4.2 steps 4-5): check fields, redact, then type-check the redacted items.

    Returns the redacted items, unknown fields kept in `extra`, and unknown fields dropped as identifying.
    `require_discarded=False` is used when replaying an archived raw file, which is already redacted.
    """
    unknown = check_fields(items, require_discarded)
    redacted, dropped = redact_items(items, discarded, KNOWN_FIELDS)
    for i, r in enumerate(redacted):
        coerced = {k: ("" if v is None else str(v)) if k in KEPT_FIELDS else v for k, v in r.items()}
        try:
            FeedItem.model_validate(coerced)
        except ValidationError as e:
            raise SchemaError(f"item {i}: {e}") from e
        redacted[i] = coerced
    kept_unknown = [u for u in unknown if u not in dropped]
    return redacted, kept_unknown, dropped


def parse(items: list[dict[str, Any]]) -> list[FeedItem]:
    return [FeedItem.model_validate(it) for it in items]
