"""
ورود WSGI برای cPanel (Passenger)
این فایل را در ریشه اپلیکیشن Python قرار دهید.

مسیر webhook پیشنهادی: https://yourdomain.com/webhook
"""
import sys
import os

# مسیر پروژه را به sys.path اضافه کنید (بسته به ساختار cPanel تغییر دهید)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from flask import Flask, request, jsonify
import asyncio
from bale import Bot, Update

from bot.config import BALE_TOKEN
from bot.handlers import handle_start, handle_text

app = Flask(__name__)
bot = Bot(token=BALE_TOKEN)


def run_async(coro):
    """اجرای کوروتین در event loop"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@app.route("/webhook", methods=["POST"])
def webhook():
    """دریافت آپدیت از بله"""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False}), 400

    try:
        update = Update.from_dict(data)  # بسته به نسخه کتابخانه ممکن است متفاوت باشد
        # ساده‌سازی: فقط پیام متنی را هندل می‌کنیم
        if hasattr(update, "message") and update.message:
            msg = update.message
            content = getattr(msg, "content", None) or getattr(msg, "text", None)
            if content:
                if content.strip() in ("/start", "/help"):
                    run_async(handle_start(msg))
                else:
                    run_async(handle_text(msg))
    except Exception as e:
        # لاگ خطا در production
        print("Webhook error:", e)

    return jsonify({"ok": True})


@app.route("/")
def index():
    return "Taiyebestan Bale Bot is running."


# برای Passenger
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
