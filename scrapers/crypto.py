"""Scraper crypto : CoinGecko markets + Google News RSS crypto."""
from __future__ import annotations

import logging
import urllib.parse
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from bot.models import Offer
from config import DEFAULT_HEADERS, REQUEST_TIMEOUT
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"


class CryptoScraper(BaseScraper):
    name = "crypto"

    def fetch_markets(self, vs_currency: str = "usd", per_page: int = 20) -> List[dict]:
        # Prefer Binance 24h tickers (near-realtime) then enrich names via CoinGecko
        binance_rows = self._binance_top(per_page)
        if binance_rows:
            return binance_rows
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        }
        try:
            resp = requests.get(COINGECKO_URL, params=params, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.warning("[crypto] CoinGecko échec : %s", e)
            return []

    def _binance_top(self, limit: int = 20) -> List[dict]:
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            rows = resp.json()
            usdt = [
                r for r in rows
                if str(r.get("symbol", "")).endswith("USDT")
                and float(r.get("quoteVolume") or 0) > 0
            ]
            usdt.sort(key=lambda x: float(x.get("quoteVolume") or 0), reverse=True)
            out = []
            for r in usdt[:limit]:
                sym = r["symbol"]
                base = sym.replace("USDT", "")
                out.append({
                    "id": base.lower(),
                    "symbol": base.lower(),
                    "name": base,
                    "current_price": float(r.get("lastPrice") or 0),
                    "price_change_percentage_24h": float(r.get("priceChangePercent") or 0),
                    "total_volume": float(r.get("quoteVolume") or 0),
                    "_source": "binance",
                })
            return out
        except Exception as e:
            log.warning("[crypto] Binance ticker échec : %s", e)
            return []

    def markets_as_offers(self, query: Optional[str] = None) -> List[Offer]:
        markets = self.fetch_markets()
        out: List[Offer] = []
        q = (query or "").lower().strip()
        for m in markets:
            name = m.get("name") or ""
            symbol = (m.get("symbol") or "").upper()
            if q and q not in name.lower() and q not in symbol.lower() and q not in (m.get("id") or ""):
                continue
            price = m.get("current_price")
            change = m.get("price_change_percentage_24h")
            vol = m.get("total_volume")
            src = m.get("_source") or "coingecko"
            desc = (
                f"Prix : {price} USD · 24h : {change:+.2f}% · Volume : {vol} · source {src}"
                if change is not None
                else f"Prix : {price} USD · Volume : {vol} · source {src}"
            )
            out.append(Offer(
                title=f"{name} ({symbol})",
                url=(
                    f"https://www.binance.com/en/trade/{symbol}_USDT"
                    if src == "binance"
                    else f"https://www.coingecko.com/en/coins/{m.get('id')}"
                ),
                source=src,
                provider="Binance" if src == "binance" else "CoinGecko",
                offer_type="crypto",
                description=desc,
                keywords_matched=["crypto", symbol.lower(), name.lower(), src],
            ))
        return out

    def news(self, query: str = "cryptocurrency OR bitcoin OR ethereum") -> List[Offer]:
        escaped = urllib.parse.quote_plus(query)
        url = f"https://news.google.com/rss/search?q={escaped}&hl=fr&gl=FR&ceid=FR:fr"
        xml = self.fetch_static(url)
        if not xml:
            return []
        soup = BeautifulSoup(xml, "html.parser")
        out: List[Offer] = []
        for item in soup.find_all("item")[:12]:
            title = item.find("title").get_text() if item.find("title") else ""
            link = item.find("link").get_text() if item.find("link") else ""
            provider = "Google News"
            if " - " in title:
                title, provider = title.rsplit(" - ", 1)
            out.append(Offer(
                title=title,
                url=link,
                source="crypto_news",
                provider=provider,
                offer_type="crypto",
                description="Actu crypto",
                keywords_matched=["crypto", "news"],
            ))
        return out

    def run(self, query: Optional[str] = None) -> List[Offer]:
        offers = self.markets_as_offers(query)
        news_q = query if query else "cryptocurrency OR bitcoin OR ethereum"
        offers.extend(self.news(news_q))
        return offers
