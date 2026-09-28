"""
ماژول جستجو و مدیریت محصولات طیبستان
با همگام‌سازی خودکار از WooCommerce REST API
"""
import json
import os
import time
import re
from typing import List, Dict
from rapidfuzz import fuzz, process
import requests
from requests.auth import HTTPBasicAuth

from .config import PRODUCTS_CACHE, SITE_URL, WC_URL, WC_KEY, WC_SECRET

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


def _cache_is_fresh() -> bool:
    if not os.path.exists(PRODUCTS_CACHE):
        return False
    age = time.time() - os.path.getmtime(PRODUCTS_CACHE)
    return age < CACHE_TTL_SECONDS


def _format_price(price) -> str:
    """قیمت خوانا با جداکننده هزارگان"""
    if price is None or price == "":
        return ""
    s = str(price).strip()
    # حذف HTML احتمالی از price_html
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").strip()
    try:
        # عدد خام
        num = float(re.sub(r"[^0-9.]", "", s.split("-")[0].strip()) or 0)
        if num <= 0:
            return s
        return f"{int(num):,}".replace(",", "٬") + " تومان"
    except Exception:
        return s


def fetch_from_woocommerce() -> List[Dict]:
    if not WC_KEY or not WC_SECRET:
        print("WC_KEY یا WC_SECRET تنظیم نشده — همگام‌سازی رد شد.")
        return []

    products: List[Dict] = []
    page = 1
    per_page = 100
    base = WC_URL.rstrip("/") + "/wp-json/wc/v3/products"

    while True:
        try:
            resp = requests.get(
                base,
                params={
                    "per_page": per_page,
                    "page": page,
                    "status": "publish",
                },
                auth=HTTPBasicAuth(WC_KEY, WC_SECRET),
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print(f"خطا در دریافت محصولات از ووکامرس (صفحه {page}):", e)
            break

        if not batch:
            break

        for item in batch:
            name = item.get("name") or ""
            price = item.get("price") or item.get("regular_price") or ""
            products.append({
                "id": item.get("id"),
                "name": name,
                "url": item.get("permalink") or f"{SITE_URL}/?p={item.get('id')}",
                "price": str(price) if price else "",
                "sku": item.get("sku") or "",
            })

        if len(batch) < per_page:
            break
        page += 1

    print(f"{len(products)} محصول از ووکامرس دریافت شد.")
    return products


def sync_products(force: bool = False) -> List[Dict]:
    if not force and _cache_is_fresh():
        return load_products_from_file()

    products = fetch_from_woocommerce()
    if products:
        save_products(products)
        return products
    return load_products_from_file()


def load_products_from_file() -> List[Dict]:
    if not os.path.exists(PRODUCTS_CACHE):
        return []
    with open(PRODUCTS_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_products() -> List[Dict]:
    return sync_products(force=False)


def save_products(products: List[Dict]) -> None:
    with open(PRODUCTS_CACHE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def search_products(query: str, limit: int = 5) -> List[Dict]:
    """
    جستجوی دقیق‌تر:
    1) اول محصولاتی که خودِ عبارت داخل نامشان است
    2) بعد fuzzy با آستانه بالا
    3) فقط نتایج نزدیک به بهترین امتیاز
    """
    products = load_products()
    q = (query or "").strip()
    if not products or not q:
        return []

    q_norm = q.lower()

    # ۱) تطبیق مستقیم (عبارت داخل نام)
    exact = []
    for p in products:
        name = p.get("name") or ""
        if q_norm in name.lower():
            item = p.copy()
            item["_score"] = 100
            exact.append(item)

    if exact:
        # اگر تطبیق مستقیم داریم، فقط همان‌ها (مرتب‌شده کوتاه‌تر = مرتبط‌تر)
        exact.sort(key=lambda x: len(x.get("name", "")))
        return exact[:limit]

    # ۲) fuzzy — آستانه بالاتر
    names = [p.get("name", "") for p in products]
    # برای عبارت کوتاه آستانه سخت‌گیرانه‌تر
    cutoff = 80 if len(q) <= 3 else 70

    results = process.extract(
        q,
        names,
        scorer=fuzz.partial_ratio,
        limit=limit * 3,
        score_cutoff=cutoff,
    )

    if not results:
        # یک‌بار با scorer دیگر امتحان کن
        results = process.extract(
            q,
            names,
            scorer=fuzz.WRatio,
            limit=limit * 3,
            score_cutoff=cutoff,
        )

    if not results:
        return []

    best = results[0][1]
    matched = []
    for name, score, idx in results:
        # فقط نتایج نزدیک به بهترین
        if score < best - 12:
            continue
        product = products[idx].copy()
        product["_score"] = score
        matched.append(product)
        if len(matched) >= limit:
            break

    return matched


def format_product_message(product: Dict) -> str:
    """فرمت متن ساده (بدون HTML — کتابخانه parse_mode ندارد)"""
    name = product.get("name", "محصول")
    url = product.get("url") or product.get("permalink") or SITE_URL
    price = _format_price(product.get("price", ""))

    lines = [f"🛍 {name}"]
    if price:
        lines.append(f"💰 قیمت: {price}")
    lines.append(f"🔗 {url}")
    return "\n".join(lines)
