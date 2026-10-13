"""جستجو و قالب پیام محصول"""
import re
from typing import List, Dict, Tuple, Optional
from rapidfuzz import fuzz, process

from .products import (
    load_products,
    get_product_by_id,
    clean_name,
    to_fa_digits,
    _format_price,
    _variation_sort_key,
    _normalize_query,
    _extract_type_filter,
    _matches_type,
    ATTR_ORDER,
)

# چهار طبع — فقط تطبیق عبارت کامل (نه تک‌کلمه)
NATURE_EXACT = [
    {
        "key": "گرم و تر",
        "variants": [
            "گرم و تر", "گرم وتر", "گرموتر", "گرم‌وتر",
            "garm-va-tar", "garm va tar", "garmvatar",
        ],
    },
    {
        "key": "گرم و خشک",
        "variants": [
            "گرم و خشک", "گرم وخشک", "گرموخشک", "گرم‌و‌خشک",
            "garm-va-khoshk", "garm va khoshk", "garmvakhoshk",
        ],
    },
    {
        "key": "سرد و تر",
        "variants": [
            "سرد و تر", "سرد وتر", "سردوتر", "سرد‌وتر",
            "sard-va-tar", "sard va tar", "sardvatar",
        ],
    },
    {
        "key": "سرد و خشک",
        "variants": [
            "سرد و خشک", "سرد وخشک", "سردوخشک", "سرد‌و‌خشک",
            "sard-va-khoshk", "sard va khoshk", "sardvakhoshk",
        ],
    },
]


def _compact(s: str) -> str:
    s = (s or "").lower().replace("‌", "")
    s = s.replace("-", " ").replace("_", " ")
    s = re.sub(r"\s+", "", s)
    return s


def _detect_exact_nature(q: str) -> Optional[dict]:
    """اگر کوئری یکی از ۴ طبع کامل باشد، همان را برگردان."""
    qc = _compact(q)
    # حذف پیشوند نوع محصول برای تشخیص طبع
    for prefix in ("عطر", "روغن", "حرز", "دمنوش", "عود"):
        qc2 = _compact(re.sub(prefix, " ", q, flags=re.I))
        for item in NATURE_EXACT:
            for v in item["variants"]:
                if _compact(v) == qc or _compact(v) == qc2 or _compact(v) in qc or _compact(v) in qc2:
                    # فقط اگر عبارت طبع واقعاً در کوئری باشد (نه تصادفی)
                    if _compact(v) in qc or _compact(v) in qc2:
                        return item
    for item in NATURE_EXACT:
        for v in item["variants"]:
            if _compact(v) == qc or (_compact(v) in qc and len(_compact(v)) >= 5):
                return item
    return None


def _product_nature_blob(p: Dict) -> str:
    """فقط طبیعت ویژگی‌ها + برچسب‌ها (نه کل توضیحات محصول)."""
    parts = []
    for a in p.get("attributes") or []:
        an = (a.get("name") or "").lower()
        if "طبیعت" in an:
            parts.append(a.get("value") or "")
    for t in p.get("tags") or []:
        if isinstance(t, dict):
            parts.append(t.get("name") or "")
            parts.append(t.get("slug") or "")
        else:
            parts.append(str(t))
    # بعضی فروشگاه‌ها طبع را در دسته‌بندی هم می‌گذارند
    for c in p.get("categories") or []:
        cn = (c.get("name") or "") + " " + (c.get("slug") or "")
        if any(x in cn for x in ("گرم", "سرد", "garm", "sard")):
            parts.append(cn)
    return " ".join(parts).lower()


def _matches_exact_nature(p: Dict, nature_item: dict) -> bool:
    blob = _product_nature_blob(p)
    if not blob.strip():
        return False
    bc = _compact(blob)
    for v in nature_item["variants"]:
        vc = _compact(v)
        if not vc:
            continue
        # عبارت کامل داخل متن طبیعت/برچسب
        if vc in bc:
            return True
        if v.lower() in blob:
            return True
    return False


