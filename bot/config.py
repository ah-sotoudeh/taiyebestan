import os
from dotenv import load_dotenv

load_dotenv()

BALE_TOKEN = os.getenv("BALE_TOKEN", "YOUR_BOT_TOKEN_HERE")
BALE_API = f"https://tapi.bale.ai/bot{BALE_TOKEN}"
SITE_URL = "https://taiyebestan.ir"

WC_URL = os.getenv("WC_URL", "https://taiyebestan.ir")
WC_KEY = os.getenv("WC_KEY", "")
WC_SECRET = os.getenv("WC_SECRET", "")

PRODUCTS_CACHE = os.getenv("PRODUCTS_CACHE", "products.json")
CATEGORIES_CACHE = os.getenv("CATEGORIES_CACHE", "categories.json")

WELCOME_MESSAGE = """سلام {name} عزیز 🌿
به ربات فروشگاه طیبستان خوش آمدید!

🔍 نام محصول را بنویسید (حتی بخشی از نام)
⭐ محبوب‌ترین‌ها را ببینید
📂 از دسته‌بندی‌ها انتخاب کنید

یکی از دکمه‌های زیر را بزنید یا نام محصول را ارسال کنید 👇"""
