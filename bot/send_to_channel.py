"""
ارسال یک محصول نمونه به کانال برای تست دکمه فروشگاه
اجرا:
  python -m bot.send_to_channel
  python -m bot.send_to_channel @linktest
  python -m bot.send_to_channel @linktest ایران
"""
import sys
from .products import load_products, search_products, get_top_rated
from .products_ui import format_product_message, search_products as search_ui
from .reviews_helper import fetch_product_reviews
from .handlers import detail_keyboard, send_text


def main():
    channel = "@linktest"
    query = None
    if len(sys.argv) >= 2:
        channel = sys.argv[1]
    if len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])

    product = None
    if query:
        try:
            results = search_ui(query, limit=5, mode="name")
        except TypeError:
            results = search_products(query, limit=5)
        if results:
            product = results[0]
    if not product:
        top = get_top_rated(limit=5)
        product = top[0] if top else None
    if not product:
        products = load_products()
        product = products[0] if products else None
    if not product:
        print("محصولی پیدا نشد.")
        return

    reviews = []
    if product.get("rating_count"):
        reviews = fetch_product_reviews(product.get("id"))

    text = format_product_message(product, reviews=reviews)
    kb = detail_keyboard(product)

    print("ارسال به", channel, "—", product.get("name"))
    result = send_text(channel, text, reply_markup=kb)
    print(result)


if __name__ == "__main__":
    main()
