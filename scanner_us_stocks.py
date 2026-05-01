import yfinance as yf
import pandas as pd
import ta
import requests
import os
import datetime

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

MODE = "AGGRESSIVE"   # 🔥 เปลี่ยนเป็น STRICT ได้
# =========================
# 📊 SYMBOLS
# =========================

SYMBOLS = [
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
# 🧠 SCORING
# =========================
def score_setup(rr, trend_strength):
    return round((rr * 50) + (trend_strength * 50), 2)

# =========================
# 🔍 SCANNER
# =========================
def scan():
    setups = []

    for sym in SYMBOLS:
        try:
            df = yf.download(sym, period="5d", interval="1h", progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.dropna(inplace=True)

            if len(df) < 50:
                continue

            # Indicators
            df['ema'] = ta.trend.ema_indicator(df['Close'], 100)
            df['bb_upper'] = ta.volatility.bollinger_hband(df['Close'])
            df['bb_lower'] = ta.volatility.bollinger_lband(df['Close'])
            df['atr'] = ta.volatility.average_true_range(
                df['High'], df['Low'], df['Close']
            )

            last = df.iloc[-1]

            entry = last['Close']
            atr = last['atr']

            # =========================
            # 🟢 AGGRESSIVE MODE
            # =========================
            if MODE == "AGGRESSIVE":

                # LONG
                if last['Close'] > last['ema'] and last['Close'] > last['bb_upper'] * 0.98:
                    sl = entry - atr
                    tp = entry + atr * 2
                    rr = 2
                    score = score_setup(rr, 1)

                    setups.append((sym, "LONG", entry, sl, tp, rr, score))

                # SHORT
                elif last['Close'] < last['ema'] and last['Close'] < last['bb_lower'] * 1.02:
                    sl = entry + atr
                    tp = entry - atr * 2
                    rr = 2
                    score = score_setup(rr, 1)

                    setups.append((sym, "SHORT", entry, sl, tp, rr, score))

            # =========================
            # 🔵 STRICT MODE
            # =========================
            elif MODE == "STRICT":

                # LONG
                if last['Close'] > last['ema'] and last['Close'] > last['bb_upper']:
                    sl = entry - atr
                    tp = entry + atr * 3
                    rr = 3
                    score = score_setup(rr, 1.2)

                    setups.append((sym, "LONG", entry, sl, tp, rr, score))

                # SHORT
                elif last['Close'] < last['ema'] and last['Close'] < last['bb_lower']:
                    sl = entry + atr
                    tp = entry - atr * 3
                    rr = 3
                    score = score_setup(rr, 1.2)

                    setups.append((sym, "SHORT", entry, sl, tp, rr, score))

        except Exception as e:
            print(f"{sym} error:", e)

    return setups

# =========================
# 🚀 RUN
# =========================
print("[*] Running scanner...")

results = scan()

# =========================
# 🏆 RANKING
# =========================
results = sorted(results, key=lambda x: x[6], reverse=True)

# =========================
# 📩 MESSAGE
# =========================
now = datetime.datetime.utcnow()

msg = f"📊 TOP SETUPS ({MODE})\n\n"

if results:
    for r in results[:5]:
        sym, side, entry, sl, tp, rr, score = r
        msg += (
            f"{side} {sym}\n"
            f"Entry: {entry:.2f}\n"
            f"SL: {sl:.2f} | TP: {tp:.2f}\n"
            f"RR: 1:{rr} | Score: {score}\n\n"
        )
else:
    msg += "No setup ❌\n\n"

msg += f"⏰ {now} UTC"

print(msg)

# =========================
# 📤 DISCORD
# =========================
if WEBHOOK_URL:
    try:
        requests.post(WEBHOOK_URL, json={"content": msg})
        print("[+] Sent to Discord")
    except Exception as e:
        print("Discord error:", e)
else:
    print("No WEBHOOK_URL")
