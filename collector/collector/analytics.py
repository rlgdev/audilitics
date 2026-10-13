"""Statistics, deal score, like-for-like index and hot deals on configurations (spec 6).

No function here follows a single car across runs: runs are compared through configurations matched by
`config_key` (spec 5.5). Every statistic object carries `offers` and `priced`, and with `min_group` > 0 a statistic
resting on fewer offers is null, so the publication guard can check it (spec 5.5, 10.5).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import date as Date
from statistics import median
from typing import Any

from collector.rules import PROMO_KEYS, Rules

Offer = dict[str, Any]
COMPONENTS = ("D", "P", "M", "R", "B")


def days_between(a: str, b: str) -> int:
    return (Date.fromisoformat(b) - Date.fromisoformat(a)).days


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def med(values: Iterable[float | None]) -> float | None:
    v = [x for x in values if x is not None]
    return float(median(v)) if v else None


def r4(x: float | None) -> float | None:
    return None if x is None else round(x, 4)


def pct_rank(x: float, values: list[float]) -> float:
    """Percentile rank 0-100 of x within values (ties take the mid rank); a group of one scores 50."""
    n = len(values)
    if n <= 1:
        return 50.0
    below = sum(1 for v in values if v < x)
    equal = sum(1 for v in values if v == x)
    return 100.0 * (below + 0.5 * (equal - 1)) / (n - 1)


def has_badge(o: Offer, key: str, rules: Rules) -> bool:
    return bool(o["promo_bits"] >> int(rules.promo["promos"][key]["badge_bit"]) & 1)


def badge_counts(offers: list[Offer], rules: Rules) -> dict[str, int]:
    return {k: sum(1 for o in offers if has_badge(o, k, rules)) for k in PROMO_KEYS}


# ---- 6.1 statistics of a group --------------------------------------------------------------------------------
def stats(offers: list[Offer], rules: Rules, min_group: int) -> dict[str, Any]:
    """Statistics of one group of offers. Below `min_group` priced offers every price, discount and rate figure
    is null; below `min_group` offers the badge counts are null (spec 5.5)."""
    priced = [o for o in offers if o["special"] is not None]
    n, p = len(offers), len(priced)
    ok = p >= max(min_group, 1)
    sp = [o["special"] for o in priced]
    by_plan: dict[str, list[float]] = {}
    for o in priced:
        if o["rate"] is not None:
            by_plan.setdefault(o["plan_code"], []).append(o["rate"])
    rates = {}
    for plan in sorted(by_plan):
        rs = by_plan[plan]
        k_ok = len(rs) >= max(min_group, 1)
        rates[plan] = {"priced": len(rs), "rate_min": min(rs) if k_ok else None,
                       "rate_median": med(rs) if k_ok else None}
    return {
        "offers": n,
        "priced": p,
        "special_min": min(sp) if ok else None,
        "special_median": med(sp) if ok else None,
        "special_max": max(sp) if ok else None,
        "discount_pct_median": r4(med(o["discount_pct"] for o in priced)) if ok else None,
        "discount_pct_max": max((o["discount_pct"] for o in priced if o["discount_pct"] is not None),
                                default=None) if ok else None,
        "catalog_median": med(o["catalog"] for o in priced) if ok else None,
        "price_30d_median": med(o["price_30d"] for o in priced) if ok else None,
        "rates": rates,
        "promo_counts": badge_counts(offers, rules) if n >= max(min_group, 1) else None,
    }


def rate_min_overall(st: dict[str, Any]) -> tuple[float | None, str | None, int]:
    """Lowest published rate over the plans of a group, with its plan and that plan's priced count."""
    best: tuple[float | None, str | None, int] = (None, None, 0)
    for plan, r in st["rates"].items():
        if r["rate_min"] is not None and (best[0] is None or r["rate_min"] < best[0]):
            best = (r["rate_min"], plan, r["priced"])
    return best


# ---- 6.3 deal score ------------------------------------------------------------------------------------------
def score_offers(offers: list[Offer], prev_median: dict[str, float], rules: Rules) -> dict[str, dict[str, Any]]:
    """Score every priced offer of one snapshot. `prev_median` holds the previous snapshot's median special of
    each configuration that had at least the minimum group of priced offers there (spec 6.3, Momentum)."""
    sc = rules.scoring
    w = sc["weights"]
    cap = float(sc["momentum_cap_pct"])
    bonus = sc["promo_bonus"]
    priced = [o for o in offers if o["special"] is not None and o["catalog"]]
    by_model: dict[str, list[Offer]] = {}
    by_model_engine: dict[tuple[str, str | None], list[Offer]] = {}
    by_model_plan: dict[tuple[str, str], list[Offer]] = {}
    by_config: dict[str, list[float]] = {}
    for o in priced:
        by_model.setdefault(o["model"], []).append(o)
        by_model_engine.setdefault((o["model"], o["engine_group"]), []).append(o)
        by_model_plan.setdefault((o["model"], o["plan_code"]), []).append(o)
        by_config.setdefault(o["config_key"], []).append(o["special"])
    disc = {k: [o["discount_pct"] for o in v] for k, v in by_model.items()}
    spec = {k: [o["special"] for o in v] for k, v in by_model_engine.items()}
    rr = {k: [o["rate"] / o["special"] for o in v if o["rate"] is not None] for k, v in by_model_plan.items()}
    cur_median = {k: float(median(v)) for k, v in by_config.items()}

    out: dict[str, dict[str, Any]] = {}
    for o in priced:
        d = pct_rank(o["discount_pct"], disc[o["model"]])
        p = 100.0 - pct_rank(o["special"], spec[(o["model"], o["engine_group"])])
        prev = prev_median.get(o["config_key"])
        if prev is None:
            m = float(sc["momentum_new_car"])
        else:
            drop = (prev - cur_median[o["config_key"]]) / prev if prev else 0.0
            m = 100.0 * min(max(drop, 0.0), cap) / cap
        r = 100.0 - pct_rank(o["rate"] / o["special"], rr[(o["model"], o["plan_code"])]) if o["rate"] is not None \
            else 0.0
        b = 0
        if has_badge(o, "pu", rules):
            b += int(bonus["pu"])
        if has_badge(o, "fe", rules) or has_badge(o, "p15", rules):
            b += int(bonus["fe_or_p15"])
        if has_badge(o, "bo", rules):
            b += int(bonus["bo"])
        # Rounded components first, so a stored breakdown reproduces its score exactly.
        d, p, m, r = round(d, 1), round(p, 1), round(m, 1), round(r, 1)
        total = w["D"] * d + w["P"] * p + w["M"] * m + w["R"] * r + b
        out[o["offer_id"]] = {"score": round_half_up(total), "D": d, "P": p, "M": m, "R": r, "B": b}
    return out


