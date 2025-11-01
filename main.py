import os
import requests
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import time

app = FastAPI()
scheduler = AsyncIOScheduler()

# --- Твої ключі (в Render будеш ховати в Environment Variables) ---
API_KEY = os.getenv("API_KEY", "PQn5Spmh9pYoe2LNpvVhiAjV2DN0kSxlYaX2ki9TOXKS9pTZeDU8msVhBn2IE1Kr")
API_SECRET = os.getenv("API_SECRET", "lm8WehzeRZ598K0VIu8Mpjo34nviWkka8GFh2C4v303Ud210Gw5ALnprZfwIVHck")
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'LTCUSDT', 'ADAUSDT', 'LINKUSDT', 'AVAXUSDT']
TOKEN = os.getenv("TOKEN", "7803487145:AAF854eKw2BuORYL-VzIqmxgbRk1nMPuBWc")
CHAT_ID = os.getenv("CHAT_ID", "556546336")

INTERVAL = '15m'
EMA_SHORT = 20
EMA_LONG = 50
previous_states = {}

# === Отримання даних ===
def get_klines(symbol, interval, limit=60):
    try:
        url = 'https://fapi.binance.com/fapi/v1/klines'
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'Помилка {symbol}: {e}')
        return []

# === EMA ===
def calculate_ema(prices, period):
    ema = []
    k = 2 / (period + 1)
    for i, price in enumerate(prices):
        if i == 0:
            ema.append(price)
        else:
            ema.append(price * k + ema[-1] * (1 - k))
    return ema

# === Telegram ===
def send_telegram(text):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    try:
        requests.get(url, params={'chat_id': CHAT_ID, 'text': text}, timeout=10)
    except Exception as e:
        print(f'Telegram error: {e}')

# === Перевірка перетину ===
def check_cross(symbol):
    data = get_klines(symbol, INTERVAL, limit=EMA_LONG + 10)
    if not data or len(data) < EMA_LONG + 1:
        return None

    closes = [float(candle[4]) for candle in data]
    ema_short = calculate_ema(closes, EMA_SHORT)
    ema_long = calculate_ema(closes, EMA_LONG)

    prev_diff = ema_short[-2] - ema_long[-2]
    curr_diff = ema_short[-1] - ema_long[-1]

    if prev_diff < 0 and curr_diff > 0:
        return 'UP'
    elif prev_diff > 0 and curr_diff < 0:
        return 'DOWN'
    return None

# === Основна логіка (виконується кожні 15 хв) ===
def check_all_symbols():
    print(f"Перевірка о {time.strftime('%H:%M:%S')}")
    for symbol in SYMBOLS:
        cross = check_cross(symbol)
        if cross and previous_states.get(symbol) != cross:
            direction = 'Вгору ↑ (Лонг)' if cross == 'UP' else 'Вниз ↓ (Шорт)'
            msg = f"EMA {EMA_SHORT}/{EMA_LONG} {symbol}\n{direction}\nТаймфрейм: {INTERVAL}"
            print(msg)
            send_telegram(msg)
            previous_states[symbol] = cross
        elif cross is None:
            previous_states[symbol] = None

# === Запуск при старті ===
@app.on_event("startup")
async def startup():
    scheduler.add_job(check_all_symbols, "interval", minutes=15, next_run_time=time.strftime('%Y-%m-%d %H:%M:%S'))
    scheduler.start()
    send_telegram('Бот EMA 20/50 (15m) запущений на Render!')

# === Головна сторінка (щоб Render не "засинав") ===
@app.get("/")
def home():
    return {
        "status": "Бот працює!",
        "pairs": SYMBOLS,
        "ema": f"{EMA_SHORT}/{EMA_LONG}",
        "interval": INTERVAL
    }

# Для локального тестування
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
