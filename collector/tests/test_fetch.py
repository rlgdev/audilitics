"""Fetcher behaviour without network (spec 4.2, 4.3, 11 Politeness)."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest
import requests

from collector.config import Settings
from collector.fetch import Client, FetchError, fetch_live
from collector.rules import Rules

from .sim import fake_vin


class FakeResponse:
    def __init__(self, status: int, body: Any = None, text: str = ""):
        self.status_code = status
        self.content = (json.dumps(body) if body is not None else text).encode("utf-8")
        self.text = text or self.content.decode("utf-8")
        self.headers = {"content-type": "text/html; charset=UTF-8"}


class FakeSession:
    def __init__(self, routes: list[Any]):
        self.routes = routes
        self.calls: list[tuple[str, Any]] = []
        self.headers: dict[str, str] = {}

    def get(self, url: str, params: Any = None, timeout: float = 0) -> FakeResponse:
        self.calls.append((url, params))
        r = self.routes.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def live_items(raw: dict[str, Any], n: int) -> list[dict[str, Any]]:
    items = copy.deepcopy(raw["feed"]["items"][:n])
    for i, it in enumerate(items):
        it.update(vin=fake_vin(i), komisja="2026000000", link="https://www.audi.pl/x", kod_audi="", telefon="+48 1")
    return items


def feed(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"count": len(items), "items": items}


def test_403_stops_immediately(settings: Settings, rules: Rules) -> None:
    sess = FakeSession([FakeResponse(403, text="no")])
    c = Client(settings, session=sess, sleep=lambda s: None)  # type: ignore[arg-type]
    with pytest.raises(FetchError) as e:
        fetch_live(settings, "2026-10-27", rules.slider_params(), client=c)
    assert e.value.kind == "blocked" and len(sess.calls) == 1


def test_full_run_ten_requests_redacted_counts(settings: Settings, rules: Rules, raw: dict[str, Any]) -> None:
    items = live_items(raw, 5)
    routes = [FakeResponse(200, text='<script src="main.abc123.js">'), FakeResponse(200, {"Audi Q5": {}}),
              FakeResponse(200, {"9101": "X"}), FakeResponse(200, feed(items))]
    routes += [FakeResponse(200, feed(items[:2])) for _ in range(6)]
    sess = FakeSession(routes)
    c = Client(settings, session=sess, sleep=lambda s: None)  # type: ignore[arg-type]
    out = fetch_live(settings, "2026-10-27", rules.slider_params(), client=c)
    assert out["request_count"] == 10 and len(sess.calls) == 10
    assert out["bundle"] == {"name": "main.abc123.js", "hash": "abc123"}
    assert not any("main.abc123.js" in url for url, _ in sess.calls)  # the bundle is never requested
    assert out["redacted"] is True
    text = json.dumps(out)
    assert fake_vin(0) not in text and "2026000000" not in text and "audi.pl/x" not in text and "+48 1" not in text
    model = items[0]["model"]
    assert set(out["slider_counts"]) == {"bo", "fe", "l101", "pu", "be", "pks"}
    assert sum(out["slider_counts"]["bo"].values()) == 2 and model in out["slider_counts"]["bo"]
    fe_params = sess.calls[5][1]
    assert ("m[]", "Audi Q7") in fe_params and ("mc[]", "4MQ*") in fe_params and ("rm", "2026") in fe_params


def test_schema_failure_is_reported_without_identifiers(settings: Settings, rules: Rules,
                                                        raw: dict[str, Any]) -> None:
    items = live_items(raw, 3)
    del items[1]["rata"]
    routes = [FakeResponse(200, text="main.abc.js"), FakeResponse(200, {}), FakeResponse(200, {}),
              FakeResponse(200, feed(items))]
    c = Client(settings, session=FakeSession(routes), sleep=lambda s: None)  # type: ignore[arg-type]
    with pytest.raises(FetchError) as e:
        fetch_live(settings, "2026-10-27", rules.slider_params(), client=c)
    assert e.value.kind == "schema" and fake_vin(1) not in str(e.value)


def test_count_mismatch_retries_then_fails(settings: Settings, rules: Rules) -> None:
    bad = {"count": 5, "items": [{"model": "A"}]}
    sleeps: list[float] = []
    routes = [FakeResponse(200, text="main.abc.js"), FakeResponse(200, {}), FakeResponse(200, {})]
    routes += [FakeResponse(200, bad) for _ in range(4)]
    c = Client(settings, session=FakeSession(routes), sleep=sleeps.append)  # type: ignore[arg-type]
    with pytest.raises(FetchError, match="count 5 != 1"):
        fetch_live(settings, "2026-10-27", rules.slider_params(), client=c)
    assert [s for s in sleeps if s >= 10] == [10, 30, 90]


def test_connection_error_retried_with_backoff(settings: Settings) -> None:
    sleeps: list[float] = []
    sess = FakeSession([requests.ConnectionError("x"), FakeResponse(200, {"count": 0, "items": []})])
    c = Client(settings, session=sess, sleep=sleeps.append)  # type: ignore[arg-type]
    r = c.get("/ajax/get2.php", [], retry=True)
    assert r.status_code == 200 and 10 in sleeps and c.count == 1


def test_budget_enforced(settings: Settings) -> None:
    sess = FakeSession([FakeResponse(200, {}) for _ in range(11)])
    c = Client(settings, session=sess, sleep=lambda s: None)  # type: ignore[arg-type]
    for _ in range(10):
        c.get("/x")
    with pytest.raises(FetchError, match="budget"):
        c.get("/x")


def test_user_agent_names_the_public_repository(settings: Settings) -> None:
    assert settings.user_agent == "audilitics/1.1.0 (price trend research; +https://github.com/rlgdev/audilitics)"
