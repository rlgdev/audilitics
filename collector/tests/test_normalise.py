"""Normalisation, canonical order, keys, slugs (spec 4.2 step 7, 4.6, 5.1, 5.2, 5.5)."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest

from collector.lifecycle import assign_engine_slots, segment_of, slugify
from collector.normalise import config_key, normalise, num
from collector.rules import Rules
from collector.schema import SchemaError, parse, validate_and_redact

from .sim import fake_vin


def offers_of(raw: dict[str, Any], rules: Rules) -> list[dict[str, Any]]:
    items, _, _ = validate_and_redact(raw["feed"]["items"], False)
    return normalise(parse(items), rules, raw["date"])


def test_num() -> None:
    assert num("136700") == 136700
    assert num("") is None
    assert num(None) is None
    assert num("1150.5") == 1150.5
    assert num("abc") is None


def test_offer_ids_follow_canonical_order(raw: dict[str, Any], rules: Rules) -> None:
    offers = offers_of(raw, rules)
    assert [o["offer_id"] for o in offers] == [f"{raw['date']}/{i}" for i in range(1, len(offers) + 1)]
    keys = [(o["model"], o["engine"] or "", o["code"] or "", o["model_year"] or "", o["special"] is None,
             o["special"] or 0) for o in offers]
    assert keys == sorted(keys)
    shuffled = copy.deepcopy(raw)
    shuffled["feed"]["items"].reverse()
    again = offers_of(shuffled, rules)
    assert [(o["config_key"], o["special"], o["dealer_nr"]) for o in again] == \
        [(o["config_key"], o["special"], o["dealer_nr"]) for o in offers]


def test_config_key_is_the_release_1_0_formula(raw: dict[str, Any], rules: Rules) -> None:
    o = offers_of(raw, rules)[0]
    expected = hashlib.sha1("\x1f".join([o["model"], o["engine"], o["code"], o["model_year"]]).encode()).hexdigest()
    assert config_key(o) == o["config_key"] == expected[:16]


def test_offer_has_no_identifier_fields(raw: dict[str, Any], rules: Rules) -> None:
    for o in offers_of(raw, rules):
        assert not {"vin", "komisja", "link", "kod_audi", "telefon", "phone"} & o.keys()


def test_null_special_price(raw: dict[str, Any], rules: Rules) -> None:
    offers = offers_of(raw, rules)
    nulls = [o for o in offers if o["special"] is None]
    assert nulls, "the synthetic fixture has offers without a special price"
    assert all(o["discount"] is None and o["discount_pct"] is None for o in nulls)
    assert offers.index(nulls[0]) > offers.index(next(o for o in offers if o["model"] == nulls[0]["model"]))


def test_missing_field_fails_live_validation(raw: dict[str, Any]) -> None:
    items = copy.deepcopy(raw["feed"]["items"][:3])
    for i, it in enumerate(items):
        it.update(vin=fake_vin(i), komisja="2026000000", link="https://example.invalid/x", kod_audi="", telefon="1")
    validate_and_redact(items, True)
    del items[1]["vin"]
    with pytest.raises(SchemaError):
        validate_and_redact(items, True)
    del items[0]["cena_vtp"]
    with pytest.raises(SchemaError):
        validate_and_redact(items, False)


def test_identical_offers_share_version_key(raw: dict[str, Any], rules: Rules) -> None:
    items = copy.deepcopy(raw["feed"]["items"][:1]) * 2
    items[1] = {**items[1], "dealer_nr": "9199"}
    a, b = normalise(parse(validate_and_redact(items, False)[0]), rules, "2026-10-13")
    assert a["version_key"] == b["version_key"]
    items[1]["cena_vtp"] = "1"
    a, b = normalise(parse(validate_and_redact(items, False)[0]), rules, "2026-10-13")
    assert a["version_key"] != b["version_key"] and a["config_key"] == b["config_key"]


@pytest.mark.parametrize(("name", "slug", "segment"), [
    ("Audi Q6 Sportback e-tron", "q6-sportback-e-tron", "e-tron"),
    ("Audi Q5 Sportback e-hybrid", "q5-sportback-e-hybrid", "Q"),
    ("Audi A3 Sportback TFSI e", "a3-sportback-tfsi-e", "A"),
    ("Audi RS Q8", "rs-q8", "S/RS"),
    ("Audi SQ6 e-tron", "sq6-e-tron", "S/RS"),
    ("Audi S3 Limousine", "s3-limousine", "S/RS"),
    ("Audi S e-tron GT", "s-e-tron-gt", "e-tron"),
    ("Audi Q9", "q9", "Q"),
    ("Audi A8", "a8", "A"),
])
def test_slug_and_segment(name: str, slug: str, segment: str) -> None:
    assert slugify(name) == slug
    assert segment_of(name) == segment


def test_engine_slots_fixed_order() -> None:
    slots = assign_engine_slots(["TDI", "TFSI", "e-hybrid", "TFSI quattro", "modele S", "X", "Y"])
    assert slots["TFSI"] == 1 and slots["TDI"] == 2 and slots["TFSI quattro"] == 3 and slots["e-hybrid"] == 5
    assert slots["modele S"] == 4
    assert slots["X"] == 0 and slots["Y"] == 0  # folded into "Other"
