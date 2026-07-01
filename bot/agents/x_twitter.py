"""Agent X / Twitter (best-effort, inactif sans cookies).

L'API free est post-only ; le scraping nécessite tes cookies de session.
"""
from __future__ import annotations

import logging
from typing import List
from urllib.parse import quote

from bot.agents.base import BaseAgent
from bot.agents.social_pw import fetch_with_cookies
from bot.config import X_COOKIES, X_ENABLED
from bot.credibility.dna import offer_dna
from bot.credibility.expiry import infer_expiry
from bot.models import Offer
from normalizer import classify, matches_keywords
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

_QUERIES = ["free AI credits", "free LLM API", "AI free tier", "free AI course"]


class XAgent(BaseAgent):
    name = "x"
    network = "x"

    def run(self) -> List[Offer]:
        if not X_ENABLED:
            log.info("[x] inactif (X_ENABLED=0)")
            return []
        offers: List[Offer] = []
        for q in _QUERIES:
            url = f"https://twitter.com/search?q={quote(q)}&f=live"
            html = fetch_with_cookies(url, X_COOKIES)
            if not html:
                continue
            for l in BaseScraper.extract_links(html, "https://twitter.com"):
                href = l["href"]
                if "/status/" not in href:
                    continue
                blob = f"{l['text']} {href}"
                if not matches_keywords(blob):
                    continue
                o = Offer(title=(l["text"] or href)[:80], url=href, source="x",
                          agent="x", provider="X", offer_type=classify(blob) or "promotion",
                          network="x", description=l["text"][:300],
                          keywords_matched=matches_keywords(blob))
                o.dna_hash = offer_dna(o)
                o.expires_at = infer_expiry(blob, o.found_at)
                o.provenance = [{"source": "x", "url": href, "found_at": o.found_at, "alive": True}]
                offers.append(o)
        log.info("[x] %d offres", len(offers))
        return offers
