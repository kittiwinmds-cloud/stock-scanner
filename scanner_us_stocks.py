import yfinance as yf
import pandas as pd
import ta
import requests
import os
import time
from datetime import datetime

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ==============================
# 🔥 ดึงหุ้น Volume สูง (Dynamic)
# ==============================
def get_dynamic_symbols():
    # กลุ่มหุ้น US ใหญ่ ๆ (ETF + Tech)
    base_list = [
        "AAPL","NVDA","TSLA","MSFT","AMZN","META","GOOGL",
        "AMD","NFLX","PLTR","COIN","SHOP","EOSE","ROKU","SNOW",
        "PANW","CRWD","ZS","NET","DDOG",
        "SPY","QQQ"
    ]

    volumes = []

    for symbol in base_list:
        try:
            df = yf.download(symbol, period="5d", interval="1d", progress=False)

            if df is None or df.empty:
                continue

            vol = df['Volume'].iloc[-1]

            if isinstance(vol, pd.Series):
                vol = vol.values[0]

            vol = float(vol)

            volumes.append((symbol, vol))

            time.sleep(0.2)

        except Exception as e:
            print(f"[!] Skip {symbol}: {e}")
            continue
    # 🔥 เรียงจาก Volume สูง
    volumes = sorted(volumes, key=lambda x: x[1], reverse=True)

    # เอา Top 15
    top_symbols = [v[0] for v in volumes[:15]]

    print("[*] Top Volume Symbols:", top_symbols)
    return top_symbols

# ==============================
# CLEAN DATA
# ==============================
def clean_df(df):
    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.reset_index(inplace=True)

    df.rename(columns={
        'Datetime': 'datetime',
        'Date': 'datetime',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }, inplace=True)

    cols = ['open','high','low','close','volume']
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(inplace=True)
    return df

# ==============================
# SCORE
# ==============================
def calculate_score(prev, last):
    score = 0

    if last['close'] > last['ema_200']:
        score += 1
    else:
        score -= 1

    if prev['close'] <= prev['bb_upper'] and last['close'] > last['bb_upper']:
        score += 2
    elif prev['close'] >= prev['bb_lower'] and last['close'] < last['bb_lower']:
        score += 2

    if last['volume'] > last['vol_sma']:
        score += 1

    return score

# ==============================
# MAIN
# ==============================
print("[*] Fetching Dynamic Symbols...")
SYMBOLS = get_dynamic_symbols()

print("\n[*] Scanning...\n")

results = []

for symbol in SYMBOLS:
    try:
        df = yf.download(symbol, interval="1h", period="60d", progress=False)

        df = clean_df(df)
        if df is None or len(df) < 50:
            continue

        df['ema_200'] = ta.trend.ema_indicator(df['close'], window=200)
        df['bb_upper'] = ta.volatility.bollinger_hband(df['close'], window=20)
        df['bb_lower'] = ta.volatility.bollinger_lband(df['close'], window=20)
        df['vol_sma'] = df['volume'].rolling(20).mean()
        df['atr'] = ta.volatility.average_true_range(
            df['high'], df['low'], df['close'], window=14
        )

        df.dropna(inplace=True)

        prev = df.iloc[-3]
        last = df.iloc[-2]

        score = calculate_score(prev, last)
        if score < 2:
            continue

        direction = "LONG" if last['close'] > last['ema_200'] else "SHORT"

        entry = last['close']
        atr = last['atr']

        if direction == "LONG":
            sl = entry - (2 * atr)
            tp = entry + (2 * atr * 2)
        else:
            sl = entry + (2 * atr)
            tp = entry - (2 * atr * 2)

        results.append({
            "symbol": symbol,
            "direction": direction,
            "score": score,
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2)
        })

        time.sleep(0.3)

    except Exception as e:
        print(f"[!] Error {symbol}: {e}")

# ==============================
# RESULT
# ==============================
results = sorted(results, key=lambda x: x['score'], reverse=True)
top_results = results[:5]

print("========== RESULT ==========")

if not top_results:
    print("No setup ❌")
else:
    for r in top_results:
        print(f"{r['symbol']} {r['direction']} Score:{r['score']}")
        print(f"Entry:{r['entry']} SL:{r['sl']} TP:{r['tp']}")
        print("-"*30)

print("============================")

# ==============================
# DISCORD
# ==============================
if top_results and WEBHOOK_URL:
    msg = f"🚀 DYNAMIC SCANNER ({datetime.now().strftime('%H:%M')})\n\n"

    for r in top_results:
        msg += (
            f"{r['symbol']} → {r['direction']} (Score {r['score']})\n"
            f"Entry:{r['entry']} SL:{r['sl']} TP:{r['tp']}\n\n"
        )

    requests.post(WEBHOOK_URL, json={"content": msg})
