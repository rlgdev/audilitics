"""Versioned rules from rules/*.yaml (spec 3.4, 4.5, 6.3, 6.4).

Every rule file holds a list of rule sets with a `valid_from` date; a snapshot is processed with the newest
set valid on its date, so a rule change never rewrites history unless `make rebuild` is run on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROMO_KEYS = ("bo", "fe", "l101", "pu", "be", "p15")


def _pick(path: Path, date: str) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    sets = sorted(doc["rule_sets"], key=lambda r: str(r["valid_from"]))
    valid = [r for r in sets if str(r["valid_from"]) <= date]
    if not valid:
        # A date before the first rule set (e.g. a replay of older data) uses the oldest set.
        valid = sets[:1]
    return dict(valid[-1])


def _starts(code: str, prefixes: list[str]) -> bool:
    return any(code.startswith(p) for p in prefixes)


@dataclass
class Rules:
    promo: dict[str, Any]
    plans: dict[str, Any]
    scoring: dict[str, Any]
    models: dict[str, Any]

    @property
    def version(self) -> str:
        return f"promo:{self.promo['version']}/plans:{self.plans['version']}/scoring:{self.scoring['version']}"

    # ---- sliders -------------------------------------------------------------------------------------
    def slider_params(self) -> dict[str, dict[str, Any]]:
        return {k: dict(v["params"]) for k, v in self.promo["sliders"].items()}

    # ---- badges (spec 3.4) ---------------------------------------------------------------------------
    def badges(self, item: dict[str, Any]) -> dict[str, Any]:
        """Return {promo_key: bool} for the card badges plus `package_type` for the insurance badge."""
        b = self.promo["badges"]
        model = item["model"]
        code = (item["kod_modelowy"] or "").strip().upper()
        prod = str(item["rok_produkcji"] or "")
        stock_cleaning = str(item["stock_cleaning"] or "").strip().lower() == "tak"

        r = b["bo"]
        best = not _starts(code, r["exclude_code_prefixes"]) and (
            (r.get("include_stock_cleaning") and stock_cleaning) or _starts(code, r["include_code_prefixes"])
        )

        r = b["fe"]
        fe = model in r["models"] and _starts(code, r["code_prefixes"]) and prod == str(r["production_year"])

        r = b["l101"]
        l101 = model in r["models_by_production_year"].get(prod, [])

        package = "none"
        for pr in b["pu"]["package_rules"]:
            if model not in pr["models"]:
                continue
            if pr.get("production_year") and prod != str(pr["production_year"]):
                continue
            if pr.get("stock_cleaning") and not stock_cleaning:
                continue
            if pr.get("code_prefixes") and not _starts(code, pr["code_prefixes"]):
                continue
            package = pr["type"]
            break

        r = b["be"]
        be = str(item["business_edition"]).strip().lower() == "tak" and not (r.get("suppressed_by") == "fe" and fe)

        r = b["p15"]
        prefix = r["model_code_prefixes"].get(model)
        p15 = prefix is not None and code.startswith(prefix) and prod == str(r["production_year"])

        return {"bo": bool(best), "fe": fe, "l101": l101, "pu": package != "none", "be": be, "p15": p15,
                "package_type": package}

    def badge_bit(self, key: str) -> int:
        return int(self.promo["promos"][key]["badge_bit"])

    # ---- plans (spec 3.4 footnote rule, 6.4) ------------------------------------------------------------
    @staticmethod
    def _cond(cond: dict[str, Any], model: str, code: str, model_year: str) -> bool:
        if "model_contains" in cond and cond["model_contains"] not in model:
            return False
        if "code_prefixes" in cond and not _starts(code, cond["code_prefixes"]):
            return False
        return not ("model_year" in cond and model_year != str(cond["model_year"]))

    def footnote(self, item: dict[str, Any]) -> int:
        model, code, my = item["model"], item["kod_modelowy"] or "", str(item["rok_modelowy"] or "")
        for rule in self.plans["footnote_rules"]:
            if any(self._cond(c, model, code, my) for c in rule["any"]):
                return int(rule["footnote"])
        return 1

    def plan_code(self, item: dict[str, Any]) -> str:
        fn = self.footnote(item)
        model, code, my = item["model"], item["kod_modelowy"] or "", str(item["rok_modelowy"] or "")
        if fn == 2:
            exc = self.plans["footnote_2_exception"]
            if any(self._cond(c, model, code, my) for c in exc["any"]):
                return str(exc["plan"])
        for plan, p in self.plans["plans"].items():
            if int(p["footnote"]) == fn:
                return str(plan)
        return "APL-1"

    def plan(self, code: str) -> dict[str, Any]:
        return dict(self.plans["plans"][code])

    # ---- models overrides ----------------------------------------------------------------------------
    def model_override(self, name: str) -> dict[str, Any]:
        return dict((self.models.get("overrides") or {}).get(name) or {})


def load_rules(rules_dir: Path, date: str) -> Rules:
    models = yaml.safe_load((rules_dir / "models.yaml").read_text(encoding="utf-8")) or {}
    return Rules(
        promo=_pick(rules_dir / "promo_rules.yaml", date),
        plans=_pick(rules_dir / "plans.yaml", date),
        scoring=_pick(rules_dir / "scoring.yaml", date),
        models=models,
    )
