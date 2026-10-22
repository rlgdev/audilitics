"""One collector run: redacted raw -> snapshot -> derived files -> exports -> report -> guard (spec 4.2, 4.3)."""

from __future__ import annotations

from datetime import date as Date
from pathlib import Path
from typing import Any

from collector.analytics import has_badge
from collector.config import Settings
from collector.export_xlsx import write_csv, write_xlsx
from collector.fetch import FetchError, fetch_live
from collector.guard import guard_public, identifier_check
from collector.indexes import load_index, rebuild
from collector.io import read_json_gz, write_json, write_json_gz, write_text
from collector.normalise import normalise
from collector.report import render
from collector.rules import PROMO_KEYS, Rules, load_rules
from collector.schema import SchemaError, parse, validate_and_redact

RUN_DIR = ".run"  # outside data/: result.json and report.md for the workflow (never committed)
LEGACY_RAW_KEYS = ("sliders", "_bundle_bytes")  # release 1.0 keys that must never be archived again


def _result(date: str, status: str, **kw: Any) -> dict[str, Any]:
    return {"date": date, "status": status, "warnings": [], "issues": [], "gates": [], **kw}


def _write_run(settings: Settings, result: dict[str, Any], report_md: str) -> None:
    d = settings.data.parent / RUN_DIR
    write_json(d / "result.json", result, pretty=True)
    write_text(d / "report.md", report_md + "\n")


def guard_skip(settings: Settings, date: str) -> str | None:
    """Return the newest snapshot date when it is younger than the guard (spec 4.1)."""
    index = load_index(settings.data)
    if not index:
        return None
    newest = max(e["date"] for e in index)
    age = (Date.fromisoformat(date) - Date.fromisoformat(newest)).days
    return newest if age < int(settings.get("min_snapshot_age_days", 6)) else None


def collect_live(settings: Settings, date: str, force: bool = False) -> dict[str, Any]:
    if not force:
        newest = guard_skip(settings, date)
        if newest:
            res = _result(date, "skipped", message=f"newest snapshot {newest} is younger than "
                                                     f"{settings.get('min_snapshot_age_days', 6)} days")
            _write_run(settings, res, render(res, None, None))
            return res
    rules = load_rules(settings.rules_dir, date)
    try:
        raw = fetch_live(settings, date, rules.slider_params())
    except FetchError as e:
        label = {"blocked": "collector-blocked"}.get(e.kind, "collector-failure")
        res = _result(date, "failed", message=str(e))
        title = "blocked" if e.kind == "blocked" else "failed"
        res["issues"].append({"label": label, "title": f"Collector {title} on {date}",
                              "body": f"{e}\n\nNo snapshot was written; the previous site stays online."
                                      + ("\n\nDo not work around the block (spec 11); see docs/runbook.md."
                                         if e.kind == "blocked" else "")})
        res["gates"].append({"gate": "schema" if e.kind == "schema" else "fetch", "result": "failed"})
        _write_run(settings, res, render(res, {"requests": e.requests_log, "source": "live"}, None))
        return res
    return process_raw(settings, raw, archive=True)


def slider_gate(offers: list[dict[str, Any]], slider_counts: dict[str, dict[str, int]], rules: Rules,
                tolerance: float) -> list[str]:
    """Slider count of a promo vs its badge count in total (spec 4.3)."""
    out = []
    for key in PROMO_KEYS:
        if key not in slider_counts:
            continue
        sliders = sum(slider_counts[key].values())
        if key == "be":
            # the Business Edition slider filters on the flag and also returns Final Edition cars (spec 3.4)
            badges = sum(1 for o in offers if o["business_edition"])
        else:
            badges = sum(1 for o in offers if has_badge(o, key, rules))
        if badges and abs(sliders - badges) / badges > tolerance:
            out.append(f"{key}: slider {sliders} vs badge {badges}")
    return out


