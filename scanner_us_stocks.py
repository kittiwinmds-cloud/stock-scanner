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
        "NVDA","MSFT","AAPL","AMZN","GOOGL","META","PLTR",
        "TSLA","AMD","SMCI","COIN","SNOW","CRWD",
        "AVGO","MU","QCOM","INTC","MRVL","AMAT",
        "JPM","BAC","GS","MS","WFC","C",
        "XOM","CVX","OXY","SLB","COP",
        "BA","LMT","RTX","CAT","GE",
        "NKE","SBUX","MCD","WMT","COST","TGT",
        "JNJ","PFE","LLY","ABBV","MRK",
        "NFLX","DIS","CMCSA",
        "O","PLD","AMT",
        "SPY","QQQ","IWM","ARKK"
    ]
def scan():
    results = []

    for sym in symbols:
        try:
            df = yf.download(sym, period="5d", interval="1h", progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.dropna(inplace=True)

            if len(df) < 50:
                continue

            df['ema'] = ta.trend.ema_indicator(df['Close'], 100)
            df['bb_upper'] = ta.volatility.bollinger_hband(df['Close'])
            df['bb_lower'] = ta.volatility.bollinger_lband(df['Close'])

            last = df.iloc[-1]

            # 🔥 เงื่อนไข (ปรับให้ออก signal ง่ายขึ้น)
            if last['Close'] > last['ema'] and last['Close'] > last['bb_upper'] * 0.99:
                results.append(f"🚀 LONG: {sym}")

            elif last['Close'] < last['ema'] and last['Close'] < last['bb_lower'] * 1.01:
                results.append(f"🔻 SHORT: {sym}")

        except Exception as e:
            print(f"[!] {sym} error:", e)

    return results

# =========================
# RUN
# =========================
print("[*] Running scanner...")

signals = scan()

# 🔥 ALWAYS SEND
if signals:
    message = "📊 STOCK SCANNER\n\n" + "\n".join(signals)
else:
    message = "📊 STOCK SCANNER\n\nNo setup ❌"

message += f"\n\n⏰ {datetime.datetime.utcnow()} UTC"

print(message)

# 🔥 SEND DISCORD
if WEBHOOK_URL:
    requests.post(WEBHOOK_URL, json={"content": message})
