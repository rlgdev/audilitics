"""Command line entry point (spec 4.4). The Makefile targets are thin wrappers around these commands.

    python -m collector --data-dir ../audilitics-private/data collect [--force] [--date YYYY-MM-DD]   live run
    python -m collector --data-dir DIR collect --from DIR/raw/2026-10-27.json.gz       replay one raw file
    python -m collector --data-dir DIR collect --fixture [synthetic|real]               run on a fixture
    python -m collector --data-dir DIR rebuild                                          replay all raw files
    python -m collector guard DIR                       publication guard on a public tree (spec 10.5)
    python -m collector idcheck DIR                     identifier check on any tree (spec 10.5, first row)
    python -m collector issues [--dry-run]              open or update GitHub issues for the last run
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from collector.config import find_root, load_settings
from collector.guard import guard_public, identifier_check
from collector.issues import publish
from collector.pipeline import RUN_DIR, collect_live, process_raw, rebuild_all, replay_file


def default_data_dir(root: Path) -> Path:
    env = os.environ.get("AUDILITICS_DATA")
    if env:
        return Path(env)
    return root.parent / "audilitics-private" / "data"


def synthetic_raws(root: Path) -> list[Path]:
    return sorted((root / "collector" / "tests" / "fixtures" / "synthetic").glob("raw-*.json.gz"))


def real_fixture(root: Path) -> Path:
    env = os.environ.get("AUDILITICS_REAL_FIXTURE")
    if env:
        return Path(env)
    return root.parent / "audilitics-private" / "fixtures" / "2026-10-13" / "raw.json.gz"


def _print(res: dict[str, Any]) -> None:
    print(f"{res['date']}: {res['status']}" + (f" - {res.get('message')}" if res.get("message") else ""))
    entry = res.get("entry")
    if isinstance(entry, dict):
        print(f"  {entry['offers']} offers, {entry['models']} models, {entry['configurations']} configurations"
              + (f" ({entry['public_configurations']} published)" if entry.get("public_configurations") is not None
                 else ""))
    for w in res.get("warnings", []):
        print(f"  warning: {w}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="audilitics")
    ap.add_argument("--root", type=Path, default=None, help="public repository root (default: auto-detect)")
    ap.add_argument("--data-dir", "--data", dest="data", type=Path, default=None,
                    help="private data directory (default: $AUDILITICS_DATA or ../audilitics-private/data)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--from", dest="from_", type=Path, default=None)
    c.add_argument("--fixture", nargs="?", const="synthetic", choices=["synthetic", "real"], default=None)
    c.add_argument("--force", action="store_true")
    c.add_argument("--date", default=None)
    sub.add_parser("rebuild")
    g = sub.add_parser("guard")
    g.add_argument("dir", type=Path)
    k = sub.add_parser("idcheck")
    k.add_argument("dir", type=Path)
    k.add_argument("--public", action="store_true", help="also treat offer_id keys as identifiers")
    i = sub.add_parser("issues")
    i.add_argument("--result", type=Path, default=None)
    i.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    root = a.root or find_root()
    if a.cmd == "guard":
        findings = guard_public(a.dir, int(load_settings(root, a.dir).min_group))
        for f in findings:
            print(f)
        print(f"guard: {'FAILED' if findings else 'pass'} ({len(findings)} findings) on {a.dir}")
        return 1 if findings else 0
    if a.cmd == "idcheck":
        findings = identifier_check(a.dir, public=a.public)
        for f in findings:
            print(f)
        print(f"identifier check: {'FAILED' if findings else 'pass'} ({len(findings)} findings) on {a.dir}")
        return 1 if findings else 0

    s = load_settings(root, a.data or default_data_dir(root))
    if a.cmd == "collect":
        if a.from_:
            results = [replay_file(s, a.from_, a.date)]
        elif a.fixture == "synthetic":
            from collector.io import read_json_gz

            results = [process_raw(s, read_json_gz(p), archive=True) for p in synthetic_raws(root)]
            if not results:
                raise SystemExit("no synthetic fixture under collector/tests/fixtures/synthetic/")
        elif a.fixture == "real":
            results = [replay_file(s, real_fixture(root), a.date)]
        else:
            date = a.date or datetime.now(UTC).date().isoformat()
            results = [collect_live(s, date, force=a.force)]
        for res in results:
            _print(res)
        return 1 if any(r["status"] == "failed" for r in results) else 0
    if a.cmd == "rebuild":
        results = rebuild_all(s)
        for r in results:
            _print(r)
        return 1 if any(r["status"] == "failed" for r in results) else 0
    if a.cmd == "issues":
        publish(a.result or s.data.parent / RUN_DIR / "result.json", dry_run=a.dry_run)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
