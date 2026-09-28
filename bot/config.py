import os
from dotenv import load_dotenv

load_dotenv()

# توکن ربات از BotFather
BALE_TOKEN = os.getenv("BALE_TOKEN", "YOUR_BOT_TOKEN_HERE")

# آدرس پایه API بله
BALE_API = f"https://tapi.bale.ai/bot{BALE_TOKEN}"

# آدرس سایت
SITE_URL = "https://taiyebestan.ir"

# اگر از WooCommerce REST API استفاده می‌کنید:
WC_URL = os.getenv("WC_URL", "https://taiyebestan.ir")
WC_KEY = os.getenv("WC_KEY", "")
WC_SECRET = os.getenv("WC_SECRET", "")

# مسیر فایل کش محصولات (JSON)
PRODUCTS_CACHE = os.getenv("PRODUCTS_CACHE", "products.json")

# پیام خوشامد
WELCOME_MESSAGE = """سلام {name} عزیز 🌿
به ربات فروشگاه طیبستان خوش آمدید!

نام محصول مورد نظرتون رو بنویسید (حتی بخشی از نام کافیه) تا لینکش رو براتون بفرستم.

برای مشاهده کامل فروشگاه روی دکمه زیر بزنید 👇"""
