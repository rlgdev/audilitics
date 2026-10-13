"""Redacted feed item -> typed offer (spec 4.2 step 7, spec 5.2, 5.5).

An offer exists only inside its snapshot: `offer_id` = `<date>/<n>` where n is the 1-based position in the
canonical order. The offer has no attribute for any field of spec 3.5.
"""

from __future__ import annotations

import hashlib
from typing import Any

from collector.rules import PROMO_KEYS, Rules
from collector.schema import KEPT_FIELDS, FeedItem

OFFER_FIELDS = (
    "offer_id", "model", "engine", "engine_group", "code", "model_year", "production_year", "dealer_nr", "dealer",
    "catalog", "special", "price_30d", "catalog_30d", "rate", "rate_old", "rate_30d", "business_edition",
    "stock_cleaning", "moj_elektryk", "promo_bits", "package_type", "footnote", "plan_code", "discount",
    "discount_pct", "config_key", "version_key",
)


def num(v: str | None) -> int | float | None:
    """Numeric string -> number; empty string -> None (spec 3.3)."""
    if v is None:
        return None
    s = str(v).strip().replace(" ", "").replace(",", ".")
    if s == "":
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return int(f) if f.is_integer() else round(f, 2)


def text(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _sha1(*parts: Any) -> str:
    h = hashlib.sha1("\x1f".join("" if p is None else str(p) for p in parts).encode("utf-8"))
    return h.hexdigest()[:16]


def config_key(o: dict[str, Any]) -> str:
    """Configuration identity, computed exactly as in release 1.0 (spec 5.1, ADR-0006)."""
    return _sha1(o["model"], o["engine"], o["code"], o["model_year"])


def version_key(o: dict[str, Any]) -> str:
    """Identical offers share it (spec 5.1); promo_bits hold badge bits only from 1.1."""
    return _sha1(o["model"], o["engine"], o["code"], o["model_year"], o["catalog"], o["special"],
                 o["price_30d"], o["rate"], o["promo_bits"])


def _order_key(item: tuple[int, dict[str, Any]]) -> tuple[Any, ...]:
    """Canonical order (spec 5.5): model, engine, code, model_year, special (nulls last), catalog, rate,
    dealer_nr, promo_bits, then feed order."""
    pos, o = item

    def n(v: Any) -> tuple[bool, float]:
        return (v is None, float(v) if v is not None else 0.0)

    return (o["model"], o["engine"] or "", o["code"] or "", o["model_year"] or "", n(o["special"]),
            n(o["catalog"]), n(o["rate"]), o["dealer_nr"] or "", o["promo_bits"], pos)


def normalise(items: list[FeedItem], rules: Rules, date: str) -> list[dict[str, Any]]:
    offers: list[tuple[int, dict[str, Any]]] = []
    for pos, it in enumerate(items):
        d = it.model_dump()
        badges = rules.badges(d)
        bits = 0
        for key in PROMO_KEYS:
            if badges[key]:
                bits |= 1 << rules.badge_bit(key)
        catalog, special = num(it.cena_katalogowa), num(it.cena_vtp)
        o: dict[str, Any] = {
            "model": it.model.strip(),
            "engine": text(it.silnik),
            "engine_group": text(it.silnik2),
            "code": text(it.kod_modelowy),
            "model_year": text(it.rok_modelowy),
            "production_year": text(it.rok_produkcji),
            "dealer_nr": text(it.dealer_nr),
            "dealer": text(it.dealer),
            "catalog": catalog,
            "special": special,
            "price_30d": num(it.cena_historyczna),
            "catalog_30d": num(it.cena_historyczna_katalogowa),
            "rate": num(it.rata),
            "rate_old": num(it.stara_rata),
            "rate_30d": num(it.rata_historyczna),
            "business_edition": it.business_edition.strip().lower() == "tak",
            "stock_cleaning": it.stock_cleaning.strip().lower() == "tak",
            "moj_elektryk": it.moj_elektryk.strip().lower() == "tak",
            "promo_bits": bits,
            "package_type": badges["package_type"],
            "footnote": rules.footnote(d),
            "plan_code": rules.plan_code(d),
        }
        if catalog is not None and special is not None:
            o["discount"] = catalog - special
            o["discount_pct"] = round((catalog - special) / catalog, 4) if catalog else None
        else:
            o["discount"] = None
            o["discount_pct"] = None
        o["config_key"] = config_key(o)
        o["version_key"] = version_key(o)
        extra = {k: v for k, v in d.items() if k not in KEPT_FIELDS}
        if extra:
            o["extra"] = extra
        offers.append((pos, o))
    offers.sort(key=_order_key)
    out = []
    for n, (_, o) in enumerate(offers, start=1):
        out.append({"offer_id": f"{date}/{n}", **o})
    return out


def badge_set(bits: int, rules: Rules) -> list[str]:
    """Promo keys whose card badge is set in `bits`."""
    return [k for k in PROMO_KEYS if bits >> int(rules.promo["promos"][k]["badge_bit"]) & 1]
