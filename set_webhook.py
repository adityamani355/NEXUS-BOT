"""Run locally once: python set_webhook.py https://YOUR-PROJECT.vercel.app"""
import json
import os
import re
import sys
import urllib.request
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN", "").strip()
secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
if not token or token == "123456789:REPLACE_WITH_REAL_TOKEN":
    raise SystemExit("Set your real BOT_TOKEN in .env first.")
if not secret:
    raise SystemExit("Set TELEGRAM_WEBHOOK_SECRET in .env first.")
if len(sys.argv) != 2:
    raise SystemExit("Usage: python set_webhook.py https://YOUR-PROJECT.vercel.app")
base = sys.argv[1].rstrip("/")
if not base.startswith("https://"):
    raise SystemExit("Vercel deployment URL must start with https://")
url = f"https://api.telegram.org/bot{token}/setWebhook"
data = json.dumps({
    "url": base + "/api/webhook",
    "secret_token": secret,
    "allowed_updates": ["message", "edited_message", "callback_query", "chat_join_request", "chat_member"]
}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=30) as response:
    result = json.loads(response.read().decode())
if not result.get("ok"):
    raise SystemExit("Telegram rejected webhook setup: " + str(result))
print("Webhook configured successfully:", base + "/api/webhook")
