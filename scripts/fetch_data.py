"""
抓取本週價格行為週報所需數據 → 寫出 datapack.json
所有計算都在這裡完成(零 AI token),AI 只吃 datapack.json 產生敘事。

用法: python3 scripts/fetch_data.py
"""
import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from curl_cffi import requests

sys.path.insert(0, os.path.dirname(__file__))
import config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(ROOT, config.HISTORY_FILE)
DATAPACK_PATH = os.path.join(ROOT, config.DATAPACK_FILE)


def get_daily_history(ticker, period="14mo"):
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"{ticker} 抓不到資料(yfinance 回傳空)")
    df.index = df.index.tz_localize(None)
    return df


def weekly_resample(daily_df):
    weekly = daily_df.resample("W-FRI").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
    return weekly.dropna(how="all")


def pct(a, b):
    return round((a / b - 1) * 100, 2)


def compute_index_metrics(ticker, daily=None):
    daily = daily if daily is not None else get_daily_history(ticker)
    weekly = weekly_resample(daily)
    if len(weekly) < 4:
        raise RuntimeError(f"{ticker} 週線資料不足,無法計算結構")

    this_wk = weekly.iloc[-1]
    prev_wk = weekly.iloc[-2]
    wk3_ago = weekly.iloc[-4]

    hh_lh = "HH" if this_wk["High"] > prev_wk["High"] else "LH"
    hl_ll = "HL" if this_wk["Low"] > prev_wk["Low"] else "LL"
    struct = f"{hh_lh}/{hl_ll}"

    close = daily["Close"].iloc[-1]
    ma50 = daily["Close"].rolling(50).mean().iloc[-1]
    ma200 = daily["Close"].rolling(200).mean().iloc[-1]
    hi52 = daily["High"].tail(252).max()
    lo52 = daily["Low"].tail(252).min()

    wk_hi = this_wk["High"]
    wk_lo = this_wk["Low"]
    close_pos = round((close - wk_lo) / (wk_hi - wk_lo) * 100, 1) if wk_hi != wk_lo else 50.0

    wk_ret = pct(this_wk["Close"], prev_wk["Close"])
    wk_ret_3 = pct(this_wk["Close"], wk3_ago["Close"])

    return {
        "symbol": ticker,
        "struct": struct,
        "close_pos": close_pos,
        "wk_ret": wk_ret,
        "wk_ret_3": wk_ret_3,
        "vs_ma50": pct(close, ma50),
        "vs_ma200": pct(close, ma200),
        "dist_hi": pct(close, hi52),
        "levels": {
            "ma50": round(ma50, 2),
            "ma200": round(ma200, 2),
            "wk_hi": round(wk_hi, 2),
            "wk_lo": round(wk_lo, 2),
            "hi52": round(hi52, 2),
            "lo52": round(lo52, 2),
        },
    }


def fetch_funding_rate():
    """
    OKX 回傳兩個費率:
    - fundingRate:當前預測值,結算前會一直跳動,可能中途翻負
    - settFundingRate:上一次「實際結算/真的收走」的費率,才是真正收付方向
    敘事只能用 settFundingRate 判斷多空是誰在付錢,fundingRate 只能當「當下情緒」的參考。
    """
    try:
        r = requests.get(
            config.OKX_FUNDING_URL,
            params={"instId": config.OKX_INST_ID},
            timeout=15,
            impersonate="chrome",
        )
        r.raise_for_status()
        data = r.json()["data"][0]
        settled = float(data["settFundingRate"])
        current = float(data["fundingRate"])
        return round(settled * 100, 4), round(current * 100, 4)
    except Exception as e:
        print(f"[warn] OKX 資金費率抓取失敗: {e}", file=sys.stderr)
        return None, None


def fetch_btcd():
    try:
        r = requests.get(config.COINGECKO_GLOBAL_URL, timeout=15, impersonate="chrome")
        r.raise_for_status()
        pct_map = r.json()["data"]["market_cap_percentage"]
        return round(pct_map["btc"], 2)
    except Exception as e:
        print(f"[warn] CoinGecko BTC.D 抓取失敗: {e}", file=sys.stderr)
        return None


def load_history():
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sector_rank_history": {}, "btcd_last": None}


def save_history(history):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def compute_streak(sector, is_top3, is_bottom3, history):
    key = sector
    rec = history["sector_rank_history"].get(key, {"top3_streak": 0, "bottom3_streak": 0})
    top_streak = rec["top3_streak"] + 1 if is_top3 else 0
    bottom_streak = rec["bottom3_streak"] + 1 if is_bottom3 else 0
    history["sector_rank_history"][key] = {
        "top3_streak": top_streak,
        "bottom3_streak": bottom_streak,
    }
    return top_streak, bottom_streak


