"""Badge and plan rules on hand-made items (spec 3.4, 6.4); counts on real data are in test_acceptance_real.py."""

from __future__ import annotations

from typing import Any

import pytest

from collector.rules import Rules


def base_item(**kw: str) -> dict[str, Any]:
    d = {"model": "Audi A4", "kod_modelowy": "8WCAAA", "rok_produkcji": "2026", "rok_modelowy": "2026",
         "stock_cleaning": "Nie", "business_edition": "Nie"}
    d.update(kw)
    return d


@pytest.mark.parametrize(("kw", "expected"), [
    ({"kod_modelowy": "8YFBNG"}, True),
    ({"kod_modelowy": "8YYANG"}, False),
    ({"kod_modelowy": "8YFRWY"}, False),
    ({"kod_modelowy": "8YYANG", "stock_cleaning": "Tak"}, False),
    ({"kod_modelowy": "GUBAAA", "stock_cleaning": "Tak"}, True),
    ({"kod_modelowy": "4MQCN2"}, True),
    ({"kod_modelowy": "GUBAAA"}, False),
])
def test_best_offer_rule(rules: Rules, kw: dict[str, str], expected: bool) -> None:
    assert rules.badges(base_item(**kw))["bo"] is expected


@pytest.mark.parametrize(("kw", "package"), [
    ({"model": "Audi Q5", "rok_produkcji": "2025"}, "insuranceAndService"),
    ({"model": "Audi Q5", "rok_produkcji": "2026", "stock_cleaning": "Tak"}, "insuranceOrService"),
    ({"model": "Audi Q5", "rok_produkcji": "2026"}, "none"),
    ({"model": "Audi A6 Avant", "kod_modelowy": "FN5XXX"}, "insuranceOrService"),
    ({"model": "Audi A6 Avant", "kod_modelowy": "FN3XXX"}, "none"),
    ({"model": "Audi SQ7", "kod_modelowy": "4MQXXX"}, "insuranceOnly"),
])
def test_insurance_package(rules: Rules, kw: dict[str, str], package: str) -> None:
    assert rules.badges(base_item(**kw))["package_type"] == package


def test_final_edition_replaces_business_edition(rules: Rules) -> None:
    b = rules.badges(base_item(model="Audi Q7", kod_modelowy="4MQCN2", business_edition="Tak"))
    assert b["fe"] and not b["be"]
    b = rules.badges(base_item(model="Audi Q7", kod_modelowy="4MQCN2", business_edition="Tak", rok_produkcji="2025"))
    assert not b["fe"] and b["be"]


def test_p15_and_l101_2025(rules: Rules) -> None:
    assert rules.badges(base_item(model="Audi Q6 e-tron", kod_modelowy="GFAAAA"))["p15"]
    assert not rules.badges(base_item(model="Audi Q6 e-tron", kod_modelowy="GHAAAA"))["p15"]
    assert rules.badges(base_item(model="Audi Q5", rok_produkcji="2025"))["l101"]
    assert not rules.badges(base_item(model="Audi A3 Sportback", rok_produkcji="2025"))["l101"]


@pytest.mark.parametrize(("kw", "plan"), [
    ({"model": "Audi Q4 e-tron", "rok_modelowy": "2026"}, "APL-2-EV"),
    ({"model": "Audi Q4 e-tron", "rok_modelowy": "2027"}, "APL-2"),
    ({"model": "Audi A6 Avant e-tron", "kod_modelowy": "GHXXXX", "rok_modelowy": "2027"}, "APL-2-EV"),
    ({"model": "Audi Q7", "kod_modelowy": "4MQXXX"}, "APL-3"),
    ({"model": "Audi A5 Avant", "kod_modelowy": "FUXXXX"}, "APL-3"),
    ({"model": "Audi Q2", "kod_modelowy": "GAXXXX"}, "APL-1"),
    ({"model": "Audi S3 Sportback", "kod_modelowy": "8YFXXX"}, "APL-3"),
])
def test_plan_rule(rules: Rules, kw: dict[str, str], plan: str) -> None:
    assert rules.plan_code(base_item(**kw)) == plan


def test_rule_set_picked_by_date(tmp_path: Any) -> None:
    from collector.rules import _pick

    p = tmp_path / "r.yaml"
    p.write_text("rule_sets:\n  - {version: v1, valid_from: 2026-10-13}\n  - {version: v2, valid_from: 2027-01-01}\n")
    assert _pick(p, "2026-12-31")["version"] == "v1"
    assert _pick(p, "2027-01-01")["version"] == "v2"
    assert _pick(p, "2020-01-01")["version"] == "v1"
