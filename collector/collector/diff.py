"""Changes between consecutive ok snapshots at configuration and model level (spec 6.2).

Offers are never matched across runs; configurations are matched by `config_key` and models by name.
"""

from __future__ import annotations

from statistics import median
from typing import Any

from collector.rules import PROMO_KEYS

Stats = dict[str, Any]


def _cfg_entry(info: dict[str, Any]) -> dict[str, Any]:
    return {k: info[k] for k in ("config_key", "label", "model", "slug", "engine", "engine_group", "code",
                                 "model_year", "plan_code")}


def changes(
    prev_date: str | None,
    cur_date: str,
    prev_cfg: dict[str, Stats] | None,
    cur_cfg: dict[str, Stats],
    cfg_info: dict[str, dict[str, Any]],
    cur_summary: dict[str, dict[str, Any]],
    drop_streak: dict[str, int],
    prev_model: dict[str, Stats] | None,
    cur_model: dict[str, Stats],
    model_net: dict[str, tuple[int, int]],
    slug_of: dict[str, str],
    model_events: dict[str, list[dict[str, Any]]],
    min_group: int,
) -> dict[str, Any]:
    """`*_cfg` and `*_model` map keys to statistics computed with the minimum group (nulls below it)."""
    lists = ("configs_new", "configs_gone", "price_drops", "price_rises", "stock", "promo_changes")
    out: dict[str, Any] = {"date": cur_date, "previous": prev_date, **{k: [] for k in lists}}
    out.update({k: model_events.get(k, []) for k in ("models_new", "models_retired", "models_returned")})
    published_now = {ck for ck, s in cur_cfg.items() if s["priced"] >= min_group}
    if prev_cfg is None or prev_model is None:
        out["summary"] = {**{k: 0 for k in lists}, "median_drop_pct": None, "priced": 0, "largest_drop": None,
                          "models_most_added": [], "first_run": True,
                          **{k: len(out[k]) for k in ("models_new", "models_retired", "models_returned")}}
        return out
    published_prev = {ck for ck, s in prev_cfg.items() if s["priced"] >= min_group}

    for ck in sorted(published_now - published_prev, key=lambda k: cfg_info[k]["label"]):
        s = cur_cfg[ck]
        out["configs_new"].append({
            **_cfg_entry(cfg_info[ck]), "offers": s["offers"], "priced": s["priced"],
            "special_median": s["special_median"], "score_best": cur_summary.get(ck, {}).get("score_best"),
            "reason": "new_in_stock" if ck not in prev_cfg or prev_cfg[ck]["offers"] == 0 else "reached_minimum",
        })
    for ck in sorted(published_prev - published_now, key=lambda k: cfg_info[k]["label"]):
        p = prev_cfg[ck]
        out["configs_gone"].append({
            **_cfg_entry(cfg_info[ck]), "offers": cur_cfg[ck]["offers"] if ck in cur_cfg else 0,
            "priced": p["priced"], "special_median": p["special_median"],
            "reason": "none_left" if ck not in cur_cfg or cur_cfg[ck]["offers"] == 0 else "below_minimum",
        })
    for ck in sorted(published_now & published_prev, key=lambda k: cfg_info[k]["label"]):
        old, new = prev_cfg[ck]["special_median"], cur_cfg[ck]["special_median"]
        if old is None or new is None or old == new:
            continue
        diff = new - old
        row = {**_cfg_entry(cfg_info[ck]), "offers": cur_cfg[ck]["offers"],
               "priced": min(cur_cfg[ck]["priced"], prev_cfg[ck]["priced"]),
               "old": old, "new": new, "diff": diff, "pct": round(diff / old, 4)}
        if diff < 0:
            row["consecutive_drops"] = drop_streak.get(ck, 1)
            out["price_drops"].append(row)
        else:
            out["price_rises"].append(row)
    out["price_drops"].sort(key=lambda r: (r["pct"], r["label"]))
    out["price_rises"].sort(key=lambda r: (-r["pct"], r["label"]))

    for model in sorted(set(cur_model) | set(prev_model)):
        before = prev_model.get(model, {}).get("offers", 0)
        now = cur_model.get(model, {}).get("offers", 0)
        added, removed = model_net.get(model, (0, 0))
        out["stock"].append({"model": model, "slug": slug_of.get(model, ""), "offers_before": before,
                             "offers": now, "net_added": added, "net_removed": removed})
        pb = prev_model.get(model, {}).get("promo_counts")
        pn = cur_model.get(model, {}).get("promo_counts")
        if pb and pn:
            changed = {k: {"before": pb[k], "now": pn[k]} for k in PROMO_KEYS if pb[k] != pn[k]}
            if changed:
                out["promo_changes"].append({"model": model, "slug": slug_of.get(model, ""),
                                             "offers_before": before, "offers": now, "promo_changes": changed})

    drops = out["price_drops"]
    most_added = sorted(out["stock"], key=lambda r: (-r["net_added"], r["model"]))
    out["summary"] = {
        **{k: len(out[k]) for k in lists},
        "median_drop_pct": round(median([-r["pct"] for r in drops]), 4) if drops else None,
        "priced": min((r["priced"] for r in drops), default=0),
        "largest_drop": ({"label": drops[0]["label"], "config_key": drops[0]["config_key"], "diff": drops[0]["diff"],
                          "pct": drops[0]["pct"], "priced": drops[0]["priced"]} if drops else None),
        "models_most_added": [{"model": r["model"], "slug": r["slug"], "net_added": r["net_added"]}
                              for r in most_added[:5] if r["net_added"] > 0],
        "first_run": False,
        **{k: len(out[k]) for k in ("models_new", "models_retired", "models_returned")},
    }
    return out
