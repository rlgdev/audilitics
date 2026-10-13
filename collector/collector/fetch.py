"""HTTP access to gotowedoodbioru.audi.pl (spec 3, 4.2 steps 1-6).

Produces one *raw* dict per run. Items are validated and redacted here, before the raw dict exists, so no
identifying field (spec 3.5) ever reaches disk, a log or normalisation. Slider responses are reduced to item
counts per model in memory. The site's bundle is never requested; only the hash in its file name is recorded.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import requests

from collector import __version__
from collector.config import Settings
from collector.schema import SchemaError, validate_and_redact

KEEP_HEADERS = ("content-type", "content-length", "date", "server", "last-modified", "cache-control")


class FetchError(Exception):
    """A run that cannot produce a snapshot. `kind` selects the issue label (spec 4.3)."""

    def __init__(self, kind: str, message: str, requests_log: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.kind = kind  # "blocked" | "failure" | "schema"
        self.requests_log = requests_log or []


class Client:
    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.s = settings
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = settings.user_agent
        self.sleep = sleep
        self.budget = int(settings.get("request_budget", 10))
        self.spacing = float(settings.get("request_spacing_s", 1.0))
        self.timeout = float(settings.get("timeout_s", 60))
        self.count = 0
        self.log: list[dict[str, Any]] = []
        self._last = 0.0

    def get(self, path: str, params: list[tuple[str, str]] | None = None, counted: bool = True,
            retry: bool = False) -> requests.Response:
        if counted:
            if self.count >= self.budget:
                raise FetchError("failure", f"request budget of {self.budget} exhausted before {path}", self.log)
            self.count += 1
        url = self.s.base_url + path
        delays = list(self.s.get("backoff_s", [10, 30, 90])) if retry else []
        attempt = 0
        while True:
            wait = self.spacing - (time.monotonic() - self._last)
            if self._last and wait > 0:
                self.sleep(wait)
            t0 = time.monotonic()
            entry: dict[str, Any] = {"path": path, "params": params or [], "attempt": attempt + 1, "counted": counted}
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                self._last = time.monotonic()
                entry.update(status=None, error=type(e).__name__, ms=round((self._last - t0) * 1000))
                self.log.append(entry)
                if delays:
                    self.sleep(delays.pop(0))
                    attempt += 1
                    continue
                raise FetchError("failure", f"{path}: {type(e).__name__}", self.log) from e
            self._last = time.monotonic()
            entry.update(status=r.status_code, bytes=len(r.content), ms=round((self._last - t0) * 1000),
                         content_type=r.headers.get("content-type"))
            self.log.append(entry)
            if r.status_code in (403, 429):
                # Stop immediately, no retry storm, no workaround (spec 4.3, 11).
                raise FetchError("blocked", f"{path}: HTTP {r.status_code}", self.log)
            if r.status_code >= 500 and delays:
                self.sleep(delays.pop(0))
                attempt += 1
                continue
            if r.status_code != 200:
                raise FetchError("failure", f"{path}: HTTP {r.status_code}", self.log)
            return r


def _json(r: requests.Response, what: str, log: list[dict[str, Any]]) -> Any:
    # The feed answers with Content-Type text/html although the body is JSON (spec 3.1).
    try:
        return json.loads(r.content.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as e:
        raise FetchError("failure", f"{what}: JSON parse error", log) from e


def _params(base: dict[str, str], extra: dict[str, Any]) -> list[tuple[str, str]]:
    out = list(base.items())
    for k, v in extra.items():
        if isinstance(v, list):
            out.extend((k, str(x)) for x in v)
        else:
            out.append((k, str(v)))
    return out


def count_by_model(items: list[dict[str, Any]]) -> dict[str, int]:
    """Slider responses are reduced to item counts per model; their items are never stored (spec 3.5)."""
    c = Counter(str(it.get("model", "")) for it in items)
    return dict(sorted(c.items()))


def fetch_live(settings: Settings, date: str, slider_params: dict[str, dict[str, Any]],
               client: Client | None = None) -> dict[str, Any]:
    """Run steps 1-6 of spec 4.2 and return the redacted raw dict."""
    c = client or Client(settings)
    t_start = time.monotonic()
    page = str(settings.get("page_size", 20000))
    main_params = {"p": "1", "c": page, "s": "price", "d": "asc"}

    # 1. index page -> bundle name and hash; the bundle itself is never requested (spec 3.1, 3.6).
    r = c.get("/")
    m = re.search(r"main\.([0-9a-f]+)\.js", r.text)
    bundle = {"name": m.group(0), "hash": m.group(1)} if m else {"name": None, "hash": None}

    # 2. model and dealer directories (dealer names stay in the private repository).
    models_json = _json(c.get("/ajax/data_models2.json"), "data_models2.json", c.log)
    dealers_json = _json(c.get("/ajax/data_dealers2.json"), "data_dealers2.json", c.log)

    # 3. the main pull; count must equal len(items) after retries.
    feed: dict[str, Any] | None = None
    headers: dict[str, str] = {}
    delays = list(settings.get("backoff_s", [10, 30, 90]))
    for attempt in range(len(delays) + 1):
        r = c.get("/ajax/get2.php", list(main_params.items()), counted=attempt == 0, retry=True)
        headers = {k: v for k, v in r.headers.items() if k.lower() in KEEP_HEADERS}
        try:
            feed = _json(r, "get2.php", c.log)
        except FetchError:
            if attempt < len(delays):
                c.sleep(delays[attempt])
                continue
            raise
        assert feed is not None
        if int(feed.get("count", -1)) == len(feed.get("items", [])):
            break
        if attempt < len(delays):
            c.sleep(delays[attempt])
            continue
        raise FetchError("failure",
                         f"get2.php: count {feed.get('count')} != {len(feed.get('items', []))} items", c.log)
    assert feed is not None

    # 4-5. validate, then redact: no later step can see the fields of spec 3.5.
    try:
        items, unknown, dropped = validate_and_redact(list(feed.get("items", [])), True, settings.discarded)
    except SchemaError as e:
        raise FetchError("schema", f"schema: {e}", c.log) from e
    feed = {"count": len(items), "items": items}

    # 6. slider sets: keep only the number of items per model.
    slider_counts: dict[str, dict[str, int]] = {}
    for key, params in slider_params.items():
        sr = c.get("/ajax/get2.php", _params(main_params, params))
        data = _json(sr, f"slider {key}", c.log)
        slider_counts[key] = count_by_model(list(data.get("items", [])))
        del data

    return {
        "date": date,
        "fetched_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "duration_s": round(time.monotonic() - t_start, 1),
        "collector_version": __version__,
        "source": "live",
        "redacted": True,
        "bundle": bundle,
        "models_json": models_json,
        "dealers_json": dealers_json,
        "feed": feed,
        "schema": {"unknown_fields": unknown, "dropped_identifying_fields": dropped},
        "slider_counts": slider_counts,
        "headers": headers,
        "requests": c.log,
        "request_count": c.count,
    }
