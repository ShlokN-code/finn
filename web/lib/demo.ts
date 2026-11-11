// The demo portfolio every phone starts with (no login). Mirrors backend/finn/portfolio.py DEMO_WEIGHTS.
export const DEMO_WEIGHTS: Record<string, number> = {
  HAL: 6, EICHERMOT: 6, GRASIM: 5, TATAPOWER: 5, ALKEM: 5, KALYANKJIL: 5, COCHINSHIP: 5, TITAGARH: 4, IDEA: 3,
  RELIANCE: 8, HDFCBANK: 8, BAJFINANCE: 6, INFY: 7, ITC: 6, DIVISLAB: 5, TATASTEEL: 5, JUBLFOOD: 5, DIXON: 6,
};

// Dossiers built and checked in Phase 3 (also shipped as fixtures in /public/fixtures for offline fallback).
export const DEMO_TICKERS = ["BAJFINANCE", "INFY", "PERSISTENT", "POLYCAB"] as const;
export const FIXTURE_DATE = "11 Nov 2026";

export const SHOWCASE_DATE = "2026-10-30";
export const SHOWCASE_LABEL = "Fri 30 Oct 2026";
