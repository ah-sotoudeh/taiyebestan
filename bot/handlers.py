"""
هندلرهای بازو طیبستان
"""
import requests
from bale import Message

from .config import WELCOME_MESSAGE, SITE_URL, BALE_TOKEN
from .products import (
    search_products,
    format_product_message,
    clean_name,
    get_top_rated,
    get_categories,
    get_by_category,
    find_category_by_name,
    get_product_by_id,
    paginate,
    PAGE_SIZE,
    to_fa_digits,
)
from .reviews_helper import fetch_product_reviews, format_reviews_instant_view

API = f"https://tapi.bale.ai/bot{BALE_TOKEN}"


def main_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "⭐ محبوب‌ترین‌ها", "callback_data": "popular:0"},
                {"text": "📂 دسته‌بندی‌ها", "callback_data": "categories"},
            ],
            [{"text": "🛒 فروشگاه", "web_app": {"url": SITE_URL}}],
        ]
    }


def _btn_label(product) -> str:
    name = clean_name(product.get("name") or "محصول")
    avg = product.get("average_rating") or 0
    cnt = product.get("rating_count") or 0
    try:
        avg_f = float(avg)
    except Exception:
        avg_f = 0
    if avg_f > 0 and cnt:
        label = f"{name}، {to_fa_digits(f'{avg_f:.1f}')} ({to_fa_digits(cnt)} نظر)"
    elif avg_f > 0:
        label = f"{name}، {to_fa_digits(f'{avg_f:.1f}')}"
    else:
        label = name
    if len(label) > 64:
        label = label[:61] + "..."
    return label


def short_list_keyboard(products, page: int, total_pages: int, prefix: str):
    rows = []
    for p in products:
        rows.append([{
            "text": _btn_label(p),
            "callback_data": f"prod:{p.get('id')}",
        }])

    nav = []
    if page > 0:
        nav.append({"text": "قبلی ➡️", "callback_data": f"{prefix}:{page - 1}"})
    if total_pages > 1:
        nav.append({
            "text": f"{to_fa_digits(page + 1)}/{to_fa_digits(total_pages)}",
            "callback_data": "noop",
        })
    if page < total_pages - 1:
        nav.append({"text": "بعدی ⬅️", "callback_data": f"{prefix}:{page + 1}"})
    if nav:
        rows.append(nav)

    rows.append([
        {"text": "⭐ محبوب‌ترین‌ها", "callback_data": "popular:0"},
        {"text": "📂 دسته‌ها", "callback_data": "categories"},
    ])
    rows.append([{"text": "🏠 منوی اصلی", "callback_data": "home"}])
    return {"inline_keyboard": rows}


def detail_keyboard(product):
    name = clean_name(product.get("name") or "محصول")
    label = name if len(name) <= 35 else name[:32] + "..."
    url = product.get("url") or SITE_URL
    pid = product.get("id")
    rcount = product.get("rating_count") or 0

    rows = [
        [{
            "text": f"مشاهده «{label}» در فروشگاه",
            "web_app": {"url": url},
        }],
    ]
    if rcount and pid:
        rows.append([{
            "text": f"💬 مشاهده دیدگاه‌ها ({to_fa_digits(rcount)})",
            "callback_data": f"reviews:{pid}",
        }])
    rows.append([
        {"text": "⭐ محبوب‌ترین‌ها", "callback_data": "popular:0"},
        {"text": "📂 دسته‌ها", "callback_data": "categories"},
    ])
    rows.append([{"text": "🏠 منوی اصلی", "callback_data": "home"}])
    return {"inline_keyboard": rows}


def categories_keyboard(cats):
    rows = []
    row = []
    for c in cats:
        name = c.get("name") or "دسته"
        label = name if len(name) <= 28 else name[:25] + "..."
        count = c.get("count") or 0
        text = f"{label}" + (f" ({to_fa_digits(count)})" if count else "")
        row.append({"text": text, "callback_data": f"cat:{c.get('id')}:0"})
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


def _send_short_list(chat_id, title: str, all_products: list, page: int, prefix: str):
    if not all_products:
        send_text(chat_id, f"{title}\n\nمحصولی پیدا نشد.", reply_markup=main_menu_keyboard())
        return
    page_items, page, total_pages = paginate(all_products, page, PAGE_SIZE)
    text = f"{title}\nروی محصول بزنید تا جزئیات را ببینید."
    if total_pages > 1:
        text += f"\nصفحه {to_fa_digits(page + 1)} از {to_fa_digits(total_pages)}"
    send_text(
        chat_id,
        text,
        reply_markup=short_list_keyboard(page_items, page, total_pages, prefix),
    )


