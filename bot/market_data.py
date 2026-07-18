"""Données de marché multi-providers (gratuit / freemium).

Priorité :
- Crypto → Binance (multi-hosts) → Yahoo BTC-USD → CoinGecko
- Actions → Yahoo → Stooq → Finnhub/Alpha Vantage si clé
"""
from __future__ import annotations

import logging
import os
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from config import DEFAULT_HEADERS, REQUEST_TIMEOUT

log = logging.getLogger(__name__)

_QUOTE_CACHE: Dict[str, Tuple[float, dict]] = {}
_CHART_CACHE: Dict[str, Tuple[float, dict]] = {}
QUOTE_TTL = 5.0
STOCK_QUOTE_TTL = 45.0
CHART_TTL = 60.0

CRYPTO_ALIASES = {
    "BTC": "BTCUSDT",
    "BITCOIN": "BTCUSDT",
    "ETH": "ETHUSDT",
    "ETHEREUM": "ETHUSDT",
    "BNB": "BNBUSDT",
    "SOL": "SOLUSDT",
    "SOLANA": "SOLUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "DOT": "DOTUSDT",
    "AVAX": "AVAXUSDT",
    "MATIC": "MATICUSDT",
    "LINK": "LINKUSDT",
    "ATOM": "ATOMUSDT",
    "LTC": "LTCUSDT",
}

BINANCE_REST_HOSTS = (
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
)

_MARKET_HEADERS = {
    **DEFAULT_HEADERS,
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 ScoutMarket/1.2",
}

COINGECKO_IDS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin",
}

RANGE_TO_YAHOO = {
    "1d": ("1d", "5m"),
    "5d": ("5d", "15m"),
    "1mo": ("1mo", "1d"),
    "3mo": ("3mo", "1d"),
    "6mo": ("6mo", "1d"),
    "1y": ("1y", "1d"),
    "5y": ("5y", "1wk"),
}

RANGE_TO_BINANCE = {
    "1d": ("5m", 288),
    "5d": ("15m", 480),
    "1mo": ("1h", 720),
    "3mo": ("4h", 540),
    "6mo": ("1d", 180),
    "1y": ("1d", 365),
    "5y": ("1w", 260),
}


def market_api_key() -> str:
    return (os.getenv("MARKET_API_KEY") or "").strip()


def market_provider() -> str:
    return (os.getenv("MARKET_PROVIDER") or "auto").strip().lower()


def normalize_symbol(symbol: str) -> str:
    s = (symbol or "").strip().upper().replace("-", "").replace("/", "")
    if s.endswith("USD") and not s.endswith("USDT") and len(s) > 3:
        base = s[:-3]
        if base in CRYPTO_ALIASES or (base + "USDT") in CRYPTO_ALIASES.values():
            return base + "USDT"
    return CRYPTO_ALIASES.get(s, s)


def is_crypto_symbol(symbol: str) -> bool:
    s = normalize_symbol(symbol)
    if s.endswith(("USDT", "BUSD")) and len(s) >= 6:
        return True
    base = s.replace("USDT", "").replace("BUSD", "")
    return base in CRYPTO_ALIASES or s in CRYPTO_ALIASES.values() or s in CRYPTO_ALIASES


def _binance_pair(symbol: str) -> str:
    pair = normalize_symbol(symbol)
    if not pair.endswith("USDT") and is_crypto_symbol(pair):
        pair = CRYPTO_ALIASES.get(pair, pair + "USDT")
    return pair


def yahoo_crypto_symbol(sym: str) -> str:
    s = normalize_symbol(sym)
    if s.endswith("USDT"):
        return s[:-4] + "-USD"
    return s


def _cache_get(cache: dict, key: str) -> Optional[dict]:
    hit = cache.get(key)
    if not hit:
        return None
    expires, payload = hit
    if time.time() > expires:
        return None
    return payload


