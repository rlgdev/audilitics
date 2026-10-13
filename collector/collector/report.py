"""Run report in Markdown, private repository (spec 4.2 step 10, spec 11 Observability). It contains no
wall-clock values other than those archived in the raw file, so a replay reproduces it byte for byte."""

from __future__ import annotations

from typing import Any


def _fmt(n: Any) -> str:
    if n is None:
        return "–"
    if isinstance(n, float):
        return f"{n:,.1f}".replace(",", " ")
    if isinstance(n, int):
        return f"{n:,}".replace(",", " ")
    return str(n)


def render(result: dict[str, Any], raw: dict[str, Any] | None, summary: dict[str, Any] | None) -> str:
    L: list[str] = [f"# Run report {result['date']}", ""]
    L.append(f"Status: **{result['status']}**" + (f" — {result['message']}" if result.get("message") else ""))
    L.append("")
    entry = result.get("entry") or {}
    L += ["| Measure | Value |", "|---|---|"]
    for k, label in (("offers", "Offers"), ("models", "Models"), ("configurations", "Configurations"),
                     ("public_configurations", "Published configurations (≥ 3 priced offers)"),
                     ("dealers", "Dealers"), ("versions", "Versions")):
        if entry.get(k) is not None:
            L.append(f"| {label} | {_fmt(entry[k])} |")
    if result.get("previous"):
        p = result["previous"]
        L.append(f"| Previous ok run | {p['date']} ({_fmt(p['offers'])} offers) |")
    if result.get("ratio") is not None:
        L.append(f"| Count vs previous | {result['ratio'] * 100:.1f} % |")
    L.append(f"| Rules version | {entry.get('rules_version', '–')} |")
    L.append(f"| Bundle hash | {entry.get('bundle_hash', '–')} |")
    if raw:
        L.append(f"| Source | {raw.get('source', 'live')} |")
        L.append(f"| Fetch duration | {_fmt(raw.get('duration_s'))} s |")
        L.append(f"| Requests (budgeted) | {raw.get('request_count', '–')} |")
    L.append("")

    L += ["## Quality gates", "", "| Gate | Result |", "|---|---|"]
    for g in result.get("gates", []):
        L.append(f"| {g['gate']} | {g['result']} |")
    L.append("")

    if raw and raw.get("slider_counts"):
        L += ["## Slider counts (the site's own filter numbers)", "", "| Slider | Items |", "|---|---|"]
        for k, per in sorted(raw["slider_counts"].items()):
            L.append(f"| {k} | {_fmt(sum(per.values()))} |")
        L.append("")

    if result.get("warnings"):
        L += ["## Warnings", ""] + [f"- {w}" for w in result["warnings"]] + [""]

    if summary:
        ev = summary.get("events") or {}
        for key, title in (("models_new", "New models"), ("models_retired", "Retired models"),
                           ("models_returned", "Returned models")):
            items = ev.get(key) or []
            if items:
                L += [f"## {title}", ""]
                for m in items:
                    extra = f" — possible rename of {m['possible_rename_of']}" if m.get("possible_rename_of") else ""
                    L.append(f"- {m['model']} (`{m['slug']}`, segment {m['segment']}, {m['cars_now']} offers){extra}")
                L.append("")
        ch = (summary.get("changes") or {}).get("summary") or {}
        if ch and not ch.get("first_run"):
            L += ["## Changes vs previous run (configurations)", "", "| List | Count |", "|---|---|"]
            for k in ("configs_new", "configs_gone", "price_drops", "price_rises", "promo_changes"):
                L.append(f"| {k.replace('_', ' ')} | {_fmt(ch.get(k))} |")
            if ch.get("median_drop_pct") is not None:
                L.append(f"| median configuration drop | {ch['median_drop_pct'] * 100:.1f} % |")
            L.append("")
        elif ch.get("first_run"):
            L += ["First ok snapshot: nothing to compare yet.", ""]
        L += [f"Hot configurations: {len(summary.get('hot') or {})}", ""]

    if raw and raw.get("requests"):
        L += ["## Request log", "", "| # | Path | Status | Bytes | ms | Budgeted |", "|---|---|---|---|---|---|"]
        for i, r in enumerate(raw["requests"], start=1):
            L.append(f"| {i} | `{r['path']}` | {r.get('status')} | {_fmt(r.get('bytes'))} | {r.get('ms')} | "
                     f"{'yes' if r.get('counted', True) else 'no'} |")
        L.append("")
    return "\n".join(L)
