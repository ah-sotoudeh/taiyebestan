"""
ماژول جستجو و مدیریت محصولات طیبستان
"""
import json
import os
import time
import re
from typing import List, Dict, Optional, Tuple
from rapidfuzz import fuzz, process
import requests
from requests.auth import HTTPBasicAuth

from .config import (
    PRODUCTS_CACHE, CATEGORIES_CACHE, SITE_URL,
    WC_URL, WC_KEY, WC_SECRET,
)

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
PAGE_SIZE = 8

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

ATTR_ORDER = [
    ("طبیعت", "🌱"),
    ("ستاره", "⭐️"),
    ("مزاج", "⭐️"),
    ("شروع مصرف", "🗓️"),
    ("ترکیبات", "🧪"),
    ("خلوص", "💧"),
    ("خواص درمانی", "✅"),
    ("خواص", "✅"),
    ("احساس", "❤️"),
]

# کلیدواژه‌های نوع محصول در نام / دسته
TYPE_KEYWORDS = [
    "عطر", "روغن", "حرز", "دمنوش", "بخور", "عود",
    "اسپری", "کرم", "شامپو", "صابون", "آبزن", "ملکه",
]

# عبارات رایج طبیعت (مزاج)
NATURE_PHRASES = [
    "گرم و تر", "گرم وتر", "گرم‌وتر",
    "گرم و خشک", "گرم وخشک", "گرم‌و‌خشک",
    "سرد و تر", "سرد وتر", "سرد‌وتر",
    "سرد و خشک", "سرد وخشک", "سرد‌و‌خشک",
    "درجه اول", "درجه دوم", "درجه سوم",
]


def to_fa_digits(value) -> str:
    return str(value).translate(_FA_DIGITS)


def _auth():
    return HTTPBasicAuth(WC_KEY, WC_SECRET)


def _cache_fresh(path: str) -> bool:
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) < CACHE_TTL_SECONDS


def clean_name(name: str) -> str:
    if not name:
        return "محصول"
    n = re.sub(r"\s*طیبستان\s*", " ", name)
    n = re.sub(r"\s+", " ", n).strip(" -–|،,")
    return n or name.strip()


def _strip_emoji(text: str) -> str:
    if not text:
        return ""
    return re.sub(
        r"[🌱🌿⭐️⭐☆📅🗓️🧪✅✔️❤️❤✨💧🍃🚫🛍📦•]+\s*",
        "",
        text,
    ).strip()


def _format_price(price) -> str:
    if price is None or price == "":
        return ""
    s = str(price).strip()
    s = re.sub(r"<[^>]+>", "", s).replace("&nbsp;", " ").strip()
    try:
        num = float(re.sub(r"[^0-9.]", "", s.split("-")[0].strip()) or 0)
        if num <= 0:
            return to_fa_digits(s)
        formatted = f"{int(num):,}".replace(",", "٬") + " تومان"
        return to_fa_digits(formatted)
    except Exception:
        return to_fa_digits(s)


def _parse_attributes(item: Dict) -> List[Dict]:
    result = []
    for a in item.get("attributes") or []:
        if a.get("variation"):
            continue
        name = _strip_emoji((a.get("name") or "").strip())
        options = a.get("options") or []
        if not name or not options:
            continue
        value = "، ".join(str(o) for o in options if o)
        value = re.sub(r"<[^>]+>", "", value).strip()
        if value:
            result.append({"name": name, "value": value})
    return result


def _variation_label(variation: Dict) -> str:
    attrs = variation.get("attributes") or []
    parts = [str(a.get("option") or a.get("name") or "") for a in attrs if a.get("option") or a.get("name")]
    if parts:
        return " / ".join(parts)
    return variation.get("sku") or "تنوع"


def _variation_sort_key(v: Dict) -> float:
    label = v.get("label") or ""
    m = re.search(r"(\d+(?:[./]\d+)?)", label.replace("/", "."))
    if m:
        try:
            return float(m.group(1).replace("/", "."))
        except ValueError:
            pass
    return 9999


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
    variations.sort(key=_variation_sort_key)
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
                "in_stock": item.get("stock_status") == "instock",
                "variations": variations,
                "average_rating": avg,
                "rating_count": rcount,
                "categories": cats,
                "attributes": _parse_attributes(item),
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


def get_product_by_id(product_id: int) -> Optional[Dict]:
    for p in load_products():
        if p.get("id") == product_id:
            return p
    return None


def _bayesian_score(avg: float, count: int, global_mean: float, m: float = 10.0) -> float:
    v = float(count)
    R = float(avg)
    C = float(global_mean)
    return (v / (v + m)) * R + (m / (v + m)) * C


