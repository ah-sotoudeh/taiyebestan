"""دریافت دیدگاه‌ها و قالب Instant View بله"""
import re
from typing import List, Dict
import requests
from requests.auth import HTTPBasicAuth

from .config import WC_URL, WC_KEY, WC_SECRET
from .products import clean_name, to_fa_digits
from .jalali import to_jalali_str


def fetch_product_reviews(product_id: int, limit: int = 50) -> List[Dict]:
    if not WC_KEY or not WC_SECRET:
        return []
    url = f"{WC_URL.rstrip('/')}/wp-json/wc/v3/products/reviews"
    reviews = []
    page = 1
    while len(reviews) < limit:
        try:
            resp = requests.get(
                url,
                params={
                    "product": product_id,
                    "per_page": min(100, limit),
                    "page": page,
                    "status": "approved",
                },
                auth=HTTPBasicAuth(WC_KEY, WC_SECRET),
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print(f"خطا در دریافت دیدگاه‌های محصول {product_id}:", e)
            break
        if not batch:
            break
        for r in batch:
            text = re.sub(r"<[^>]+>", "", r.get("review") or "").strip()
            text = re.sub(r"\s+", " ", text)
            if not text:
                continue
            raw_date = r.get("date_created") or ""
            reviews.append({
                "reviewer": r.get("reviewer") or r.get("name") or "خریدار",
                "rating": int(r.get("rating") or 0),
                "review": text,
                "date": to_jalali_str(raw_date),
            })
        if len(batch) < 100:
            break
        page += 1
    return reviews[:limit]


def format_reviews_instant_view(product: Dict, reviews: List[Dict]) -> str:
    name = clean_name(product.get("name") or "محصول")
    avg = product.get("average_rating") or 0
    rcount = product.get("rating_count") or len(reviews)
    try:
        avg_f = float(avg)
    except Exception:
        avg_f = 0

    title = f"دیدگاه‌های {name}"
    if avg_f and rcount:
        title += f" — ⭐ {to_fa_digits(f'{avg_f:.1f}')} از {to_fa_digits(rcount)} نظر"

    body_parts = []
    for i, r in enumerate(reviews, 1):
        stars = "⭐" * max(0, min(5, r.get("rating") or 0))
        reviewer = r.get("reviewer") or "خریدار"
        date = r.get("date") or ""
        header = f"{to_fa_digits(i)}. {reviewer}"
        if stars:
            header += f"  {stars}"
        if date:
            header += f"  ({date})"
        body_parts.append(header)
        body_parts.append(r.get("review") or "")
        body_parts.append("────────")

    if body_parts and body_parts[-1] == "────────":
        body_parts.pop()

    body = "\n".join(body_parts)
    return f"```[{title}]\n{body}\n```"
