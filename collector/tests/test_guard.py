"""Publication guard (spec 10.5, 12.1): passes on a real public tree, fails on every seeded violation."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from collector.config import Settings, load_settings
from collector.guard import guard_public, identifier_check
from collector.io import read_json_gz
from collector.pipeline import process_raw

from .sim import ROOT, SYNTHETIC_RAWS, fake_vin


@pytest.fixture(scope="module")
def public_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    s = load_settings(ROOT, data=tmp_path_factory.mktemp("guard") / "data")
    for p in SYNTHETIC_RAWS:
        assert process_raw(s, read_json_gz(p))["status"] == "ok"
    return s.public_dir


@pytest.fixture
def tree(public_tree: Path, tmp_path: Path) -> Path:
    t = tmp_path / "public"
    shutil.copytree(public_tree, t)
    return t


def edit(tree: Path, rel: str, fn: Callable[[Any], None]) -> None:
    p = tree / rel
    obj = json.loads(p.read_text(encoding="utf-8"))
    fn(obj)
    p.write_text(json.dumps(obj), encoding="utf-8")


def test_passes_on_the_public_tree(public_tree: Path) -> None:
    assert guard_public(public_tree) == []
    assert identifier_check(public_tree, public=True) == []


def first_config(obj: Any) -> dict[str, Any]:
    return obj["configs"][0]  # type: ignore[no-any-return]


@pytest.mark.parametrize(("name", "rel", "mutate", "expect"), [
    ("vin", "dashboard/deals.json", lambda o: first_config(o).update(note=fake_vin(9)), "VIN-shaped"),
    ("link key", "dashboard/deals.json", lambda o: first_config(o).update(link="x"), "identifier key"),
    ("offer_id key", "dashboard/deals.json", lambda o: first_config(o).update(offer_id="2026-10-13/1"),
     "identifier key"),
    ("audi url", "dashboard/latest.json", lambda o: o["run"].update(source="https://gotowedoodbioru.audi.pl/x"),
     "link to audi.pl"),
    ("dealer key", "dashboard/deals.json", lambda o: first_config(o).update(dealer="Salon Alfa"), "dealer key"),
    ("2 priced offers", "dashboard/deals.json", lambda o: first_config(o).update(priced=2), "fewer than 3"),
    ("statistic without count", "dashboard/deals.json", lambda o: first_config(o).pop("priced"), "without its"),
    ("badge counts below 3 offers", "dashboard/deals.json", lambda o: first_config(o).update(offers=2),
     "fewer than 3 offers"),
    ("series below 3", "dashboard/trends.json", lambda o: o["totals"]["priced"].__setitem__(-1, 1), "fewer than 3"),
])
def test_fails_on_seeded_violation(tree: Path, name: str, rel: str, mutate: Callable[[Any], None],
                                   expect: str) -> None:
    edit(tree, rel, mutate)
    findings = guard_public(tree)
    assert findings, name
    assert any(expect in f for f in findings), findings


def test_fails_on_file_outside_layout(tree: Path) -> None:
    (tree / "private").mkdir()
    (tree / "private" / "deals.json").write_text("{}", encoding="utf-8")
    (tree / "dashboard" / "dealers.json").write_text("{}", encoding="utf-8")
    findings = guard_public(tree)
    assert len([f for f in findings if "outside the public layout" in f]) == 2


def test_identifier_check_reads_gz_and_xlsx(tmp_path: Path) -> None:
    import gzip

    (tmp_path / "a.json.gz").write_bytes(gzip.compress(json.dumps({"x": fake_vin(3)}).encode()))
    from openpyxl import Workbook

    wb = Workbook()
    wb.active.append(["VIN", fake_vin(4)])
    wb.save(tmp_path / "b.xlsx")
    findings = identifier_check(tmp_path)
    assert {f.split(":")[0] for f in findings} == {"a.json.gz", "b.xlsx"}


def test_failed_guard_fails_the_run(settings: Settings, synthetic: list[dict[str, Any]],
                                    monkeypatch: pytest.MonkeyPatch) -> None:
    import collector.pipeline as pl

    monkeypatch.setattr(pl, "guard_public", lambda root, mg: ["dashboard/deals.json: seeded"])
    res = process_raw(settings, synthetic[0])
    assert res["status"] == "failed"
    assert [i["label"] for i in res["issues"]] == ["publication-guard"]