def get_top_rated(limit: int = 50) -> List[Dict]:
    products = load_products()
    rated = [
        p for p in products
        if (p.get("rating_count") or 0) > 0 and (p.get("average_rating") or 0) > 0
    ]
    if not rated:
        return []
    total_r = sum(float(p.get("average_rating") or 0) * int(p.get("rating_count") or 0) for p in rated)
    total_c = sum(int(p.get("rating_count") or 0) for p in rated)
    global_mean = (total_r / total_c) if total_c else 4.0
    for p in rated:
        p["_popularity"] = _bayesian_score(
            float(p.get("average_rating") or 0),
            int(p.get("rating_count") or 0),
            global_mean,
            m=10.0,
        )
    rated.sort(key=lambda p: p.get("_popularity", 0), reverse=True)
    return rated[:limit]


def get_by_category(category_id: int, limit: int = 100) -> List[Dict]:
    products = load_products()
    matched = []
    for p in products:
        for c in p.get("categories") or []:
            if c.get("id") == category_id:
                matched.append(p)
                break
    rated = [p for p in matched if (p.get("rating_count") or 0) > 0]
    if rated:
        total_r = sum(float(p.get("average_rating") or 0) * int(p.get("rating_count") or 0) for p in rated)
        total_c = sum(int(p.get("rating_count") or 0) for p in rated)
        global_mean = (total_r / total_c) if total_c else 4.0
        for p in matched:
            avg = float(p.get("average_rating") or 0)
            cnt = int(p.get("rating_count") or 0)
            p["_popularity"] = _bayesian_score(avg, cnt, global_mean, m=5.0) if cnt else 0
        matched.sort(key=lambda p: p.get("_popularity", 0), reverse=True)
    else:
        matched.sort(key=lambda p: clean_name(p.get("name") or ""))
    return matched[:limit]


def paginate(items: List, page: int, page_size: int = PAGE_SIZE) -> Tuple[List, int, int]:
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return items[start:start + page_size], page, total_pages


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


def _product_search_blob(p: Dict) -> str:
    """متن یکپارچه برای جستجو: نام + دسته + همه ویژگی‌ها"""
    parts = [
        p.get("name") or "",
        clean_name(p.get("name") or ""),
    ]
    for c in p.get("categories") or []:
        parts.append(c.get("name") or "")
    for a in p.get("attributes") or []:
        parts.append(a.get("name") or "")
        parts.append(a.get("value") or "")
    return " ".join(parts).lower()


def _normalize_query(q: str) -> str:
    q = q.strip().lstrip("/").lower()
    q = q.replace("‌", "")  # حذف نیم‌فاصله
    q = re.sub(r"\s+", " ", q)
    return q


def _extract_type_filter(q: str) -> Tuple[Optional[str], str]:
    """اگر نوع محصول در کوئری بود جدا کن (عطر / روغن / …)"""
    for t in TYPE_KEYWORDS:
        if t in q:
            rest = q.replace(t, " ").strip()
            rest = re.sub(r"\s+", " ", rest)
            return t, rest
    return None, q


def _extract_nature_phrases(q: str) -> Tuple[List[str], str]:
    """عبارات طبیعت را پیدا کن"""
    found = []
    rest = q
    # اول عبارات چندکلمه‌ای
    for phrase in sorted(NATURE_PHRASES, key=len, reverse=True):
        norm_phrase = phrase.replace("‌", "").replace(" ", "")
        norm_rest = rest.replace("‌", "").replace(" ", "")
        if phrase in rest or norm_phrase in norm_rest:
            found.append(phrase.replace("‌", " ").replace("  ", " "))
            rest = rest.replace(phrase, " ")
            # حالت بدون فاصله
            for variant in (phrase, phrase.replace(" ", ""), phrase.replace(" و ", " و")):
                rest = rest.replace(variant, " ")
    rest = re.sub(r"\s+", " ", rest).strip()
    return found, rest


def _matches_type(p: Dict, type_kw: str) -> bool:
    blob = _product_search_blob(p)
    return type_kw in blob


def _matches_nature(p: Dict, phrases: List[str]) -> bool:
    if not phrases:
        return True
    # فقط روی ویژگی طبیعت (و در صورت نبود، کل blob)
    nature_vals = []
    for a in p.get("attributes") or []:
        an = (a.get("name") or "").lower()
        if "طبیعت" in an or "مزاج" in an:
            nature_vals.append((a.get("value") or "").lower())
    target = " ".join(nature_vals) if nature_vals else _product_search_blob(p)
    target_compact = target.replace(" ", "").replace("‌", "")
    for ph in phrases:
        ph_l = ph.lower()
        ph_c = ph_l.replace(" ", "").replace("‌", "")
        if ph_l in target or ph_c in target_compact:
            return True
        # گرم + تر جدا
        tokens = [t for t in re.split(r"\s+و\s+|\s+", ph_l) if t and t != "و"]
        if tokens and all(t in target for t in tokens):
            return True
    return False


