"""Rebuild every derived file from the stored snapshots (spec 4.2 step 9, spec 5.3).

Private files go to data/private/ and data/meta/; the public tree is assembled by public.py into data/public/.
Everything is a pure function of data/snapshots/ and rules/, so a run is idempotent and `make rebuild` reproduces
history exactly (spec 11, Reproducibility).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date as Date
from datetime import timedelta
from pathlib import Path
from typing import Any

from collector.analytics import (
    COMPONENTS,
    config_summary,
    days_between,
    hot_configs,
    lfl_step,
    score_offers,
    stats,
)
from collector.config import Settings
from collector.diff import changes
from collector.io import read_json, read_json_gz, write_json
from collector.lifecycle import SEGMENTS, build_directory
from collector.public import write_public
from collector.rules import load_rules

Offer = dict[str, Any]

OFFER_COLUMNS = [
    "offer_id", "model", "slug", "segment", "engine", "engine_group", "code", "model_year", "production_year",
    "catalog", "special", "discount", "discount_pct", "price_30d", "promo_bits", "rate", "plan_code", "initial_fee",
    "term", "identical", "dealer_nr", "dealer", "config_key", "config_change", "lowest_ever", "score", "D", "P", "M",
    "R", "B", "flags", "hot",
]


def load_index(data: Path) -> list[dict[str, Any]]:
    p = data / "snapshots" / "index.json"
    return list(read_json(p)) if p.exists() else []


def next_run(date: str, min_age_days: int = 13) -> str:
    """Next Monday on or after date + 13 days (cron Mondays + 13-day guard, spec 4.1)."""
    d = Date.fromisoformat(date) + timedelta(days=min_age_days)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d.isoformat()


def dealer_city(name: str | None) -> str | None:
    if not name:
        return None
    n = name.strip()
    for sep in (" - ", ", "):
        if sep in n:
            return n.split(sep)[-1].strip() or None
    m = re.match(r"^(?:Audi Centrum|Audi|Porsche)\s+(.+)$", n)
    return m.group(1).strip() if m else None


def config_label(o: Offer) -> str:
    return f"{o['model'].removeprefix('Audi ')} {o['engine'] or '(engine not listed)'}, {o['code']}, {o['model_year']}"


def by(offers: list[Offer], key: str) -> dict[Any, list[Offer]]:
    out: dict[Any, list[Offer]] = {}
    for o in offers:
        out.setdefault(o[key], []).append(o)
    return out


def rebuild(settings: Settings) -> dict[str, Any]:
    data = settings.data
    mg = settings.min_group
    entries = sorted(load_index(data), key=lambda e: e["date"])
    ok_dates = [e["date"] for e in entries if e["status"] == "ok"]
    rules = load_rules(settings.rules_dir, ok_dates[-1] if ok_dates else "9999-12-31")
    aliases = {name: ov["merge_into"] for name, ov in (rules.models.get("overrides") or {}).items()
               if ov and ov.get("merge_into")}

    snaps: list[tuple[str, list[Offer]]] = []
    sliders: list[dict[str, dict[str, int]]] = []
    runs = []
    dealers_meta: dict[str, dict[str, Any]] = {}
    for e in entries:
        snap = read_json_gz(data / "snapshots" / f"{e['date']}.json.gz")
        for nr, name in sorted((snap.get("dealers_json") or {}).items()):
            dealers_meta.setdefault(nr, {"nr": nr, "name": name, "first_seen": e["date"]})["name"] = name
        for o in snap["offers"]:
            if o["dealer_nr"]:
                d = dealers_meta.setdefault(o["dealer_nr"], {"nr": o["dealer_nr"], "name": o["dealer"],
                                                             "first_seen": e["date"]})
                d["last_seen"] = e["date"]
        if e["status"] != "ok":
            continue
        offers = snap["offers"]
        for o in offers:
            o["model"] = aliases.get(o["model"], o["model"])
        runs.append((e["date"], [aliases.get(m, m) for m in snap.get("models_listed", [])], offers))
        snaps.append((e["date"], offers))
        sliders.append(snap.get("slider_counts") or {})
    for d in dealers_meta.values():
        d["city"] = dealer_city(d["name"])

    directory, events = build_directory(runs, rules, int(settings.get("empty_runs_to_retire", 3)))
    slug_of = {m["name"]: m["slug"] for m in directory}
    segment_of = {m["name"]: m["segment"] for m in directory}
    dates = [d for d, _ in snaps]
    n = len(dates)

    cfg_info: dict[str, dict[str, Any]] = {}
    for _, offers in snaps:
        for o in offers:
            if o["config_key"] not in cfg_info:
                cfg_info[o["config_key"]] = {
                    "config_key": o["config_key"], "label": config_label(o), "model": o["model"],
                    "slug": slug_of[o["model"]], "segment": segment_of[o["model"]], "engine": o["engine"],
                    "engine_group": o["engine_group"], "code": o["code"], "model_year": o["model_year"],
                    "plan_code": o["plan_code"],
                }

    # LFL groups: total, each segment, each model (spec 6.1)
    group_pred: dict[str, Callable[[str], bool]] = {"total": lambda ck: True}
    for seg in SEGMENTS:
        group_pred[f"seg:{seg}"] = lambda ck, sg=seg: cfg_info[ck]["segment"] == sg  # type: ignore[misc]
    for m in directory:
        group_pred[f"model:{m['name']}"] = lambda ck, nm=m["name"]: cfg_info[ck]["model"] == nm  # type: ignore[misc]

    # ---- walk the ok snapshots in order ---------------------------------------------------------------------
    cfg_pub: list[dict[str, dict[str, Any]]] = []      # per snapshot: config -> public statistics
    cfg_priv: list[dict[str, dict[str, Any]]] = []     # per snapshot: config -> unrestricted statistics
    cfg_summ: list[dict[str, dict[str, Any]]] = []     # per snapshot: published config -> summary
    model_pub: list[dict[str, dict[str, Any]]] = []
    seg_pub: list[dict[str, dict[str, Any]]] = []
    total_pub: list[dict[str, Any]] = []
    engine_pub: list[dict[str, dict[str, dict[str, Any]]]] = []
    lfl = {k: 100.0 for k in group_pred}
    lfl_series: dict[str, list[float | None]] = {k: [] for k in group_pred}
    net: list[dict[str, tuple[int, int]]] = []
    cfg_drops_count: list[int | None] = []
    lowest_cfg: dict[str, float] = {}          # running minimum of published special_min
    lowest_cfg_any: dict[str, float] = {}      # running minimum over every priced offer (private offer flag)
    model_low: dict[str, float] = {}
    model_low_series: dict[str, list[float | None]] = {m["name"]: [] for m in directory}
    first_published: dict[str, str] = {}
    streak: dict[str, int] = {}
    changes_by_date: dict[str, dict[str, Any]] = {}
    dealer_series: dict[str, dict[str, list[Any]]] = {}
    flags_by_date: list[dict[str, list[str]]] = []
    scores: dict[str, dict[str, Any]] = {}

    for i, (date, offers) in enumerate(snaps):
        cfg = by(offers, "config_key")
        cp = {ck: stats(os_, rules, mg) for ck, os_ in cfg.items()}
        cv = {ck: stats(os_, rules, 0) for ck, os_ in cfg.items()}
        prev_median = {ck: s["special_median"] for ck, s in (cfg_pub[-1] if cfg_pub else {}).items()
                       if s["priced"] >= mg and s["special_median"] is not None}
        scores = score_offers(offers, prev_median, rules)
        summ = {ck: config_summary(os_, scores, rules, mg) for ck, os_ in cfg.items() if cp[ck]["priced"] >= mg}
        cfg_pub.append(cp)
        cfg_priv.append(cv)
        cfg_summ.append(summ)

        bm = by(offers, "model")
        model_pub.append({m: stats(os_, rules, mg) for m, os_ in bm.items()})
        seg_pub.append({s: stats([o for o in offers if segment_of[o["model"]] == s], rules, mg) for s in SEGMENTS})
        total_pub.append(stats(offers, rules, mg))
        engine_pub.append({m: {(g or "(none)"): stats(os2, rules, mg) for g, os2 in by(os_, "engine_group").items()}
                           for m, os_ in bm.items()})

        # like-for-like over matched configurations (spec 6.1)
        for key, pred in group_pred.items():
            if i > 0:
                prev = {ck: (s["priced"], s["special_median"]) for ck, s in cfg_pub[i - 1].items() if pred(ck)}
                cur = {ck: (s["priced"], s["special_median"]) for ck, s in cp.items() if pred(ck)}
                ratio = lfl_step(prev, cur, mg)
                lfl[key] *= ratio if ratio else 1.0
            lfl_series[key].append(round(lfl[key], 2))

        # net stock movement per model: sum of positive and negative configuration count changes (spec 6.1)
        moves: dict[str, tuple[int, int]] = {}
        if i > 0:
            prev_counts = {ck: s["offers"] for ck, s in cfg_priv[i - 1].items()}
            for ck in sorted(set(prev_counts) | set(cv)):
                delta = (cv[ck]["offers"] if ck in cv else 0) - prev_counts.get(ck, 0)
                mdl = cfg_info[ck]["model"]
                a, r_ = moves.get(mdl, (0, 0))
                moves[mdl] = (a + max(delta, 0), r_ + max(-delta, 0))
        net.append(moves)

        # configuration flags, drop streaks and first publication (spec 6.3)
        flags: dict[str, list[str]] = {}
        drops_pct: dict[str, float] = {}
        for ck, cs in summ.items():
            first_published.setdefault(ck, date)
            lowest_cfg[ck] = min(lowest_cfg.get(ck, cs["special_min"]), cs["special_min"])
            fl = []
            if cs["special_min"] <= lowest_cfg[ck]:
                fl.append("lowest_ever")
            if i > 0 and first_published[ck] == date:
                fl.append("new_config")
            prev_s = cfg_summ[i - 1].get(ck) if i > 0 else None
            if prev_s and prev_s["special_median"] and cs["special_median"] < prev_s["special_median"]:
                streak[ck] = streak.get(ck, 0) + 1
                drops_pct[ck] = (prev_s["special_median"] - cs["special_median"]) / prev_s["special_median"]
            else:
                streak[ck] = 0
            flags[ck] = fl
        best_drop: dict[str, float] = {}
        for ck, p in drops_pct.items():
            best_drop[cfg_info[ck]["model"]] = max(best_drop.get(cfg_info[ck]["model"], 0.0), p)
        for ck, p in drops_pct.items():
            if p == best_drop[cfg_info[ck]["model"]]:
                flags[ck].append("biggest_drop_this_run")
        flags_by_date.append(flags)
        cfg_drops_count.append(len(drops_pct) if i > 0 else None)
        for o in offers:
            if o["special"] is not None:
                lowest_cfg_any[o["config_key"]] = min(lowest_cfg_any.get(o["config_key"], o["special"]), o["special"])

        for m in directory:
            st = model_pub[i].get(m["name"])
            if st and st["special_min"] is not None:
                model_low[m["name"]] = min(model_low.get(m["name"], st["special_min"]), st["special_min"])
                model_low_series[m["name"]].append(model_low[m["name"]])
            else:
                model_low_series[m["name"]].append(None)

        changes_by_date[date] = changes(
            dates[i - 1] if i > 0 else None, date, cfg_pub[i - 1] if i > 0 else None, cp, cfg_info, summ, streak,
            model_pub[i - 1] if i > 0 else None, model_pub[i], moves, slug_of, events.get(date, {}), mg)

        for nr, os_ in by(offers, "dealer_nr").items():
            ds = dealer_series.setdefault(nr or "", {"offers": [0] * i, "discount_pct_median": [None] * i})
            st = stats(os_, rules, 0)
            ds["offers"].append(st["offers"])
            ds["discount_pct_median"].append(st["discount_pct_median"])
        for ds in dealer_series.values():
            while len(ds["offers"]) < i + 1:
                ds["offers"].append(0)
                ds["discount_pct_median"].append(None)

    # ---- current snapshot --------------------------------------------------------------------------------------
    cur_date = dates[-1] if dates else None
    cur_offers = snaps[-1][1] if snaps else []
    cur_summ = cfg_summ[-1] if cfg_summ else {}
    hot: dict[str, dict[str, Any]] = {}
    window: tuple[str, str] = ("", "")
    if snaps and cur_date:
        wdays = int(rules.scoring["hot_window_days"])
        win = [(d, cfg_pub[k]) for k, d in enumerate(dates) if days_between(d, cur_date) <= wdays]
        window = (win[0][0], cur_date)
        lowest_now = {ck for ck, fl in flags_by_date[-1].items() if "lowest_ever" in fl}
        hot = hot_configs(win, cur_summ, lowest_now, first_published, dates[0], rules, mg)

    version_count: dict[str, int] = {}
    for o in cur_offers:
        version_count[o["version_key"]] = version_count.get(o["version_key"], 0) + 1
    prev_med = {ck: s["special_median"] for ck, s in (cfg_priv[-2] if n > 1 else {}).items()}
    cur_med = {ck: s["special_median"] for ck, s in (cfg_priv[-1] if n else {}).items()}
    offer_rows: list[dict[str, Any]] = []
    for o in cur_offers:
        plan = rules.plan(o["plan_code"])
        sv = scores.get(o["offer_id"])
        ck = o["config_key"]
        lowest = o["special"] is not None and o["special"] <= lowest_cfg_any.get(ck, o["special"])
        fl = (["lowest_ever"] if lowest else []) + (["last_one"] if version_count[o["version_key"]] == 1 else [])
        pm_, cm_ = prev_med.get(ck), cur_med.get(ck)
        offer_rows.append({
            "offer_id": o["offer_id"], "model": o["model"], "slug": slug_of[o["model"]],
            "segment": segment_of[o["model"]], "engine": o["engine"], "engine_group": o["engine_group"],
            "code": o["code"], "model_year": o["model_year"], "production_year": o["production_year"],
            "catalog": o["catalog"], "special": o["special"], "discount": o["discount"],
            "discount_pct": o["discount_pct"], "price_30d": o["price_30d"], "promo_bits": o["promo_bits"],
            "rate": o["rate"], "plan_code": o["plan_code"],
            "initial_fee": round(plan["fee_pct"] * o["catalog"]) if o["catalog"] else None,
            "term": plan["term_months"], "identical": version_count[o["version_key"]], "dealer_nr": o["dealer_nr"],
            "dealer": o["dealer"], "config_key": ck,
            "config_change": (cm_ - pm_) if pm_ is not None and cm_ is not None else None,
            "lowest_ever": lowest, "score": sv["score"] if sv else None,
            **{c: (sv[c] if sv else None) for c in COMPONENTS}, "flags": fl, "hot": ck in hot,
        })

    def table(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {"columns": OFFER_COLUMNS, "rows": [[r[c] for c in OFFER_COLUMNS] for r in rows]}

    def out(rel: str, obj: Any, pretty: bool = False) -> None:
        write_json(data / rel, obj, pretty=pretty)

    # ---- private files ------------------------------------------------------------------------------------------
    out("meta/models.json", directory, pretty=True)
    out("meta/dealers.json", {k: {f: dealers_meta[k].get(f) for f in ("nr", "name", "city", "first_seen",
                                                                       "last_seen")}
                              for k in sorted(dealers_meta)}, pretty=True)
    bundles: dict[str, str] = {}
    for e in entries:
        if e.get("bundle_hash") and e["bundle_hash"] not in bundles:
            bundles[e["bundle_hash"]] = e["date"]
    out("meta/bundles.json", [{"hash": h, "first_seen": d} for h, d in bundles.items()], pretty=True)

    rows_by_slug: dict[str, list[dict[str, Any]]] = {}
    for r in offer_rows:
        rows_by_slug.setdefault(r["slug"], []).append(r)
    keep: set[str] = set()
    for m in directory:
        keep.add(f"{m['slug']}.json")
        cfgs = []
        for ck, info in sorted(cfg_info.items(), key=lambda kv: kv[1]["label"]):
            if info["model"] != m["name"]:
                continue
            cfgs.append({**info, "history": {
                f: [cfg_priv[k][ck][f] if ck in cfg_priv[k] else (0 if f in ("offers", "priced") else None)
                    for k in range(n)]
                for f in ("offers", "priced", "special_min", "special_median", "special_max")}})
        out(f"private/models/{m['slug']}.json", {
            "model": {k: m[k] for k in ("name", "slug", "segment", "status")}, "dates": dates,
            "offers": table(rows_by_slug.get(m["slug"], [])), "configurations": cfgs})
    pm = data / "private" / "models"
    if pm.exists():
        for f in pm.glob("*.json"):
            if f.name not in keep:
                f.unlink()

    scored = sorted((r for r in offer_rows if r["score"] is not None),
                    key=lambda r: (-r["score"], -(r["discount"] or 0), r["offer_id"]))
    rk = rules.scoring["rankings"]
    per_model: dict[str, list[str]] = {}
    per_seg: dict[str, list[str]] = {}
    for r in scored:
        lst = per_model.setdefault(r["slug"], [])
        if len(lst) < int(rk["top_per_model"]):
            lst.append(r["offer_id"])
        sl = per_seg.setdefault(r["segment"], [])
        if len(sl) < int(rk["top_per_segment"]):
            sl.append(r["offer_id"])
    out("private/deals.json", {"date": cur_date, "hot_window": list(window), **table(scored), "rankings": {
        "top_overall": [r["offer_id"] for r in scored[: int(rk["top_overall"])]],
        "top_per_model": per_model, "top_per_segment": per_seg}})

    cur_by_dealer = by(cur_offers, "dealer_nr")
    out("private/dealers.json", {"dates": dates, "dealers": [
        {"nr": nr, "name": (dealers_meta.get(nr) or {}).get("name"), "city": (dealers_meta.get(nr) or {}).get("city"),
         **dealer_series[nr],
         "models_now": dict(sorted((slug_of[m], len(os_))
                                   for m, os_ in by(cur_by_dealer.get(nr, []), "model").items()))}
        for nr in sorted(dealer_series)]})

    # ---- public tree --------------------------------------------------------------------------------------------
    write_public(
        settings=settings, rules=rules, entries=entries, dates=dates, directory=directory, cfg_info=cfg_info,
        cfg_pub=cfg_pub, cfg_summ=cfg_summ, flags_by_date=flags_by_date, model_pub=model_pub, seg_pub=seg_pub,
        total_pub=total_pub, engine_pub=engine_pub, lfl_series=lfl_series, net=net, cfg_drops=cfg_drops_count,
        model_low_series=model_low_series, sliders=sliders, changes_by_date=changes_by_date, hot=hot,
        window=window,
        next_run=next_run(entries[-1]["date"], int(settings.get("min_snapshot_age_days", 13))) if entries else None)

    return {"directory": directory, "events": events.get(cur_date or "", {}),
            "changes": changes_by_date.get(cur_date or "", {}), "offer_rows": offer_rows, "hot": hot,
            "window": window, "dates": dates, "rules": rules, "dealers": dealers_meta,
            "config_count": len(cfg_pub[-1]) if cfg_pub else 0, "public_config_count": len(cur_summ)}
