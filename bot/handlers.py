"""
هندلرهای پیام ربات طیبستان
"""
from bale import Message, InlineKeyboardMarkup, InlineKeyboardButton

from .config import WELCOME_MESSAGE, SITE_URL
from .products import search_products, format_product_message


def get_shop_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            text="🛒 فروشگاه طیبستان",
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
    if not query or query.startswith("/"):
        return

    results = search_products(query, limit=5)

    if not results:
        await message.reply(
            f"متأسفانه محصولی با عنوان «{query}» پیدا نشد 😕\n"
            "لطفاً نام دیگری امتحان کنید یا از دکمه فروشگاه استفاده کنید.",
            components=get_shop_keyboard(),
        )
        return

    parts = [f"🔍 نتایج برای «{query}»:\n"]
    for i, p in enumerate(results, 1):
        parts.append(format_product_message(p))
        if i < len(results):
            parts.append("────────")

    await message.reply("\n".join(parts), components=get_shop_keyboard())