def compute_sector_rs(spy_daily, history):
    spy_weekly = weekly_resample(spy_daily)
    spy_r1 = pct(spy_weekly["Close"].iloc[-1], spy_weekly["Close"].iloc[-2])
    spy_r3 = pct(spy_weekly["Close"].iloc[-1], spy_weekly["Close"].iloc[-4])

    rows = []
    for etf in config.SECTOR_ETFS:
        daily = get_daily_history(etf)
        weekly = weekly_resample(daily)
        r1 = round(pct(weekly["Close"].iloc[-1], weekly["Close"].iloc[-2]) - spy_r1, 2)
        r3 = round(pct(weekly["Close"].iloc[-1], weekly["Close"].iloc[-4]) - spy_r3, 2)
        rows.append({"s": etf, "r1": r1, "r3": r3})

    rows.sort(key=lambda x: x["r1"], reverse=True)
    top3 = {r["s"] for r in rows[:3]}
    bottom3 = {r["s"] for r in rows[-3:]}
    for r in rows:
        top_streak, bottom_streak = compute_streak(
            r["s"], r["s"] in top3, r["s"] in bottom3, history
        )
        if top_streak > 0:
            r["streak_top3"] = top_streak
        if bottom_streak > 0:
            r["streak_bottom3"] = bottom_streak
    return rows


def compute_leaders_laggards(sector_rs):
    top_sector = sector_rs[0]["s"]
    bottom_sector = sector_rs[-1]["s"]

    def stock_returns(sector):
        out = []
        for t in config.SECTOR_STOCKS.get(sector, []):
            try:
                daily = get_daily_history(t, period="1mo")
                weekly = weekly_resample(daily)
                w = pct(weekly["Close"].iloc[-1], weekly["Close"].iloc[-2])
                w3 = pct(weekly["Close"].iloc[-1], weekly["Close"].iloc[-4]) if len(weekly) >= 4 else None
                out.append({"t": t, "w": w, "w3": w3})
            except Exception as e:
                print(f"[warn] {t} 抓取失敗: {e}", file=sys.stderr)
        return out

    leaders_all = stock_returns(top_sector)
    laggards_all = stock_returns(bottom_sector)
    leaders_all.sort(key=lambda x: x["w"], reverse=True)
    laggards_all.sort(key=lambda x: x["w"])

    return (
        {"sector": top_sector, "stocks": leaders_all[:5]},
        {"sector": bottom_sector, "stocks": laggards_all[:5]},
    )


def main():
    print("抓取 SPY / QQQ / IWM ...")
    spy_daily = get_daily_history("SPY")
    indices = [compute_index_metrics("SPY", spy_daily)]
    for t in config.INDEX_TICKERS[1:]:
        indices.append(compute_index_metrics(t))

    print("抓取 BTC ...")
    btc_daily = get_daily_history(config.BTC_TICKER)
    btc_metrics = compute_index_metrics(config.BTC_TICKER, btc_daily)
    btc_metrics["symbol"] = "BTC"
    indices.append(btc_metrics)

    print("抓資金費率 / BTC.D ...")
    funding_settled, funding_current = fetch_funding_rate()
    btcd = fetch_btcd()

    history = load_history()
    btcd_chg = round(btcd - history["btcd_last"], 2) if (btcd is not None and history["btcd_last"] is not None) else None

    print("計算板塊輪動 (11 檔 SPDR) ...")
    sector_rs = compute_sector_rs(spy_daily, history)

    print("點名板塊龍頭/落後個股 ...")
    leaders, laggards = compute_leaders_laggards(sector_rs)

    qqq = next(i for i in indices if i["symbol"] == "QQQ")
    iwm = next(i for i in indices if i["symbol"] == "IWM")
    qqq_iwm_chg = round(qqq["wk_ret"] - iwm["wk_ret"], 2)

    if btcd is not None:
        history["btcd_last"] = btcd
    save_history(history)

    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    datapack = {
        "week": f"{monday:%Y-%m-%d}/{friday:%Y-%m-%d}",
        "data_note": "美股至最近收盤；BTC 即時",
        "indices": indices,
        "btc_extra": {
            "funding": funding_settled,  # 上一次「實際結算」的費率,判斷多空是誰在付錢要用這個
            "funding_current": funding_current,  # 當前預測值,結算前會一直跳動,僅供參考走勢
            "btcd": btcd,
            "btcd_chg": btcd_chg,
        },
        "sector_rs": sector_rs,
        "leaders": leaders,
        "laggards": laggards,
        "style": {"qqq_iwm_chg": qqq_iwm_chg},
    }

    with open(DATAPACK_PATH, "w", encoding="utf-8") as f:
        json.dump(datapack, f, ensure_ascii=False, indent=2)

    print(f"\n完成 → {DATAPACK_PATH}")


if __name__ == "__main__":
    main()