def _cache_set(cache: dict, key: str, payload: dict, ttl: float) -> dict:
    cache[key] = (time.time() + ttl, payload)
    return payload


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def binance_quote(symbol: str) -> Optional[dict]:
    pair = _binance_pair(symbol)
    last_err = None
    for host in BINANCE_REST_HOSTS:
        try:
            r = requests.get(
                f"{host}/api/v3/ticker/24hr",
                params={"symbol": pair},
                headers=_MARKET_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code != 200:
                last_err = f"{host} HTTP {r.status_code}"
                continue
            d = r.json()
            price = float(d.get("lastPrice") or 0)
            if price <= 0:
                continue
            return {
                "symbol": pair,
                "price": price,
                "open": float(d.get("openPrice") or 0) or None,
                "high": float(d.get("highPrice") or 0) or None,
                "low": float(d.get("lowPrice") or 0) or None,
                "volume": float(d.get("volume") or 0) or None,
                "change_pct_24h": float(d.get("priceChangePercent") or 0),
                "source": "binance",
                "latency": "near_realtime",
                "delay_note": f"Binance ({host.split('//')[1]}) — REST near-realtime",
                "as_of": _now_iso(),
            }
        except Exception as e:
            last_err = str(e)
            continue
    log.warning("[market] Binance quote %s : %s", pair, last_err)
    return None


def binance_klines(symbol: str, interval: str = "1h", limit: int = 200) -> List[dict]:
    pair = _binance_pair(symbol)
    iv = "1w" if interval in ("1w", "1W") else interval
    last_err = None
    for host in BINANCE_REST_HOSTS:
        try:
            r = requests.get(
                f"{host}/api/v3/klines",
                params={"symbol": pair, "interval": iv, "limit": min(int(limit), 1000)},
                headers=_MARKET_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code != 200:
                last_err = f"{host} HTTP {r.status_code}"
                continue
            rows = r.json()
            if not isinstance(rows, list) or not rows:
                last_err = f"{host} empty"
                continue
            out = []
            for row in rows:
                out.append({
                    "ts": datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).isoformat(),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "price": float(row[4]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                    "source": "binance",
                })
            return out
        except Exception as e:
            last_err = str(e)
            continue
    log.warning("[market] Binance klines %s : %s", pair, last_err)
    return []


def yahoo_chart(ticker: str, range_: str = "3mo", interval: str = "1d") -> List[dict]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}"
    params = {"range": range_, "interval": interval}
    headers = {**_MARKET_HEADERS, "User-Agent": "Mozilla/5.0 ScoutMarket/1.2"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            return []
        r0 = result[0]
        timestamps = r0.get("timestamp") or []
        quote = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        points = []
        for i, ts in enumerate(timestamps):
            if i >= len(closes) or closes[i] is None:
                continue
            points.append({
                "ts": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "open": float(opens[i]) if i < len(opens) and opens[i] is not None else None,
                "high": float(highs[i]) if i < len(highs) and highs[i] is not None else None,
                "low": float(lows[i]) if i < len(lows) and lows[i] is not None else None,
                "price": float(closes[i]),
                "close": float(closes[i]),
                "volume": float(volumes[i]) if i < len(volumes) and volumes[i] is not None else None,
                "source": "yahoo",
            })
        return points
    except Exception as e:
        log.warning("[market] Yahoo chart %s : %s", ticker, e)
        return []


def yahoo_quote(ticker: str) -> Optional[dict]:
    points = yahoo_chart(ticker, range_="5d", interval="1d") or yahoo_chart(ticker, range_="1d", interval="5m")
    if not points:
        return None
    last, first = points[-1], points[0]
    change = None
    if first.get("price"):
        change = ((last["price"] - first["price"]) / first["price"]) * 100
    return {
        "symbol": ticker.upper(),
        "price": last["price"],
        "volume": last.get("volume"),
        "change_pct_24h": round(change, 3) if change is not None else None,
        "source": "yahoo",
        "latency": "delayed",
        "delay_note": "Yahoo Finance — retard typique ~15 min",
        "as_of": last.get("ts") or _now_iso(),
    }


def stooq_quote(ticker: str) -> Optional[dict]:
    sym = ticker.lower()
    if "." not in sym and not sym.endswith("us"):
        sym = f"{sym}.us"
    url = f"https://stooq.com/q/l/?s={urllib.parse.quote(sym)}&f=sd2t2ohlcv&h&e=csv"
    try:
        r = requests.get(url, headers=_MARKET_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        lines = r.text.strip().splitlines()
        if len(lines) < 2:
            return None
        parts = lines[1].split(",")
        if len(parts) < 7 or parts[6] in ("N/D", ""):
            return None
        price = float(parts[6])
        return {
            "symbol": ticker.upper(),
            "price": price,
            "open": float(parts[3]) if parts[3] not in ("N/D", "") else None,
            "high": float(parts[4]) if parts[4] not in ("N/D", "") else None,
            "low": float(parts[5]) if parts[5] not in ("N/D", "") else None,
            "volume": float(parts[7]) if len(parts) > 7 and parts[7] not in ("N/D", "") else None,
            "source": "stooq",
            "latency": "eod_or_delayed",
            "delay_note": "Stooq — backup historique",
            "as_of": f"{parts[1]}T{parts[2]}Z" if parts[1] != "N/D" else _now_iso(),
        }
    except Exception as e:
        log.warning("[market] Stooq %s : %s", ticker, e)
        return None


def finnhub_quote(ticker: str) -> Optional[dict]:
    key = market_api_key()
    if not key or market_provider() not in ("auto", "finnhub"):
        return None
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": ticker.upper(), "token": key},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        d = r.json()
        price = float(d.get("c") or 0)
        if price <= 0:
            return None
        prev = float(d.get("pc") or 0)
        change = ((price - prev) / prev * 100) if prev else None
        return {
            "symbol": ticker.upper(),
            "price": price,
            "high": float(d.get("h") or 0) or None,
            "low": float(d.get("l") or 0) or None,
            "open": float(d.get("o") or 0) or None,
            "change_pct_24h": round(change, 3) if change is not None else None,
            "source": "finnhub",
            "latency": "near_realtime",
            "delay_note": "Finnhub free tier",
            "as_of": _now_iso(),
        }
    except Exception as e:
        log.warning("[market] Finnhub %s : %s", ticker, e)
        return None


def alphavantage_quote(ticker: str) -> Optional[dict]:
    key = market_api_key()
    if not key or market_provider() not in ("auto", "alphavantage", "alpha_vantage"):
        return None
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "GLOBAL_QUOTE", "symbol": ticker.upper(), "apikey": key},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        g = (r.json() or {}).get("Global Quote") or {}
        price = float(g.get("05. price") or 0)
        if price <= 0:
            return None
        change = g.get("10. change percent", "").replace("%", "")
        return {
            "symbol": ticker.upper(),
            "price": price,
            "volume": float(g.get("06. volume") or 0) or None,
            "change_pct_24h": float(change) if change else None,
            "source": "alphavantage",
            "latency": "near_realtime",
            "delay_note": "Alpha Vantage free — ~25 req/jour",
            "as_of": _now_iso(),
        }
    except Exception as e:
        log.warning("[market] Alpha Vantage %s : %s", ticker, e)
        return None


def coingecko_quote(symbol: str) -> Optional[dict]:
    pair = _binance_pair(symbol)
    cid = COINGECKO_IDS.get(pair)
    if not cid:
        return None
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": cid, "vs_currencies": "usd", "include_24hr_change": "true"},
            headers=_MARKET_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        d = r.json().get(cid) or {}
        price = float(d.get("usd") or 0)
        if price <= 0:
            return None
        return {
            "symbol": pair,
            "price": price,
            "change_pct_24h": d.get("usd_24h_change"),
            "source": "coingecko",
            "latency": "delayed",
            "delay_note": "CoinGecko — fallback",
            "as_of": _now_iso(),
        }
    except Exception as e:
        log.warning("[market] CoinGecko quote %s : %s", symbol, e)
        return None


def coingecko_chart(symbol: str, range_: str = "3mo") -> List[dict]:
    pair = _binance_pair(symbol)
    cid = COINGECKO_IDS.get(pair)
    if not cid:
        return []
    days_map = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "5y": "max"}
    days = days_map.get(range_, 90)
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart",
            params={"vs_currency": "usd", "days": days},
            headers=_MARKET_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        prices = (r.json() or {}).get("prices") or []
        out = []
        for ts_ms, price in prices:
            px = float(price)
            out.append({
                "ts": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat(),
                "price": px,
                "close": px,
                "open": px,
                "high": px,
                "low": px,
                "source": "coingecko",
            })
        return out
    except Exception as e:
        log.warning("[market] CoinGecko chart %s : %s", symbol, e)
        return []


def get_quote(symbol: str, force: bool = False) -> Optional[dict]:
    sym = normalize_symbol(symbol)
    cache_key = f"q:{sym}"
    if not force:
        cached = _cache_get(_QUOTE_CACHE, cache_key)
        if cached:
            return cached

    if is_crypto_symbol(sym):
        quote = binance_quote(sym) or yahoo_quote(yahoo_crypto_symbol(sym)) or coingecko_quote(sym)
        ttl = QUOTE_TTL
    else:
        quote = finnhub_quote(sym)
        if not quote and market_provider() in ("alphavantage", "alpha_vantage"):
            quote = alphavantage_quote(sym)
        if not quote:
            quote = yahoo_quote(sym) or stooq_quote(sym)
        if not quote and market_provider() == "auto":
            quote = alphavantage_quote(sym)
        ttl = STOCK_QUOTE_TTL

    if quote:
        return _cache_set(_QUOTE_CACHE, cache_key, quote, ttl)
    return None


def get_chart(symbol: str, range_: str = "3mo", force: bool = False) -> dict:
    sym = normalize_symbol(symbol)
    range_ = range_ if range_ in RANGE_TO_YAHOO else "3mo"
    cache_key = f"c:{sym}:{range_}"
    if not force:
        cached = _cache_get(_CHART_CACHE, cache_key)
        # Ne jamais servir un cache vide
        if cached and cached.get("points"):
            return cached

    points: List[dict] = []
    source = "none"
    latency = "unknown"
    delay_note = ""

    if is_crypto_symbol(sym):
        iv, limit = RANGE_TO_BINANCE[range_]
        points = binance_klines(sym, interval=iv, limit=limit)
        if points:
            source, latency = "binance", "near_realtime"
            delay_note = "Binance klines — gratuit, quasi temps réel"
        if not points:
            yr, yi = RANGE_TO_YAHOO[range_]
            points = yahoo_chart(yahoo_crypto_symbol(sym), range_=yr, interval=yi)
            if points:
                source, latency = "yahoo", "delayed"
                delay_note = "Yahoo crypto (BTC-USD…) — fallback"
        if not points:
            points = coingecko_chart(sym, range_)
            if points:
                source, latency = "coingecko", "delayed"
                delay_note = "CoinGecko market_chart — fallback"
        if not points:
            q = get_quote(sym, force=True)
            if q and q.get("price"):
                points = [{
                    "ts": q.get("as_of") or _now_iso(),
                    "price": q["price"],
                    "close": q["price"],
                    "open": q.get("open") or q["price"],
                    "high": q.get("high") or q["price"],
                    "low": q.get("low") or q["price"],
                    "source": q.get("source") or "quote",
                }]
                source = q.get("source") or "quote"
                latency = q.get("latency") or "unknown"
                delay_note = "Point unique depuis quote (historique indisponible)"
    else:
        yr, yi = RANGE_TO_YAHOO[range_]
        points = yahoo_chart(sym, range_=yr, interval=yi)
        if points:
            source, latency = "yahoo", "delayed"
            delay_note = "Yahoo Finance — retard typique ~15 min"
        if not points:
            q = stooq_quote(sym) or get_quote(sym, force=True)
            if q and q.get("price"):
                points = [{
                    "ts": q.get("as_of") or _now_iso(),
                    "price": q["price"],
                    "close": q["price"],
                    "source": q.get("source") or "stooq",
                }]
                source = q.get("source") or "stooq"
                latency = q.get("latency") or "eod_or_delayed"
                delay_note = "Backup quote seule"

    sma20 = _sma([p["price"] for p in points], 20)
    payload = {
        "symbol": sym,
        "range": range_,
        "source": source,
        "latency": latency,
        "delay_note": delay_note,
        "points": points,
        "count": len(points),
        "sma20": sma20,
        "last_price": points[-1]["price"] if points else None,
        "as_of": points[-1]["ts"] if points else None,
    }
    # Cache uniquement les succès
    if points:
        return _cache_set(_CHART_CACHE, cache_key, payload, CHART_TTL)
    return payload


def _sma(values: List[float], window: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            chunk = values[i + 1 - window : i + 1]
            out.append(round(sum(chunk) / window, 6))
    return out


def providers_status() -> dict:
    return {
        "yahoo": {"free": True, "realtime": False, "note": "~15 min retard actions / crypto fallback"},
        "binance": {"free": True, "realtime": True, "note": "Crypto multi-hosts REST"},
        "stooq": {"free": True, "realtime": False, "note": "Backup historique actions"},
        "coingecko": {"free": True, "realtime": False, "note": "Fallback crypto quote+chart"},
        "finnhub": {
            "free": True,
            "realtime": True,
            "configured": bool(market_api_key()) and market_provider() in ("auto", "finnhub"),
            "note": "MARKET_API_KEY + MARKET_PROVIDER=finnhub",
        },
        "alphavantage": {
            "free": True,
            "realtime": True,
            "configured": bool(market_api_key()) and market_provider() in ("auto", "alphavantage", "alpha_vantage"),
            "note": "~25 req/jour",
        },
        "active_provider_pref": market_provider(),
        "has_market_api_key": bool(market_api_key()),
    }


def resolve_watch_asset(title: str, ticker: Optional[str] = None) -> Tuple[Optional[str], str]:
    if ticker:
        t = normalize_symbol(ticker)
        return t, ("crypto" if is_crypto_symbol(t) else "equity")
    low = title.lower()
    for name, pair in (("bitcoin", "BTCUSDT"), ("btc", "BTCUSDT"), ("ethereum", "ETHUSDT"), ("eth", "ETHUSDT"), ("solana", "SOLUSDT"), ("bnb", "BNBUSDT")):
        if name in low:
            return pair, "crypto"
    return None, "unknown"


def clear_market_caches() -> None:
    _QUOTE_CACHE.clear()
    _CHART_CACHE.clear()
