"""
Sina Finance scraper for Chinese commodity futures (robust version).

Strategy for resilience:
  1. Multiple symbol variants (uppercase/lowercase/specific contract month)
  2. Retry with exponential backoff on transient failures
  3. User-Agent rotation
  4. Detailed logging — every attempt is logged for post-mortem diagnosis

Endpoints:
  • K-line daily: stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine
  • Live quote:   hq.sinajs.cn/list=nf_SYMBOL
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from typing import List, Dict, Optional

import requests

log = logging.getLogger(__name__)

KLINE_URL_PRIMARY = (
    "https://stock2.finance.sina.com.cn/futures/api/json.php"
    "/IndexService.getInnerFuturesDailyKLine"
)
QUOTE_URL = "https://hq.sinajs.cn/list=nf_{symbol}"

USER_AGENTS = [
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
     "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) "
     "Gecko/20100101 Firefox/124.0"),
]


def _build_headers(ua_index: int = 0) -> dict:
    return {
        "User-Agent": USER_AGENTS[ua_index % len(USER_AGENTS)],
        "Referer": "https://finance.sina.com.cn/",
        "Origin": "https://finance.sina.com.cn",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,ko;q=0.6",
        "Connection": "keep-alive",
    }


def _current_contract_months(prefix: str) -> List[str]:
    """Generate plausible specific contract symbols like LC2509, LC2601, LC2605.

    GFEX/SHFE futures use YYMM format. We try months around current date since
    main contracts rotate. Most-liquid contracts are typically 1-6 months ahead.
    """
    now = datetime.now()
    out = []
    # Prefer near-term contracts (most liquid), then expand
    offsets = [1, 3, 5, 7, 9, 11, -1, -3, 2, 4, 6, 8, 10, 12]
    for offset in offsets:
        m_total = now.year * 12 + (now.month - 1) + offset
        y = m_total // 12
        m = (m_total % 12) + 1
        out.append(f"{prefix}{y % 100:02d}{m:02d}")
    return out


def _symbol_variants(base: str) -> List[str]:
    """Generate symbol variants in order of preference."""
    base_upper = base.upper()
    variants = [base_upper, base.lower()]
    if base_upper.endswith("0"):
        prefix = base_upper[:-1]
        variants.extend(_current_contract_months(prefix))
    return variants


def _try_fetch_kline(symbol: str, ua_index: int, timeout: int = 25) -> Optional[List[Dict]]:
    """Single attempt at K-line fetch. Returns parsed series or None on failure."""
    try:
        r = requests.get(
            KLINE_URL_PRIMARY,
            params={"symbol": symbol},
            headers=_build_headers(ua_index),
            timeout=timeout,
        )
    except requests.RequestException as e:
        log.warning("    ✗ %s ua=%d: network error: %s", symbol, ua_index, e)
        return None

    if r.status_code != 200:
        log.warning("    ✗ %s ua=%d: HTTP %d (body=%r)",
                    symbol, ua_index, r.status_code, r.text[:120])
        return None

    text = r.text.strip()
    if not text:
        log.warning("    ✗ %s ua=%d: empty body", symbol, ua_index)
        return None

    if text in ("null", "[]", "[null]"):
        log.warning("    ✗ %s ua=%d: empty result (response=%r)", symbol, ua_index, text)
        return None

    if not text.startswith("["):
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            log.warning("    ✗ %s ua=%d: unparseable response (first 120=%r)",
                        symbol, ua_index, text[:120])
            return None
        text = m.group(0)

    try:
        rows = json.loads(text)
    except json.JSONDecodeError as e:
        log.warning("    ✗ %s ua=%d: JSON parse error: %s", symbol, ua_index, e)
        return None

    if not rows or not isinstance(rows, list):
        log.warning("    ✗ %s ua=%d: empty or non-list rows", symbol, ua_index)
        return None

    series: List[Dict] = []
    for row in rows:
        if not row or len(row) < 5:
            continue
        try:
            series.append({
                "date": str(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "value": float(row[4]),
                "volume": float(row[5]) if len(row) > 5 and row[5] not in (None, "") else None,
            })
        except (TypeError, ValueError):
            continue

    series.sort(key=lambda p: p["date"])

    if len(series) < 5:
        log.warning("    ✗ %s ua=%d: too few valid rows (%d)", symbol, ua_index, len(series))
        return None

    return series


def fetch_kline(base_symbol: str, max_attempts: int = 8) -> List[Dict]:
    """Fetch K-line with multiple variants and retries.

    Strategy: try (variant, UA) pairs until one succeeds.
    Order: prefer original symbol first, then variants. Within each variant,
    cycle through UAs. Backoff between attempts to be polite.
    """
    variants = _symbol_variants(base_symbol)
    log.info("  Sina K-line for %s — variants to try: %s", base_symbol, variants[:8])

    attempt = 0
    for variant in variants:
        for ua_idx in range(len(USER_AGENTS)):
            attempt += 1
            if attempt > max_attempts:
                raise ValueError(
                    f"Sina K-line for {base_symbol}: exhausted {max_attempts} attempts"
                )

            log.info("    attempt %d: symbol=%s ua=%d", attempt, variant, ua_idx)
            series = _try_fetch_kline(variant, ua_idx)
            if series:
                log.info("    ✓ SUCCESS via variant=%s ua=%d (%d pts, latest=%s on %s)",
                         variant, ua_idx,
                         series[-1]["value"], series[-1]["date"], len(series))
                return series

            # Polite backoff between failed attempts
            wait = min(2 ** (min(attempt - 1, 3)), 8)
            time.sleep(wait)

    raise ValueError(
        f"Sina K-line for {base_symbol}: all attempts failed "
        f"(tried {len(variants)} variants × {len(USER_AGENTS)} UAs)"
    )


def fetch_live_quote(symbol: str, timeout: int = 15) -> Optional[Dict]:
    """Fetch latest live quote. Non-fatal — returns None on failure."""
    for ua_idx in range(2):
        try:
            r = requests.get(
                QUOTE_URL.format(symbol=symbol),
                headers=_build_headers(ua_idx),
                timeout=timeout,
            )
            if r.status_code != 200:
                continue
            m = re.search(r'"([^"]+)"', r.text)
            if not m:
                continue
            fields = m.group(1).split(",")
            if len(fields) < 14:
                continue
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
            log.debug("    live quote %s ua=%d failed: %s", symbol, ua_idx, e)
            continue
    return None


def _augment_with_live(series: List[Dict], symbol: str) -> List[Dict]:
    if not series:
        return series
    quote = fetch_live_quote(symbol)
    if not quote or not quote.get("last") or not quote.get("date"):
        return series
    if quote["date"] > series[-1]["date"]:
        series.append({
            "date": quote["date"],
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "value": quote["last"],
            "volume": None,
        })
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
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    for fn, name in [(fetch_lithium, "lithium"), (fetch_nickel, "nickel")]:
        try:
            s = fn()
            print(f"\n{name}: ✓ {len(s)} pts, latest={s[-1]['value']:,.0f} on {s[-1]['date']}\n")
        except Exception as e:
            print(f"\n{name}: ✗ ERROR {e}\n")
