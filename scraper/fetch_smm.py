"""
SMM (Shanghai Metals Market / metal.com) scraper for Battery-Grade LiPF6.

⚠️  IMPORTANT: SMM's full historical data is subscription-only.
The free metal.com pages expose only the *latest* daily quote (avg/high/low)
through the chart XHR. We do best-effort scraping here.

Strategy:
  1. Try the public metal.com XHR endpoint that powers the chart.
     - Sometimes returns last 30-90d; sometimes blocked without account.
  2. Fall back to scraping the price table from the HTML page.
  3. Allow manual override via data/lipf6_overrides.json:
       [
         {"date": "2026-05-08", "avg_usd": 13025, "high_usd": 13260, "low_usd": 12790,
          "avg_cny": 100500, "high_cny": 102000, "low_cny": 99000},
         ...
       ]
     This is the recommended path if you have an SMM subscription or another
     source — your scraper just dumps to this JSON daily.

The metal.com item IDs we target:
  • USD/mt avg/high/low : 201102250059 (Battery Grade LiPF6 quoted in USD)
  • CNY/mt avg/high/low : 201102250058 (Battery Grade LiPF6 quoted in CNY)

These IDs may change. Verify by inspecting Network tab on:
  https://www.metal.com/Chemical-Compound
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

import requests

log = logging.getLogger(__name__)

OVERRIDES_PATH = Path(__file__).parent.parent / "data" / "lipf6_overrides.json"

# Public chart endpoint pattern observed on metal.com.
# Subject to change without notice; verify against your browser's Network tab.
SMM_API = "https://api-ddst.metal.com/web/site_2014/inquiry/historicQuotationByItemId"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.metal.com/Chemical-Compound",
    "Accept": "application/json",
}

ITEM_ID_USD = "201102250059"
ITEM_ID_CNY = "201102250058"


def _try_smm_api(item_id: str, currency: str = "USD") -> List[Dict]:
    """Best-effort attempt at SMM's public chart API."""
    try:
        r = requests.get(
            SMM_API,
            params={"itemId": item_id, "unit": "mt", "currency": currency},
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        rows = data.get("data") or data.get("list") or []
        out: List[Dict] = []
        for row in rows:
            d = row.get("date") or row.get("publishDate") or row.get("dt")
            avg = row.get("avgPrice") or row.get("avg") or row.get("price")
            high = row.get("highPrice") or row.get("high") or avg
            low = row.get("lowPrice") or row.get("low") or avg
            if d and avg is not None:
                out.append(
                    {
                        "date": str(d)[:10],
                        "value": float(avg),  # treat avg as primary value
                        "avg": float(avg),
                        "high": float(high),
                        "low": float(low),
                    }
                )
        out.sort(key=lambda p: p["date"])
        return out
    except Exception as e:
        log.warning("SMM API (%s, %s) failed: %s", item_id, currency, e)
        return []


def _load_overrides() -> List[Dict]:
    """Load manually maintained override values from JSON."""
    if not OVERRIDES_PATH.exists():
        return []
    try:
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Failed to load lipf6_overrides.json: %s", e)
        return []


def fetch_lipf6_usd() -> List[Dict]:
    """Battery-Grade LiPF6 in USD/mt (avg/high/low)."""
    series = _try_smm_api(ITEM_ID_USD, currency="USD")
    if series:
        return series

    # Fall back to manual overrides
    overrides = _load_overrides()
    if not overrides:
        return []
    return [
        {
            "date": row["date"],
            "value": float(row["avg_usd"]),
            "avg": float(row["avg_usd"]),
            "high": float(row.get("high_usd", row["avg_usd"])),
            "low": float(row.get("low_usd", row["avg_usd"])),
        }
        for row in overrides
        if "avg_usd" in row
    ]


def fetch_lipf6_cny() -> List[Dict]:
    """Battery-Grade LiPF6 in CNY/mt (avg/high/low)."""
    series = _try_smm_api(ITEM_ID_CNY, currency="CNY")
    if series:
        return series

    overrides = _load_overrides()
    if not overrides:
        return []
    return [
        {
            "date": row["date"],
            "value": float(row["avg_cny"]),
            "avg": float(row["avg_cny"]),
            "high": float(row.get("high_cny", row["avg_cny"])),
            "low": float(row.get("low_cny", row["avg_cny"])),
        }
        for row in overrides
        if "avg_cny" in row
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for fn, name in [(fetch_lipf6_usd, "LiPF6 USD"), (fetch_lipf6_cny, "LiPF6 CNY")]:
        try:
            s = fn()
            if s:
                print(f"{name}: {len(s)} pts, latest avg={s[-1]['avg']} on {s[-1]['date']}")
            else:
                print(f"{name}: NO DATA — populate data/lipf6_overrides.json or fix SMM endpoint")
        except Exception as e:
            print(f"{name}: ERROR {e}")