def _score_product(p: Dict, tokens: List[str], full_q: str) -> int:
    """امتیاز تطبیق روی نام و ویژگی‌ها (خواص، ترکیبات، …)"""
    if not tokens and not full_q:
        return 50
    blob = _product_search_blob(p)
    name = (p.get("name") or "").lower()
    score = 0

    if full_q and full_q in blob:
        score += 40
    if full_q and full_q in name:
        score += 30

    for t in tokens:
        if len(t) < 2:
            continue
        if t in name:
            score += 25
        elif t in blob:
            score += 15
        else:
            # fuzzy سبک روی نام
            if fuzz.partial_ratio(t, name) >= 80:
                score += 10

    return score


def search_products(query: str, limit: int = 20) -> List[Dict]:
    """
    جستجوی هوشمند:
    - نام محصول
    - طبیعت (گرم و تر، …)
    - خواص درمانی و بقیه ویژگی‌ها
    - نوع: عطر / روغن / حرز / …
    """
    products = load_products()
    q_raw = (query or "").strip()
    if not products or not q_raw:
        return []

    m = re.match(r"^/?p?(\d+)$", q_raw, re.I)
    if m:
        p = get_product_by_id(int(m.group(1)))
        return [p] if p else []

    q = _normalize_query(q_raw)
    type_kw, q = _extract_type_filter(q)
    nature_phrases, q = _extract_nature_phrases(q)
    tokens = [t for t in re.split(r"[\s،,]+", q) if len(t) >= 2]

    scored = []
    for p in products:
        if type_kw and not _matches_type(p, type_kw):
            continue
        if nature_phrases and not _matches_nature(p, nature_phrases):
            continue

        # اگر فقط نوع یا طبیعت بود، همهٔ فیلترشده را بیاور
        if not tokens and (type_kw or nature_phrases):
            item = p.copy()
            item["_score"] = 60
            scored.append(item)
            continue

        if not tokens and not type_kw and not nature_phrases:
            continue

        sc = _score_product(p, tokens, q)
        if sc <= 0:
            continue
        item = p.copy()
        item["_score"] = sc
        scored.append(item)

    if scored:
        scored.sort(key=lambda x: (-x.get("_score", 0), len(x.get("name") or "")))
        return scored[:limit]

    # fallback: fuzzy فقط روی نام (رفتار قبلی)
    names = [p.get("name", "") for p in products]
    cutoff = 80 if len(q_raw) <= 3 else 70
    results = process.extract(
        q_raw, names, scorer=fuzz.partial_ratio, limit=limit * 2, score_cutoff=cutoff,
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


def _ordered_attributes(attrs: List[Dict]) -> List[Tuple[str, str, str]]:
    used = set()
    ordered = []

    def match_key(attr_name: str, key: str) -> bool:
        an = attr_name.replace(" و ", " ")
        return key in an

    for key, emo in ATTR_ORDER:
        for a in attrs:
            an = a.get("name") or ""
            if an in used:
                continue
            if match_key(an, key):
                label = key if key != "مزاج" else "ستاره"
                if key == "خواص":
                    label = "خواص درمانی"
                if "خلوص" in an:
                    label = "خلوص"
                ordered.append((emo, label, a.get("value") or ""))
                used.add(an)
                break

    for a in attrs:
        an = a.get("name") or ""
        if an not in used:
            ordered.append(("•", an, a.get("value") or ""))
            used.add(an)

    return ordered


def format_product_message(product: Dict) -> str:
    name = clean_name(product.get("name", "محصول"))
    lines = []

    avg = product.get("average_rating") or 0
    rcount = product.get("rating_count") or 0
    try:
        avg_f = float(avg)
    except Exception:
        avg_f = 0

    if avg_f > 0 and rcount:
        lines.append(
            f"🛍 *{name}*  ⭐ {to_fa_digits(f'{avg_f:.1f}')}  (از {to_fa_digits(rcount)} دیدگاه)"
        )
    elif avg_f > 0:
        lines.append(f"🛍 *{name}*  ⭐ {to_fa_digits(f'{avg_f:.1f}')}")
    else:
        lines.append(f"🛍 *{name}*")

    lines.append("")

    attrs = product.get("attributes") or []
    for emo, label, value in _ordered_attributes(attrs):
        if label in ("خواص درمانی", "احساس"):
            lines.append("")
        lines.append(f"{emo} *{label}:* {to_fa_digits(value)}")

    variations = list(product.get("variations") or [])
    if variations:
        variations = sorted(variations, key=_variation_sort_key)
        lines.append("")
        lines.append("📦 *تنوع‌ها و قیمت:*")
        for v in variations:
            vlabel = to_fa_digits(v.get("label") or "تنوع")
            price = _format_price(v.get("price", ""))
            stock_note = " ❌ ناموجود" if not v.get("in_stock", True) else ""
            if price:
                lines.append(f"• {vlabel}: {price}{stock_note}")
            else:
                lines.append(f"• {vlabel}{stock_note}")
    else:
        price = _format_price(product.get("price", ""))
        if price:
            stock = "" if product.get("in_stock", True) else " (ناموجود)"
            lines.append("")
            lines.append(f"💰 *قیمت:* {price}{stock}")

    return "\n".join(lines)
