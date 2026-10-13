"""Helpers that build simulated runs from the synthetic fixture (no pytest import: usable from scripts too).

Raw files are in the redacted 1.1 format, so offers have no identity; simulations change whole configurations
(by model code) or models instead of single cars.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC = ROOT / "collector" / "tests" / "fixtures" / "synthetic"
SYNTHETIC_RAWS = sorted(SYNTHETIC.glob("raw-*.json.gz"))
REAL_FIXTURE = Path(os.environ.get("AUDILITICS_REAL_FIXTURE",
                                   ROOT.parent / "audilitics-private" / "fixtures" / "2026-10-13" / "raw.json.gz"))


def fake_vin(n: int) -> str:
    """A VIN-shaped test string built at run time, so no 17-character token appears in the source."""
    return "WAU" + "ZZZ" + "TEST" + f"{n:07d}"


def simulate(raw: dict[str, Any], date: str, *, drop_models: tuple[str, ...] = (), keep_ratio: float = 1.0,
             price_factor: dict[str, float] | None = None, add_items: list[dict[str, Any]] | None = None,
             drop_codes: tuple[str, ...] = ()) -> dict[str, Any]:
    """A later run: remove models or model codes, scale special prices per model code, add items."""
    r = copy.deepcopy(raw)
    r["date"] = date
    r["source"] = "simulated"
    items = [it for it in r["feed"]["items"] if it["model"] not in drop_models and it["kod_modelowy"] not in drop_codes]
    if keep_ratio < 1.0:
        items = items[: int(len(items) * keep_ratio)]
    for it in items:
        f = (price_factor or {}).get(it["kod_modelowy"])
        if f and it["cena_vtp"]:
            it["cena_vtp"] = str(int(int(it["cena_vtp"]) * f))
    items.extend(add_items or [])
    r["feed"]["items"] = items
    r["feed"]["count"] = len(items)
    models = {it["model"] for it in items}
    if keep_ratio < 1.0 or drop_codes:
        r["slider_counts"] = {}  # per-model slider counts no longer describe the truncated feed
    else:
        r["slider_counts"] = {k: {m: n for m, n in v.items() if m in models}
                              for k, v in r.get("slider_counts", {}).items()}
    r["models_json"] = {k: v for k, v in (r.get("models_json") or {}).items() if k in models}
    return r


def make_item(template: dict[str, Any], **kw: str) -> dict[str, Any]:
    it = copy.deepcopy(template)
    it.update(kw)
    return it