def _send_product_detail(chat_id, product):
    send_text(chat_id, format_product_message(product), reply_markup=detail_keyboard(product))


def _send_reviews(chat_id, product_id: int):
    product = get_product_by_id(product_id)
    if not product:
        send_text(chat_id, "محصول پیدا نشد.", reply_markup=main_menu_keyboard())
        return

    reviews = fetch_product_reviews(product_id)
    if not reviews:
        send_text(
            chat_id,
            f"برای «{clean_name(product.get('name') or '')}» هنوز دیدگاهی ثبت نشده.",
            reply_markup=detail_keyboard(product),
        )
        return

    text = format_reviews_instant_view(product, reviews)
    send_text(chat_id, text, reply_markup=detail_keyboard(product))


async def handle_start(message: Message):
    name = getattr(message.author, "first_name", None) or "کاربر"
    send_text(message.chat_id, WELCOME_MESSAGE.format(name=name), reply_markup=main_menu_keyboard())


async def handle_popular(chat_id, page: int = 0):
    products = get_top_rated(limit=50)
    _send_short_list(chat_id, "⭐ محبوب‌ترین محصولات", products, page, "popular")


async def handle_categories_list(chat_id):
    cats = get_categories()
    if not cats:
        send_text(chat_id, "دسته‌بندی‌ای یافت نشد.", reply_markup=main_menu_keyboard())
        return
    send_text(chat_id, "📂 یک دسته‌بندی را انتخاب کنید:", reply_markup=categories_keyboard(cats))


async def handle_category(chat_id, category_id: int, page: int = 0):
    cats = get_categories()
    cat_name = "دسته"
    for c in cats:
        if c.get("id") == category_id:
            cat_name = c.get("name") or cat_name
            break
    products = get_by_category(category_id, limit=100)
    _send_short_list(chat_id, f"📂 {cat_name}", products, page, f"cat:{category_id}")


async def handle_text(message: Message):
    query = (getattr(message, "content", None) or "").strip()
    if not query or query.startswith("/start") or query.startswith("/help"):
        return

    chat_id = message.chat_id
    q = query.strip()

    if q in ("محبوب", "محبوب‌ترین", "محبوب ترین", "محبوب‌ترین‌ها"):
        await handle_popular(chat_id, 0)
        return
    if q in ("دسته", "دسته‌بندی", "دسته بندی", "دسته‌ها"):
        await handle_categories_list(chat_id)
        return
    if q in ("منو", "خانه", "menu", "home"):
        await handle_start(message)
        return

    if q.startswith("/") and q[1:].lstrip("pP").isdigit():
        product = get_product_by_id(int(q[1:].lstrip("pP")))
        if product:
            _send_product_detail(chat_id, product)
            return

    cat = find_category_by_name(q.lstrip("/"))
    if cat:
        await handle_category(chat_id, cat["id"], 0)
        return

    results = search_products(q, limit=20)
    if not results:
        send_text(chat_id, f"متأسفانه محصولی با عنوان «{q}» پیدا نشد 😕", reply_markup=main_menu_keyboard())
        return

    if len(results) == 1:
        _send_product_detail(chat_id, results[0])
        return

    _send_short_list(chat_id, f"🔍 نتایج «{q}»", results, 0, "search")


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
    if not chat_id or data == "noop":
        return

    if data == "home":
        send_text(
            chat_id,
            "منوی اصلی 🌿\nنام محصول را بنویسید یا یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data == "categories":
        await handle_categories_list(chat_id)
        return

    if data.startswith("popular:"):
        try:
            page = int(data.split(":")[1])
        except (IndexError, ValueError):
            page = 0
        await handle_popular(chat_id, page)
        return

    if data.startswith("cat:"):
        parts = data.split(":")
        try:
            cat_id = int(parts[1])
            page = int(parts[2]) if len(parts) > 2 else 0
            await handle_category(chat_id, cat_id, page)
        except (IndexError, ValueError):
            pass
        return

    if data.startswith("reviews:"):
        try:
            _send_reviews(chat_id, int(data.split(":", 1)[1]))
        except ValueError:
            pass
        return

    if data.startswith("prod:"):
        try:
            product = get_product_by_id(int(data.split(":", 1)[1]))
            if product:
                _send_product_detail(chat_id, product)
        except ValueError:
            pass
