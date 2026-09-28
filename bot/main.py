"""
نقطه ورود ربات طیبستان - حالت polling (برای تست محلی)
برای production روی cPanel از webhook + Flask استفاده کنید.
"""
from bale import Bot, Message
from bale.handlers import MessageHandler, CommandHandler

from .config import BALE_TOKEN
from .handlers import handle_start, handle_text

bot = Bot(token=BALE_TOKEN)


@bot.listen("on_ready")
async def on_ready():
    print(f"ربات {bot.user} آماده است!")


@bot.handle(CommandHandler("start"))
async def start_cmd(message: Message):
    await handle_start(message)


@bot.handle(CommandHandler("help"))
async def help_cmd(message: Message):
    await handle_start(message)


@bot.handle(MessageHandler())
async def on_message(message: Message):
    # فقط پیام‌های متنی
    if message.content:
        await handle_text(message)


if __name__ == "__main__":
    bot.run()
