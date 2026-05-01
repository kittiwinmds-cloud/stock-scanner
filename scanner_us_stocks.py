import yfinance as yf
import pandas as pd
import ta
import requests
import os
import datetime

# =========================
# 🔐 ENV
# =========================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# =========================
# 📊 SYMBOLS (Dynamic Base)
# =========================
def get_symbols():
    return [
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

# =========================
# 🔍 SCANNER
# =========================
def scan(symbols):
    results = []
    movers = []

    for sym in symbols:
        try:
            df = yf.download(sym, period="5d", interval="1h", progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.dropna(inplace=True)

            if len(df) < 50:
                continue

            # 📊 Indicator
            df['ema'] = ta.trend.ema_indicator(df['Close'], 100)
            df['bb_upper'] = ta.volatility.bollinger_hband(df['Close'])
            df['bb_lower'] = ta.volatility.bollinger_lband(df['Close'])

            last = df.iloc[-1]
            first = df.iloc[0]

            # 📈 % Change (Top mover)
            change = (last['Close'] - first['Close']) / first['Close'] * 100
            movers.append((sym, round(change, 2)))

            # 🔥 SIGNAL (ปรับให้มี signal ออกจริง)
            if last['Close'] > last['ema'] and last['Close'] > last['bb_upper'] * 0.99:
                results.append(f"🚀 LONG: {sym}")

            elif last['Close'] < last['ema'] and last['Close'] < last['bb_lower'] * 1.01:
                results.append(f"🔻 SHORT: {sym}")

        except Exception as e:
            print(f"[!] {sym} error:", e)

    # 🔝 Top Movers
    movers.sort(key=lambda x: x[1], reverse=True)
    top_movers = movers[:5]

    return results, top_movers

# =========================
# 🚀 RUN
# =========================
print("[*] Running scanner...")

symbols = get_symbols()
print(f"Loaded {len(symbols)} symbols")

signals, movers = scan(symbols)

# =========================
# 📩 MESSAGE
# =========================
now = datetime.datetime.utcnow()

msg = "📊 STOCK SCANNER\n\n"

if signals:
    msg += "\n".join(signals)
else:
    msg += "No setup ❌"

msg += "\n\n🔥 Top Movers:\n"
for m in movers:
    msg += f"{m[0]}: {m[1]}%\n"

msg += f"\n⏰ {now} UTC"

print(msg)

# =========================
# 📤 DISCORD
# =========================
if WEBHOOK_URL:
    try:
        requests.post(WEBHOOK_URL, json={"content": msg})
        print("[+] Sent to Discord")
    except Exception as e:
        print("[!] Discord error:", e)
else:
    print("[!] No WEBHOOK_URL found")

print("WEBHOOK:", WEBHOOK_URL)
