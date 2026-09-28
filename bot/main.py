"""
ربات طیبستان — فقط polling
اجرا:
    python -u -m bot.main
"""
import sys
from bale import Bot, Message
from bale.handlers import MessageHandler, CommandHandler

from .config import BALE_TOKEN
from .handlers import handle_start, handle_text

# برای اینکه print فوری در bot.log دیده شود
print = lambda *a, **k: (sys.stdout.write(" ".join(map(str, a)) + "\n"), sys.stdout.flush())

bot = Bot(token=BALE_TOKEN)


@bot.listen("on_before_ready")
async def on_before_ready():
    try:
        await bot.delete_webhook()
        print("Webhook حذف شد — polling فعال.")
    except Exception as e:
        print("حذف webhook:", e)


@bot.listen("on_ready")
async def on_ready():
    print("ربات آماده است:", bot.user)


@bot.handle(CommandHandler("start"))
async def start_cmd(message: Message):
    await handle_start(message)


@bot.handle(CommandHandler("help"))
async def help_cmd(message: Message):
    await handle_start(message)


@bot.handle(MessageHandler())
async def on_any_message(message: Message):
    content = (getattr(message, "content", None) or "").strip()
    if not content:
        return
    if content.startswith("/"):
        return
    await handle_text(message)


if __name__ == "__main__":
    print("در حال استارت ربات...")
    if not BALE_TOKEN or BALE_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("خطا: BALE_TOKEN در .env تنظیم نشده!")
        sys.exit(1)
    bot.run()
