"""
هندلرهای ربات طیبستان
فهرست خلاصه → جزئیات با زدن روی محصول
"""
import requests
from bale import Message

from .config import WELCOME_MESSAGE, SITE_URL, BALE_TOKEN
from .products import (
    search_products,
    format_product_message,
    format_product_short,
    get_top_rated,
    get_categories,
    get_by_category,
    find_category_by_name,
    get_product_by_id,
)

API = f"https://tapi.bale.ai/bot{BALE_TOKEN}"


def main_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "⭐ محبوب‌ترین‌ها", "callback_data": "popular"},
                {"text": "📂 دسته‌بندی‌ها", "callback_data": "categories"},
            ],
            [{"text": "🛒 فروشگاه", "web_app": {"url": SITE_URL}}],
        ]
    }


def short_list_keyboard(products):
    """
    هر محصول یک دکمه: نام  ⭐ ۴.۸
    با زدن → جزئیات کامل
    """
    rows = []
    for p in products:
        name = (p.get("name") or "محصول").strip()
        avg = p.get("average_rating") or 0
        try:
            avg_f = float(avg)
        except Exception:
            avg_f = 0
        if avg_f > 0:
            label = f"{name}  ⭐ {avg_f:.1f}"
        else:
            label = name
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([{
            "text": label,
            "callback_data": f"prod:{p.get('id')}",
        }])
    rows.append([
        {"text": "⭐ محبوب‌ترین‌ها", "callback_data": "popular"},
        {"text": "📂 دسته‌ها", "callback_data": "categories"},
    ])
    rows.append([{"text": "🏠 منوی اصلی", "callback_data": "home"}])
    return {"inline_keyboard": rows}


def detail_keyboard(product):
    """فقط یک دکمه مینی‌اپ برای همان محصول"""
    name = (product.get("name") or "محصول").strip()
    label = name if len(name) <= 35 else name[:32] + "..."
    url = product.get("url") or SITE_URL
    return {
        "inline_keyboard": [
            [{
                "text": f"مشاهده «{label}» در فروشگاه",
                "web_app": {"url": url},
            }],
            [
                {"text": "⭐ محبوب‌ترین‌ها", "callback_data": "popular"},
                {"text": "📂 دسته‌ها", "callback_data": "categories"},
            ],
            [{"text": "🏠 منوی اصلی", "callback_data": "home"}],
        ]
    }


def categories_keyboard(cats):
    rows = []
    row = []
    for c in cats:
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


def _send_short_list(chat_id, title: str, products: list):
    if not products:
        send_text(chat_id, f"{title}\n\nمحصولی پیدا نشد.", reply_markup=main_menu_keyboard())
        return
    # متن کوتاه + دکمه‌ها برای انتخاب
    lines = [title, "", "روی نام محصول بزنید تا جزئیات و قیمت را ببینید:", ""]
    for i, p in enumerate(products, 1):
        lines.append(f"{i}. {format_product_short(p)}")
    send_text(chat_id, "\n".join(lines), reply_markup=short_list_keyboard(products))


def _send_product_detail(chat_id, product):
    text = format_product_message(product)
    send_text(chat_id, text, reply_markup=detail_keyboard(product))


async def handle_start(message: Message):
    name = getattr(message.author, "first_name", None) or "کاربر"
    text = WELCOME_MESSAGE.format(name=name)
    send_text(message.chat_id, text, reply_markup=main_menu_keyboard())


async def handle_popular(chat_id):
    products = get_top_rated(limit=10)
    _send_short_list(chat_id, "⭐ محبوب‌ترین محصولات", products)


async def handle_categories_list(chat_id):
    cats = get_categories()
    if not cats:
        send_text(chat_id, "دسته‌بندی‌ای یافت نشد.", reply_markup=main_menu_keyboard())
        return
    send_text(chat_id, "📂 یک دسته‌بندی را انتخاب کنید:", reply_markup=categories_keyboard(cats))


async def handle_category(chat_id, category_id: int):
    cats = get_categories()
    cat_name = "دسته"
    for c in cats:
        if c.get("id") == category_id:
            cat_name = c.get("name") or cat_name
            break
    products = get_by_category(category_id, limit=15)
    _send_short_list(chat_id, f"📂 {cat_name}", products)


async def handle_text(message: Message):
    query = (getattr(message, "content", None) or "").strip()
    if not query or query.startswith("/start") or query.startswith("/help"):
        return

    chat_id = message.chat_id
    q = query.strip()

    if q in ("محبوب", "محبوب‌ترین", "محبوب ترین", "محبوب‌ترین‌ها"):
        await handle_popular(chat_id)
        return
    if q in ("دسته", "دسته‌بندی", "دسته بندی", "دسته‌ها"):
        await handle_categories_list(chat_id)
        return
    if q in ("منو", "خانه", "menu", "home"):
        await handle_start(message)
        return

    # دستور جزئیات: /p123 یا /123
    if q.startswith("/") and q[1:].lstrip("pP").isdigit():
        pid = int(q[1:].lstrip("pP"))
        product = get_product_by_id(pid)
        if product:
            _send_product_detail(chat_id, product)
            return

    cat = find_category_by_name(q.lstrip("/"))
    if cat:
        await handle_category(chat_id, cat["id"])
        return

    results = search_products(q, limit=5)
    if not results:
        send_text(
            chat_id,
            f"متأسفانه محصولی با عنوان «{q}» پیدا نشد 😕",
            reply_markup=main_menu_keyboard(),
        )
        return

    # اگر فقط یک نتیجه دقیق → مستقیم جزئیات
    if len(results) == 1:
        _send_product_detail(chat_id, results[0])
        return

    _send_short_list(chat_id, f"🔍 نتایج برای «{q}»", results)


async def handle_callback(callback):
    data = getattr(callback, "data", None) or ""
    cq_id = getattr(callback, "id", None)
    msg = getattr(callback, "message", None)
    chat_id = None
    if msg is not None:
        chat_id = getattr(msg, "chat_id", None) or getattr(getattr(msg, "chat", None), "id", None)
    if isinstance(callback, dict):
        data = callback.get("data") or data
        cq_id = callback.get("id") or cq_id
        chat_id = chat_id or callback.get("message", {}).get("chat", {}).get("id")

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
            await handle_category(chat_id, int(data.split(":", 1)[1]))
        except ValueError:
            pass
    elif data.startswith("prod:"):
        try:
            pid = int(data.split(":", 1)[1])
            product = get_product_by_id(pid)
            if product:
                _send_product_detail(chat_id, product)
        except ValueError:
            pass
