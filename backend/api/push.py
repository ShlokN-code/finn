"""Brief, card and Telegram endpoints.

POST /brief                  holdings + window + rules → ranked cards (holdings used only for this request)
GET  /events/{id}/card       one card, unranked (the web's /e/<id> page; Telegram 'Open in FINN')
POST /telegram/link          upload symbols + weights → single-use t.me deep link + subscriber secret
POST /telegram/webhook       Telegram updates (checked against TELEGRAM_WEBHOOK_SECRET)
GET|PUT|DELETE /subscriptions/me   bearer = subscriber secret (browser) — view, update, disconnect & delete
"""

from __future__ import annotations

import hmac
import logging
import os
from datetime import timedelta

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from finn.calendar import now_utc
from finn.cards.brief import brief, single_card
from finn.db import connect
from finn.models import AlertSettings, BriefHolding, BriefRequest, WeightRule
from finn.push import subscriptions as subs
from finn.push.bot import handle_update
from finn.push.telegram import Telegram

log = logging.getLogger("finn.api.push")
router = APIRouter()

WINDOWS = {"24h": timedelta(hours=24), "3d": timedelta(days=3), "7d": timedelta(days=7)}


@router.post("/brief")
def post_brief(body: BriefRequest):
    # Holdings are used only to rank this response: never stored, never logged.
    since = (
        body.since if body.window == "since" else (None if body.window == "all" else now_utc() - WINDOWS[body.window])
    )
    weights = {h.symbol.strip().upper(): h.weight_pct for h in body.holdings}
    if all(w is None for w in weights.values()):
        weights = {s: round(100 / len(weights), 4) for s in weights}
    with connect() as conn:
        b = brief(conn, weights, since, body.rules, body.feedback, window=body.window)
    return b.model_dump(mode="json")


@router.get("/events/{event_id}/card")
def get_card(event_id: str):
    with connect() as conn:
        card = single_card(conn, event_id)
    if card is None:
        raise HTTPException(404, "event not found")
    return card.model_dump(mode="json")


class LinkIn(BaseModel):
    holdings: list[BriefHolding] = Field(min_length=1, max_length=subs.MAX_SYMBOLS)
    settings: AlertSettings | None = None


@router.post("/telegram/link")
def post_link(body: LinkIn):
    bot = os.environ.get("TELEGRAM_BOT_USERNAME", "").lstrip("@")
    if not bot:
        raise HTTPException(503, "Telegram is not configured yet")
    with connect() as conn:
        try:
            holdings = subs.clean_holdings(conn, [h.model_dump() for h in body.holdings])
        except subs.HoldingsError as e:
            raise HTTPException(422, str(e)) from None
        token, secret, expires = subs.create_link(conn, holdings, body.settings)
    return {"deep_link": f"https://t.me/{bot}?start={token}", "secret": secret, "expires_at": expires,
            "bot_username": bot, "uploaded": holdings}  # fmt: skip


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header("")):
    expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not expected or not hmac.compare_digest(x_telegram_bot_api_secret_token, expected):
        raise HTTPException(401, "bad secret")
    update = await request.json()
    with connect() as conn:
        what = handle_update(conn, Telegram(), update)
    log.info("telegram update %s → %s", update.get("update_id"), what)
    return {"ok": True}


def _sub_from(authorization: str) -> tuple[object, dict]:
    secret = authorization.removeprefix("Bearer ").strip()
    conn = connect()
    sub = subs.by_secret(conn, secret)
    if sub is None:
        conn.close()
        raise HTTPException(404, "no Telegram connection for this device")
    return conn, sub


@router.get("/subscriptions/me")
def get_me(authorization: str = Header("")):
    conn, sub = _sub_from(authorization)
    with conn:
        return {"holdings": sub["holdings"], "settings": subs.settings_of(sub).model_dump(mode="json"),
                "rules": [r.model_dump(mode="json") for r in subs.rules(conn, sub["id"])],
                "snoozed": subs.snoozed(conn, sub["id"]), "created_at": sub["created_at"]}  # fmt: skip


class MeIn(BaseModel):
    holdings: list[BriefHolding] | None = Field(None, max_length=subs.MAX_SYMBOLS)
    settings: AlertSettings | None = None
    rules: list[WeightRule] | None = Field(None, max_length=500)


@router.put("/subscriptions/me")
def put_me(body: MeIn, authorization: str = Header("")):
    conn, sub = _sub_from(authorization)
    with conn:
        holdings = None
        if body.holdings is not None:
            try:
                holdings = subs.clean_holdings(conn, [h.model_dump() for h in body.holdings])
            except subs.HoldingsError as e:
                raise HTTPException(422, str(e)) from None
        subs.update(conn, sub["id"], holdings, body.settings.model_dump(mode="json") if body.settings else None)
        if body.rules is not None:
            subs.replace_rules(conn, sub["id"], body.rules)
    return {"ok": True}


@router.delete("/subscriptions/me")
def delete_me(authorization: str = Header("")):
    conn, sub = _sub_from(authorization)
    with conn:
        subs.delete(conn, sub["id"])
        tg = Telegram()
        if tg.available():
            try:
                tg.send(sub["chat_id"], "Disconnected from the FINN app. Your holdings, rules and snoozes are deleted.")
            except Exception:  # the delete already happened; a failed goodbye is fine
                pass
    return {"ok": True}
