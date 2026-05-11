"""
Yahoo Finance scraper for COMEX futures (구리 HG=F, 알루미늄 ALI=F).

Uses yfinance which queries query1.finance.yahoo.com under the hood.
Returns last ~280 trading days (≈ 9 months) of daily close prices.
"""
from __future__ import annotations

import logging
from typing import List, Dict

import yfinance as yf

log = logging.getLogger(__name__)


def _fetch(ticker: str, period: str = "1y") -> List[Dict]:
    """Fetch daily OHLC from Yahoo Finance for a single ticker."""
    df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
    if df is None or df.empty:
        log.warning("Yahoo returned empty frame for %s", ticker)
        return []

    df = df.reset_index()
    series: List[Dict] = []
    for _, row in df.iterrows():
        close = row["Close"]
        if close is None or str(close) == "nan":
            continue
        series.append(
            {
                "date": row["Date"].strftime("%Y-%m-%d"),
                "value": round(float(close), 4),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "volume": int(row["Volume"]) if not str(row["Volume"]) == "nan" else 0,
            }
        )
    return series


def fetch_copper() -> List[Dict]:
    """COMEX High-Grade Copper continuous futures (USD/lb)."""
    return _fetch("HG=F", period="1y")


def fetch_aluminum() -> List[Dict]:
    """COMEX Aluminum continuous futures (USD/t).

    Note: HG=F is in USD/lb; ALI=F is in USD per metric ton.
    LME aluminum is referenced via this COMEX proxy contract.
    """
    return _fetch("ALI=F", period="1y")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for fn, name in [(fetch_copper, "copper"), (fetch_aluminum, "aluminum")]:
        s = fn()
        if s:
            print(f"{name}: {len(s)} pts, latest={s[-1]['value']} on {s[-1]['date']}")
        else:
            print(f"{name}: NO DATA")
