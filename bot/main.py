"""
ربات طیبستان — polling پایدار
اجرا: python -u -m bot.main

همگام‌سازی محصولات فقط یک‌بار در استارت انجام می‌شود.
"""
import sys
import time
import traceback

from bale import Bot, Message

from .config import BALE_TOKEN
from .handlers import handle_start, handle_text, handle_callback
from .products import sync_products, sync_categories


def log(*a):
    sys.stdout.write(" ".join(map(str, a)) + "\n")
    sys.stdout.flush()


def sync_once():
    """یک‌بار همگام‌سازی از ووکامرس هنگام روشن شدن بازو"""
    log("همگام‌سازی محصولات و دسته‌ها از فروشگاه...")
    try:
        products = sync_products(force=True)
        cats = sync_categories(force=True)
        log(f"همگام‌سازی تمام شد: {len(products)} محصول، {len(cats)} دسته")
    except Exception:
        log("خطا در همگام‌سازی (از کش قبلی استفاده می‌شود):\n" + traceback.format_exc())


def build_bot() -> Bot:
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
        try:
            content = (getattr(message, "content", None) or "").strip()
            if not content:
                return
            if content in ("/start", "/help") or content.startswith("/start"):
                await handle_start(message)
                return
            await handle_text(message)
        except Exception:
            log("on_message error:\n" + traceback.format_exc())

    @bot.listen("on_callback")
    async def on_callback(callback):
        try:
            await handle_callback(callback)
        except Exception:
            log("on_callback error:\n" + traceback.format_exc())

    @bot.listen("on_error")
    async def on_error(event_name, error):
        log(f"on_error [{event_name}]:", error)

    return bot


if __name__ == "__main__":
    log("در حال استارت ربات...")
    if not BALE_TOKEN or BALE_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log("خطا: BALE_TOKEN در .env تنظیم نشده!")
        sys.exit(1)

    # فقط یک‌بار هنگام روشن شدن — نه وسط کار، نه با کرون
    sync_once()

    restart_delay = 3
    while True:
        try:
            bot = build_bot()
            bot.run()
            log("bot.run() تمام شد — راه‌اندازی مجدد...")
        except KeyboardInterrupt:
            log("توقف توسط کاربر.")
            break
        except Exception:
            log("کرش ربات:\n" + traceback.format_exc())
        log(f"صبر {restart_delay} ثانیه قبل از استارت دوباره...")
        time.sleep(restart_delay)
        restart_delay = min(restart_delay * 2, 60)
