"""Shared helpers for data-source spikes.

Polite HTTP: per-host rate limit, retries with backoff, raw-response disk cache.
Samples (trimmed outputs) are written to backend/spikes/samples/ and committed;
raw downloads go to backend/spikes/.cache/ (gitignored).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / ".cache"
SAMPLES_DIR = HERE / "samples"
CACHE_DIR.mkdir(exist_ok=True)
SAMPLES_DIR.mkdir(exist_ok=True)

# NSE/BSE reject non-browser User-Agents, so exchanges get a browser UA.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
FINN_UA = "FINN-research/0.1 (+https://github.com/ShlokN-code/finn)"

MIN_INTERVAL = {  # seconds between requests to the same host
    "www.nseindia.com": 2.5,
    "nsearchives.nseindia.com": 1.5,
    "archives.nseindia.com": 1.5,
    "api.bseindia.com": 2.0,
    "www.bseindia.com": 2.0,
    "www.screener.in": 3.0,
}
DEFAULT_INTERVAL = 1.0

_last_hit: dict[str, float] = {}
NO_CACHE = os.environ.get("SPIKE_NO_CACHE") == "1"  # set in CI to force live calls


def _throttle(url: str) -> None:
    host = urlparse(url).netloc
    gap = MIN_INTERVAL.get(host, DEFAULT_INTERVAL)
    wait = _last_hit.get(host, 0) + gap - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


def polite_get(
    session: requests.Session,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    use_cache: bool = True,
    retries: int = 3,
    timeout: float = 20,
) -> requests.Response:
    """GET with throttle, retries (backoff on 401/403/429/5xx), and a raw cache."""
    key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()[:24]
    cache_file = CACHE_DIR / key
    if use_cache and not NO_CACHE and cache_file.exists():
        resp = requests.Response()
        meta = json.loads((CACHE_DIR / f"{key}.meta").read_text())
        resp.status_code = meta["status"]
        resp.headers.update(meta["headers"])
        resp._content = cache_file.read_bytes()
        resp.url = meta["url"]
        resp.from_cache = True  # type: ignore[attr-defined]
        return resp

    last: requests.Response | None = None
    for attempt in range(retries):
        _throttle(url)
        try:
            last = session.get(url, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            log(f"  ! {type(e).__name__}: {e}")
            time.sleep(2 ** (attempt + 1))
            continue
        if last.status_code in (401, 403, 429) or last.status_code >= 500:
            log(f"  ! HTTP {last.status_code} on {url} (attempt {attempt + 1}/{retries})")
            time.sleep(2 ** (attempt + 1))
            continue
        break
    if last is None:  # every attempt raised (timeout/connection) — report as status 0
        last = requests.Response()
        last.status_code = 0
        last.url = url
        last._content = b""
    last.from_cache = False  # type: ignore[attr-defined]
    if last.ok and use_cache:
        cache_file.write_bytes(last.content)
        (CACHE_DIR / f"{key}.meta").write_text(
            json.dumps({"status": last.status_code, "url": last.url,
                        "headers": {k: v for k, v in last.headers.items() if k.lower() == "content-type"}})
        )
    return last


def nse_session() -> requests.Session:
    """Session with NSE cookies obtained via homepage warm-up."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": BROWSER_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    })
    _throttle("https://www.nseindia.com/")
    r = s.get("https://www.nseindia.com/", headers={"Accept": "text/html"}, timeout=20)
    log(f"NSE warm-up: HTTP {r.status_code}, cookies={sorted(s.cookies.keys())}")
    return s


def bse_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": BROWSER_UA,
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bseindia.com/",
        "Origin": "https://www.bseindia.com",
    })
    return s


def finn_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": FINN_UA})
    return s


def save_sample(name: str, data: Any) -> Path:
    p = SAMPLES_DIR / name
    if isinstance(data, (dict, list)):
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        p.write_text(str(data))
    return p


def log(msg: str) -> None:
    print(msg, flush=True)


class Result:
    """Collects pass/fail per check; exit code 1 if any 'required' check failed."""

    def __init__(self, name: str):
        self.name = name
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, label: str, ok: bool, detail: str = "") -> bool:
        self.checks.append((label, ok, detail))
        log(f"  [{'OK' if ok else 'FAIL'}] {label}{' — ' + detail if detail else ''}")
        return ok

    def finish(self) -> None:
        n_ok = sum(1 for _, ok, _ in self.checks if ok)
        log(f"\n== {self.name}: {n_ok}/{len(self.checks)} checks passed ==")
        save_sample(f"_result_{self.name}.json",
                    [{"check": c, "ok": ok, "detail": d} for c, ok, d in self.checks])
        sys.exit(0 if n_ok == len(self.checks) else 1)
