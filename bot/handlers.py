"""
هندلرهای پیام ربات طیبستان
مینی‌اپ روی دامنه اصلی: https://taiyebestan.ir
"""
from bale import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from .config import WELCOME_MESSAGE, SITE_URL
from .products import search_products, format_product_message


def get_shop_keyboard() -> InlineKeyboardMarkup:
    """دکمه مینی‌اپ روی دامنه اصلی سایت"""
    kb = InlineKeyboardMarkup()
    # مینی‌اپ بله — همان سایت اصلی
    kb.add(
        InlineKeyboardButton(
            text="🛒 فروشگاه طیبستان (مینی‌اپ)",
            web_app=WebAppInfo(url=SITE_URL),
        )
    )
    # لینک معمولی در مرورگر
    kb.add(
        InlineKeyboardButton(
            text="🌐 باز کردن در مرورگر",
            url=SITE_URL,
        )
    )
    return kb


async def handle_start(message: Message):
    name = getattr(message.author, "first_name", None) or "کاربر"
    text = WELCOME_MESSAGE.format(name=name)
    await message.reply(text, components=get_shop_keyboard())


async def handle_text(message: Message):
    query = (getattr(message, "content", None) or "").strip()
    if not query:
        return

    if query.startswith("/"):
        return

    results = search_products(query, limit=5)

    if not results:
        await message.reply(
            f"متأسفانه محصولی با عنوان «{query}» پیدا نشد 😕\n"
            "لطفاً نام دیگری امتحان کنید یا از دکمه فروشگاه استفاده کنید.",
            components=get_shop_keyboard(),
        )
        return

    reply_parts = [f"🔍 نتایج جستجو برای «{query}»:\n"]
    for p in results:
        reply_parts.append(format_product_message(p))
        reply_parts.append("")

    await message.reply("\n".join(reply_parts), components=get_shop_keyboard())
