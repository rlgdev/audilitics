"""The public tree data/public/ (spec 5.3 public layout, 5.5 publication rules).

Only aggregates are written here: no offer-level row, no offer_id, no dealer, no URL, no field of spec 3.5 and
no single offer's score components. Every statistic object carries `offers` and `priced` (arrays aligned with
`dates` in time series) so the publication guard can check the minimum group size (spec 10.5).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from collector import __version__
from collector.config import Settings
from collector.io import sha1_file, write_json
from collector.lifecycle import SEGMENTS
from collector.rules import PROMO_KEYS, Rules

SLIDER_KEYS = ("bo", "fe", "l101", "pu", "be", "pks")
STAT_FIELDS = ("special_min", "special_median", "special_max", "discount_pct_median")


def _empty() -> dict[str, Any]:
    return {"offers": 0, "priced": 0, **{f: None for f in STAT_FIELDS}, "rates": {}, "promo_counts": None}


def series(stats_list: Sequence[dict[str, Any] | None]) -> dict[str, Any]:
    """Per-snapshot statistics -> arrays aligned with dates."""
    sl = [s or _empty() for s in stats_list]
    out: dict[str, Any] = {"offers": [s["offers"] for s in sl], "priced": [s["priced"] for s in sl]}
    for f in STAT_FIELDS:
        out[f] = [s[f] for s in sl]
    plans = sorted({p for s in sl for p in s["rates"]})
    out["rates"] = {p: {f: [s["rates"].get(p, {}).get(f, 0 if f == "priced" else None) for s in sl]
                        for f in ("priced", "rate_min", "rate_median")} for p in plans}
    out["promo_counts"] = {k: [s["promo_counts"][k] if s["promo_counts"] else None for s in sl] for k in PROMO_KEYS}
    return out


def _slider_series(sliders: list[dict[str, dict[str, int]]], models: set[str] | None, offers: list[int],
                   min_group: int) -> dict[str, list[int | None]]:
    """Slider item counts (the site's own filter numbers), summed over `models` (None = every model, including
    items the migration could not attribute to a model); null below the minimum group of offers."""
    out: dict[str, list[int | None]] = {}
    for key in SLIDER_KEYS:
        vals: list[int | None] = []
        for i, sc in enumerate(sliders):
            per = sc.get(key)
            if per is None or offers[i] < min_group:
                vals.append(None)
                continue
            vals.append(sum(v for m, v in per.items() if models is None or m in models))
        out[key] = vals
    return out


def _null_below(values: list[Any], priced: list[int], min_group: int) -> list[Any]:
    return [v if p >= min_group else None for v, p in zip(values, priced, strict=True)]


def write_public(*, settings: Settings, rules: Rules, entries: list[dict[str, Any]], dates: list[str],
                 directory: list[dict[str, Any]], cfg_info: dict[str, dict[str, Any]],
                 cfg_pub: list[dict[str, dict[str, Any]]], cfg_summ: list[dict[str, dict[str, Any]]],
                 flags_by_date: list[dict[str, list[str]]], model_pub: list[dict[str, dict[str, Any]]],
                 seg_pub: list[dict[str, dict[str, Any]]], total_pub: list[dict[str, Any]],
                 engine_pub: list[dict[str, dict[str, dict[str, Any]]]], lfl_series: dict[str, list[float | None]],
                 net: list[dict[str, tuple[int, int]]], cfg_drops: list[int | None],
                 model_low_series: dict[str, list[float | None]], sliders: list[dict[str, dict[str, int]]],
                 changes_by_date: dict[str, dict[str, Any]], hot: dict[str, dict[str, Any]],
                 window: tuple[str, str], next_run: str | None) -> list[str]:
    root = settings.public_dir
    mg = settings.min_group
    n = len(dates)
    written: list[str] = []

    def out(rel: str, obj: Any, pretty: bool = False) -> None:
        write_json(root / rel, obj, pretty=pretty)
        written.append(rel)

    segment_models = {s: {m["name"] for m in directory if m["segment"] == s} for s in SEGMENTS}

    def net_for(models: set[str] | None) -> tuple[list[int | None], list[int | None]]:
        added: list[int | None] = []
        removed: list[int | None] = []
        for i, mv in enumerate(net):
            if i == 0:
                added.append(None)
                removed.append(None)
                continue
            sel = [v for m, v in mv.items() if models is None or m in models]
            added.append(sum(a for a, _ in sel))
            removed.append(sum(r for _, r in sel))
        return added, removed

    # ---- trends.json ----------------------------------------------------------------------------------------
    totals = series(total_pub)
    ta, tr = net_for(None)
    totals.update(net_added=ta, net_removed=tr, lfl_index=_null_below(lfl_series["total"], totals["priced"], mg),
                  slider_counts=_slider_series(sliders, None, totals["offers"], mg), config_drops=cfg_drops)
    segments = {}
    for s in SEGMENTS:
        ss = series([seg_pub[i].get(s) for i in range(n)])
        seg_added, seg_removed = net_for(segment_models[s])
        ss.update(net_added=seg_added, net_removed=seg_removed,
                  lfl_index=_null_below(lfl_series[f"seg:{s}"], ss["priced"], mg),
                  slider_counts=_slider_series(sliders, segment_models[s], ss["offers"], mg))
        segments[s] = ss
    models_series: dict[str, dict[str, Any]] = {}
    for m in directory:
        ms = series([model_pub[i].get(m["name"]) for i in range(n)])
        m_added, m_removed = net_for({m["name"]})
        ms.update(net_added=m_added, net_removed=m_removed,
                  lfl_index=_null_below(lfl_series[f"model:{m['name']}"], ms["priced"], mg),
                  lowest_version_special=_null_below(model_low_series[m["name"]], ms["priced"], mg),
                  slider_counts=_slider_series(sliders, {m["name"]}, ms["offers"], mg))
        models_series[m["slug"]] = ms
    out("dashboard/trends.json", {"dates": dates, "totals": totals, "segments": segments, "models": models_series})

    # ---- configuration rows -----------------------------------------------------------------------------------
    cur_summ = cfg_summ[-1] if cfg_summ else {}
    cur_flags = flags_by_date[-1] if flags_by_date else {}

    def config_row(ck: str) -> dict[str, Any]:
        s = cur_summ[ck]
        h = hot.get(ck)
        return {
            **cfg_info[ck],
            **{f: s[f] for f in ("offers", "priced", "catalog_median", "special_min", "special_median",
                                 "special_max", "price_30d_median", "discount_pct_median", "discount_pct_max",
                                 "rate_min", "term", "initial_fee", "score_best", "score_median", "components",
                                 "offers_80", "promo_counts")},
            "plan_code": s["plan_code"],
            "flags": cur_flags.get(ck, []),
            "hot": h is not None,
            "hot_score": h["hot_score"] if h else None,
            "drop": h["drop"] if h else None,
            "drop_pct": h["drop_pct"] if h else None,
        }

    def rank_key(r: dict[str, Any]) -> tuple[Any, ...]:
        return (-r["score_best"], -(r["score_median"] or 0), -(r["discount_pct_median"] or 0), r["label"])

    rows = sorted((config_row(ck) for ck in cur_summ), key=rank_key)
    rk = rules.scoring["rankings"]
    per_model: dict[str, list[str]] = {}
    per_seg: dict[str, list[str]] = {}
    for r in rows:
        lst = per_model.setdefault(r["slug"], [])
        if len(lst) < int(rk["top_per_model"]):
            lst.append(r["config_key"])
        sl = per_seg.setdefault(r["segment"], [])
        if len(sl) < int(rk["top_per_segment"]):
            sl.append(r["config_key"])
    out("dashboard/deals.json", {
        "date": dates[-1] if dates else None, "hot_window": list(window), "configs": rows,
        "rankings": {"top_overall": [r["config_key"] for r in rows[: int(rk["top_overall"])]],
                     "top_per_model": per_model, "top_per_segment": per_seg}})

    # ---- models/<slug>.json -------------------------------------------------------------------------------------
    published_ever: set[str] = {ck for summ in cfg_summ for ck in summ}
    keep_models: set[str] = set()
    for m in directory:
        slug = m["slug"]
        keep_models.add(f"{slug}.json")
        groups = sorted({g for i in range(n) for g in engine_pub[i].get(m["name"], {})})
        engines = {}
        for g in groups:
            es = series([engine_pub[i].get(m["name"], {}).get(g) for i in range(n)])
            engines[g] = {"slot": m["engine_slots"].get(g, 0),
                          **{k: es[k] for k in ("offers", "priced", "special_min", "special_median")}}
        configs = []
        for ck in sorted(published_ever, key=lambda k: cfg_info[k]["label"]):
            if cfg_info[ck]["model"] != m["name"]:
                continue
            hist: dict[str, list[Any]] = {f: [] for f in ("offers", "priced", "special_min", "special_median",
                                                          "special_max")}
            for i in range(n):
                cst = cfg_pub[i].get(ck)
                pub = cst is not None and cst["priced"] >= mg
                for f in hist:
                    hist[f].append(cst[f] if pub and cst is not None else None)
            configs.append({**cfg_info[ck], "current": config_row(ck) if ck in cur_summ else None,
                            "history": hist})
        out(f"models/{slug}.json", {
            "model": {k: m[k] for k in ("name", "slug", "segment", "order", "status", "first_seen", "last_seen",
                                        "retired_on", "empty_runs", "engine_groups", "engine_slots",
                                        "possible_rename_of")},
            "dates": dates, "timeline": models_series[slug], "engines": engines, "configurations": configs})

    # ---- changes/<date>.json -----------------------------------------------------------------------------------
    for date, ch in changes_by_date.items():
        out(f"dashboard/changes/{date}.json", ch)

    # ---- latest.json --------------------------------------------------------------------------------------------
    newest = entries[-1] if entries else None
    t = totals

    def kpi(values: list[Any], **extra: Any) -> dict[str, Any]:
        v = values[-1] if values else None
        p = values[-2] if len(values) > 1 else None
        return {"value": v, "delta": (v - p) if v is not None and p is not None else None,
                "spark": values[-12:], **extra}

    rmin: dict[str, Any] = {"value": None, "plan_code": None, "model": None, "priced": 0}
    for mdl, st in (model_pub[-1] if model_pub else {}).items():
        for plan, r in st["rates"].items():
            if r["rate_min"] is not None and (rmin["value"] is None or r["rate_min"] < rmin["value"]):
                rmin = {"value": r["rate_min"], "plan_code": plan, "model": mdl, "priced": r["priced"]}
    tiles = []
    for m in directory:
        ms = models_series[m["slug"]]
        offers = ms["offers"]
        pc = ms["promo_counts"]
        top = sorted((k for k in PROMO_KEYS if pc[k] and pc[k][-1]), key=lambda k: (-(pc[k][-1] or 0),
                                                                                   PROMO_KEYS.index(k)))[:3]
        tiles.append({
            "slug": m["slug"], "name": m["name"], "segment": m["segment"], "status": m["status"],
            "order": m["order"], "offers": offers[-1] if offers else 0,
            "delta": (offers[-1] - offers[-2]) if len(offers) > 1 else None,
            "priced": ms["priced"][-1] if offers else 0,
            "special_min": ms["special_min"][-1] if offers else None,
            "spark": {"special_median": ms["special_median"][-12:], "priced": ms["priced"][-12:]},
            "promos": top, "engine_groups": m["engine_groups"], "first_seen": m["first_seen"],
            "retired_on": m["retired_on"],
        })
    hot_sorted = sorted(hot.items(), key=lambda kv: (-kv[1]["hot_score"], -kv[1]["drop"], cfg_info[kv[0]]["label"]))
    hot_cards = []
    for ck, h in hot_sorted[: int(rules.scoring["hot_latest_limit"])]:
        cs = cur_summ[ck]
        hot_cards.append({
            **{k: cfg_info[ck][k] for k in ("config_key", "label", "model", "slug", "segment", "engine",
                                             "engine_group", "code", "model_year", "plan_code")},
            "offers": cs["offers"], "priced": cs["priced"], "special_median": cs["special_median"],
            "start_price": h["start_price"], "drop": h["drop"], "drop_pct": h["drop_pct"],
            "score_best": cs["score_best"], "hot_score": h["hot_score"], "flags": cur_flags.get(ck, []),
            "reasons": h["reasons"], "promo_counts": cs["promo_counts"], "points": h["points"],
        })
    cur_changes = changes_by_date.get(dates[-1], {}) if dates else {}
    active_models = [sum(1 for m in directory if models_series[m["slug"]]["offers"][i] > 0) for i in range(n)]
    out("dashboard/latest.json", {
        "run": {
            "date": newest["date"] if newest else None, "status": newest["status"] if newest else None,
            "data_date": dates[-1] if dates else None, "next_run": next_run,
            "rules_version": newest.get("rules_version") if newest else None,
            "bundle_hash": newest.get("bundle_hash") if newest else None,
            "duration_s": newest.get("duration_s") if newest else None,
            "snapshots_ok": n, "collector_version": __version__,
            "stale_after_days": int(settings.get("stale_after_days", 9)),
        },
        "kpis": {
            "offers": kpi(t["offers"]),
            "models": kpi(active_models),
            "discount_pct_median": {"discount_pct_median": t["discount_pct_median"][-1] if n else None,
                                    "priced": t["priced"][-1] if n else 0},
            "rate_min": {"rate_min": rmin["value"], "plan_code": rmin["plan_code"],
                         "model": rmin["model"], "priced": rmin["priced"]},
            "config_drops": {"value": cfg_drops[-1] if cfg_drops else None, "first_run": n < 2},
        },
        "models": tiles,
        "hot_configs": hot_cards,
        "hot_count": len(hot),
        "hot_window": list(window),
        "changes": {"date": cur_changes.get("date"), "previous": cur_changes.get("previous"),
                    "summary": cur_changes.get("summary", {}),
                    **{k: cur_changes.get(k, []) for k in ("models_new", "models_retired", "models_returned")}},
        "directory": {
            "segments": list(SEGMENTS),
            "engine_groups": sorted({g for i in range(n) for mm in engine_pub[i].values() for g in mm}),
            "plans": rules.plans["plans"],
            "plan_footnotes": {str(k): v for k, v in rules.plans.get("footnote_texts", {}).items()},
            "leasing_101": rules.plans.get("leasing_101"),
            "promos": {k: {"name": v["name"], "slot": v["color_slot"], "badge_bit": v["badge_bit"],
                           "footnote": rules.promo.get("footnotes", {}).get(k)}
                       for k, v in rules.promo["promos"].items()},
            "scoring": {"weights": rules.scoring["weights"], "momentum_cap_pct": rules.scoring["momentum_cap_pct"],
                        "momentum_new_car": rules.scoring["momentum_new_car"],
                        "promo_bonus": rules.scoring["promo_bonus"],
                        "hot": {k: rules.scoring[k] for k in ("hot_window_days", "hot_drop_pct", "hot_drop_pln",
                                                               "hot_new_score")}},
            "min_group": mg,
            "not_collected": ["VIN", "dealer stock number (komisja)", "offer link", "dealer phone number"],
        },
    })

    # ---- index, model directory, manifest -------------------------------------------------------------------
    out("snapshots/index.json", [
        {"date": e["date"], "status": e["status"]} if e["status"] != "ok" else
        {k: e.get(k) for k in ("date", "status", "offers", "models", "configurations", "rules_version",
                               "bundle_hash")}
        for e in entries], pretty=True)
    out("meta/models.json", [{k: m[k] for k in ("name", "slug", "segment", "order", "status", "first_seen",
                                                "last_seen", "retired_on", "engine_groups")} for m in directory],
        pretty=True)

    # remove files of earlier runs that are no longer part of the public tree
    keep = set(written) | {"manifest.json"}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.relative_to(root).as_posix() not in keep:
                path.unlink()
    files = sorted(written)
    out("manifest.json", {"latest": dates[-1] if dates else None,
                          "newest_snapshot": newest["date"] if newest else None,
                          "files": {rel: sha1_file(root / rel)[:12] for rel in files}}, pretty=True)
    return sorted(written)


def public_path_ok(rel: str) -> bool:
    import re

    return bool(re.fullmatch(
        r"manifest\.json|snapshots/index\.json|dashboard/(latest|trends|deals)\.json|"
        r"dashboard/changes/\d{4}-\d{2}-\d{2}\.json|models/[a-z0-9-]+\.json|meta/models\.json", rel))


def public_root(settings: Settings) -> Path:
    return settings.public_dir
