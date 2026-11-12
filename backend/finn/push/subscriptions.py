"""Opt-in server copy for push (DECISIONS: holdings): symbols + weights only, keyed to a Telegram chat.

Secrets: the deep-link token and the browser's subscriber secret are random 32-byte values; only their
SHA-256 is stored. Deleting a subscription cascades to its rules, snoozes and alert log.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from psycopg.types.json import Jsonb

from finn.models import AlertSettings, WeightRule
from finn.portfolio import DEMO_PORTFOLIO

MAX_SYMBOLS = 40
LINK_TTL = timedelta(minutes=15)


class HoldingsError(ValueError):
    pass


def sha(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()


def demo_holdings() -> list[dict]:
    w = round(100 / len(DEMO_PORTFOLIO), 4)
    return [{"symbol": s, "weight_pct": w} for s in DEMO_PORTFOLIO]


def clean_holdings(conn, holdings: list[dict]) -> list[dict]:
    """Validate symbols against the NSE equity list; equal weights when none are given. Never stores quantity."""
    seen: dict[str, float | None] = {}
    for h in holdings:
        sym = str(h.get("symbol") or "").strip().upper()
        if sym and sym not in seen:
            w = h.get("weight_pct")
            seen[sym] = float(w) if isinstance(w, int | float) and 0 < w <= 100 else None
    if not seen:
        raise HoldingsError("no symbols")
    if len(seen) > MAX_SYMBOLS:
        raise HoldingsError(f"at most {MAX_SYMBOLS} symbols")
    known = {
        r["symbol"]
        for r in conn.execute("select symbol from public.securities where symbol = any(%s)", (list(seen),)).fetchall()
    }
    unknown = sorted(set(seen) - known)
    if unknown:
        raise HoldingsError(f"not NSE symbols: {', '.join(unknown[:10])}")
    if all(w is None for w in seen.values()):
        eq = round(100 / len(seen), 4)
        return [{"symbol": s, "weight_pct": eq} for s in seen]
    return [{"symbol": s, "weight_pct": w} for s, w in seen.items()]


def create_link(conn, holdings: list[dict], settings: AlertSettings | None = None) -> tuple[str, str, datetime]:
    token, secret = secrets.token_urlsafe(24), secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + LINK_TTL
    conn.execute(
        "insert into public.telegram_link_tokens (token_hash, holdings, settings, secret_hash, expires_at) "
        "values (%s,%s,%s,%s,%s)",
        (sha(token), Jsonb(holdings), Jsonb((settings or AlertSettings()).model_dump(mode="json")), sha(secret),
         expires),
    )  # fmt: skip
    return token, secret, expires


def consume_link(conn, token: str) -> dict | None:
    return conn.execute(
        "update public.telegram_link_tokens set used_at = now() where token_hash = %s and used_at is null "
        "and expires_at > now() returning holdings, settings, secret_hash",
        (sha(token),),
    ).fetchone()


def upsert(conn, chat_id: int, holdings: list[dict], settings: dict, secret_hash: str | None, source: str) -> int:
    return conn.execute(
        "insert into public.push_subscriptions (chat_id, holdings, settings, secret_hash, source) "
        "values (%s,%s,%s,%s,%s) on conflict (chat_id) do update set holdings = excluded.holdings, "
        "settings = excluded.settings, secret_hash = excluded.secret_hash, source = excluded.source, "
        "updated_at = now() returning id",
        (chat_id, Jsonb(holdings), Jsonb(settings), secret_hash, source),
    ).fetchone()["id"]


def by_chat(conn, chat_id: int) -> dict | None:
    return conn.execute("select * from public.push_subscriptions where chat_id = %s", (chat_id,)).fetchone()


def by_secret(conn, secret: str) -> dict | None:
    if not secret:
        return None
    return conn.execute("select * from public.push_subscriptions where secret_hash = %s", (sha(secret),)).fetchone()


def all_subscriptions(conn) -> list[dict]:
    return conn.execute("select * from public.push_subscriptions order by id").fetchall()


def delete(conn, sub_id: int) -> None:
    conn.execute("delete from public.push_subscriptions where id = %s", (sub_id,))


def update(conn, sub_id: int, holdings: list[dict] | None = None, settings: dict | None = None) -> None:
    if holdings is not None:
        conn.execute("update public.push_subscriptions set holdings = %s, updated_at = now() where id = %s",
                     (Jsonb(holdings), sub_id))  # fmt: skip
    if settings is not None:
        conn.execute("update public.push_subscriptions set settings = %s, updated_at = now() where id = %s",
                     (Jsonb(settings), sub_id))  # fmt: skip


def snooze(conn, sub_id: int, symbol: str, days: int) -> datetime:
    until = datetime.now(UTC) + timedelta(days=days)
    conn.execute(
        "insert into public.snoozes (subscription_id, symbol, until) values (%s,%s,%s) on conflict "
        "(subscription_id, symbol) do update set until = excluded.until",
        (sub_id, symbol, until),
    )
    return until


def snoozed(conn, sub_id: int) -> dict[str, datetime]:
    rows = conn.execute(
        "select symbol, until from public.snoozes where subscription_id = %s and until > now()", (sub_id,)
    ).fetchall()
    return {r["symbol"]: r["until"] for r in rows}


def replace_snoozes(conn, sub_id: int, snoozes: dict[str, datetime]) -> None:
    """The phone's snooze list replaces the server's (Rules screen: add 1 day / 1 week, or remove)."""
    with conn.transaction():
        conn.execute("delete from public.snoozes where subscription_id = %s", (sub_id,))
        for sym, until in snoozes.items():
            if until > datetime.now(UTC):
                conn.execute("insert into public.snoozes (subscription_id, symbol, until) values (%s,%s,%s)",
                             (sub_id, sym.upper(), until))  # fmt: skip


def rules(conn, sub_id: int) -> list[WeightRule]:
    rows = conn.execute("select rule from public.feedback_rules where subscription_id = %s", (sub_id,)).fetchall()
    return [WeightRule.model_validate(r["rule"]) for r in rows]


def replace_rules(conn, sub_id: int, new: list[WeightRule]) -> None:
    with conn.transaction():
        conn.execute("delete from public.feedback_rules where subscription_id = %s", (sub_id,))
        for r in new:
            conn.execute(
                "insert into public.feedback_rules (subscription_id, rule_id, rule) values (%s,%s,%s)",
                (sub_id, r.id, Jsonb(r.model_dump(mode="json"))),
            )


def settings_of(sub: dict) -> AlertSettings:
    return AlertSettings.model_validate(sub.get("settings") or {})


def weights_of(sub: dict) -> dict[str, float | None]:
    return {h["symbol"]: h.get("weight_pct") for h in sub["holdings"]}
