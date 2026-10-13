"""Model discovery and lifecycle (spec 4.6).

The model directory is rebuilt from the sequence of `ok` snapshots on every run, so it is a pure function of
the snapshots plus rules/models.yaml and a replay always yields the same directory.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from collector.rules import Rules

SEGMENTS = ("A", "Q", "S/RS", "e-tron")
# Fixed colour-slot order for engine groups (spec 8.2); anything else takes the next free slot up to 5.
ENGINE_SLOT_ORDER = ("TFSI", "TDI", "TFSI quattro", "TDI quattro", "e-hybrid / e-tron")


def slugify(name: str) -> str:
    s = re.sub(r"^Audi\s+", "", name.strip())
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def segment_of(name: str) -> str:
    if name.startswith("Audi RS") or re.match(r"^Audi S[0-9Q]", name):
        return "S/RS"
    if "e-tron" in name:
        return "e-tron"
    if name.startswith("Audi Q"):
        return "Q"
    return "A"


def engine_family(group: str | None) -> str:
    g = (group or "").strip()
    if "hybrid" in g or "e-tron" in g or g.endswith(" e"):
        return "e-hybrid / e-tron"
    return g


def assign_engine_slots(groups: list[str]) -> dict[str, int]:
    """Colour slot 1-5 per engine group of one model; 0 = folded into 'Other' (spec 8.2)."""
    slots: dict[str, int] = {}
    used: set[int] = set()
    for g in groups:
        fam = engine_family(g)
        if fam in ENGINE_SLOT_ORDER:
            s = ENGINE_SLOT_ORDER.index(fam) + 1
            if s not in used:
                slots[g] = s
                used.add(s)
    for g in groups:
        if g in slots:
            continue
        free = [s for s in range(1, 6) if s not in used]
        slots[g] = free[0] if free else 0
        if free:
            used.add(free[0])
    return slots


def build_directory(
    runs: list[tuple[str, list[str], list[dict[str, Any]]]],
    rules: Rules,
    empty_runs_to_retire: int = 3,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, list[dict[str, Any]]]]]:
    """runs = [(date, models_listed_by_site, observations)] for every ok snapshot, oldest first.

    Returns the model directory (sorted by order) and per-date events
    {date: {models_new: [...], models_retired: [...], models_returned: [...]}}.
    """
    models: dict[str, dict[str, Any]] = {}
    events: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for date, listed, obs in runs:
        ev: dict[str, list[dict[str, Any]]] = {"models_new": [], "models_retired": [], "models_returned": []}
        counts: dict[str, int] = {}
        engines: dict[str, list[str]] = {}
        prefixes: dict[str, set[str]] = {}
        for o in obs:
            counts[o["model"]] = counts.get(o["model"], 0) + 1
            eg = o["engine_group"] or "(none)"
            engines.setdefault(o["model"], [])
            if eg not in engines[o["model"]]:
                engines[o["model"]].append(eg)
            if o["code"]:
                prefixes.setdefault(o["model"], set()).add(o["code"][:3])

        # Site order: data_models2.json order first, then models only seen in items.
        seen_order = list(dict.fromkeys([*listed, *sorted(counts)]))
        first_run = not models
        for pos, name in enumerate(seen_order):
            if name in models:
                continue
            seg = segment_of(name)
            if first_run:
                order: float = (pos + 1) * 10
            else:
                same = [m["order"] for m in models.values() if m["segment"] == seg]
                order = (max(same) if same else max([m["order"] for m in models.values()] or [0])) + 1
            m: dict[str, Any] = {
                "name": name, "slug": slugify(name), "segment": seg, "order": order, "status": "active",
                "first_seen": date, "last_seen": date if counts.get(name) else None, "retired_on": None,
                "empty_runs": 0, "engine_groups": [], "possible_rename_of": None, "code_prefixes": [],
            }
            # A new name whose cars carry the code prefix of a retired or empty model (spec 4.6).
            pref = prefixes.get(name, set())
            for other in models.values():
                if other["status"] == "retired" or other["empty_runs"] > 0:
                    if pref & set(other["code_prefixes"]):
                        m["possible_rename_of"] = other["name"]
                        break
            models[name] = m
            if not first_run:
                ev["models_new"].append(m)

        for name, m in models.items():
            n = counts.get(name, 0)
            if n:
                if m["status"] == "retired":
                    m["status"] = "active"
                    m["retired_on"] = None
                    ev["models_returned"].append(m)
                m["empty_runs"] = 0
                m["last_seen"] = date
                for g in engines.get(name, []):
                    if g not in m["engine_groups"]:
                        m["engine_groups"].append(g)
                m["code_prefixes"] = sorted(set(m["code_prefixes"]) | prefixes.get(name, set()))
            else:
                m["empty_runs"] += 1
                if m["status"] == "active" and m["empty_runs"] >= empty_runs_to_retire:
                    m["status"] = "retired"
                    m["retired_on"] = date
                    ev["models_retired"].append(m)
            m["cars_now"] = n
        events[date] = {k: [_event(x) for x in v] for k, v in ev.items()}

    out = []
    for name, m in models.items():
        ov = rules.model_override(name)
        for k in ("slug", "segment", "order", "status"):
            if k in ov:
                m[k] = ov[k]
        m["engine_slots"] = assign_engine_slots(m["engine_groups"])
        out.append(m)
    out.sort(key=lambda m: (m["order"], m["name"]))
    for i, m in enumerate(out):
        m["order"] = i + 1
    return out, events


def _event(m: dict[str, Any]) -> dict[str, Any]:
    return {"model": m["name"], "slug": m["slug"], "segment": m["segment"], "cars_now": m.get("cars_now", 0),
            "first_seen": m["first_seen"], "last_seen": m["last_seen"],
            "possible_rename_of": m.get("possible_rename_of")}
