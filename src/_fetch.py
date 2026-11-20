"""Small, dependency-free download helpers shared by the download scripts.

fetch() resumes interrupted downloads, skips files that are already complete,
and checks the final size against the server's Content-Length.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = {"User-Agent": "data-analyst-portfolio/1.0 (reproducible download script)"}


def _ssl_context():
    """Use certifi's CA bundle when available (python.org builds on macOS ship without system certificates)."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_SSL = _ssl_context()


def content_length(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    with urllib.request.urlopen(req, timeout=60, context=_SSL) as resp:
        value = resp.headers.get("Content-Length")
    return int(value) if value else None


def fetch(url: str, dest: Path, retries: int = 4) -> Path:
    """Download url to dest with resume support; skip files that are already complete."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        total = content_length(url)
    except Exception:  # noqa: BLE001 - some servers refuse HEAD; fall back to a plain GET
        total = None
    if dest.exists() and dest.stat().st_size > 0 and (total is None or dest.stat().st_size == total):
        return dest
    part = dest.with_name(dest.name + ".part")
    for attempt in range(1, retries + 1):
        try:
            have = part.stat().st_size if part.exists() else 0
            headers = dict(UA)
            if have and total:
                headers["Range"] = f"bytes={have}-"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=300, context=_SSL) as resp, open(part, "ab" if have else "wb") as out:
                if have and resp.status != 206:  # server ignored the range request: start over
                    out.seek(0)
                    out.truncate()
                shutil.copyfileobj(resp, out, 1 << 20)
            if total and part.stat().st_size != total:
                raise OSError(f"incomplete download: {part.stat().st_size} of {total} bytes")
            part.replace(dest)
            return dest
        except Exception:  # noqa: BLE001 - retry any network error, re-raise on the last attempt
            if attempt == retries:
                raise
            time.sleep(5 * attempt)
    return dest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(raw_dir: Path, entries: list[dict]) -> None:
    """Record what was downloaded, from where, and its checksum."""
    payload = {"downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": entries}
    (raw_dir / "MANIFEST.json").write_text(json.dumps(payload, indent=2))
