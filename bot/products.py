"""بارگذاری ماژول محصولات از نسخه پایدار ریپو"""
import urllib.request

_URL = (
    "https://raw.githubusercontent.com/ah-sotoudeh/taiyebestan/"
    "e49e1c7614a71ce5166d4b1fa0e233c4b27ce9b2/bot/products.py"
)

_code = urllib.request.urlopen(_URL, timeout=60).read().decode("utf-8")
exec(compile(_code, "products.py", "exec"), globals())
