"""
هندلرهای پیام ربات طیبستان
برای هر محصول یک دکمه مینی‌اپ جدا
"""
import requests
from bale import Message

from .config import WELCOME_MESSAGE, SITE_URL, BALE_TOKEN
from .products import search_products, format_product_message

API = f"https://tapi.bale.ai/bot{BALE_TOKEN}"


def products_keyboard(products=None):
    """
    برای هر محصول یک دکمه مینی‌اپ:
    مشاهده «نام محصول» در فروشگاه
    """
    rows = []
    if products:
        for p in products:
            name = (p.get("name") or "محصول").strip()
            # متن دکمه نباید خیلی بلند باشد
            label = name if len(name) <= 40 else name[:37] + "..."
            url = p.get("url") or SITE_URL
            rows.append([
                {
                    "text": f"مشاهده «{label}» در فروشگاه",
                    "web_app": {"url": url},
                }
            ])
    else:
        rows.append([
            {
                "text": "مشاهده فروشگاه طیبستان",
                "web_app": {"url": SITE_URL},
            }
        ])
    return {"inline_keyboard": rows}


def send_text(chat_id, text, reply_markup=None, reply_to=None):
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
    send_text(message.chat_id, text, reply_markup=products_keyboard())


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
            reply_markup=products_keyboard(),
        )
        return

    parts = [f"🔍 نتایج برای «{query}»:\n"]
    for i, p in enumerate(results, 1):
        parts.append(format_product_message(p))
        if i < len(results):
            parts.append("────────")

    send_text(
        chat_id,
        "\n".join(parts),
        reply_markup=products_keyboard(results),
    )
