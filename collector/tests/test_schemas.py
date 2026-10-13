"""Collector outputs match the JSON Schemas in collector/schemas/ (spec 9, data-model)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from collector.config import Settings, load_settings
from collector.io import read_json, read_json_gz
from collector.pipeline import process_raw

from .sim import ROOT

SCHEMAS = ROOT / "collector" / "schemas"


def validator(name: str) -> Draft202012Validator:
    reg: Registry = Registry()
    for p in SCHEMAS.glob("*.schema.json"):
        reg = reg.with_resource(p.name, Resource.from_contents(json.loads(p.read_text(encoding="utf-8"))))
    return Draft202012Validator(json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8")),
                                registry=reg)


@pytest.fixture(scope="module")
def data(tmp_path_factory: pytest.TempPathFactory, synthetic: list[dict[str, Any]]) -> Settings:
    s = load_settings(ROOT, data=tmp_path_factory.mktemp("schemas") / "data")
    for raw in synthetic:
        process_raw(s, raw)
    return s


@pytest.mark.parametrize(("schema", "path"), [
    ("snapshot-index", "snapshots/index.json"),
    ("snapshot-index", "public/snapshots/index.json"),
    ("latest", "public/dashboard/latest.json"),
    ("deals", "public/dashboard/deals.json"),
    ("trends", "public/dashboard/trends.json"),
    ("changes", "public/dashboard/changes/2026-10-13.json"),
    ("model", "public/models/q5.json"),
    ("private-deals", "private/deals.json"),
    ("private-dealers", "private/dealers.json"),
])
def test_json_files(data: Settings, schema: str, path: str) -> None:
    errors = list(validator(schema).iter_errors(read_json(data.data / path)))
    assert errors == [], [e.message for e in errors[:3]]


def test_snapshot_file(data: Settings) -> None:
    snap = read_json_gz(data.data / "snapshots" / "2026-10-13.json.gz")
    errors = list(validator("snapshot").iter_errors(snap))
    assert errors == [], [e.message for e in errors[:3]]


def test_schema_files_are_valid() -> None:
    for p in SCHEMAS.glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(p.read_text(encoding="utf-8")))
