"""
ارسال خودکار محصولات به کانال

تست دستی:
  python -m bot.post_daily
  python -m bot.post_daily 3
  python -m bot.post_daily 1 @linktest

کرون (مثلاً هر روز ۱۰ صبح و ۶ عصر):
  0 10,18 * * * cd /home/taiyebes/taiyebestanbot && /home/taiyebes/virtualenv/taiyebestanbot/3.11/bin/python -m bot.post_daily >> channel.log 2>&1
"""
import sys
from .channel_poster import run_daily_posts


def main():
    count = None
    chat_id = None
    if len(sys.argv) >= 2 and sys.argv[1].isdigit():
        count = int(sys.argv[1])
    if len(sys.argv) >= 3:
        chat_id = sys.argv[2]
    elif len(sys.argv) >= 2 and not sys.argv[1].isdigit():
        chat_id = sys.argv[1]
    run_daily_posts(count=count, chat_id=chat_id)


if __name__ == "__main__":
    main()