def search_products(query: str, limit: int = 20, mode: str = "name") -> List[Dict]:
    """
    mode=name   → فقط در نام محصول
    mode=feature → طبیعت، خواص، ترکیبات و سایر ویژگی‌ها (+ نوع محصول)
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

    if mode == "name":
        exact = []
        for p in products:
            name = (p.get("name") or "").lower()
            cname = clean_name(p.get("name") or "").lower()
            if q in name or q in cname:
                item = p.copy()
                item["_score"] = 100 if q == cname or q == name else 90
                exact.append(item)
        if exact:
            exact.sort(key=lambda x: (-x.get("_score", 0), len(x.get("name") or "")))
            return exact[:limit]

        names = [p.get("name", "") for p in products]
        cutoff = 80 if len(q) <= 3 else 72
        results = process.extract(
            q, names, scorer=fuzz.partial_ratio, limit=limit * 2, score_cutoff=cutoff,
        )
        if not results:
            return []
        best = results[0][1]
        matched = []
        for name, score, idx in results:
            if score < best - 10:
                continue
            product = products[idx].copy()
            product["_score"] = score
            matched.append(product)
            if len(matched) >= limit:
                break
        return matched

    # ——— حالت ویژگی —————————
    nature_item = _detect_exact_nature(q)
    type_kw, q2 = _extract_type_filter(q)

    # اگر طبع تشخیص داده شد، کلمات طبع را از باقیمانده حذف کن
    if nature_item:
        rest = q2
        for v in nature_item["variants"]:
            rest = rest.replace(v, " ")
            rest = rest.replace(v.replace(" ", ""), " ")
        # حذف تکه‌های گرم/سرد/تر/خشک فقط وقتی طبع کامل تشخیص شده
        rest = re.sub(r"\b(گرم|سرد|تر|خشک)\b", " ", rest)
        q2 = re.sub(r"\s+", " ", rest).strip()

    tokens = [t for t in re.split(r"[\s،,]+", q2) if len(t) >= 2 and t not in ("و",)]

    scored = []
    for p in products:
        if type_kw and not _matches_type(p, type_kw):
            continue

        if nature_item:
            if not _matches_exact_nature(p, nature_item):
                continue
            # طبع به‌تنهایی کافی است
            if not tokens:
                item = p.copy()
                item["_score"] = 80
                scored.append(item)
                continue

        attr_blob = " ".join(
            f"{a.get('name','')} {a.get('value','')}" for a in (p.get("attributes") or [])
        ).lower()
        cat_blob = " ".join(
            f"{(c.get('name') or '')} {(c.get('slug') or '')}" for c in (p.get("categories") or [])
        ).lower()
        tag_blob = " ".join(
            f"{(t.get('name') or '')} {(t.get('slug') or '')}" if isinstance(t, dict) else str(t)
            for t in (p.get("tags") or [])
        ).lower()
        feature_blob = (attr_blob + " " + cat_blob + " " + tag_blob).strip()

        if not tokens and not nature_item and not type_kw:
            continue

        if not tokens and (nature_item or type_kw):
            item = p.copy()
            item["_score"] = 70
            scored.append(item)
            continue

        score = 0
        full = q2 if q2 else q
        if full and full in feature_blob:
            score += 40
        for t in tokens:
            if t in feature_blob:
                score += 20
            elif fuzz.partial_ratio(t, feature_blob) >= 85:
                score += 10
        if score <= 0:
            continue
        item = p.copy()
        item["_score"] = score + (20 if nature_item else 0)
        scored.append(item)

    scored.sort(key=lambda x: (-x.get("_score", 0), len(x.get("name") or "")))
    return scored[:limit]


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


def format_product_message(product: Dict, reviews: List[Dict] = None) -> str:
    name = clean_name(product.get("name", "محصول"))
    lines = []

    avg = product.get("average_rating") or 0
    rcount = product.get("rating_count") or 0
    try:
        avg_f = float(avg)
    except Exception:
        avg_f = 0

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

    if reviews:
        iv = format_reviews_body(product, reviews)
        lines.append("")
        lines.append(iv)
    elif avg_f > 0 and rcount:
        lines.append("")
        lines.append(
            f"⭐ {to_fa_digits(f'{avg_f:.1f}')} از {to_fa_digits(rcount)} دیدگاه"
        )

    return "\n".join(lines)


def format_reviews_body(product: Dict, reviews: List[Dict]) -> str:
    name = clean_name(product.get("name") or "محصول")
    avg = product.get("average_rating") or 0
    rcount = product.get("rating_count") or len(reviews)
    try:
        avg_f = float(avg)
    except Exception:
        avg_f = 0

    title = f"⭐ {to_fa_digits(f'{avg_f:.1f}')} از {to_fa_digits(rcount)} دیدگاه"
    body_parts = [f"دیدگاه‌های {name}", ""]
    for i, r in enumerate(reviews, 1):
        stars = "⭐" * max(0, min(5, r.get("rating") or 0))
        reviewer = r.get("reviewer") or "خریدار"
        date = r.get("date") or ""
        header = f"{to_fa_digits(i)}. {reviewer}"
        if stars:
            header += f"  {stars}"
        if date:
            header += f"  ({to_fa_digits(date)})"
        body_parts.append(header)
        body_parts.append(r.get("review") or "")
        body_parts.append("────────")
    if body_parts and body_parts[-1] == "────────":
        body_parts.pop()
    body = "\n".join(body_parts)
    return f"```[{title}]\n{body}\n```\n"
