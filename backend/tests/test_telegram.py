from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from finn.cards.build import NEUTRAL_SCORE, build_card
from finn.push import bot
from finn.push.format import buttons, card_text

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


class FakeTG:
    def __init__(self):
        self.sent, self.answers, self.edits = [], [], []

    def available(self):
        return True

    def send(self, chat_id, text, buttons=None):
        self.sent.append((chat_id, text, buttons))
        return {"message_id": len(self.sent)}

    def answer_callback(self, cid, text=""):
        self.answers.append(text)

    def edit_buttons(self, chat_id, message_id, buttons):
        self.edits.append(message_id)


EVENT = {"id": "COCHINSHIP:results:Q2 FY27", "symbol": "COCHINSHIP", "category": "results", "title": "Q2 FY27 results",
         "started_at": NOW, "timeline": [{"stage": "outcome", "filing_id": "NSE:1", "at": NOW.isoformat(),
                                          "label": "Outcome"}],
         "impact": "positive", "so_what": "Revenue +12% YoY", "detail": None}  # fmt: skip
FILINGS = {"NSE:1": {"id": "NSE:1", "attachment_url": "https://nsearchives.nseindia.com/corporate/x.pdf",
                     "subject": "Financial results", "filed_at": NOW, "fetched_at": NOW}}  # fmt: skip


@pytest.fixture
def fake_db(monkeypatch):
    state = {"subs": {}, "snoozes": [], "alerts": [], "links": {"good": {"holdings": [{"symbol": "INFY",
             "weight_pct": 50}, {"symbol": "TCS", "weight_pct": 50}], "settings": {}, "secret_hash": "h"}}}  # fmt: skip

    def upsert(conn, chat_id, holdings, settings, secret_hash, source):
        state["subs"][chat_id] = {"id": 7, "chat_id": chat_id, "holdings": holdings, "settings": settings,
                                  "source": source}  # fmt: skip
        return 7

    monkeypatch.setattr(bot.subs, "consume_link", lambda conn, t: state["links"].pop(t, None))
    monkeypatch.setattr(bot.subs, "upsert", upsert)
    monkeypatch.setattr(bot.subs, "by_chat", lambda conn, c: state["subs"].get(c))
    monkeypatch.setattr(bot.subs, "delete", lambda conn, i: state["subs"].clear())
    monkeypatch.setattr(bot.subs, "rules", lambda conn, i: [])
    monkeypatch.setattr(bot.subs, "snooze", lambda conn, i, s, d: state["snoozes"].append((s, d)) or NOW)
    card = build_card(EVENT, FILINGS, NEUTRAL_SCORE)
    monkeypatch.setattr(bot, "brief", lambda conn, w, since, rules: {"cards": [card]})
    monkeypatch.setattr(bot, "record_alert", lambda *a, **k: state["alerts"].append(a[3:5]))
    return state


def msg(text, chat=42):
    return {"update_id": 1, "message": {"chat": {"id": chat, "type": "private"}, "text": text}}


def test_bare_start_subscribes_demo_and_sends_test_alert(fake_db):
    tg = FakeTG()
    assert bot.handle_update(None, tg, msg("/start")) == "start"
    assert fake_db["subs"][42]["source"] == "demo" and len(fake_db["subs"][42]["holdings"]) == 18
    assert "demo portfolio" in tg.sent[0][1]
    assert "Test alert" in tg.sent[1][1] and "COCHINSHIP" in tg.sent[1][1]
    assert [b["text"] for b in tg.sent[1][2][0]][-1] == "Snooze"
    assert fake_db["alerts"] == [("test", "sent")]


def test_start_with_token_uses_uploaded_holdings_once(fake_db):
    tg = FakeTG()
    bot.handle_update(None, tg, msg("/start good"))
    assert fake_db["subs"][42]["source"] == "link" and "2 holdings" in tg.sent[0][1]
    bot.handle_update(None, tg, msg("/start good", chat=43))
    assert "expired" in tg.sent[-1][1] and 43 not in fake_db["subs"]


def test_snooze_flow_and_stop(fake_db):
    tg = FakeTG()
    bot.handle_update(None, tg, msg("/start"))
    cq = {"id": "c1", "data": "snz:INFY", "message": {"message_id": 5, "chat": {"id": 42}}}
    assert bot.handle_update(None, tg, {"callback_query": cq}) == "snooze: asked"
    cq["data"] = "snz:INFY:7"
    assert bot.handle_update(None, tg, {"callback_query": cq}) == "snoozed INFY 7d"
    assert fake_db["snoozes"] == [("INFY", 7)] and tg.edits == [5]
    assert bot.handle_update(None, tg, msg("/stop")) == "stop" and not fake_db["subs"]


def test_group_chats_ignored(fake_db):
    u = msg("/start")
    u["message"]["chat"]["type"] = "group"
    assert bot.handle_update(None, FakeTG(), u).startswith("ignored")


def test_message_escapes_html_and_links_source(monkeypatch):
    monkeypatch.setenv("WEB_BASE_URL", "https://finn.example")
    e = {**EVENT, "title": "Results <b>& more</b>"}
    card = build_card(e, FILINGS, NEUTRAL_SCORE)
    text = card_text(card)
    assert "&lt;b&gt;" in text and "Source filing" in text
    assert buttons(card)[0][0]["url"] == "https://finn.example/e/COCHINSHIP%3Aresults%3AQ2%20FY27"


def test_webhook_rejects_wrong_secret(monkeypatch):
    from api.main import app

    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    c = TestClient(app)
    assert c.post("/telegram/webhook", json={}, headers={"X-Telegram-Bot-Api-Secret-Token": "nope"}).status_code == 401
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET")
    assert c.post("/telegram/webhook", json={}, headers={"X-Telegram-Bot-Api-Secret-Token": ""}).status_code == 401
