"""
Main orchestrator — fetches all 6 commodities and writes data/current.json.

Schema (consumed by the React dashboard):
{
  "as_of": "2026-05-10",
  "updated_at": "2026-05-10T08:00:00Z",
  "commodities": {
    "lithium": {
      "title": "탄산리튬 (LC0)",
      "unit": "CNY/t",
      "source": "Sina Finance",
      "source_url": "...",
      "decimals": 0,
      "type": "single" | "range",
      "latest": 196560.0,
      "points": 245,
      "returns": {"1D": -1.26, "1W": 10.04, "1M": 24.52, "3M": 9.44, "6M": 140.76},
      "series": [{"date": "2025-08-01", "value": 65000}, ...]
    },
    ...
  }
}
"""
from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

from fetch_yahoo import fetch_copper, fetch_aluminum
from fetch_sina import fetch_lithium, fetch_nickel
from fetch_smm import fetch_lipf6_usd, fetch_lipf6_cny

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT = DATA_DIR / "current.json"

# Trading-day approximations for return horizons.
HORIZONS = {"1D": 1, "1W": 5, "1M": 22, "3M": 66, "6M": 132}


def compute_returns(series: List[Dict], value_key: str = "value") -> Dict[str, Optional[float]]:
    if not series:
        return {k: None for k in HORIZONS}
    latest = series[-1].get(value_key)
    if latest is None:
        return {k: None for k in HORIZONS}
    out: Dict[str, Optional[float]] = {}
    for label, days in HORIZONS.items():
        if len(series) > days:
            past = series[-1 - days].get(value_key)
            if past and past > 0:
                out[label] = round(((latest - past) / past) * 100, 2)
            else:
                out[label] = None
        else:
            out[label] = None
    return out


COMMODITIES = [
    {
        "id": "lithium",
        "title": "탄산리튬 (LC0)",
        "unit": "CNY/t",
        "source": "Sina Finance",
        "source_url": "https://finance.sina.com.cn/futures/quotes/LC0.shtml",
        "decimals": 0,
        "type": "single",
        "fetch": fetch_lithium,
    },
    {
        "id": "nickel",
        "title": "니켈 SHFE (NI0)",
        "unit": "CNY/t",
        "source": "Sina Finance",
        "source_url": "https://finance.sina.com.cn/futures/quotes/NI0.shtml",
        "decimals": 0,
        "type": "single",
        "fetch": fetch_nickel,
    },
    {
        "id": "copper",
        "title": "구리 (COMEX HG, LME 대리)",
        "unit": "USD/lb",
        "source": "Yahoo Finance",
        "source_url": "https://finance.yahoo.com/quote/HG=F",
        "decimals": 3,
        "type": "single",
        "fetch": fetch_copper,
    },
    {
        "id": "aluminum",
        "title": "알루미늄 (COMEX ALI, LME 대리)",
        "unit": "USD/t",
        "source": "Yahoo Finance",
        "source_url": "https://finance.yahoo.com/quote/ALI=F",
        "decimals": 0,
        "type": "single",
        "fetch": fetch_aluminum,
    },
    {
        "id": "lipf6_usd",
        "title": "LiPF6 — SMM (USD/mt)",
        "unit": "USD/mt",
        "source": "SMM",
        "source_url": "https://www.metal.com/Chemical-Compound",
        "decimals": 3,
        "type": "range",
        "fetch": fetch_lipf6_usd,
    },
    {
        "id": "lipf6_cny",
        "title": "LiPF6 — SMM (CNY/mt, 구간)",
        "unit": "CNY/mt",
        "source": "SMM",
        "source_url": "https://www.metal.com/Chemical-Compound",
        "decimals": 0,
        "type": "range",
        "fetch": fetch_lipf6_cny,
    },
]


def build_commodity(spec: Dict, *, log: logging.Logger) -> Optional[Dict]:
    log.info("→ %-12s %s", spec["id"], "fetching...")
    try:
        series = spec["fetch"]()
    except Exception as e:
        log.error("✗ %-12s FETCH FAILED: %s", spec["id"], e)
        log.debug(traceback.format_exc())
        return None

    if not series:
        log.warning("✗ %-12s no data returned", spec["id"])
        return None

    latest_row = series[-1]
    if spec["type"] == "range":
        latest = latest_row.get("avg") or latest_row.get("value")
        returns = compute_returns(series, value_key="avg")
    else:
        latest = latest_row.get("value")
        returns = compute_returns(series, value_key="value")

    log.info("✓ %-12s %d pts | latest=%s | 1D=%s%% 6M=%s%%",
             spec["id"], len(series), latest, returns.get("1D"), returns.get("6M"))

    return {
        "title": spec["title"],
        "unit": spec["unit"],
        "source": spec["source"],
        "source_url": spec["source_url"],
        "decimals": spec["decimals"],
        "type": spec["type"],
        "latest": latest,
        "points": len(series),
        "returns": returns,
        "series": series,
    }


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("scraper")

    log.info("=" * 60)
    log.info("Battery materials scraper starting")
    log.info("=" * 60)

    output = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "commodities": {},
        "errors": [],
    }

    success_count = 0
    for spec in COMMODITIES:
        result = build_commodity(spec, log=log)
        if result is not None:
            output["commodities"][spec["id"]] = result
            success_count += 1
        else:
            output["errors"].append(spec["id"])

    DATA_DIR.mkdir(exist_ok=True, parents=True)

    # Atomic write: write to .tmp then rename
    tmp = OUT.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    tmp.replace(OUT)

    log.info("=" * 60)
    log.info("Wrote %s — %d/%d commodities", OUT, success_count, len(COMMODITIES))
    log.info("=" * 60)

    # Exit non-zero if more than half failed (CI signal)
    if success_count < len(COMMODITIES) // 2:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
