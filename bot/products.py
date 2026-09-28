"""
ماژول جستجو و مدیریت محصولات طیبستان
"""
import json
import os
from typing import List, Dict, Optional
from rapidfuzz import fuzz, process

from .config import PRODUCTS_CACHE, SITE_URL


def load_products() -> List[Dict]:
    """بارگذاری لیست محصولات از فایل JSON"""
    if not os.path.exists(PRODUCTS_CACHE):
        return []
    with open(PRODUCTS_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_products(products: List[Dict]) -> None:
    """ذخیره لیست محصولات"""
    with open(PRODUCTS_CACHE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def search_products(query: str, limit: int = 5, score_cutoff: int = 50) -> List[Dict]:
    """
    جستجوی fuzzy روی نام محصولات.
    حتی با بخشی از نام هم نتیجه می‌دهد.
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
    text += f"🔗 <a href=\"{url}\">{مشاهده و خرید</a>"
    return text


# نمونه ساختار products.json:
# [
#   {"name": "عطر بهارنارنج طیبستان", "url": "https://taiyebestan.ir/product/bahar-narenj-perfume/", "price": "۱۳۰٬۰۰۰"},
#   ...
# ]
