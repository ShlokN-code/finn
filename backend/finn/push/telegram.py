"""Minimal Telegram Bot API client (requests only, so it runs on Render and in jobs).

The bot token is read from TELEGRAM_BOT_TOKEN and never logged (errors are reported without the URL).
"""

from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger("finn.telegram")
API = "https://api.telegram.org"


class TelegramError(RuntimeError):
    pass


class Telegram:
    def __init__(self, token: str | None = None, session: requests.Session | None = None):
        self.token = token if token is not None else os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.s = session or requests.Session()

    def available(self) -> bool:
        return bool(self.token)

    def call(self, method: str, **payload) -> dict:
        if not self.token:
            raise TelegramError("TELEGRAM_BOT_TOKEN not set")
        try:
            r = self.s.post(f"{API}/bot{self.token}/{method}", json=payload, timeout=20)
        except requests.RequestException as e:  # never include the URL: it carries the token
            raise TelegramError(f"{method}: {type(e).__name__}") from None
        try:
            body = r.json()
        except ValueError:
            raise TelegramError(f"{method}: HTTP {r.status_code}, non-JSON body") from None
        if not body.get("ok"):
            raise TelegramError(f"{method}: {body.get('error_code')} {body.get('description')}")
        return body.get("result") or {}

    def send(self, chat_id: int, text: str, buttons: list[list[dict]] | None = None) -> dict:
        payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "link_preview_options":
                         {"is_disabled": True}}  # fmt: skip
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        return self.call("sendMessage", **payload)

    def answer_callback(self, callback_id: str, text: str = "") -> None:
        self.call("answerCallbackQuery", callback_query_id=callback_id, text=text[:190])

    def edit_buttons(self, chat_id: int, message_id: int, buttons: list[list[dict]] | None) -> None:
        self.call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
                  reply_markup={"inline_keyboard": buttons or []})  # fmt: skip
