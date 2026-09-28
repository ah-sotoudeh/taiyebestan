"""
اسکریپت همگام‌سازی دستی محصولات از ووکامرس
اجرا از ترمینال:
    python -m bot.sync_products
"""
from .products import sync_products

if __name__ == "__main__":
    products = sync_products(force=True)
    print(f"تمام. تعداد محصولات در کش: {len(products)}")
