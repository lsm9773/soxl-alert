import os
import json
import requests
import yfinance as yf
import pandas as pd

# ==========================
# 텔레그램 설정
# ==========================

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STATE_FILE = "state.json"


def send_message(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )


# ==========================
# 상태파일 읽기
# ==========================

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"cloud_break": False}

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


state = load_state()

# ==========================
# SOXL 데이터
# ==========================

df = yf.download(
    "SOXL",
    interval="60m",
    period="90d",
    auto_adjust=True,
    progress=False
)

if len(df) < 300:
    raise Exception("데이터 부족")

close = df["Close"]

# ==========================
# 240MA
# ==========================

ma240 = close.rolling(240).mean()

# ==========================
# 일목균형표
# ==========================

high9 = df["High"].rolling(9).max()
low9 = df["Low"].rolling(9).min()
tenkan = (high9 + low9) / 2

high26 = df["High"].rolling(26).max()
low26 = df["Low"].rolling(26).min()
kijun = (high26 + low26) / 2

senkou_a = (tenkan + kijun) / 2

high52 = df["High"].rolling(52).max()
low52 = df["Low"].rolling(52).min()
senkou_b = (high52 + low52) / 2

cloud_top = pd.concat(
    [senkou_a, senkou_b],
    axis=1
).max(axis=1)

# ==========================
# 최근값
# ==========================

prev_close = float(close.iloc[-2])
curr_close = float(close.iloc[-1])

prev_cloud = float(cloud_top.iloc[-2])
curr_cloud = float(cloud_top.iloc[-1])

prev_ma = float(ma240.iloc[-2])
curr_ma = float(ma240.iloc[-1])

# ==========================
# 1. 구름대 상단 돌파 감지
# ==========================

cloud_cross_up = (
    prev_close <= prev_cloud
    and curr_close > curr_cloud
)

if cloud_cross_up:

    state["cloud_break"] = True

    send_message(
        f"☁️ SOXL 구름대 상단 돌파\n\n"
        f"가격: {curr_close:.2f}\n"
        f"240MA 돌파 대기중"
    )

# ==========================
# 2. 구름대 아래 재진입
# ==========================

if curr_close < curr_cloud:

    if state["cloud_break"]:

        send_message(
            f"⚠️ SOXL 구름대 재이탈\n\n"
            f"가격: {curr_close:.2f}\n"
            f"대기 상태 초기화"
        )

    state["cloud_break"] = False

# ==========================
# 3. 240MA 상향 돌파
# ==========================

ma_cross_up = (
    prev_close <= prev_ma
    and curr_close > curr_ma
)

if state["cloud_break"] and ma_cross_up:

    send_message(
        f"🚀 SOXL LONG SIGNAL\n\n"
        f"구름대 유지 상태\n"
        f"240MA 상향 돌파 완료\n\n"
        f"가격: {curr_close:.2f}"
    )

    state["cloud_break"] = False

# ==========================
# 저장
# ==========================

save_state(state)
