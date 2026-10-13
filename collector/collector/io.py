"""Deterministic file writing: same input, byte-identical output (spec 12.1)."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Any


def dumps(obj: Any, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def write_json(path: Path, obj: Any, pretty: bool = False) -> None:
    write_text(path, dumps(obj, pretty=pretty))


def write_json_gz(path: Path, obj: Any) -> None:
    """gzip with mtime=0 and no file name so the archive bytes depend only on content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(dumps(obj).encode("utf-8"))
    data = buf.getvalue()
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_gz(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def sha1_file(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()
