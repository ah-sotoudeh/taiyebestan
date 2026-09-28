"""
ماژول جستجو و مدیریت محصولات طیبستان
با همگام‌سازی خودکار از WooCommerce REST API
"""
import json
import os
import time
from typing import List, Dict
from rapidfuzz import fuzz, process
import requests
from requests.auth import HTTPBasicAuth

from .config import PRODUCTS_CACHE, SITE_URL, WC_URL, WC_KEY, WC_SECRET

# هر چند ثانیه یک‌بار کش از API به‌روز شود (پیش‌فرض: ۱ ساعت)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


def _cache_is_fresh() -> bool:
    """آیا فایل کش هنوز تازه است؟"""
    if not os.path.exists(PRODUCTS_CACHE):
        return False
    age = time.time() - os.path.getmtime(PRODUCTS_CACHE)
    return age < CACHE_TTL_SECONDS


def fetch_from_woocommerce() -> List[Dict]:
    """
    دریافت همه محصولات منتشرشده از WooCommerce REST API
    و تبدیل به فرمت داخلی ربات.
    """
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
            # قیمت نمایشی
            price = item.get("price") or item.get("regular_price") or ""
            if item.get("type") == "variable" and not price:
                # برای محصولات متغیر، محدوده قیمت اگر موجود باشد
                price = item.get("price_html", "")  # HTML — بعداً ساده می‌کنیم
                # ساده‌سازی: فقط عدد خام اگر باشد
                if not price and item.get("meta_data"):
                    pass
            products.append({
                "id": item.get("id"),
                "name": name,
                "url": item.get("permalink") or f"{SITE_URL}/?p={item.get('id')}",
                "price": str(price) if price else "",
                "sku": item.get("sku") or "",
            })

        # اگر کمتر از per_page برگشت، صفحه آخر است
        if len(batch) < per_page:
            break
        page += 1

    print(f"{len(products)} محصول از ووکامرس دریافت شد.")
    return products


def sync_products(force: bool = False) -> List[Dict]:
    """
    اگر کش منقضی شده یا force=True، از API بگیر و ذخیره کن.
    در غیر این صورت از فایل بخوان.
    """
    if not force and _cache_is_fresh():
        return load_products_from_file()

    products = fetch_from_woocommerce()
    if products:
        save_products(products)
        return products

    # اگر API شکست خورد، حداقل فایل قبلی را برگردان
    return load_products_from_file()


def load_products_from_file() -> List[Dict]:
    """بارگذاری لیست محصولات از فایل JSON"""
    if not os.path.exists(PRODUCTS_CACHE):
        return []
    with open(PRODUCTS_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_products() -> List[Dict]:
    """بارگذاری با همگام‌سازی خودکار در صورت نیاز"""
    return sync_products(force=False)


def save_products(products: List[Dict]) -> None:
    """ذخیره لیست محصولات"""
    with open(PRODUCTS_CACHE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def search_products(query: str, limit: int = 5, score_cutoff: int = 50) -> List[Dict]:
    """
    جستجوی fuzzy روی نام محصولات.
    حتی با بخشی از نام هم نتیجه می‌دهد.
    قبل از جستجو در صورت نیاز کش را به‌روز می‌کند.
    """
    products = load_products()
    if not products or not query.strip():
        return []

    names = [p.get("name", "") for p in products]
    results = process.extract(
        query,
        names,
        scorer=fuzz.partial_ratio,
        limit=limit,
        score_cutoff=score_cutoff,
    )

    matched = []
    for name, score, idx in results:
        product = products[idx].copy()
        product["_score"] = score
        matched.append(product)
    return matched


def format_product_message(product: Dict) -> str:
    """فرمت پیام لینک محصول"""
    name = product.get("name", "محصول")
    url = product.get("url") or product.get("permalink") or f"{SITE_URL}/?s={name}"
    price = product.get("price", "")
    text = f"🛍 <b>{name}</b>\n"
    if price:
        text += f"💰 قیمت: {price}\n"
    text += f"🔗 <a href=\"{url}\">مشاهده و خرید</a>"
    return text
