"""Agent LinkedIn (best-effort, inactif sans cookies).

Anti-bot agressif + ToS : à activer manuellement (LINKEDIN_ENABLED=1 + cookies).
"""
from __future__ import annotations

import logging
from typing import List
from urllib.parse import quote

from bot.agents.base import BaseAgent
from bot.agents.social_pw import fetch_with_cookies
from bot.config import LINKEDIN_COOKIES, LINKEDIN_ENABLED
from bot.credibility.dna import offer_dna
from bot.credibility.expiry import infer_expiry
from bot.models import Offer
from normalizer import classify, matches_keywords
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

_QUERIES = ["free AI credits", "free LLM API", "AI free tier", "free AI certification"]


class LinkedInAgent(BaseAgent):
    name = "linkedin"
    network = "linkedin"

    def run(self) -> List[Offer]:
        if not LINKEDIN_ENABLED:
            log.info("[linkedin] inactif (LINKEDIN_ENABLED=0)")
            return []
        offers: List[Offer] = []
        for q in _QUERIES:
            url = (f"https://www.linkedin.com/search/results/content/"
                   f"?keywords={quote(q)}")
            html = fetch_with_cookies(url, LINKEDIN_COOKIES)
            if not html:
                continue
            for l in BaseScraper.extract_links(html, "https://www.linkedin.com"):
                blob = f"{l['text']} {l['href']}"
                if not matches_keywords(blob):
                    continue
                o = Offer(title=(l["text"] or l["href"])[:80], url=l["href"],
                          source="linkedin", agent="linkedin", provider="LinkedIn",
                          offer_type=classify(blob) or "promotion", network="linkedin",
                          description=l["text"][:300], keywords_matched=matches_keywords(blob))
                o.dna_hash = offer_dna(o)
                o.expires_at = infer_expiry(blob, o.found_at)
                o.provenance = [{"source": "linkedin", "url": l["href"],
                                 "found_at": o.found_at, "alive": True}]
                offers.append(o)
        log.info("[linkedin] %d offres", len(offers))
        return offers
