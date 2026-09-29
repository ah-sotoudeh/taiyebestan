"""
همگام‌سازی محصولات و دسته‌بندی‌ها
python -m bot.sync_products
"""
from .products import sync_products, sync_categories

if __name__ == "__main__":
    products = sync_products(force=True)
    cats = sync_categories(force=True)
    print(f"محصولات: {len(products)} | دسته‌بندی‌ها: {len(cats)}")
