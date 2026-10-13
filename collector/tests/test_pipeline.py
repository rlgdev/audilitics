"""Collector runs on the synthetic fixture and simulated later runs (spec 12.1, 12.2)."""

from __future__ import annotations

import math
import shutil
from pathlib import Path
from statistics import median
from typing import Any

import pytest

from collector.config import Settings, load_settings
from collector.io import read_json, read_json_gz
from collector.pipeline import process_raw, rebuild_all

from .sim import ROOT, make_item, simulate

LATER = ["2026-10-27", "2026-11-10", "2026-11-24", "2026-12-08"]


@pytest.fixture(scope="module")
def three(tmp_path_factory: pytest.TempPathFactory, synthetic: list[dict[str, Any]]) -> Settings:
    s = load_settings(ROOT, data=tmp_path_factory.mktemp("three") / "data")
    for raw in synthetic:
        assert process_raw(s, raw)["status"] == "ok"
    return s


def rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(zip(table["columns"], r, strict=True)) for r in table["rows"]]


def test_files_of_both_trees(three: Settings) -> None:
    d = three.data
    for f in ("raw/2026-10-13.json.gz", "snapshots/2026-10-13.json.gz", "snapshots/index.json", "meta/models.json",
              "meta/dealers.json", "meta/bundles.json", "private/deals.json", "private/dealers.json",
              "private/models/q5.json", "exports/2026-10-13.xlsx", "exports/latest.csv", "reports/2026-10-13.md",
              "public/manifest.json", "public/snapshots/index.json", "public/dashboard/latest.json",
              "public/dashboard/trends.json", "public/dashboard/deals.json",
              "public/dashboard/changes/2026-10-13.json", "public/models/q5.json", "public/meta/models.json"):
        assert (d / f).exists(), f
    public = sorted(p.relative_to(three.public_dir).as_posix() for p in three.public_dir.rglob("*") if p.is_file())
    assert not [p for p in public if "private" in p or p.endswith(".gz") or "dealer" in p]
    dealers = read_json(d / "meta" / "dealers.json")
    assert all("phone" not in v for v in dealers.values())


def test_configuration_changes(three: Settings) -> None:
    ch = read_json(three.public_dir / "dashboard" / "changes" / "2026-10-13.json")
    new = {r["code"]: r for r in ch["configs_new"]}
    assert new["4MQCX2"]["reason"] == "new_in_stock"
    gone = {r["code"]: r for r in ch["configs_gone"]}
    assert gone["GUBAZY"]["reason"] == "none_left" and gone["GUBAZY"]["special_median"] is not None
    assert "8YFBTG" not in new and "8YFBTG" not in gone  # never reaches the minimum group
    drops = {r["code"]: r for r in ch["price_drops"]}
    q7 = drops["4MQCN2"]
    assert q7["new"] < q7["old"] and q7["diff"] == q7["new"] - q7["old"]
    assert q7["pct"] == pytest.approx(q7["diff"] / q7["old"], abs=1e-4)
    assert q7["consecutive_drops"] == 2
    stock = {r["slug"]: r for r in ch["stock"]}
    assert stock["q7"]["net_added"] >= 6
    assert ch["summary"]["price_drops"] == len(ch["price_drops"])


def test_lfl_index_and_trends(three: Settings) -> None:
    t = read_json(three.public_dir / "dashboard" / "trends.json")
    assert t["dates"] == ["2026-09-15", "2026-09-29", "2026-10-13"]
    assert t["models"]["q5"]["lfl_index"][0] == 100.0
    assert t["models"]["q5"]["lfl_index"][2] < 100.0
    assert t["totals"]["lfl_index"][0] == 100.0
    assert t["totals"]["net_added"][0] is None and t["totals"]["net_added"][2] is not None
    assert t["models"]["a3-sportback"]["slider_counts"]["bo"][2] is not None


