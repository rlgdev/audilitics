from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from collector.config import Settings, load_settings
from collector.io import read_json_gz
from collector.rules import Rules, load_rules

from .sim import REAL_FIXTURE, ROOT, SYNTHETIC_RAWS, make_item, simulate  # noqa: F401  (re-exported for the tests)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "real: acceptance tests on the redacted real fixture (private repository)")


@pytest.fixture(scope="session")
def synthetic() -> list[dict[str, Any]]:
    return [read_json_gz(p) for p in SYNTHETIC_RAWS]


@pytest.fixture(scope="session")
def real_raw() -> dict[str, Any]:
    if not REAL_FIXTURE.exists():
        pytest.skip("redacted real fixture not available (it lives in the private repository)")
    return read_json_gz(REAL_FIXTURE)


@pytest.fixture
def raw(synthetic: list[dict[str, Any]]) -> dict[str, Any]:
    return copy.deepcopy(synthetic[-1])


@pytest.fixture(scope="session")
def rules() -> Rules:
    return load_rules(ROOT / "rules", "2026-10-13")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return load_settings(ROOT, data=tmp_path / "data")
