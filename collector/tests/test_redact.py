"""Redaction at ingestion (spec 3.5, 12.1 Redaction): items carrying all five fields leave no trace anywhere."""

from __future__ import annotations

import copy
import gzip
from pathlib import Path
from typing import Any

from collector.config import Settings
from collector.guard import identifier_check
from collector.pipeline import process_raw
from collector.redact import looks_identifying, redact_item

from .sim import fake_vin

SECRETS = ("2026990001", "https://www.audi.pl/pl/offer-test", "+48 (00) 000 00 00")


def unredacted(raw: dict[str, Any]) -> dict[str, Any]:
    r = copy.deepcopy(raw)
    r.pop("redacted", None)
    for i, it in enumerate(r["feed"]["items"]):
        it.update(vin=fake_vin(i), komisja=SECRETS[0], link=SECRETS[1], kod_audi="", telefon=SECRETS[2])
    return r


def all_text(root: Path) -> str:
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            b = p.read_bytes()
            if p.suffix == ".gz":
                b = gzip.decompress(b)
            if p.suffix == ".xlsx":
                import zipfile

                with zipfile.ZipFile(p) as z:
                    b = b"".join(z.read(n) for n in z.namelist())
            out.append(b.decode("utf-8", errors="replace"))
    return "\n".join(out)


def test_no_output_contains_a_discarded_field(settings: Settings, raw: dict[str, Any]) -> None:
    res = process_raw(settings, unredacted(raw))
    assert res["status"] == "ok", res
    text = all_text(settings.data) + all_text(settings.data.parent / ".run")
    assert fake_vin(0) not in text and "WAUZZZTEST" not in text
    for s in SECRETS:
        assert s not in text
    for key in ('"vin"', '"komisja"', '"link"', '"kod_audi"', '"telefon"', '"phone"'):
        assert key not in text
    assert identifier_check(settings.data) == []


def test_unknown_identifying_field_is_dropped_and_reported(settings: Settings, raw: dict[str, Any]) -> None:
    r = copy.deepcopy(raw)
    r["feed"]["items"][0]["nr_rejestracyjny"] = "WX 12345"
    r["feed"]["items"][0]["nowe_pole"] = "x"
    res = process_raw(settings, r)
    assert sorted(i["label"] for i in res["issues"]) == ["schema-change"]
    assert "nr_rejestracyjny" in res["warnings"][0] and "nowe_pole" in res["warnings"][0]
    text = all_text(settings.data)
    assert "WX 12345" not in text
    assert '"nowe_pole"' in text  # kept in extra (private only)


def test_redact_item_and_heuristic() -> None:
    item = {"model": "Audi Q5", "vin": fake_vin(1), "link": "https://x", "komisja": "1", "kod_audi": "",
            "telefon": "1", "x_url": "https://y", "colour": "blue"}
    out, dropped = redact_item(item, known=("model", "vin", "link", "komisja", "kod_audi", "telefon"))
    assert out == {"model": "Audi Q5", "colour": "blue"}
    assert dropped == ["x_url"]
    assert looks_identifying("seller_phone", "1") and looks_identifying("note", fake_vin(2))
    assert not looks_identifying("colour", "blue")
