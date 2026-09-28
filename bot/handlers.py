"""
هندلرهای پیام ربات طیبستان
دکمه مینی‌اپ با فیلد web_app مستقیم از API بله
"""
import requests
from bale import Message

from .config import WELCOME_MESSAGE, SITE_URL, BALE_TOKEN
from .products import search_products, format_product_message

API = f"https://tapi.bale.ai/bot{BALE_TOKEN}"


def miniapp_keyboard(product_url: str = None):
    """
    کیبورد با دکمه مینی‌اپ.
    اگر product_url داده شود، همان صفحه محصول در مینی‌اپ باز می‌شود؛
    وگرنه صفحه اصلی فروشگاه.
    """
    url = product_url or SITE_URL
    return {
        "inline_keyboard": [
            [{"text": "🛒 باز کردن در مینی‌اپ", "web_app": {"url": url}}],
            [{"text": "🌐 باز کردن در مرورگر", "url": url}],
        ]
    }


def send_text(chat_id, text, reply_markup=None, reply_to=None):
    """ارسال پیام مستقیم با API بله (پشتیبانی web_app)"""
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        r = requests.post(f"{API}/sendMessage", json=payload, timeout=20)
        return r.json()
    except Exception as e:
        print("send_text error:", e)
        return None


async def handle_start(message: Message):
    name = getattr(message.author, "first_name", None) or "کاربر"
    text = WELCOME_MESSAGE.format(name=name)
    chat_id = message.chat_id
    send_text(chat_id, text, reply_markup=miniapp_keyboard())


async def handle_text(message: Message):
    query = (getattr(message, "content", None) or "").strip()
    if not query or query.startswith("/"):
        return

    results = search_products(query, limit=5)
    chat_id = message.chat_id

    if not results:
        send_text(
            chat_id,
            f"متأسفانه محصولی با عنوان «{query}» پیدا نشد 😕\n"
            "لطفاً نام دیگری امتحان کنید یا از دکمه فروشگاه استفاده کنید.",
            reply_markup=miniapp_keyboard(),
        )
        return

    # اگر فقط یک نتیجه بود، دکمه مینی‌اپ همان محصول را باز کند
    product_url = results[0].get("url") if len(results) == 1 else SITE_URL

    parts = [f"🔍 نتایج برای «{query}»:\n"]
    for i, p in enumerate(results, 1):
        parts.append(format_product_message(p))
        if i < len(results):
            parts.append("────────")

    send_text(
        chat_id,
        "\n".join(parts),
        reply_markup=miniapp_keyboard(product_url),
    )
