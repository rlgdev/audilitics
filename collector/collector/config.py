"""Paths and collector configuration (spec 4.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from collector import __version__


def find_root(start: Path | None = None) -> Path:
    """Repository root: the first parent that holds both rules/ and collector/."""
    here = (start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / "rules").is_dir() and (p / "collector").is_dir():
            return p
    # Fall back to the location of this file (collector/collector/config.py).
    return Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    root: Path
    data: Path
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def rules_dir(self) -> Path:
        return self.root / "rules"

    @property
    def fixtures_dir(self) -> Path:
        return self.root / "collector" / "tests" / "fixtures"

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    @property
    def base_url(self) -> str:
        return str(self.raw["base_url"]).rstrip("/")

    @property
    def user_agent(self) -> str:
        return str(self.raw["user_agent"]).format(version=__version__, public_repo=self.public_repo)

    @property
    def public_repo(self) -> str:
        return str(self.raw.get("public_repo", "rlgdev/audilitics"))

    @property
    def discarded(self) -> tuple[str, ...]:
        return tuple(self.raw.get("discarded_fields") or ("vin", "komisja", "link", "kod_audi", "telefon"))

    @property
    def min_group(self) -> int:
        return int(self.raw.get("public_min_group", 3))

    @property
    def public_dir(self) -> Path:
        return self.data / "public"

    @property
    def private_dir(self) -> Path:
        return self.data / "private"


def load_settings(root: Path | None = None, data: Path | None = None) -> Settings:
    root = root or find_root()
    cfg_path = root / "collector" / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    return Settings(root=root, data=data or root / "data", raw=raw)
