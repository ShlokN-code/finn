"""Tavily web search — only for incoming-executive background (PRODUCT §13 exception). Optional: without
TAVILY_API_KEY, or when the quota is hit, callers fall back to the filing alone. LinkedIn is excluded
(no scraping); we only read the snippets Tavily returns."""

from __future__ import annotations

import os

import requests

URL = "https://api.tavily.com/search"
EXCLUDE = ["linkedin.com", "in.linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com"]


class TavilyUnavailable(RuntimeError):
    pass


def available() -> bool:
    return bool(os.environ.get("TAVILY_API_KEY"))


def search(query: str, max_results: int = 5, session: requests.Session | None = None) -> list[dict]:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise TavilyUnavailable("TAVILY_API_KEY not set")
    try:
        r = (session or requests).post(
            URL,
            json={"query": query, "max_results": max_results, "search_depth": "basic", "exclude_domains": EXCLUDE},
            headers={"Authorization": f"Bearer {key}", "User-Agent": "FINN-research/0.1"},
            timeout=20,
        )
    except requests.RequestException as e:
        raise TavilyUnavailable(type(e).__name__) from None
    if r.status_code in (401, 403, 429, 432, 433):
        raise TavilyUnavailable(f"HTTP {r.status_code} (key or quota)")
    if not r.ok:
        raise TavilyUnavailable(f"HTTP {r.status_code}")
    out = []
    for x in r.json().get("results", []):
        url = x.get("url") or ""
        if any(d in url for d in EXCLUDE):
            continue
        out.append({"url": url, "title": x.get("title") or "", "content": x.get("content") or ""})
    return out
