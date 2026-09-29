"""
ماژول جستجو و مدیریت محصولات طیبستان
"""
import json
import os
import time
import re
from typing import List, Dict, Optional
from rapidfuzz import fuzz, process
import requests
from requests.auth import HTTPBasicAuth

from .config import (
    PRODUCTS_CACHE, CATEGORIES_CACHE, SITE_URL,
    WC_URL, WC_KEY, WC_SECRET,
)

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


def _auth():
    return HTTPBasicAuth(WC_KEY, WC_SECRET)


def _cache_fresh(path: str) -> bool:
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) < CACHE_TTL_SECONDS


def _format_price(price) -> str:
    if price is None or price == "":
        return ""
    s = str(price).strip()
    s = re.sub(r"<[^>]+>", "", s).replace("&nbsp;", " ").strip()
    try:
        num = float(re.sub(r"[^0-9.]", "", s.split("-")[0].strip()) or 0)
        if num <= 0:
            return s
        return f"{int(num):,}".replace(",", "٬") + " تومان"
    except Exception:
        return s


def _stars(rating: float) -> str:
    """نمایش ستاره از روی میانگین"""
    try:
        r = float(rating)
    except Exception:
        return ""
    full = int(round(r))
    full = max(0, min(5, full))
    return "⭐" * full + "☆" * (5 - full) + f" ({r:.1f})"


def _variation_label(variation: Dict) -> str:
    attrs = variation.get("attributes") or []
    parts = [str(a.get("option") or a.get("name") or "") for a in attrs if a.get("option") or a.get("name")]
    if parts:
        return " / ".join(parts)
    return variation.get("sku") or "تنوع"


