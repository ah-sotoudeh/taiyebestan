#!/bin/bash
# نگهبان بازو طیبستان — اگر پروسه مرده باشد دوباره روشن می‌کند
# کرون پیشنهادی (هر ۱ دقیقه):
# * * * * * /home/taiyebes/taiyebestanbot/keep_alive.sh >> /home/taiyebes/taiyebestanbot/keep_alive.log 2>&1

set -e

BOT_DIR="/home/taiyebes/taiyebestanbot"
VENV_PY="/home/taiyebes/virtualenv/taiyebestanbot/3.11/bin/python"
LOG_FILE="${BOT_DIR}/bot.log"
MARKER="bot.main"

cd "$BOT_DIR" || exit 1

# اگر از قبل در حال اجراست، کاری نکن
if pgrep -f "python.*${MARKER}" >/dev/null 2>&1; then
  exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] بازو نبود — راه‌اندازی مجدد..."

# پاک‌سازی پروسه‌های نیمه‌مرده
pkill -9 -f "${MARKER}" 2>/dev/null || true
sleep 1

if [ ! -x "$VENV_PY" ]; then
  echo "پایتون مجازی پیدا نشد: $VENV_PY"
  exit 1
fi

nohup "$VENV_PY" -u -m bot.main >> "$LOG_FILE" 2>&1 &
echo "[$(date '+%Y-%m-%d %H:%M:%S')] استارت شد PID=$!"
