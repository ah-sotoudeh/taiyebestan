"""
ماژول جستجو و مدیریت محصولات طیبستان
با همگام‌سازی خودکار از WooCommerce REST API + تنوع‌ها
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


def _auth():
    return HTTPBasicAuth(WC_KEY, WC_SECRET)


def _cache_is_fresh() -> bool:
    if not os.path.exists(PRODUCTS_CACHE):
        return False
    age = time.time() - os.path.getmtime(PRODUCTS_CACHE)
    return age < CACHE_TTL_SECONDS


def _format_price(price) -> str:
    if price is None or price == "":
        return ""
    s = str(price).strip()
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").strip()
    try:
        num = float(re.sub(r"[^0-9.]", "", s.split("-")[0].strip()) or 0)
        if num <= 0:
            return s
        return f"{int(num):,}".replace(",", "٬") + " تومان"
    except Exception:
        return s


def _variation_label(variation: Dict) -> str:
    """برچسب تنوع از attributes (مثلاً ۵ میلی‌لیتر)"""
    attrs = variation.get("attributes") or []
    parts = []
    for a in attrs:
        opt = a.get("option") or a.get("name") or ""
        if opt:
            parts.append(str(opt))
    if parts:
        return " / ".join(parts)
    sku = variation.get("sku") or ""
    if sku:
        return sku
    return "تنوع"


def fetch_variations(product_id: int) -> List[Dict]:
    """دریافت همه تنوع‌های یک محصول متغیر"""
    url = f"{WC_URL.rstrip('/')}/wp-json/wc/v3/products/{product_id}/variations"
    variations = []
    page = 1
    while True:
        try:
            resp = requests.get(
                url,
                params={"per_page": 100, "page": page, "status": "publish"},
                auth=_auth(),
                timeout=30,
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
            stock = v.get("stock_status", "")
            variations.append({
                "id": v.get("id"),
                "label": _variation_label(v),
                "price": str(price) if price else "",
                "sku": v.get("sku") or "",
                "in_stock": stock == "instock",
            })
        if len(batch) < 100:
            break
        page += 1
    return variations


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
                auth=_auth(),
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
            ptype = item.get("type") or "simple"
            short_desc = item.get("short_description") or ""
            short_desc = re.sub(r"<[^>]+>", "", short_desc).strip()
            if len(short_desc) > 120:
                short_desc = short_desc[:117] + "..."

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
    products = load_products()
    q = (query or "").strip()
    if not products or not q:
        return []

    q_norm = q.lower()

    exact = []
    for p in products:
        name = p.get("name") or ""
        if q_norm in name.lower():
            item = p.copy()
            item["_score"] = 100
            exact.append(item)

    if exact:
        exact.sort(key=lambda x: len(x.get("name", "")))
        return exact[:limit]

    names = [p.get("name", "") for p in products]
    cutoff = 80 if len(q) <= 3 else 70

    results = process.extract(
        q, names, scorer=fuzz.partial_ratio, limit=limit * 3, score_cutoff=cutoff,
    )
    if not results:
        results = process.extract(
            q, names, scorer=fuzz.WRatio, limit=limit * 3, score_cutoff=cutoff,
        )
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
    """نام + توضیح کوتاه + همه تنوع‌ها با قیمت"""
    name = product.get("name", "محصول")
    lines = [f"🛍 {name}"]

    desc = product.get("short_description") or ""
    if desc:
        lines.append(f"📝 {desc}")

    variations = product.get("variations") or []
    if variations:
        lines.append("📦 تنوع‌ها و قیمت:")
        for v in variations:
            label = v.get("label") or "تنوع"
            price = _format_price(v.get("price", ""))
            stock = "✅" if v.get("in_stock", True) else "❌ ناموجود"
            if price:
                lines.append(f"  • {label}: {price} {stock if not v.get('in_stock', True) else ''}".rstrip())
            else:
                lines.append(f"  • {label} {stock}")
    else:
        price = _format_price(product.get("price", ""))
        if price:
            stock = "" if product.get("in_stock", True) else " (ناموجود)"
            lines.append(f"💰 قیمت: {price}{stock}")

    return "\n".join(lines)
