"""
هندلرهای پیام ربات طیبستان
"""
from bale import Bot, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from .config import WELCOME_MESSAGE, SITE_URL
from .products import search_products, format_product_message


def get_shop_keyboard() -> InlineKeyboardMarkup:
    """دکمه مینی‌اپ فروشگاه"""
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            text="🛒 مشاهده فروشگاه طیبستان",
            web_app=WebAppInfo(url=SITE_URL),
        )
    )
    kb.add(
        InlineKeyboardButton(
            text="🌐 باز کردن در مرورگر",
            url=SITE_URL,
        )
    )
    return kb


async def handle_start(message: Message):
    """دستور /start و خوشامدگویی"""
    name = message.author.first_name or "کاربر"
    text = WELCOME_MESSAGE.format(name=name)
    await message.reply(text, components=get_shop_keyboard())


async def handle_text(message: Message):
    """جستجوی محصول با متن پیام"""
    query = (message.content or "").strip()
    if not query:
        return

    # دستورات خاص
    if query.startswith("/"):
        if query in ("/start", "/help"):
            await handle_start(message)
        return

    results = search_products(query, limit=5)

    if not results:
        await message.reply(
            f"متأسفانه محصولی با عنوان «{query}» پیدا نشد 😕\n"
            "لطفاً نام دیگری امتحان کنید یا از دکمه فروشگاه استفاده کنید.",
            components=get_shop_keyboard(),
        )
        return

    # ارسال نتایج
    reply_parts = [f"🔍 نتایج جستجو برای «{query}»:\n"]
    for p in results:
        reply_parts.append(format_product_message(p))
        reply_parts.append("")  # فاصله

    text = "\n".join(reply_parts)
    await message.reply(text, components=get_shop_keyboard())