def fetch_variations(product_id: int) -> List[Dict]:
    url = f"{WC_URL.rstrip('/')}/wp-json/wc/v3/products/{product_id}/variations"
    variations = []
    page = 1
    while True:
        try:
            resp = requests.get(
                url,
                params={"per_page": 100, "page": page, "status": "publish"},
                auth=_auth(), timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print(f"خطا در تنوع محصول {product_id}:", e)
            break
        if not batch:
            break
        for v in batch:
            price = v.get("price") or v.get("regular_price") or ""
            variations.append({
                "id": v.get("id"),
                "label": _variation_label(v),
                "price": str(price) if price else "",
                "sku": v.get("sku") or "",
                "in_stock": v.get("stock_status") == "instock",
            })
        if len(batch) < 100:
            break
        page += 1
    return variations


def fetch_categories() -> List[Dict]:
    if not WC_KEY or not WC_SECRET:
        return []
    cats = []
    page = 1
    base = WC_URL.rstrip("/") + "/wp-json/wc/v3/products/categories"
    while True:
        try:
            resp = requests.get(
                base,
                params={"per_page": 100, "page": page, "hide_empty": True},
                auth=_auth(), timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print("خطا در دسته‌بندی‌ها:", e)
            break
        if not batch:
            break
        for c in batch:
            # رد کردن uncategorized
            slug = (c.get("slug") or "").lower()
            if slug in ("uncategorized", "بدون-دسته", "without-category"):
                continue
            cats.append({
                "id": c.get("id"),
                "name": c.get("name") or "",
                "slug": c.get("slug") or "",
                "count": c.get("count") or 0,
                "parent": c.get("parent") or 0,
            })
        if len(batch) < 100:
            break
        page += 1
    cats.sort(key=lambda x: (-x["count"], x["name"]))
    print(f"{len(cats)} دسته‌بندی دریافت شد.")
    return cats


def fetch_from_woocommerce() -> List[Dict]:
    if not WC_KEY or not WC_SECRET:
        print("WC_KEY یا WC_SECRET تنظیم نشده.")
        return []

    products: List[Dict] = []
    page = 1
    per_page = 100
    base = WC_URL.rstrip("/") + "/wp-json/wc/v3/products"

    while True:
        try:
            resp = requests.get(
                base,
                params={"per_page": per_page, "page": page, "status": "publish"},
                auth=_auth(), timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print(f"خطا در محصولات صفحه {page}:", e)
            break
        if not batch:
            break

        for item in batch:
            name = item.get("name") or ""
            price = item.get("price") or item.get("regular_price") or ""
            ptype = item.get("type") or "simple"
            short_desc = re.sub(r"<[^>]+", "", item.get("short_description") or "").strip()
            short_desc = re.sub(r"<[^>]+>", "", item.get("short_description") or "").strip()
            if len(short_desc) > 120:
                short_desc = short_desc[:117] + "..."

            cats = [
                {"id": c.get("id"), "name": c.get("name"), "slug": c.get("slug")}
                for c in (item.get("categories") or [])
            ]

            try:
                avg = float(item.get("average_rating") or 0)
            except Exception:
                avg = 0.0
            try:
                rcount = int(item.get("rating_count") or 0)
            except Exception:
                rcount = 0

            variations = []
            if ptype == "variable":
                variations = fetch_variations(item.get("id"))

            products.append({
                "id": item.get("id"),
                "name": name,
                "url": item.get("permalink") or f"{SITE_URL}/?p={item.get('id')}",
                "price": str(price) if price else "",
                "sku": item.get("sku") or "",
                "type": ptype,
                "short_description": short_desc,
                "in_stock": item.get("stock_status") == "instock",
                "variations": variations,
                "average_rating": avg,
                "rating_count": rcount,
                "categories": cats,
            })

        if len(batch) < per_page:
            break
        page += 1

    print(f"{len(products)} محصول دریافت شد.")
    return products


def sync_products(force: bool = False) -> List[Dict]:
    if not force and _cache_fresh(PRODUCTS_CACHE):
        return load_products_from_file()
    products = fetch_from_woocommerce()
    if products:
        save_json(PRODUCTS_CACHE, products)
        return products
    return load_products_from_file()


def sync_categories(force: bool = False) -> List[Dict]:
    if not force and _cache_fresh(CATEGORIES_CACHE):
        return load_categories()
    cats = fetch_categories()
    if cats:
        save_json(CATEGORIES_CACHE, cats)
        return cats
    return load_categories()


def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_products_from_file() -> List[Dict]:
    if not os.path.exists(PRODUCTS_CACHE):
        return []
    with open(PRODUCTS_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_products() -> List[Dict]:
    return sync_products(force=False)


def load_categories() -> List[Dict]:
    if not os.path.exists(CATEGORIES_CACHE):
        return []
    with open(CATEGORIES_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_categories() -> List[Dict]:
    return sync_categories(force=False)


def get_top_rated(limit: int = 8) -> List[Dict]:
    """محبوب‌ترین‌ها بر اساس میانگین ستاره و تعداد نظر"""
    products = load_products()
    rated = [p for p in products if (p.get("rating_count") or 0) > 0 and (p.get("average_rating") or 0) > 0]
    rated.sort(
        key=lambda p: (float(p.get("average_rating") or 0), int(p.get("rating_count") or 0)),
        reverse=True,
    )
    return rated[:limit]


def get_by_category(category_id: int, limit: int = 10) -> List[Dict]:
    products = load_products()
    matched = []
    for p in products:
        for c in p.get("categories") or []:
            if c.get("id") == category_id:
                matched.append(p)
                break
    # مرتب‌سازی: امتیاز بالاتر اول
    matched.sort(
        key=lambda p: (float(p.get("average_rating") or 0), int(p.get("rating_count") or 0)),
        reverse=True,
    )
    return matched[:limit]


def find_category_by_name(name: str) -> Optional[Dict]:
    cats = get_categories()
    n = (name or "").strip().lower()
    for c in cats:
        if (c.get("name") or "").lower() == n:
            return c
    for c in cats:
        if n in (c.get("name") or "").lower():
            return c
    return None


def search_products(query: str, limit: int = 5) -> List[Dict]:
    products = load_products()
    q = (query or "").strip()
    if not products or not q:
        return []

    q_norm = q.lower()
    exact = []
    for p in products:
        if q_norm in (p.get("name") or "").lower():
            item = p.copy()
            item["_score"] = 100
            exact.append(item)
    if exact:
        exact.sort(key=lambda x: len(x.get("name", "")))
        return exact[:limit]

    names = [p.get("name", "") for p in products]
    cutoff = 80 if len(q) <= 3 else 70
    results = process.extract(q, names, scorer=fuzz.partial_ratio, limit=limit * 3, score_cutoff=cutoff)
    if not results:
        results = process.extract(q, names, scorer=fuzz.WRatio, limit=limit * 3, score_cutoff=cutoff)
    if not results:
        return []

    best = results[0][1]
    matched = []
    for name, score, idx in results:
        if score < best - 12:
            continue
        product = products[idx].copy()
        product["_score"] = score
        matched.append(product)
        if len(matched) >= limit:
            break
    return matched


def format_product_message(product: Dict) -> str:
    name = product.get("name", "محصول")
    lines = [f"🛍 {name}"]

    avg = product.get("average_rating") or 0
    rcount = product.get("rating_count") or 0
    if avg and rcount:
        lines.append(f"{_stars(avg)} — {rcount} دیدگاه")

    desc = product.get("short_description") or ""
    if desc:
        lines.append(f"📝 {desc}")

    variations = product.get("variations") or []
    if variations:
        lines.append("📦 تنوع‌ها و قیمت:")
        for v in variations:
            label = v.get("label") or "تنوع"
            price = _format_price(v.get("price", ""))
            stock_note = " ❌ ناموجود" if not v.get("in_stock", True) else ""
            if price:
                lines.append(f"  • {label}: {price}{stock_note}")
            else:
                lines.append(f"  • {label}{stock_note}")
    else:
        price = _format_price(product.get("price", ""))
        if price:
            stock = "" if product.get("in_stock", True) else " (ناموجود)"
            lines.append(f"💰 قیمت: {price}{stock}")

    return "\n".join(lines)
