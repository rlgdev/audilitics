"""Acceptance on the redacted real fixture of 13 Oct 2026 (spec 12.1). The fixture lives in the private
repository; set AUDILITICS_REAL_FIXTURE or keep ../audilitics-private next to this checkout. Skipped otherwise."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from collector.config import load_settings
from collector.guard import guard_public, identifier_check
from collector.normalise import normalise
from collector.pipeline import process_raw
from collector.rules import PROMO_KEYS, Rules
from collector.schema import parse, validate_and_redact

from .sim import REAL_FIXTURE, ROOT

pytestmark = pytest.mark.real
EXPECTED = REAL_FIXTURE.parent / "expected.json"


@pytest.fixture(scope="module")
def offers(real_raw: dict[str, Any], rules: Rules) -> list[dict[str, Any]]:
    items, _, _ = validate_and_redact(real_raw["feed"]["items"], False)
    return normalise(parse(items), rules, "2026-10-13")


def bit(o: dict[str, Any], n: int) -> bool:
    return bool(o["promo_bits"] >> n & 1)


def test_counts(offers: list[dict[str, Any]]) -> None:
    assert len(offers) == 4768
    assert len({o["model"] for o in offers}) == 53
    assert len({o["dealer_nr"] for o in offers}) == 38
    assert len({o["version_key"] for o in offers}) == 3092


def test_badge_counts(offers: list[dict[str, Any]], rules: Rules) -> None:
    counts = {k: sum(bit(o, rules.badge_bit(k)) for o in offers) for k in PROMO_KEYS}
    assert counts == {"bo": 2347, "fe": 230, "l101": 4676, "pu": 1916, "be": 2847, "p15": 81}


def test_slider_counts(real_raw: dict[str, Any]) -> None:
    totals = {k: sum(v.values()) for k, v in real_raw["slider_counts"].items()}
    assert {k: totals[k] for k in ("bo", "fe", "l101", "pu", "be")} == \
        {"bo": 2347, "fe": 230, "l101": 4675, "pu": 1916, "be": 2847}


def test_plan_codes(offers: list[dict[str, Any]]) -> None:
    assert set(Counter(o["plan_code"] for o in offers if "e-tron" in o["model"])) <= {"APL-2", "APL-2-EV"}
    assert {o["plan_code"] for o in offers if o["model"] == "Audi A3 Limousine" and o["code"].startswith("8YM")} \
        == {"APL-3"}
    assert {o["plan_code"] for o in offers if "Q5" in o["model"] and o["code"].startswith("GU")} == {"APL-3"}
    assert {o["plan_code"] for o in offers if o["model"] == "Audi A3 Sportback" and o["code"].startswith("8YY")} \
        == {"APL-1"}


def test_full_run_and_expected_output(real_raw: dict[str, Any], tmp_path: Path) -> None:
    s = load_settings(ROOT, data=tmp_path / "data")
    res = process_raw(s, real_raw)
    assert res["status"] == "ok", res
    assert guard_public(s.public_dir) == []
    assert identifier_check(s.data) == []
    deals = json.loads((s.private_dir / "deals.json").read_text(encoding="utf-8"))
    assert len(deals["rows"]) == 4766
    got = {"configurations": res["entry"]["configurations"],
           "public_configurations": res["entry"]["public_configurations"]}
    if EXPECTED.exists():
        assert got == json.loads(EXPECTED.read_text(encoding="utf-8"))
    else:
        pytest.skip(f"no expected.json next to the fixture; observed {got}")
