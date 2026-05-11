"""
Sina Finance scraper for Chinese commodity futures.

Endpoints used:
  • Live quote (last price + day stats):
      https://hq.sinajs.cn/list=nf_LC0   (lithium carbonate, GFEX 광저우선물)
      https://hq.sinajs.cn/list=nf_NI0   (nickel, SHFE 상해선물)

  • Historical daily K-line:
      https://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol=LC0
      https://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol=NI0

The K-line endpoint returns rows in the form: [date, open, high, low, close, volume].
The "0" suffix on a symbol denotes the front-month / main contract proxy (主力).

Sina occasionally requires a Referer header to avoid 403; we set it.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Dict, Optional

import requests

log = logging.getLogger(__name__)

KLINE_URL = (
    "https://stock2.finance.sina.com.cn/futures/api/json.php"
    "/IndexService.getInnerFuturesDailyKLine"
)
QUOTE_URL = "https://hq.sinajs.cn/list=nf_{symbol}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://finance.sina.com.cn/",
}


def fetch_kline(symbol: str, timeout: int = 30) -> List[Dict]:
    """Fetch daily K-line history from Sina for a futures symbol like 'LC0' or 'NI0'."""
    r = requests.get(KLINE_URL, params={"symbol": symbol}, headers=HEADERS, timeout=timeout)
    r.raise_for_status()

    text = r.text.strip()
    # Some Sina endpoints wrap JSON in JSONP; strip any wrapper.
    if not text.startswith("["):
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            raise ValueError(f"Sina K-line for {symbol}: unparseable response")
        text = m.group(0)

    rows = json.loads(text)
    series: List[Dict] = []
    for row in rows:
        if len(row) < 5:
            continue
        try:
            series.append(
                {
                    "date": str(row[0]),  # 'YYYY-MM-DD'
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "value": float(row[4]),  # close
                    "volume": float(row[5]) if len(row) > 5 and row[5] not in (None, "") else None,
                }
            )
        except (TypeError, ValueError) as e:
            log.warning("Skipping row %r for %s: %s", row, symbol, e)
            continue

    series.sort(key=lambda p: p["date"])
    return series


def fetch_live_quote(symbol: str, timeout: int = 15) -> Optional[Dict]:
    """Fetch the latest live quote (today's open/high/low/last) from Sina hq endpoint.

    Useful when K-line lags by a day. Returns None if unavailable.
    """
    try:
        r = requests.get(QUOTE_URL.format(symbol=symbol), headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        # Format: var hq_str_nf_LC0="碳酸锂连续,094000,196560.00,...";
        m = re.search(r'"([^"]+)"', r.text)
        if not m:
            return None
        fields = m.group(1).split(",")
        if len(fields) < 8:
            return None
        # Sina futures field layout:
        #   0:name 1:time 2:open 3:high 4:low 5:prev_settle 6:bid 7:ask
        #   8:current(last) 9:settle 10:volume 11:open_interest 12:position 13:date
        last = float(fields[8]) if fields[8] else None
        return {
            "name": fields[0],
            "time": fields[1],
            "open": float(fields[2]) if fields[2] else None,
            "high": float(fields[3]) if fields[3] else None,
            "low": float(fields[4]) if fields[4] else None,
            "prev_settle": float(fields[5]) if fields[5] else None,
            "last": last,
            "date": fields[13] if len(fields) > 13 else None,
        }
    except Exception as e:
        log.warning("Live quote for %s failed: %s", symbol, e)
        return None


def _augment_with_live(series: List[Dict], symbol: str) -> List[Dict]:
    """If today's quote is fresher than last K-line row, append it."""
    if not series:
        return series
    quote = fetch_live_quote(symbol)
    if not quote or not quote.get("last") or not quote.get("date"):
        return series
    if quote["date"] > series[-1]["date"]:
        series.append(
            {
                "date": quote["date"],
                "open": quote["open"],
                "high": quote["high"],
                "low": quote["low"],
                "value": quote["last"],
                "volume": None,
            }
        )
    return series


def fetch_lithium() -> List[Dict]:
    """탄산리튬 (lithium carbonate) main contract on GFEX, CNY/t."""
    series = fetch_kline("LC0")
    return _augment_with_live(series, "LC0")


def fetch_nickel() -> List[Dict]:
    """니켈 (nickel) main contract on SHFE, CNY/t."""
    series = fetch_kline("NI0")
    return _augment_with_live(series, "NI0")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for fn, name in [(fetch_lithium, "lithium"), (fetch_nickel, "nickel")]:
        try:
            s = fn()
            if s:
                print(f"{name}: {len(s)} pts, latest={s[-1]['value']:,.0f} on {s[-1]['date']}")
            else:
                print(f"{name}: NO DATA")
        except Exception as e:
            print(f"{name}: ERROR {e}")
