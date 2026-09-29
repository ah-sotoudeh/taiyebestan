"""
ربات طیبستان — polling
اجرا: python -u -m bot.main
"""
import sys
from bale import Bot, Message

from .config import BALE_TOKEN
from .handlers import handle_start, handle_text, handle_callback


def log(*a):
    sys.stdout.write(" ".join(map(str, a)) + "\n")
    sys.stdout.flush()


bot = Bot(token=BALE_TOKEN)


@bot.listen("on_before_ready")
async def on_before_ready():
    try:
        await bot.delete_webhook()
        log("Webhook حذف شد — polling فعال.")
    except Exception as e:
        log("حذف webhook:", e)


@bot.listen("on_ready")
async def on_ready():
    log("ربات آماده است:", bot.user)


@bot.listen("on_message")
async def on_message(message: Message):
    content = (getattr(message, "content", None) or "").strip()
    if not content:
        return
    if content in ("/start", "/help") or content.startswith("/start"):
        await handle_start(message)
        return
    await handle_text(message)


@bot.listen("on_callback")
async def on_callback(callback):
    try:
        await handle_callback(callback)
    except Exception as e:
        log("callback error:", e)


if __name__ == "__main__":
    log("در حال استارت ربات...")
    if not BALE_TOKEN or BALE_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log("خطا: BALE_TOKEN در .env تنظیم نشده!")
        sys.exit(1)
    bot.run()
