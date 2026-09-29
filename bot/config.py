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

# کانال ارسال خودکار (مثلاً @linktest یا آیدی عددی)
CHANNEL_ID = os.getenv("CHANNEL_ID", "@linktest")
# تعداد محصول در هر اجرای کرون
CHANNEL_POSTS_PER_RUN = int(os.getenv("CHANNEL_POSTS_PER_RUN", "2"))
# فایل وضعیت ارسال‌شده‌ها
CHANNEL_STATE_FILE = os.getenv("CHANNEL_STATE_FILE", "channel_posted.json")
# صف دستی (اختیاری): لیست id محصول
CHANNEL_QUEUE_FILE = os.getenv("CHANNEL_QUEUE_FILE", "channel_queue.json")
# روش انتخاب: rotate | top_rated | queue
CHANNEL_PICK_MODE = os.getenv("CHANNEL_PICK_MODE", "rotate")

WELCOME_MESSAGE = """سلام {name} عزیز 🌿
به *بازو فروشگاه طیبستان* خوش آمدید!

یکی از گزینه‌های زیر را انتخاب کنید:

⭐ محبوب‌ترین‌ها
📂 دسته‌بندی‌ها
🔍 جستجوی نام محصول
🌿 جستجو با ویژگی / کاربرد

در جستجوی ویژگی می‌توانید مثلاً بنویسید:
• گرم و تر
• عطر گرم و خشک
• تمرکز
• اضطراب
• خواب
• تقویت قلب"""

PROMPT_NAME_SEARCH = "🔍 نام محصول را بنویسید (حتی بخشی از نام کافیست):"

PROMPT_FEATURE_SEARCH = """🌿 ویژگی یا کاربرد مورد نظرتان را بنویسید.

مثال‌ها:
• گرم و تر
• روغن گرم و خشک
• تمرکز
• اضطراب / خواب / تقویت قلب
• حرز

هر کلمه‌ای که در طبیعت، خواص درمانی یا سایر مشخصات محصول باشد قابل جستجو است."""
