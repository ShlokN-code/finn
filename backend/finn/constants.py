"""Shared thresholds with no imports, so any module (ranking, API) can use them without pulling in scrapers,
PDF or XBRL parsers. Keep this file dependency-free."""

BASE_EFFECT_PCT = 100.0  # PAT YoY above this ⇒ the base was under half the quarter: a base effect, not a trend
