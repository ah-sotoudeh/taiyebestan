"""
ارسال محصول به کانال بله
- عکس اول محصول
- متن قالب بازو
- دکمه لینک مستقیم (نه مینی‌اپ)
"""
import json
import os
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from .config import (
    BALE_TOKEN, WC_URL, WC_KEY, WC_SECRET,
    CHANNEL_ID, CHANNEL_STATE_FILE, CHANNEL_QUEUE_FILE,
    CHANNEL_POSTS_PER_RUN, CHANNEL_PICK_MODE,
)
from .products import (
    load_products, get_product_by_id, get_top_rated, clean_name,
)
from .products_ui import format_product_message
from .reviews_helper import fetch_product_reviews

API = f"https://tapi.bale.ai/bot{BALE_TOKEN}"


def fetch_product_image(product: Dict) -> Optional[str]:
    """آدرس تصویر شاخص از کش یا API ووکامرس"""
    if product.get("image"):
        return product["image"]
    pid = product.get("id")
    if not pid or not WC_KEY:
        return None
    try:
        url = f"{WC_URL.rstrip('/')}/wp-json/wc/v3/products/{pid}"
        resp = requests.get(url, auth=HTTPBasicAuth(WC_KEY, WC_SECRET), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        images = data.get("images") or []
        if images:
            return images[0].get("src")
    except Exception as e:
        print("خطا در دریافت تصویر:", e)
    return None


def channel_keyboard(product: Dict) -> dict:
    """دکمه لینک مستقیم — در کانال مینی‌اپ کار نمی‌کند"""
    name = clean_name(product.get("name") or "محصول")
    label = name if len(name) <= 35 else name[:32] + "..."
    url = product.get("url") or "https://taiyebestan.ir"
    return {
        "inline_keyboard": [[
            {"text": f"مشاهده «{label}» در فروشگاه", "url": url},
        ]]
    }


def send_product_to_channel(
    product: Dict,
    chat_id: str = None,
    with_reviews: bool = True,
) -> dict:
    chat_id = chat_id or CHANNEL_ID
    reviews = []
    if with_reviews and product.get("rating_count"):
        reviews = fetch_product_reviews(product.get("id"), limit=30)

    caption = format_product_message(product, reviews=reviews)
    # محدودیت کپشن بله/تلگرام حدود ۱۰۲۴ کاراکتر — اگر طولانی بود کوتاه کن
    if len(caption) > 1000:
        caption = format_product_message(product, reviews=None)
        if len(caption) > 1000:
            caption = caption[:990] + "…"

    kb = channel_keyboard(product)
    image = fetch_product_image(product)

    if image:
        payload = {
            "chat_id": chat_id,
            "photo": image,
            "caption": caption,
            "reply_markup": kb,
        }
        try:
            r = requests.post(f"{API}/sendPhoto", json=payload, timeout=60)
            data = r.json()
            if data.get("ok"):
                return data
            print("sendPhoto failed, fallback sendMessage:", data)
        except Exception as e:
            print("sendPhoto error:", e)

    payload = {
        "chat_id": chat_id,
        "text": caption,
        "reply_markup": kb,
    }
    try:
        return requests.post(f"{API}/sendMessage", json=payload, timeout=30).json()
    except Exception as e:
        print("sendMessage error:", e)
        return {"ok": False, "error": str(e)}


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_state() -> dict:
    return _load_json(CHANNEL_STATE_FILE, {"posted_ids": [], "cursor": 0})


def _save_state(state: dict) -> None:
    _save_json(CHANNEL_STATE_FILE, state)


def pick_products(count: int = None) -> List[Dict]:
    """
    انتخاب محصولات برای ارسال:
    - queue: از channel_queue.json (لیست id)
    - top_rated: محبوب‌ترین‌هایی که هنوز ارسال نشده‌اند
    - rotate: چرخش روی همه محصولات
    """
    count = count or CHANNEL_POSTS_PER_RUN
    state = _load_state()
    posted = set(state.get("posted_ids") or [])
    mode = (CHANNEL_PICK_MODE or "rotate").lower()

    if mode == "queue":
        queue = _load_json(CHANNEL_QUEUE_FILE, [])
        if isinstance(queue, dict):
            queue = queue.get("ids") or []
        picked = []
        remaining = []
        for pid in queue:
            if len(picked) >= count:
                remaining.append(pid)
                continue
            p = get_product_by_id(int(pid))
            if p:
                picked.append(p)
            else:
                remaining.append(pid)
        _save_json(CHANNEL_QUEUE_FILE, remaining)
        return picked

    products = load_products()
    if not products:
        return []

    if mode == "top_rated":
        pool = get_top_rated(limit=200)
        candidates = [p for p in pool if p.get("id") not in posted]
        if not candidates:
            # یک دور کامل تمام شده — از نو
            state["posted_ids"] = []
            _save_state(state)
            candidates = pool
        return candidates[:count]

    # rotate
    cursor = int(state.get("cursor") or 0)
    n = len(products)
    picked = []
    for i in range(n):
        if len(picked) >= count:
            break
        idx = (cursor + i) % n
        p = products[idx]
        if p.get("id") in posted and len(posted) < n:
            continue
        picked.append(p)
    state["cursor"] = (cursor + len(picked)) % max(n, 1)
    _save_state(state)
    return picked


def mark_posted(products: List[Dict]) -> None:
    state = _load_state()
    ids = state.get("posted_ids") or []
    for p in products:
        pid = p.get("id")
        if pid and pid not in ids:
            ids.append(pid)
    # جلوگیری از رشد بی‌نهایت
    if len(ids) > 5000:
        ids = ids[-2000:]
    state["posted_ids"] = ids
    _save_state(state)


def run_daily_posts(count: int = None, chat_id: str = None) -> List[dict]:
    products = pick_products(count)
    results = []
    ok_products = []
    for p in products:
        print("ارسال:", p.get("name"))
        res = send_product_to_channel(p, chat_id=chat_id)
        results.append(res)
        if res.get("ok"):
            ok_products.append(p)
    if ok_products:
        mark_posted(ok_products)
    print(f"{len(ok_products)}/{len(products)} ارسال شد.")
    return results
