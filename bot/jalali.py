"""تبدیل تاریخ میلادی به شمسی"""


def gregorian_to_jalali(gy: int, gm: int, gd: int):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def to_jalali_str(date_str: str) -> str:
    """
    ورودی: 2024-03-12 یا 2024-03-12T10:00:00
    خروجی: ۱۴۰۲/۱۲/۲۲
    """
    if not date_str:
        return ""
    part = date_str[:10]
    try:
        gy, gm, gd = [int(x) for x in part.split("-")]
        jy, jm, jd = gregorian_to_jalali(gy, gm, gd)
        s = f"{jy:04d}/{jm:02d}/{jd:02d}"
        # ارقام فارسی
        fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        return s.translate(fa)
    except Exception:
        return date_str