def test_scores_reproduce_and_summarise(three: Settings) -> None:
    offers = rows(read_json(three.private_dir / "deals.json"))
    for o in offers:
        total = 0.35 * o["D"] + 0.25 * o["P"] + 0.20 * o["M"] + 0.10 * o["R"] + o["B"]
        assert o["score"] == int(math.floor(total + 0.5)), o["offer_id"]
    deals = read_json(three.public_dir / "dashboard" / "deals.json")
    by_cfg: dict[str, list[int]] = {}
    for o in offers:
        by_cfg.setdefault(o["config_key"], []).append(o["score"])
    for c in deals["configs"]:
        assert c["priced"] >= 3
        assert c["score_median"] == median(by_cfg[c["config_key"]]), c["label"]
        assert c["score_best"] == max(by_cfg[c["config_key"]])
        assert set(c["components"]) == {"D", "P", "M", "R", "B"}
    for vals in deals["rankings"]["top_per_model"].values():
        assert len(vals) <= 3
    assert not {"offer_id", "dealer", "dealer_nr"} & set(deals["configs"][0])


def test_hot_configurations(three: Settings) -> None:
    latest = read_json(three.public_dir / "dashboard" / "latest.json")
    deals = read_json(three.public_dir / "dashboard" / "deals.json")
    hot = latest["hot_configs"]
    assert 0 < len(hot) <= 24
    assert latest["hot_count"] == sum(1 for c in deals["configs"] if c["hot"])
    assert [h["hot_score"] for h in hot] == sorted((h["hot_score"] for h in hot), reverse=True)
    for h in hot:
        assert h["reasons"]
        assert all(p["priced"] >= 3 for p in h["points"])
        if "drop" in h["reasons"]:
            assert h["drop_pct"] >= 0.03 or h["drop"] >= 5000
    assert any(h["code"] == "4MQCX2" and "new_high_score" in h["reasons"] for h in hot)


def test_single_snapshot_has_no_hot_deals(settings: Settings, synthetic: list[dict[str, Any]]) -> None:
    process_raw(settings, synthetic[0])
    latest = read_json(settings.public_dir / "dashboard" / "latest.json")
    assert latest["hot_configs"] == [] and latest["hot_count"] == 0
    assert latest["changes"]["summary"]["first_run"] is True


def test_suspect_snapshot(settings: Settings, synthetic: list[dict[str, Any]]) -> None:
    process_raw(settings, synthetic[0])
    res = process_raw(settings, simulate(synthetic[0], "2026-09-29", keep_ratio=0.6))
    assert res["status"] == "suspect"
    assert [i["label"] for i in res["issues"]] == ["collector-failure"]
    t = read_json(settings.public_dir / "dashboard" / "trends.json")
    assert t["dates"] == ["2026-09-15"]
    idx = read_json(settings.public_dir / "snapshots" / "index.json")
    assert idx[1] == {"date": "2026-09-29", "status": "suspect"}
    assert (settings.data / "snapshots" / "2026-09-29.json.gz").exists()
    res = process_raw(settings, synthetic[2])
    assert res["status"] == "ok" and res["issues"] == []


def test_failed_run_leaves_data_untouched(settings: Settings, synthetic: list[dict[str, Any]]) -> None:
    process_raw(settings, synthetic[0])
    before = {p: p.read_bytes() for p in settings.data.rglob("*") if p.is_file()}
    bad = simulate(synthetic[0], "2026-09-29")
    del bad["feed"]["items"][5]["rata"]
    res = process_raw(settings, bad)
    assert res["status"] == "failed" and res["issues"][0]["label"] == "collector-failure"
    after = {p: p.read_bytes() for p in settings.data.rglob("*") if p.is_file()}
    assert before == after


def test_bundle_change_and_slider_gate(settings: Settings, synthetic: list[dict[str, Any]]) -> None:
    process_raw(settings, synthetic[0])
    r = simulate(synthetic[0], "2026-09-29")
    r["bundle"] = {"name": "main.ffff.js", "hash": "ffff"}
    r["slider_counts"]["bo"] = {m: n * 2 for m, n in r["slider_counts"]["bo"].items()}
    res = process_raw(settings, r)
    assert res["status"] == "ok"
    assert sorted(i["label"] for i in res["issues"]) == ["rules-review", "rules-review"]