def config_summary(offers: list[Offer], scores: dict[str, dict[str, Any]], rules: Rules,
                   min_group: int) -> dict[str, Any]:
    """Public configuration summary (spec 6.3): statistics plus score summary; no single offer's components."""
    st = stats(offers, rules, min_group)
    scored = [scores[o["offer_id"]] for o in offers if o["offer_id"] in scores]
    ok = st["priced"] >= max(min_group, 1) and bool(scored)
    plan_code = offers[0]["plan_code"] if offers else None
    plan = rules.plan(plan_code) if plan_code else None
    rmin, _, _ = rate_min_overall(st)
    out = {
        **st,
        "plan_code": plan_code,
        "rate_min": rmin,
        "term": plan["term_months"] if plan else None,
        "initial_fee": round(plan["fee_pct"] * st["catalog_median"]) if plan and st["catalog_median"] else None,
        "score_best": max(s["score"] for s in scored) if ok else None,
        "score_median": med(s["score"] for s in scored) if ok else None,
        "components": {c: med(s[c] for s in scored) for c in COMPONENTS} if ok else None,
        "offers_80": sum(1 for s in scored if s["score"] >= 80) if ok else None,
    }
    return out


# ---- 6.1 like-for-like index -------------------------------------------------------------------------------------
def lfl_step(prev: dict[str, tuple[int, float | None]], cur: dict[str, tuple[int, float | None]],
             min_group: int) -> float | None:
    """Median of special_median_t / special_median_t-1 over configurations with at least the minimum group of
    priced offers in both snapshots; None when no configuration matches (the index then stays flat)."""
    ratios = []
    for ck, (p, m) in cur.items():
        q = prev.get(ck)
        if q and q[0] >= min_group and p >= min_group and q[1] and m:
            ratios.append(m / q[1])
    return med(ratios)


# ---- 6.5 hot deals ---------------------------------------------------------------------------------------------
def hot_configs(
    window: list[tuple[str, dict[str, dict[str, Any]]]],
    current: dict[str, dict[str, Any]],
    lowest_ever: set[str],
    first_published: dict[str, str],
    first_ok_date: str,
    rules: Rules,
    min_group: int,
) -> dict[str, dict[str, Any]]:
    """window = [(date, {config_key: stats})] of the ok snapshots inside the window, oldest first; the last one
    is today. `current` = published configuration summaries today."""
    sc = rules.scoring
    if len(window) < 2 and first_ok_date == window[-1][0]:
        return {}
    cur_date = window[-1][0]
    out: dict[str, dict[str, Any]] = {}
    for ck, summ in current.items():
        if summ["special_median"] is None or summ["score_best"] is None:
            continue
        points = [{"date": d, "special_median": s[ck]["special_median"], "priced": s[ck]["priced"]}
                  for d, s in window if ck in s and s[ck]["priced"] >= min_group and s[ck]["special_median"]]
        if not points:
            continue
        start = points[0]["special_median"]
        now = summ["special_median"]
        drop = start - now
        drop_pct = drop / start if start else 0.0
        fell_inside = any(b["special_median"] < a["special_median"] for a, b in zip(points, points[1:], strict=False))
        reasons = []
        if drop > 0 and (drop_pct >= float(sc["hot_drop_pct"]) or drop >= float(sc["hot_drop_pln"])):
            reasons.append("drop")
        if ck in lowest_ever and fell_inside:
            reasons.append("lowest_ever")
        fp = first_published.get(ck)
        if fp and fp != first_ok_date and days_between(fp, cur_date) <= int(sc["hot_window_days"]) \
                and fp >= window[0][0] and summ["score_best"] >= int(sc["hot_new_score"]):
            reasons.append("new_high_score")
        if not reasons:
            continue
        add = min(float(sc["hot_bonus_cap"]), float(sc["hot_bonus_per_pct"]) * max(drop_pct, 0.0) * 100)
        out[ck] = {
            "hot_score": round(summ["score_best"] + add, 1),
            "start_price": start,
            "drop": drop if drop > 0 else 0,
            "drop_pct": round(drop_pct, 4) if drop > 0 else 0.0,
            "reasons": reasons,
            "points": points,
        }
    return out
