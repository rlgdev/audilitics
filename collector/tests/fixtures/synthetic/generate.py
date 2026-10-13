"""Generate the synthetic fixture of the public repository (spec 16.4 step 4).

About 300 offers over 6 models and 3 snapshots with invented prices and dealer names, already in the redacted raw
format of release 1.1. It includes configurations below the minimum group size, a configuration that appears in
the last run only, one that leaves, and price moves big enough to make hot deals. No real data is used.

    python collector/tests/fixtures/synthetic/generate.py      (rewrites raw-*.json.gz and expected.json)
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from collector.io import write_json_gz  # noqa: E402

DATES = ["2026-09-15", "2026-09-29", "2026-10-13"]
DEALERS = {
    "9101": "Salon Alfa - Gdańsk", "9102": "Salon Beta - Poznań", "9103": "Auto Gamma - Kraków",
    "9104": "Auto Delta - Wrocław", "9105": "Centrum Epsilon - Warszawa", "9106": "Studio Zeta - Łódź",
}
# model, engine line, engine group, model code, model year, catalog price, offers per run, price factor per run
CONFIGS: list[tuple[str, str, str, str, str, int, list[int], list[float]]] = [
    ("Audi A3 Sportback", "TFSI 85 kW S tronic", "TFSI", "8YYANG", "2027", 136700, [14, 15, 15], [1.0, 1.0, 1.0]),
    ("Audi A3 Sportback", "TFSI 110(150) kW(KM) S tronic", "TFSI", "8YFBNG", "2026", 158400, [12, 12, 13],
     [1.0, 0.97, 0.94]),
    ("Audi A3 Sportback", "TDI 110(150) kW(KM) S tronic", "TDI", "8YFBTG", "2026", 166200, [2, 2, 2], [1.0, 1.0, 1.0]),
    ("Audi A6 Avant", "TDI quattro 150(204) kW(KM) S tronic", "TDI quattro", "FN5AUY", "2026", 312900, [10, 9, 9],
     [1.0, 0.99, 0.99]),
    ("Audi A6 Avant", "TFSI 150(204) kW(KM) S tronic", "TFSI", "FN5ABY", "2026", 289500, [8, 8, 7], [1.0, 1.0, 1.02]),
    ("Audi Q5", "TFSI 150(204) kW(KM) S tronic", "TFSI", "GUBAZG", "2026", 248900, [20, 21, 21], [1.0, 0.98, 0.95]),
    ("Audi Q5", "TDI quattro 150(204) kW(KM) S tronic", "TDI quattro", "GUBAUY", "2026", 271300, [16, 15, 16],
     [1.0, 1.0, 0.99]),
    ("Audi Q5", "TFSI quattro 150(204) kW(KM) S tronic", "TFSI quattro", "GUBAZY", "2025", 259800, [6, 4, 0],
     [1.0, 1.0, 1.0]),
    ("Audi Q7", "TDI quattro 210(286) kW(KM) tiptronic", "TDI quattro", "4MQCN2", "2026", 389900, [9, 9, 8],
     [1.0, 0.96, 0.92]),
    ("Audi Q7", "TFSI e quattro 270(367) kW(KM) tiptronic", "e-hybrid", "4MQCX2", "2026", 412300, [0, 0, 6],
     [1.0, 1.0, 0.86]),
    ("Audi Q4 e-tron", "e-tron 210(286) kW(KM)", "e-tron", "F4BBVY", "2026", 231500, [11, 12, 12],
     [1.0, 0.99, 0.98]),
    ("Audi Q4 e-tron", "e-tron quattro 250(340) kW(KM)", "e-tron", "F4BBXY", "2027", 262900, [3, 2, 3],
     [1.0, 1.0, 1.0]),
    ("Audi RS 3 Sportback", "TFSI quattro 294(400) kW(KM) S tronic", "modele RS", "8YARS3", "2026", 365000,
     [4, 4, 4], [1.0, 1.0, 0.97]),
]


def item(cfg: tuple[Any, ...], j: int, run: int) -> dict[str, str]:
    """Offer j of a configuration keeps its catalog price, discount, dealer and flags in every run; only the
    configuration's price factor of that run moves its special price."""
    model, engine, group, code, my, catalog, _, factors = cfg
    rng = random.Random(f"{code}-{j}")
    cat = catalog + rng.choice([0, 0, 2400, 5100, 8800])
    disc = rng.choice([0.08, 0.1, 0.12, 0.15, 0.18, 0.2])
    special = int(round(cat * (1 - disc) * factors[run] / 10) * 10)
    no_price = model == "Audi A6 Avant" and run == 2 and j in (1, 5)
    rate = int(special * rng.choice([0.0042, 0.0045, 0.0048]))
    dealer = rng.choice(sorted(DEALERS))
    return {
        "model": model, "silnik": engine, "silnik2": group, "dealer": DEALERS[dealer], "dealer_nr": dealer,
        "cena_katalogowa": str(cat), "cena_vtp": "" if no_price else str(special), "cena_historyczna": str(cat),
        "cena_historyczna_katalogowa": str(cat), "rata": "" if no_price else str(rate), "stara_rata": "",
        "rata_historyczna": str(rate), "rok_produkcji": "2025" if my == "2025" else "2026", "rok_modelowy": my,
        "kod_modelowy": code, "id": f"{my}2026{code}", "business_edition": rng.choice(["Tak", "Nie"]),
        "stock_cleaning": rng.choice(["Tak", "Nie", "Nie"]), "moj_elektryk": "Nie",
    }


def main() -> None:
    sys.path.insert(0, str(HERE.parents[2]))
    from collector.rules import load_rules
    from collector.schema import parse

    root = HERE.parents[3]
    for run, date in enumerate(DATES):
        items = [item(cfg, j, run) for cfg in CONFIGS for j in range(cfg[6][run])]
        rules = load_rules(root / "rules", date)
        badges = [rules.badges(it.model_dump()) for it in parse(items)]
        sliders: dict[str, dict[str, int]] = {}
        for key in ("bo", "fe", "l101", "pu", "be"):
            per: dict[str, int] = {}
            for it, b in zip(items, badges, strict=True):
                if (key == "be" and it["business_edition"] == "Tak") or (key != "be" and b[key]):
                    per[it["model"]] = per.get(it["model"], 0) + 1
            sliders[key] = dict(sorted(per.items()))
        sliders["pks"] = {}
        models = sorted({c[0] for c in CONFIGS})
        raw = {
            "date": date, "fetched_at": f"{date}T05:17:00+00:00", "duration_s": 9.0, "collector_version": "1.1.0",
            "source": "synthetic", "redacted": True,
            "bundle": {"name": "main.0000synthetic.js", "hash": "0000synthetic"},
            "models_json": {m: {"count": sum(1 for it in items if it["model"] == m)} for m in models},
            "dealers_json": DEALERS, "feed": {"count": len(items), "items": items},
            "schema": {"unknown_fields": [], "dropped_identifying_fields": []},
            "slider_counts": sliders, "headers": {}, "requests": [], "request_count": 10,
        }
        write_json_gz(HERE / f"raw-{date}.json.gz", raw)
        print(date, len(items), "offers")


if __name__ == "__main__":
    main()
    print("now refresh expected.json: python collector/tests/fixtures/synthetic/expected.py")
