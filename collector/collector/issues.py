"""GitHub issues for the gates of spec 4.3, created with the GitHub CLI inside the job.

An open issue with the same label is updated with a comment, never duplicated.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

LABELS = {
    "collector-failure": ("d03b3b", "Collector run failed or produced a suspect snapshot"),
    "collector-blocked": ("d03b3b", "The source answered 403 or 429"),
    "schema-change": ("fab219", "The feed schema changed"),
    "rules-review": ("2a78d6", "The site bundle changed or slider and badge counts differ; re-verify promo rules"),
    "publication-guard": ("d03b3b", "The publication guard or identifier check failed; nothing was pushed"),
}


def _gh(args: list[str], dry_run: bool) -> str:
    if dry_run:
        print("gh " + " ".join(json.dumps(a) if " " in a else a for a in args))
        return "[]" if args[:2] == ["issue", "list"] else ""
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def publish(result_path: Path, dry_run: bool = False) -> list[str]:
    result: dict[str, Any] = json.loads(result_path.read_text(encoding="utf-8"))
    issues = result.get("issues", [])
    if not issues:
        print("No issues to open.")
        return []
    if not dry_run and shutil.which("gh") is None:
        raise SystemExit("gh CLI not found; cannot create issues")
    done = []
    for iss in issues:
        label = iss["label"]
        color, desc = LABELS.get(label, ("898781", ""))
        _gh(["label", "create", label, "--color", color, "--description", desc, "--force"], dry_run)
        existing = json.loads(_gh(["issue", "list", "--label", label, "--state", "open", "--json", "number",
                                   "--limit", "1"], dry_run) or "[]")
        if existing:
            n = str(existing[0]["number"])
            _gh(["issue", "comment", n, "--body", f"**{iss['title']}**\n\n{iss['body']}"], dry_run)
            done.append(f"updated #{n} ({label})")
        else:
            _gh(["issue", "create", "--title", iss["title"], "--body", iss["body"], "--label", label], dry_run)
            done.append(f"created ({label})")
    for d in done:
        print(d)
    return done
