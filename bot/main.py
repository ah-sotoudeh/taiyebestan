"""
ربات طیبستان — polling پایدار
اجرا: python -u -m bot.main

همگام‌سازی محصولات فقط یک‌بار در استارت انجام می‌شود.
فقط به پیام‌های خصوصی پاسخ می‌دهد (نه کانال/گروه).
"""
import asyncio
import sys
import threading
import time
import traceback

from bale import Bot, Message

from .config import BALE_TOKEN
from .handlers import handle_start, handle_text, handle_callback
from .products import sync_products, sync_categories


def log(*a):
    sys.stdout.write(" ".join(map(str, a)) + "\n")
    sys.stdout.flush()


def _chat_type_str(obj) -> str:
    if obj is None:
        return ""
    ctype = getattr(obj, "type", None)
    if ctype is None and isinstance(obj, dict):
        ctype = obj.get("type")
    if ctype is None:
        return ""
    name = getattr(ctype, "name", None) or getattr(ctype, "value", None)
    s = str(name if name is not None else ctype).lower()
    return s


def is_private_message(message) -> bool:
    """فقط چت خصوصی کاربر — کانال و گروه نادیده گرفته می‌شوند."""
    chat = getattr(message, "chat", None)
    s = _chat_type_str(chat)
    if "private" in s or s in ("pv", "user", "private_chat"):
        return True
    if any(x in s for x in ("channel", "group", "supergroup", "super_group")):
        return False

    chat_id = getattr(message, "chat_id", None)
    if chat_id is None and chat is not None:
        chat_id = getattr(chat, "id", None)
    try:
        cid = int(chat_id)
        return cid > 0
    except (TypeError, ValueError):
        return False


def is_private_callback(callback) -> bool:
    msg = getattr(callback, "message", None)
    if msg is not None:
        return is_private_message(msg)
    if isinstance(callback, dict):
        chat = (callback.get("message") or {}).get("chat") or {}
        s = _chat_type_str(chat)
        if "private" in s:
            return True
        if any(x in s for x in ("channel", "group", "supergroup")):
            return False
        try:
            cid = int(chat.get("id") or 0)
            return cid > 0
        except (TypeError, ValueError):
            return False
    return False


def sync_once():
    log("همگام‌سازی محصولات و دسته‌ها از فروشگاه...")
    try:
        products = sync_products(force=True)
        cats = sync_categories(force=True)
        log(f"همگام‌سازی تمام شد: {len(products)} محصول، {len(cats)} دسته")
    except Exception:
        log("خطا در همگام‌سازی (از کش قبلی استفاده می‌شود):\n" + traceback.format_exc())


def start_heartbeat(interval_sec: int = 300):
    """هر چند دقیقه یک خط در لاگ بنویس تا بفهمیم پروسه زنده‌ست."""

    def _loop():
        while True:
            time.sleep(interval_sec)
            log(f"heartbeat — بازو زنده است ({time.strftime('%Y-%m-%d %H:%M:%S')})")

    t = threading.Thread(target=_loop, name="heartbeat", daemon=True)
    t.start()


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
            if not is_private_message(message):
                return
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
            if not is_private_callback(callback):
                return
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

    sync_once()
    start_heartbeat(300)

    restart_delay = 3
    while True:
        try:
            bot = build_bot()
            bot.run()
            log("bot.run() تمام شد — راه‌اندازی مجدد...")
        except KeyboardInterrupt:
            log("توقف توسط کاربر.")
            break
        except SystemExit:
            log("SystemExit — راه‌اندازی مجدد...")
        except BaseException:
            # هر خطایی از جمله NetworkError
            log("کرش ربات:\n" + traceback.format_exc())
        log(f"صبر {restart_delay} ثانیه قبل از استارت دوباره...")
        time.sleep(restart_delay)
        restart_delay = min(restart_delay * 2, 30)
