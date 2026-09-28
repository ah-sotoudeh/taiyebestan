"""
ربات طیبستان — فقط polling (بدون webhook)
اجرا:
    python -m bot.main
"""
import asyncio
from bale import Bot, Message

from .config import BALE_TOKEN
from .handlers import handle_start, handle_text

bot = Bot(token=BALE_TOKEN)


@bot.listen("on_before_ready")
async def on_before_ready():
    # اگر webhook قبلی ست شده باشد، polling کار نمی‌کند
    try:
        await bot.delete_webhook()
        print("Webhook حذف شد — حالت polling فعال است.")
    except Exception as e:
        print("حذف webhook:", e)


@bot.listen("on_ready")
async def on_ready():
    print(f"ربات آماده است: {bot.user}")


@bot.event
async def on_message(message: Message):
    content = (getattr(message, "content", None) or "").strip()
    if not content:
        return

    if content in ("/start", "/help") or content.startswith("/start"):
        await handle_start(message)
        return

    await handle_text(message)


if __name__ == "__main__":
    bot.run()