def test_same_raw_twice_is_byte_identical(settings: Settings, synthetic: list[dict[str, Any]], tmp_path: Path) -> None:
    process_raw(settings, synthetic[0])
    process_raw(settings, synthetic[1])
    copy = tmp_path / "copy"
    shutil.copytree(settings.data, copy)
    process_raw(settings, read_json_gz(settings.data / "raw" / "2026-09-29.json.gz"), archive=False)
    for p in settings.data.rglob("*"):
        if p.is_file():
            assert p.read_bytes() == (copy / p.relative_to(settings.data)).read_bytes(), p
    assert sorted(p.relative_to(copy) for p in copy.rglob("*")) == \
        sorted(p.relative_to(settings.data) for p in settings.data.rglob("*"))


def test_rebuild_reproduces(settings: Settings, synthetic: list[dict[str, Any]]) -> None:
    for raw in synthetic:
        process_raw(settings, raw)
    before = {p.relative_to(settings.data): p.read_bytes() for p in settings.data.rglob("*") if p.is_file()}
    assert [r["status"] for r in rebuild_all(settings)] == ["ok", "ok", "ok"]
    after = {p.relative_to(settings.data): p.read_bytes() for p in settings.data.rglob("*") if p.is_file()}
    assert before.keys() == after.keys()
    assert [str(k) for k in before if before[k] != after[k]] == []


def test_model_lifecycle(settings: Settings, synthetic: list[dict[str, Any]]) -> None:
    last = synthetic[-1]
    for raw in synthetic:
        process_raw(settings, raw)
    q5 = next(it for it in last["feed"]["items"] if it["model"] == "Audi Q5")
    q9 = [make_item(q5, model="Audi Q9", kod_modelowy="Q9AAAA") for _ in range(3)]
    for i, d in enumerate(LATER[:3]):
        process_raw(settings, simulate(last, d, drop_models=("Audi RS 3 Sportback",), add_items=q9 if i == 0 else q9))
    models = {m["slug"]: m for m in read_json(settings.data / "meta" / "models.json")}
    assert models["rs-3-sportback"]["status"] == "retired" and models["rs-3-sportback"]["retired_on"] == LATER[2]
    assert models["q9"]["segment"] == "Q" and models["q9"]["first_seen"] == LATER[0]
    latest = read_json(settings.public_dir / "dashboard" / "latest.json")
    assert next(t for t in latest["models"] if t["slug"] == "rs-3-sportback")["status"] == "retired"
    assert (settings.public_dir / "models" / "rs-3-sportback.json").exists()
    ch0 = read_json(settings.public_dir / "dashboard" / "changes" / f"{LATER[0]}.json")
    assert [m["slug"] for m in ch0["models_new"]] == ["q9"]
    process_raw(settings, simulate(last, LATER[3], add_items=q9))
    models = {m["slug"]: m for m in read_json(settings.data / "meta" / "models.json")}
    assert models["rs-3-sportback"]["status"] == "active"
    ch3 = read_json(settings.public_dir / "dashboard" / "changes" / f"{LATER[3]}.json")
    assert [m["slug"] for m in ch3["models_returned"]] == ["rs-3-sportback"]


def test_private_offer_table(three: Settings) -> None:
    d = read_json(three.private_dir / "deals.json")
    assert "vin" not in d["columns"] and "link" not in d["columns"]
    assert d["columns"][0] == "offer_id"
    offers = rows(d)
    assert all(o["special"] is not None for o in offers)
    assert offers == sorted(offers, key=lambda o: (-o["score"], -(o["discount"] or 0), o["offer_id"]))


def test_synthetic_expected_output(three: Settings) -> None:
    exp = read_json(ROOT / "collector" / "tests" / "fixtures" / "synthetic" / "expected.json")
    idx = {e["date"]: e for e in read_json(three.data / "snapshots" / "index.json")}
    for run in exp["runs"]:
        e = idx[run["date"]]
        keys = ("status", "offers", "models", "configurations")
        assert {k: e[k] for k in keys} == {k: run[k] for k in keys}
    latest = read_json(three.public_dir / "dashboard" / "latest.json")
    assert latest["hot_count"] == exp["hot_count"]
    s = latest["changes"]["summary"]
    assert {k: s[k] for k in exp["changes_latest"]} == exp["changes_latest"]
    published = [len(read_json(three.public_dir / "dashboard" / "deals.json")["configs"])]
    assert published == [exp["runs"][-1]["public_configurations"]]
