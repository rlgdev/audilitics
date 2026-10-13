"""Refresh expected.json of the synthetic fixture after a deliberate change (spec 16.4 step 4)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from collector.config import load_settings  # noqa: E402
from collector.io import read_json, read_json_gz  # noqa: E402
from collector.pipeline import process_raw  # noqa: E402


def main(work: Path) -> None:
    s = load_settings(HERE.parents[3], data=work / "data")
    runs = []
    for p in sorted(HERE.glob("raw-*.json.gz")):
        e = process_raw(s, read_json_gz(p))["entry"]
        runs.append({k: e.get(k) for k in ("date", "status", "offers", "models", "configurations",
                                           "public_configurations")})
    latest = read_json(s.public_dir / "dashboard" / "latest.json")
    ch = latest["changes"]["summary"]
    exp = {"runs": runs, "hot_count": latest["hot_count"],
           "changes_latest": {k: ch[k] for k in ("configs_new", "configs_gone", "price_drops", "price_rises")}}
    (HERE / "expected.json").write_text(json.dumps(exp, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(exp))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[3] / "build" / "expected-work")
