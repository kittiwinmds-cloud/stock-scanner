import yfinance as yf
import pandas as pd
import ta
import requests
import os
import datetime

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# =========================
# 📊 SYMBOLS
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
# 🧠 CALC SL/TP
# =========================
def calculate_trade(last, direction):
    entry = last['Close']
    atr = last['atr']

    if direction == "LONG":
        sl = entry - atr
        tp = entry + (atr * 2)
    else:
        sl = entry + atr
        tp = entry - (atr * 2)

    rr = abs((tp - entry) / (entry - sl))
    return entry, sl, tp, rr

# =========================
# 🔍 SCANNER
# =========================
def scan(symbols):
    setups = []

    for sym in symbols:
        try:
            df = yf.download(sym, period="10d", interval="1h", progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.dropna(inplace=True)

            if len(df) < 100:
                continue

            # Indicators
            df['ema'] = ta.trend.ema_indicator(df['Close'], 200)
            df['bb_upper'] = ta.volatility.bollinger_hband(df['Close'])
            df['bb_lower'] = ta.volatility.bollinger_lband(df['Close'])
            df['atr'] = ta.volatility.average_true_range(
                df['High'], df['Low'], df['Close']
            )

            last = df.iloc[-1]

            # Volume filter
            avg_vol = df['Volume'].tail(20).mean()

            # 🔥 SIGNAL LOGIC
            if last['Close'] > last['ema'] and last['Close'] > last['bb_upper'] and last['Volume'] > avg_vol:
                entry, sl, tp, rr = calculate_trade(last, "LONG")

                score = rr + ((last['Volume'] / avg_vol) * 0.5)

                setups.append({
                    "symbol": sym,
                    "type": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(rr, 2),
                    "score": round(score, 2)
                })

            elif last['Close'] < last['ema'] and last['Close'] < last['bb_lower'] and last['Volume'] > avg_vol:
                entry, sl, tp, rr = calculate_trade(last, "SHORT")

                score = rr + ((last['Volume'] / avg_vol) * 0.5)

                setups.append({
                    "symbol": sym,
                    "type": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(rr, 2),
                    "score": round(score, 2)
                })

        except Exception as e:
            print(f"[!] {sym} error:", e)

    return setups

# =========================
# 🚀 RUN
# =========================
print("[*] Running PRO scanner...")

symbols = get_symbols()
setups = scan(symbols)

# =========================
# 🏆 RANKING
# =========================
df = pd.DataFrame(setups)

if not df.empty:
    df = df.sort_values(by="score", ascending=False)
    top = df.head(5)
else:
    top = pd.DataFrame()

# =========================
# 📩 MESSAGE
# =========================
now = datetime.datetime.utcnow()

msg = "📊 TOP SETUPS (PRO)\n\n"

if not top.empty:
    for i, row in top.iterrows():
        msg += (
            f"{row['symbol']} ({row['type']})\n"
            f"Entry: {row['entry']}\n"
            f"SL: {row['sl']}\n"
            f"TP: {row['tp']}\n"
            f"RR: {row['rr']}\n"
            f"Score: {row['score']}\n\n"
        )
else:
    msg += "No setup ❌\n"

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
