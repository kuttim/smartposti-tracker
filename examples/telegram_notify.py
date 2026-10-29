"""Send new tracking events to a Telegram chat.

    set TELEGRAM_BOT_TOKEN=123:abc      (from @BotFather)
    set TELEGRAM_CHAT_ID=123456789
    python examples/telegram_notify.py CODE [CODE ...]
"""
import logging
import os
import sys

import requests

from smartposti_tracker import JsonFileStore, Watcher

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def send_to_telegram(shipment, events):
    lines = [f"📦 {shipment.tracking_code} ({shipment.status})"]
    lines += [f"{e.timestamp.astimezone():%d.%m %H:%M} {e.description}" for e in events]
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": "\n".join(lines)}, timeout=20)


logging.basicConfig(level=logging.INFO)
Watcher(store=JsonFileStore("telegram_state.json"), handlers=[send_to_telegram]).run(
    sys.argv[1:], interval=600)