def process_raw(settings: Settings, raw: dict[str, Any], date: str | None = None,
                archive: bool = True) -> dict[str, Any]:
    date = date or raw["date"]
    raw = {k: v for k, v in raw.items() if k not in LEGACY_RAW_KEYS}
    raw["date"] = date
    data = settings.data
    rules = load_rules(settings.rules_dir, date)

    # spec 4.2 steps 4-5: schema and redaction (an archived raw file is already redacted)
    try:
        items, unknown, dropped = validate_and_redact(raw["feed"]["items"], not raw.get("redacted"),
                                                      settings.discarded)
    except (SchemaError, KeyError, TypeError) as e:
        res = _result(date, "failed", message=f"schema: {e}")
        res["issues"].append({"label": "collector-failure", "title": f"Collector failed on {date}: schema",
                              "body": f"{e}\n\nNo snapshot was written."})
        res["gates"].append({"gate": "schema", "result": "failed"})
        _write_run(settings, res, render(res, {k: v for k, v in raw.items() if k != "feed"}, None))
        return res
    raw["feed"] = {"count": len(items), "items": items}
    raw["redacted"] = True
    schema_info = raw.get("schema") or {}
    unknown = sorted(set(unknown) | set(schema_info.get("unknown_fields", [])))
    dropped = sorted(set(dropped) | set(schema_info.get("dropped_identifying_fields", [])))
    raw["schema"] = {"unknown_fields": unknown, "dropped_identifying_fields": dropped}

    res = _result(date, "ok")
    if unknown or dropped:
        msg = []
        if unknown:
            msg.append("kept in extra: " + ", ".join(f"`{u}`" for u in unknown))
        if dropped:
            msg.append("dropped as identifying: " + ", ".join(f"`{u}`" for u in dropped))
        res["warnings"].append("new feed field(s) " + "; ".join(msg))
        res["issues"].append({"label": "schema-change", "title": f"Feed schema change on {date}",
                              "body": "New field(s) " + "; ".join(msg)})
    res["gates"].append({"gate": "schema", "result": "valid" + (" (new fields)" if unknown or dropped else "")})

    offers = normalise(parse(items), rules, date)

    # spec 4.3: count gate against the previous ok run
    index = load_index(data)
    existing = next((e for e in index if e["date"] == date), None)
    prev_ok = sorted((e for e in index if e["status"] == "ok" and e["date"] < date), key=lambda e: e["date"])
    prev = prev_ok[-1] if prev_ok else None
    status = "ok"
    gates = settings.get("gates", {})
    if prev:
        ratio = len(offers) / prev["offers"] if prev["offers"] else 1.0
        res["ratio"] = round(ratio, 4)
        res["previous"] = {"date": prev["date"], "offers": prev["offers"]}
        if ratio < float(gates.get("suspect_below", 0.8)):
            status = "suspect"
            res["gates"].append({"gate": "count", "result": f"suspect ({ratio * 100:.1f} % of previous)"})
            res["issues"].append({"label": "collector-failure", "title": f"Suspect snapshot on {date}",
                                  "body": f"{len(offers)} offers vs {prev['offers']} on {prev['date']} "
                                          f"({ratio * 100:.1f} %). Stored as `suspect` in the private repository and "
                                          "excluded from every public figure. If the drop is real, set its status to "
                                          "`ok` with `\"status_set_by\": \"maintainer\"` in "
                                          "`data/snapshots/index.json` and run `make rebuild`."})
        elif ratio > float(gates.get("warn_above", 1.2)):
            res["warnings"].append(f"count is {ratio * 100:.1f} % of the previous run")
            res["gates"].append({"gate": "count", "result": f"ok with warning ({ratio * 100:.1f} %)"})
        else:
            res["gates"].append({"gate": "count", "result": f"ok ({ratio * 100:.1f} % of previous)"})
    else:
        res["gates"].append({"gate": "count", "result": "ok (first run)"})
    if status == "suspect" and existing and existing.get("status_set_by") == "maintainer":
        status = "ok"
        res["warnings"].append("status kept as ok: set by a maintainer in index.json")

    # slider counts vs badge counts (spec 4.3)
    slider_counts = raw.get("slider_counts") or {}
    mismatch = slider_gate(offers, slider_counts, rules, float(gates.get("slider_badge_tolerance", 0.01)))
    if mismatch:
        res["warnings"].append("slider and badge counts differ: " + "; ".join(mismatch))
        res["issues"].append({"label": "rules-review", "title": f"Slider and badge counts differ on {date}",
                              "body": "Re-verify the badge rules of spec 3.4 on the live site:\n\n- "
                                      + "\n- ".join(mismatch)})
        res["gates"].append({"gate": "sliders", "result": "warning: " + "; ".join(mismatch)})
    else:
        res["gates"].append({"gate": "sliders", "result": "consistent" if slider_counts else "no slider counts"})

    # bundle hash change -> rules review (status unchanged); the bundle itself is never stored
    bundle_hash = (raw.get("bundle") or {}).get("hash")
    raw["bundle"] = {"name": (raw.get("bundle") or {}).get("name"), "hash": bundle_hash}
    prev_any = sorted((e for e in index if e["date"] < date and e.get("bundle_hash")), key=lambda e: e["date"])
    if bundle_hash and prev_any and prev_any[-1]["bundle_hash"] != bundle_hash:
        res["issues"].append({"label": "rules-review", "title": f"Site bundle changed on {date}",
                              "body": f"Bundle `{prev_any[-1]['bundle_hash']}` -> `{bundle_hash}`. Re-verify the "
                                      "rules of spec 3.4 (sliders, badges, footnotes) on the live site and repeat "
                                      "the reservation check; see docs/runbook.md."})
        res["gates"].append({"gate": "bundle", "result": "changed"})
    else:
        res["gates"].append({"gate": "bundle", "result": "unchanged" if prev_any else "recorded"})
    res["status"] = status

    # write raw (redacted), snapshot, index
    if archive:
        write_json_gz(data / "raw" / f"{date}.json.gz", raw)
    write_json_gz(data / "snapshots" / f"{date}.json.gz", {
        "date": date, "status": status, "rules_version": rules.version, "bundle_hash": bundle_hash,
        "models_listed": list((raw.get("models_json") or {}).keys()),
        "dealers_json": raw.get("dealers_json") or {}, "slider_counts": slider_counts, "offers": offers,
    })
    entry = {
        "date": date, "status": status, "offers": len(offers), "models": len({o["model"] for o in offers}),
        "configurations": len({o["config_key"] for o in offers}),
        "dealers": len({o["dealer_nr"] for o in offers}), "versions": len({o["version_key"] for o in offers}),
        "bundle_hash": bundle_hash, "rules_version": rules.version, "duration_s": raw.get("duration_s"),
        "source": raw.get("source", "live"), "warnings": res["warnings"],
    }
    if existing and existing.get("status_set_by"):
        entry["status_set_by"] = existing["status_set_by"]
    index = sorted([e for e in index if e["date"] != date] + [entry], key=lambda e: e["date"])
    write_json(data / "snapshots" / "index.json", index, pretty=True)
    res["entry"] = entry

    summary = rebuild(settings)
    latest_ok = summary["dates"][-1] if summary["dates"] else None
    if latest_ok == date:
        res["entry"] = {**entry, "public_configurations": summary["public_config_count"]}
        write_xlsx(data / "exports" / f"{date}.xlsx", date, summary["offer_rows"], summary["rules"],
                   summary["directory"])
        write_csv(data / "exports" / "latest.csv", summary["offer_rows"], summary["rules"])

    # spec 4.2 step 11: publication guard and identifier check; a failure fails the run before commit or push
    write_text(data / "reports" / f"{date}.md", render(res, raw, summary if latest_ok == date else None) + "\n")
    findings = guard_public(settings.public_dir, settings.min_group)
    id_findings = identifier_check(data)
    res["gates"].append({"gate": "publication guard",
                         "result": "pass" if not findings else f"failed ({len(findings)} findings)"})
    res["gates"].append({"gate": "identifier check",
                         "result": "pass" if not id_findings else f"failed ({len(id_findings)} findings)"})
    if findings or id_findings:
        res["status"] = "failed"
        res["message"] = "publication guard or identifier check failed"
        res["issues"].append({"label": "publication-guard", "title": f"Publication guard failed on {date}",
                              "body": "Nothing was committed or pushed.\n\n" + "\n".join(
                                  f"- {f}" for f in (findings + id_findings)[:100])})
    md = render(res, raw, summary if latest_ok == date else None)
    write_text(data / "reports" / f"{date}.md", md + "\n")
    _write_run(settings, res, md)
    return res


def replay_file(settings: Settings, path: Path, date: str | None = None) -> dict[str, Any]:
    raw = read_json_gz(path)
    archive = path.resolve().parent != (settings.data / "raw").resolve()
    return process_raw(settings, raw, date=date, archive=archive)


def rebuild_all(settings: Settings) -> list[dict[str, Any]]:
    """Replay every archived raw file in date order (spec 4.4 `make rebuild`). Maintainer status overrides
    in index.json are kept."""
    data = settings.data
    old = {e["date"]: e for e in load_index(data)}
    raws = sorted((data / "raw").glob("*.json.gz"))
    keep = [{"date": d, "status": e["status"], "offers": e.get("offers", 0), "status_set_by": e["status_set_by"]}
            for d, e in old.items() if e.get("status_set_by")]
    write_json(data / "snapshots" / "index.json", keep, pretty=True)
    return [process_raw(settings, read_json_gz(p), archive=False) for p in raws]
