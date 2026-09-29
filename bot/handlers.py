"""
هندلرهای پیام ربات طیبستان
جستجو + دسته‌بندی + محبوب‌ترین‌ها
"""
import requests
from bale import Message

from .config import WELCOME_MESSAGE, SITE_URL, BALE_TOKEN
from .products import (
    search_products,
    format_product_message,
    get_top_rated,
    get_categories,
    get_by_category,
    find_category_by_name,
)

API = f"https://tapi.bale.ai/bot{BALE_TOKEN}"


def main_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "⭐ محبوب‌ترین‌ها", "callback_data": "popular"},
                {"text": "📂 دسته‌بندی‌ها", "callback_data": "categories"},
            ],
            [
                {"text": "🛒 فروشگاه", "web_app": {"url": SITE_URL}},
            ],
        ]
    }


def products_keyboard(products=None):
    rows = []
    if products:
        for p in products:
            name = (p.get("name") or "محصول").strip()
            label = name if len(name) <= 40 else name[:37] + "..."
            url = p.get("url") or SITE_URL
            rows.append([{
                "text": f"مشاهده «{label}» در فروشگاه",
                "web_app": {"url": url},
            }])
    rows.append([
        {"text": "⭐ محبوب‌ترین‌ها", "callback_data": "popular"},
        {"text": "📂 دسته‌ها", "callback_data": "categories"},
    ])
    rows.append([{"text": "🏠 منوی اصلی", "callback_data": "home"}])
    return {"inline_keyboard": rows}


def categories_keyboard(cats):
    rows = []
    row = []
    for i, c in enumerate(cats):
        name = c.get("name") or "دسته"
        label = name if len(name) <= 28 else name[:25] + "..."
        count = c.get("count") or 0
        text = f"{label}" + (f" ({count})" if count else "")
        row.append({"text": text, "callback_data": f"cat:{c.get('id')}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "🏠 منوی اصلی", "callback_data": "home"}])
    return {"inline_keyboard": rows}


def send_text(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        return requests.post(f"{API}/sendMessage", json=payload, timeout=20).json()
    except Exception as e:
        print("send_text error:", e)
        return None


def answer_callback(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        requests.post(f"{API}/answerCallbackQuery", json=payload, timeout=10)
    except Exception:
        pass


def _send_product_list(chat_id, title: str, products: list):
    if not products:
        send_text(chat_id, f"{title}\n\nمحصولی پیدا نشد.", reply_markup=main_menu_keyboard())
        return
    parts = [f"{title}\n"]
    for i, p in enumerate(products, 1):
        parts.append(format_product_message(p))
        if i < len(products):
            parts.append("────────")
    send_text(chat_id, "\n".join(parts), reply_markup=products_keyboard(products))


async def handle_start(message: Message):
    name = getattr(message.author, "first_name", None) or "کاربر"
    text = WELCOME_MESSAGE.format(name=name)
    send_text(message.chat_id, text, reply_markup=main_menu_keyboard())


async def handle_popular(chat_id):
    products = get_top_rated(limit=8)
    _send_product_list(chat_id, "⭐ محبوب‌ترین محصولات (بر اساس امتیاز مشتریان)", products)


async def handle_categories_list(chat_id):
    cats = get_categories()
    if not cats:
        send_text(chat_id, "دسته‌بندی‌ای یافت نشد.", reply_markup=main_menu_keyboard())
        return
    send_text(
        chat_id,
        "📂 یک دسته‌بندی را انتخاب کنید:",
        reply_markup=categories_keyboard(cats),
    )


async def handle_category(chat_id, category_id: int):
    cats = get_categories()
    cat_name = "دسته"
    for c in cats:
        if c.get("id") == category_id:
            cat_name = c.get("name") or cat_name
            break
    products = get_by_category(category_id, limit=10)
    _send_product_list(chat_id, f"📂 {cat_name}", products)


async def handle_text(message: Message):
    query = (getattr(message, "content", None) or "").strip()
    if not query or query.startswith("/"):
        return

    chat_id = message.chat_id
    q = query.strip()

    # میانبرهای متنی
    if q in ("محبوب", "محبوب‌ترین", "محبوب ترین", "⭐", "محبوب‌ترین‌ها"):
        await handle_popular(chat_id)
        return
    if q in ("دسته", "دسته‌بندی", "دسته بندی", "دسته‌ها", "دسته بندی ها", "📂"):
        await handle_categories_list(chat_id)
        return
    if q in ("منو", "خانه", "شروع", "menu", "home"):
        await handle_start(message)
        return

    # اگر نام دسته بود
    cat = find_category_by_name(q)
    if cat:
        await handle_category(chat_id, cat["id"])
        return

    results = search_products(q, limit=5)
    if not results:
        send_text(
            chat_id,
            f"متأسفانه محصولی با عنوان «{q}» پیدا نشد 😕\n"
            "نام دیگری بنویسید یا از دکمه‌های زیر استفاده کنید.",
            reply_markup=main_menu_keyboard(),
        )
        return

    parts = [f"🔍 نتایج برای «{q}»:\n"]
    for i, p in enumerate(results, 1):
        parts.append(format_product_message(p))
        if i < len(results):
            parts.append("────────")
    send_text(chat_id, "\n".join(parts), reply_markup=products_keyboard(results))


async def handle_callback(callback):
    """پردازش دکمه‌های شیشه‌ای"""
    data = getattr(callback, "data", None) or ""
    cq_id = getattr(callback, "id", None)
    # chat از message داخل callback
    msg = getattr(callback, "message", None)
    chat_id = None
    if msg is not None:
        chat_id = getattr(msg, "chat_id", None) or getattr(getattr(msg, "chat", None), "id", None)
    if chat_id is None:
        # raw dict fallback
        if isinstance(callback, dict):
            data = callback.get("data") or data
            cq_id = callback.get("id") or cq_id
            chat_id = (
                callback.get("message", {}).get("chat", {}).get("id")
            )

    if cq_id:
        answer_callback(cq_id)

    if not chat_id:
        return

    if data == "popular":
        await handle_popular(chat_id)
    elif data == "categories":
        await handle_categories_list(chat_id)
    elif data == "home":
        send_text(
            chat_id,
            "منوی اصلی 🌿\nنام محصول را بنویسید یا یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=main_menu_keyboard(),
        )
    elif data.startswith("cat:"):
        try:
            cat_id = int(data.split(":", 1)[1])
            await handle_category(chat_id, cat_id)
        except ValueError:
            pass
