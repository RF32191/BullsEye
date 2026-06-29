"""Aggregated crypto spot prices — CoinGecko primary for exchange-aligned quotes."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

import httpx

_USER_AGENT = "Mozilla/5.0 (compatible; BullseyeAI/1.0)"
_CACHE: dict[str, tuple[float, dict]] = {}
_FRESH_TTL = 8
_NORMAL_TTL = 45

# Yahoo symbol -> CoinGecko id
COINGECKO_IDS: dict[str, str] = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "SOL-USD": "solana",
    "XRP-USD": "ripple",
    "ADA-USD": "cardano",
    "AVAX-USD": "avalanche-2",
    "DOGE-USD": "dogecoin",
    "LINK-USD": "chainlink",
    "DOT-USD": "polkadot",
    "MATIC-USD": "matic-network",
    "BNB-USD": "binancecoin",
    "LTC-USD": "litecoin",
    "SHIB-USD": "shiba-inu",
}


def _cache_get(key: str, ttl: int) -> dict | None:
    entry = _CACHE.get(key)
    if entry and time.time() - entry[0] < ttl:
        return entry[1]
    return None


def _cache_set(key: str, value: dict) -> dict:
    _CACHE[key] = (time.time(), value)
    return value


def _fetch_coingecko_batch(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(ids),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_last_updated_at": "true",
    }
    with httpx.Client(timeout=15.0, headers={"User-Agent": _USER_AGENT}) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def crypto_quote(symbol: str, fresh: bool = False) -> dict | None:
    sym = symbol.upper()
    coin_id = COINGECKO_IDS.get(sym)
    if not coin_id:
        base = sym.replace("-USD", "").replace("-USDT", "")
        coin_id = COINGECKO_IDS.get(f"{base}-USD")
    if not coin_id:
        return None

    ttl = _FRESH_TTL if fresh else _NORMAL_TTL
    cache_key = f"cg:{coin_id}:{'fresh' if fresh else 'norm'}"
    cached = _cache_get(cache_key, ttl)
    if cached:
        return cached

    try:
        payload = await asyncio.to_thread(_fetch_coingecko_batch, [coin_id])
    except Exception:
        return None

    row = payload.get(coin_id)
    if not row or row.get("usd") is None:
        return None

    price = float(row["usd"])
    change_pct = float(row.get("usd_24h_change") or 0)
    change = price * (change_pct / 100) if change_pct else 0.0
    fetched_at = datetime.utcfromtimestamp(row.get("last_updated_at") or int(time.time())).isoformat()

    result = {
        "symbol": sym,
        "name": sym.replace("-USD", ""),
        "price": round(price, 6 if price < 1 else 4),
        "change": round(change, 6 if abs(change) < 1 else 4),
        "changesPercentage": round(change_pct, 2),
        "source": "CoinGecko (aggregated exchange index)",
        "is_live": True,
        "fetched_at": fetched_at,
        "price_note": (
            "Crypto prices aggregate across major exchanges. Your broker (e.g. Robinhood) "
            "may show a different last trade or spread-adjusted price."
        ),
    }
    return _cache_set(cache_key, result)
