"""Scraper probabilités d'événements via Polymarket Gamma API."""
from __future__ import annotations

import json
import logging
from typing import List, Optional

import requests

from bot.models import Offer
from config import DEFAULT_HEADERS, REQUEST_TIMEOUT
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"


class PredictionsScraper(BaseScraper):
    name = "predictions"

    def fetch_markets(self, limit: int = 30, query: Optional[str] = None) -> List[dict]:
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "order": "volume24hr",
            "ascending": "false",
        }
        if query:
            params["query"] = query
        try:
            resp = requests.get(GAMMA_MARKETS, params=params, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("markets", data.get("data", []))
        except Exception as e:
            log.warning("[predictions] Polymarket échec : %s", e)
            return []

    @staticmethod
    def _yes_probability(market: dict) -> Optional[float]:
        prices = market.get("outcomePrices") or market.get("outcome_prices")
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except Exception:
                prices = None
        if isinstance(prices, list) and prices:
            try:
                return float(prices[0]) * 100.0
            except (TypeError, ValueError):
                return None
        # fallback lastTradePrice
        p = market.get("lastTradePrice")
        if p is not None:
            try:
                return float(p) * 100.0
            except (TypeError, ValueError):
                return None
        return None

    def run(self, query: Optional[str] = None) -> List[Offer]:
        markets = self.fetch_markets(query=query)
        out: List[Offer] = []
        q = (query or "").lower().strip()
        for m in markets:
            question = m.get("question") or m.get("title") or "Marché"
            if q and q not in question.lower() and q not in (m.get("slug") or ""):
                continue
            prob = self._yes_probability(m)
            volume = m.get("volume24hr") or m.get("volume") or 0
            slug = m.get("slug") or m.get("conditionId") or ""
            url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"
            prob_txt = f"{prob:.1f}% Yes" if prob is not None else "n/d"
            desc = f"Probabilité : {prob_txt} · Volume 24h : {volume} · Source Polymarket (pas un conseil financier)"
            out.append(Offer(
                title=question,
                url=url,
                source="polymarket",
                provider="Polymarket",
                offer_type="prediction",
                description=desc,
                keywords_matched=["prediction", "polymarket"],
            ))
        return out[:40]
