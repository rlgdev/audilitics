"""One-time migration of a release 1.0 raw file to the redacted 1.1 format (spec 16.4 step 1).

Each slider VIN list becomes item counts per model through the main feed (VINs absent from the main pull count
under the key "null"), then the fields of spec 3.5, the VIN lists and the bundle download record are dropped.

    python collector/tools/redact_raw_1_0.py IN.json.gz OUT.json.gz [OUT2.json.gz ...]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collector.guard import identifier_check  # noqa: E402
from collector.io import read_json_gz, write_json_gz  # noqa: E402
from collector.schema import validate_and_redact  # noqa: E402


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    items = raw["feed"]["items"]
    model_of = {it["vin"]: it["model"] for it in items}
    slider_counts = {}
    for key, vins in sorted((raw.get("sliders") or {}).items()):
        c = Counter(model_of.get(v, "null") for v in vins)
        slider_counts[key] = dict(sorted(c.items()))
    redacted, unknown, dropped = validate_and_redact(items, True)
    bundle = raw.get("bundle") or {}
    return {
        "date": raw["date"],
        "fetched_at": raw.get("fetched_at"),
        "duration_s": raw.get("duration_s"),
        "collector_version": raw.get("collector_version"),
        "source": raw.get("source", "live"),
        "redacted": True,
        "migrated_from": "1.0",
        "bundle": {"name": bundle.get("name"), "hash": bundle.get("hash")},
        "models_json": raw.get("models_json"),
        "dealers_json": raw.get("dealers_json"),
        "feed": {"count": len(redacted), "items": redacted},
        "schema": {"unknown_fields": unknown, "dropped_identifying_fields": dropped},
        "slider_counts": slider_counts,
        "headers": raw.get("headers"),
        "requests": [r for r in raw.get("requests", []) if not str(r.get("path", "")).startswith("/main.")],
        "request_count": raw.get("request_count"),
    }


def main() -> int:
    src, outs = Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]
    new = migrate(read_json_gz(src))
    for out in outs:
        write_json_gz(out, new)
        findings = identifier_check(out.parent)
        print(f"{out}: {new['feed']['count']} items, identifier check {'FAILED' if findings else 'pass'}")
        for f in findings[:10]:
            print("  ", f)
        if findings:
            return 1
    print({k: sum(v.values()) for k, v in new["slider_counts"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
