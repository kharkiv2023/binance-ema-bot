# binance-ema-bot
"Бот для EMA кросоверів на Binance
import time
import requests

# Твои ключи Binance API
API_KEY = 'PQn5Spmh9pYoe2LNpvVhiAjV2DN0kSxlYaX2ki9TOXKS9pTZeDU8msVhBn2IE1Kr'
API_SECRET = 'lm8WehzeRZ598K0VIu8Mpjo34nviWkka8GFh2C4v303Ud210Gw5ALnprZfwIVHck'
SYMBOLS = ['BTCUSDT', 'AVAXUSDT', 'XRPUSDT', 'LTCUSDT', 'LINKUSDT', 'ADAUSDT','ETHUSDT']
TOKEN = '7803487145:AAF854eKw2BuORYL-VzIqmxgbRk1nMPuBWc'
CHAT_ID = '556546336'
# 📈 Торгові налаштування
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'LTCUSDT', 'ADAUSDT', 'LINKUSDT', 'AVAXUSDT']
INTERVAL = '15m'   # 15-хвилинний таймфрейм
EMA_SHORT = 20    # коротка EMA
EMA_LONG = 50     # довга EMA

previous_states = {}  # зберігає попередні сигнали


# === Отримання історичних даних з Binance ===
def get_klines(symbol, interval, limit=60):
    try:
        url = 'https://fapi.binance.com/fapi/v1/klines'
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'❌ Помилка отримання даних {symbol}: {e}')
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


# === Відправка повідомлення в Telegram ===
def send_telegram(text):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    params = {'chat_id': CHAT_ID, 'text': text}
    try:
        requests.get(url, params=params, timeout=10)
    except Exception as e:
        print(f'⚠️ Помилка Telegram: {e}')


# === Перевірка перетину EMA ===
def check_cross(symbol):
    data = get_klines(symbol, INTERVAL, limit=EMA_LONG + 10)
    if not data:
        return None

    closes = [float(candle[4]) for candle in data]
    ema_short = calculate_ema(closes, EMA_SHORT)
    ema_long = calculate_ema(closes, EMA_LONG)

    prev_diff = ema_short[-2] - ema_long[-2]
    curr_diff = ema_short[-1] - ema_long[-1]

    if prev_diff < 0 and curr_diff > 0:
        return 'UP'   # EMA 20 перетнула EMA 50 знизу → сигнал на LONG
    elif prev_diff > 0 and curr_diff < 0:
        return 'DOWN' # EMA 20 перетнула EMA 50 зверху → сигнал на SHORT
    return None


# === Основний цикл роботи бота ===
def main():
    print('🚀 Старт бота EMA 20/50 (15m)...')
    send_telegram('🤖 Бот EMA 20/50 (15m) запущений!')

    while True:
        for symbol in SYMBOLS:
            cross = check_cross(symbol)
            if cross and previous_states.get(symbol) != cross:
                msg = f"⚡ EMA 20/50 перетин {symbol} ({INTERVAL}): {'Вгору ↑ (Лонг)' if cross == 'UP' else 'Вниз ↓ (Шорт)'}"
                print(msg)
                send_telegram(msg)
                previous_states[symbol] = cross
            elif cross is None:
                previous_states[symbol] = None
            else:
                print(f"{symbol}: без нового сигналу ({time.strftime('%H:%M:%S')})")

        # 🔁 Перевірка кожні 15 хвилин = 900 секунд
        print("⏳ Очікування наступної свічки...\n")
        time.sleep(750)


if __name__ == '__main__':
    main()

