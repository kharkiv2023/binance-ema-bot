import os
import requests
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import time

app = FastAPI()
scheduler = AsyncIOScheduler()

# --- Ключі (з Environment Variables на Render) ---
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'LTCUSDT', 'ADAUSDT', 'LINKUSDT', 'AVAXUSDT']
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Налаштування таймфреймів: EMA 20/50 на 15m і 1h ===
TIMEFRAMES = {
    "15m": {"interval": "15m", "ema_short": 20, "ema_long": 50, "check_every": 15},
    "1h":  {"interval": "1h",  "ema_short": 20, "ema_long": 50, "check_every": 60}
}

previous_states = {}  # {symbol}_{tf}: "UP"/"DOWN"/None

# === Отримання даних з Binance Futures ===
def get_klines(symbol, interval, limit=60):
    try:
        url = 'https://fapi.binance.com/fapi/v1/klines'
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'Помилка отримання {symbol} {interval}: {e}')
        return []

# === Розрахунок EMA ===
def calculate_ema(prices, period):
    ema = []
    k = 2 / (period + 1)
    for i, price in enumerate(prices):
        if i == 0:
            ema.append(price)
        else:
            ema.append(price * k + ema[-1] * (1 - k))
    return ema

# === Відправка в Telegram ===
def send_telegram(text):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    try:
        requests.get(url, params={'chat_id': CHAT_ID, 'text': text}, timeout=10)
    except Exception as e:
        print(f'Помилка Telegram: {e}')

# === Перевірка перетину EMA ===
def check_cross(symbol, tf):
    data = get_klines(symbol, tf["interval"], limit=tf["ema_long"] + 10)
    if not data or len(data) < tf["ema_long"] + 1:
        return None

    closes = [float(candle[4]) for candle in data]
    ema_short = calculate_ema(closes, tf["ema_short"])
    ema_long = calculate_ema(closes, tf["ema_long"])

    prev_diff = ema_short[-2] - ema_long[-2]
    curr_diff = ema_short[-1] - ema_long[-1]

    if prev_diff < 0 and curr_diff > 0:
        return 'UP'
    elif prev_diff > 0 and curr_diff < 0:
        return 'DOWN'
    return None

# === Перевірка всіх пар і таймфреймів ===
def check_all():
    print(f"Перевірка о {time.strftime('%H:%M:%S')}")
    for symbol in SYMBOLS:
        for tf_name, tf in TIMEFRAMES.items():
            state_key = f"{symbol}_{tf_name}"
            cross = check_cross(symbol, tf)

            if cross and previous_states.get(state_key) != cross:
                direction = 'Вгору ↑ (Лонг)' if cross == 'UP' else 'Вниз ↓ (Шорт)'
                msg = (
                    f"EMA 20/50 {symbol}\n"
                    f"{direction}\n"
                    f"Таймфрейм: {tf_name.upper()}"
                )
                print(msg)
                send_telegram(msg)
                previous_states[state_key] = cross
            elif cross is None:
                previous_states[state_key] = None

# === Запуск при старті ===
@app.on_event("startup")
async def startup():
    # 15m: кожні 15 хв
    scheduler.add_job(check_all, "interval", minutes=15, next_run_time=time.strftime('%Y-%m-%d %H:%M:%S'))
    # 1h: кожну годину (додатково, бо 15m * 4 = 1h)
    scheduler.add_job(check_all, "cron", hour="*", minute=0)
    scheduler.start()
    send_telegram('Бот запущено!\nEMA 20/50 на 15m і 1h')

# === Головна сторінка (для Render і UptimeRobot) ===
@app.get("/")
@app.head("/")
def home():
    return {
        "status": "Бот працює! EMA 20/50 на 15m + 1h",
        "pairs": SYMBOLS,
        "timeframes": ["15m", "1h"]
    }

# Для локального тестування
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
