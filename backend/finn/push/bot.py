"""Telegram bot conversation: /start [token], /stop, /help, Snooze buttons. Called by the API webhook.

/start <token> → subscription with the holdings the web app uploaded; bare /start → the demo portfolio.
Either way a test alert (the best recent card for those holdings) is sent immediately.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from html import escape

from finn.calendar import now_utc
from finn.cards.brief import brief
from finn.format import ist
from finn.models import AlertSettings, Card
from finn.push import subscriptions as subs
from finn.push.format import buttons, card_text, web_base
from finn.push.telegram import Telegram, TelegramError

log = logging.getLogger("finn.bot")

HELP = (
    "<b>FINN</b> tells you when something material happens to your holdings — results, management changes, "
    "unusual price moves — and hides routine filings.\n\n"
    "/start — connect (demo portfolio unless you came from the app)\n/stop — disconnect and delete your data\n"
    "Each alert has <b>Open in FINN</b> and <b>Snooze</b> (1 day / 1 week)."
)
TEST_WINDOW = timedelta(days=7)


def record_alert(conn, sub_id: int, card: Card, trigger: str, status: str, title: str, body: str,
                 message_id: int | None = None, reason: str | None = None, batch_id: str | None = None,
                 severity: str = "normal") -> None:  # fmt: skip
    from psycopg.types.json import Jsonb

    conn.execute(
        "insert into public.alerts (subscription_id, event_id, symbol, trigger, severity, status, status_reason, "
        "title, body, score, batch_id, telegram_message_id, sent_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
        "case when %s in ('sent', 'batched') then now() end) on conflict (subscription_id, event_id) do update set "
        "status = excluded.status, status_reason = excluded.status_reason, batch_id = excluded.batch_id, "
        "telegram_message_id = coalesce(excluded.telegram_message_id, alerts.telegram_message_id), "
        "sent_at = coalesce(alerts.sent_at, excluded.sent_at)",
        (sub_id, card.event_id, card.symbol, trigger, severity, status, reason, title, body[:3000],
         Jsonb(card.score.model_dump(mode="json")), batch_id, message_id, status),
    )  # fmt: skip


def send_test_alert(conn, tg: Telegram, sub: dict) -> str:
    """The best card for these holdings in the last 7 days, labelled 'Test alert'."""
    weights = subs.weights_of(sub)
    b = brief(conn, weights, now_utc() - TEST_WINDOW, subs.rules(conn, sub["id"]))
    cards = [c for c in b.cards if c.card_type != "what_to_watch"] or b.cards
    if not cards:
        tg.send(sub["chat_id"], "🔔 <b>Test alert</b> — FINN is connected. Nothing material on your holdings in "
                "the last 7 days; the next real event will arrive here.")  # fmt: skip
        return "no cards"
    card = cards[0]
    text = card_text(card, prefix="🔔 <b>Test alert</b> — this is how FINN alerts look (top event, last 7 days)")
    msg = tg.send(sub["chat_id"], text, buttons(card))
    record_alert(conn, sub["id"], card, "test", "sent", card.headline, text, msg.get("message_id"))
    return card.event_id


def _start(conn, tg: Telegram, chat_id: int, arg: str) -> None:
    if arg:
        link = subs.consume_link(conn, arg)
        if link is None:
            tg.send(chat_id, "That connect link has expired or was already used. Open FINN and tap "
                    "<b>Connect Telegram</b> again, or send /start to follow the demo portfolio.")  # fmt: skip
            return
        sid = subs.upsert(conn, chat_id, link["holdings"], link["settings"], link["secret_hash"], "link")
        n = len(link["holdings"])
        intro = (f"✅ Connected. FINN now watches your <b>{n} holdings</b> (symbols and weights only — no "
                 "quantities). /stop deletes them.")  # fmt: skip
    else:
        sid = subs.upsert(conn, chat_id, subs.demo_holdings(), AlertSettings().model_dump(mode="json"), None, "demo")
        intro = ("✅ Connected to the <b>demo portfolio</b> (18 Indian large- and mid-caps). To use your own "
                 f"holdings, open {escape(web_base() or 'FINN')} → Connect Telegram. /stop deletes this.")  # fmt: skip
    tg.send(chat_id, intro)
    sub = subs.by_chat(conn, chat_id)
    assert sub is not None and sub["id"] == sid
    send_test_alert(conn, tg, sub)


def _snooze_choice(symbol: str) -> list[list[dict]]:
    return [[{"text": f"Snooze {symbol} 1 day", "callback_data": f"snz:{symbol}:1"},
             {"text": "1 week", "callback_data": f"snz:{symbol}:7"}]]  # fmt: skip


def handle_update(conn, tg: Telegram, update: dict) -> str:
    """Returns a short label of what happened (for logs/tests). Never raises on user input."""
    try:
        if cq := update.get("callback_query"):
            return _callback(conn, tg, cq)
        msg = update.get("message") or {}
        chat = (msg.get("chat") or {}).get("id")
        text = (msg.get("text") or "").strip()
        if not chat or not text:
            return "ignored"
        if (msg.get("chat") or {}).get("type") not in (None, "private"):
            return "ignored: not a private chat"
        cmd, _, arg = text.partition(" ")
        cmd = cmd.split("@")[0].lower()
        if cmd == "/start":
            _start(conn, tg, chat, arg.strip())
            return "start"
        if cmd == "/stop":
            sub = subs.by_chat(conn, chat)
            if sub:
                subs.delete(conn, sub["id"])
            tg.send(chat, "Disconnected. Your holdings, rules and snoozes are deleted. /start to reconnect.")
            return "stop"
        tg.send(chat, HELP)
        return "help"
    except TelegramError as e:
        log.warning("telegram error: %s", e)
        return f"telegram error: {e}"


def _callback(conn, tg: Telegram, cq: dict) -> str:
    data = cq.get("data") or ""
    chat = ((cq.get("message") or {}).get("chat") or {}).get("id")
    sub = subs.by_chat(conn, chat) if chat else None
    if not data.startswith("snz:") or sub is None:
        tg.answer_callback(cq["id"], "Not connected — send /start")
        return "callback: no subscription"
    parts = data.split(":")
    symbol = parts[1]
    if len(parts) == 2:  # first tap: offer durations
        tg.answer_callback(cq["id"])
        tg.send(chat, f"Snooze alerts for <b>{escape(symbol)}</b>?", _snooze_choice(symbol))
        return "snooze: asked"
    days = 7 if parts[2] == "7" else 1
    until = subs.snooze(conn, sub["id"], symbol, days)
    tg.answer_callback(cq["id"], f"{symbol} snoozed until {ist(until)}")
    if msg := cq.get("message"):
        tg.edit_buttons(chat, msg["message_id"], None)
    tg.send(chat, f"😴 No alerts for {escape(symbol)} until {ist(until)}. It still appears in your Brief.")
    return f"snoozed {symbol} {days}d"
