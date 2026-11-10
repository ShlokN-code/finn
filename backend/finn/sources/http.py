"""Polite HTTP for every data source (CLAUDE.md rule 6).

- Per-host minimum spacing between requests (NSE 2.5 s, archives 1.5 s, BSE 2 s, screener 3 s).
- Retries with exponential backoff on 401/403/429/5xx and network errors.
- Raw responses cached on disk (FINN_CACHE_DIR, default backend/.cache): `ttl` seconds for live endpoints,
  `ttl=None` to keep forever (PDFs/XBRL never change). Every response is written, so a run can be audited.
- Browser UA for exchanges (they reject anything else, after a homepage cookie warm-up); an identifying
  FINN UA everywhere else. No personal data in headers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

log = logging.getLogger("finn.http")

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
FINN_UA = "FINN-research/0.1 (+https://github.com/ShlokN-code/finn)"

MIN_INTERVAL = {
    "www.nseindia.com": 2.5,
    "nsearchives.nseindia.com": 1.5,
    "archives.nseindia.com": 1.5,
    "api.bseindia.com": 2.0,
    "www.bseindia.com": 2.0,
    "www.screener.in": 3.0,
}
DEFAULT_INTERVAL = 1.0
RETRY_STATUS = {401, 403, 429}

_last_hit: dict[str, float] = {}


def cache_dir() -> Path:
    d = Path(os.environ.get("FINN_CACHE_DIR") or Path(__file__).resolve().parents[2] / ".cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


class FetchError(RuntimeError):
    def __init__(self, url: str, status: int, detail: str = ""):
        super().__init__(f"HTTP {status} for {url} {detail}".strip())
        self.url, self.status = url, status


def _throttle(url: str) -> None:
    host = urlparse(url).netloc
    gap = MIN_INTERVAL.get(host, DEFAULT_INTERVAL)
    wait = _last_hit.get(host, 0.0) + gap - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


def _key(url: str, params: dict | None) -> str:
    return hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()[:32]


class CachedResponse:
    """The bits of a response the sources use; same shape whether live or from cache."""

    def __init__(self, url: str, status: int, content: bytes, content_type: str, from_cache: bool, fetched_at: float):
        self.url, self.status_code, self.content = url, status, content
        self.content_type, self.from_cache, self.fetched_at = content_type, from_cache, fetched_at

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.content)


def polite_get(
    session: requests.Session,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    ttl: float | None = 0,
    retries: int = 3,
    timeout: float = 25,
    on_auth_error=None,
) -> CachedResponse:
    """GET with throttle, retries and a disk cache.

    ttl: seconds a cached copy stays valid; 0 = always fetch live (still written to cache); None = forever.
    on_auth_error: callback (e.g. NSE cookie re-warm) run once after the first 401/403.
    """
    key = _key(url, params)
    body_f, meta_f = cache_dir() / key, cache_dir() / f"{key}.meta"
    if ttl != 0 and body_f.exists() and meta_f.exists():
        meta = json.loads(meta_f.read_text())
        if ttl is None or time.time() - meta["fetched_at"] < ttl:
            body = body_f.read_bytes()
            return CachedResponse(meta["url"], meta["status"], body, meta["ctype"], True, meta["fetched_at"])

    last: requests.Response | None = None
    rewarmed = False
    for attempt in range(retries):
        _throttle(url)
        try:
            last = session.get(url, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            log.warning("%s on %s (attempt %d/%d)", type(e).__name__, url, attempt + 1, retries)
            last = None
            time.sleep(2 ** (attempt + 1))
            continue
        if last.status_code in RETRY_STATUS or last.status_code >= 500:
            log.warning("HTTP %d on %s (attempt %d/%d)", last.status_code, url, attempt + 1, retries)
            if last.status_code in (401, 403) and on_auth_error and not rewarmed:
                rewarmed = True
                on_auth_error()
            time.sleep(2 ** (attempt + 1))
            continue
        break

    if last is None:
        raise FetchError(url, 0, "network error after retries")
    ctype = last.headers.get("content-type", "").split(";")[0].strip()
    resp = CachedResponse(last.url, last.status_code, last.content, ctype, False, time.time())
    if resp.ok:
        body_f.write_bytes(resp.content)
        meta_f.write_text(
            json.dumps({"url": resp.url, "status": resp.status_code, "ctype": ctype, "fetched_at": resp.fetched_at})
        )
    return resp


def get_json(session: requests.Session, url: str, **kw):
    """polite_get + require a JSON body (NSE answers blocks with HTML)."""
    r = polite_get(session, url, **kw)
    if not r.ok:
        raise FetchError(url, r.status_code)
    if "json" not in r.content_type:
        raise FetchError(url, r.status_code, f"expected JSON, got {r.content_type or 'unknown'}")
    return r.json()


class NSESession(requests.Session):
    """requests.Session with NSE's Akamai cookies (homepage warm-up) and re-warm on 401/403."""

    def __init__(self) -> None:
        super().__init__()
        self.headers.update(
            {
                "User-Agent": BROWSER_UA,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nseindia.com/",
            }
        )
        self.warmed_at: float | None = None

    def warm(self) -> None:
        _throttle("https://www.nseindia.com/")
        try:
            r = super().get("https://www.nseindia.com/", headers={"Accept": "text/html"}, timeout=25)
            log.info("NSE warm-up: HTTP %d, cookies=%s", r.status_code, sorted(self.cookies.keys()))
        except requests.RequestException as e:
            log.warning("NSE warm-up failed: %s", e)
        self.warmed_at = time.monotonic()

    def ensure_warm(self) -> None:
        # Akamai cookies last a while; re-warm every 10 min to be safe on long runs.
        if self.warmed_at is None or time.monotonic() - self.warmed_at > 600:
            self.warm()


def finn_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": FINN_UA})
    return s
