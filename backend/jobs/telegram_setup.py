"""One-time Telegram setup (run locally): point the bot's webhook at the API and set its command list.

Needs TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET and API_PUBLIC_URL (the Render URL) in .env.
Prints only non-secret facts (bot username, webhook URL, pending updates).

python -m jobs.telegram_setup [--info]
"""

from __future__ import annotations

import argparse
import os

from finn.db import load_dotenv
from finn.push.telegram import Telegram


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--info", action="store_true", help="only show the current webhook status")
    args = ap.parse_args()
    load_dotenv()
    tg = Telegram()
    me = tg.call("getMe")
    print(f"bot: @{me.get('username')}")
    if not args.info:
        base = os.environ.get("API_PUBLIC_URL", "").rstrip("/")
        secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        if not base or not secret:
            raise SystemExit("set API_PUBLIC_URL and TELEGRAM_WEBHOOK_SECRET in .env first")
        tg.call("setWebhook", url=f"{base}/telegram/webhook", secret_token=secret,
                allowed_updates=["message", "callback_query"], drop_pending_updates=True)  # fmt: skip
        tg.call("setMyCommands", commands=[
            {"command": "start", "description": "Connect (demo portfolio unless you came from the app)"},
            {"command": "stop", "description": "Disconnect and delete your data"},
            {"command": "help", "description": "What FINN sends"},
        ])  # fmt: skip
    info = tg.call("getWebhookInfo")
    print(f"webhook: {info.get('url') or '(none)'} · pending updates: {info.get('pending_update_count')} · "
          f"last error: {info.get('last_error_message') or 'none'}")  # fmt: skip


if __name__ == "__main__":
    main()
