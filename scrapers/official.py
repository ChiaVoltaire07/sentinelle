"""Scraper des pages officielles des fournisseurs d'IA."""
from __future__ import annotations

import logging
from typing import List

from config import OFFICIAL_SOURCES
from models import Offer
from normalizer import classify, matches_keywords
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

# Mots-clés qui rendent un lien interne "intéressant" (pricing, free, docs...)
INTERESTING_LINK_HINTS = ("free", "pricing", "trial", "credit", "plan", "docs", "start", "tier")


class OfficialScraper(BaseScraper):
    name = "official"

    def run(self) -> List[Offer]:
        offers: List[Offer] = []
        for src in OFFICIAL_SOURCES:
            url = src["url"]
            log.info("[official] scraping %s", src["name"])
            html = self.fetch(url, js=src.get("js", False))
            if not html:
                continue
            text = self.extract_text(html)
            links = self.extract_links(html, url)

            # 1) La page elle-même si elle contient des mots-clés d'offre
            blob = text + " " + " ".join(l["text"] for l in links)
            kw = matches_keywords(blob)
            if kw:
                offers.append(Offer(
                    title=src["name"],
                    url=url,
                    source=self.name,
                    provider=src.get("provider", "Inconnu"),
                    offer_type=classify(blob) or "promotion",
                    description=text[:300],
                    keywords_matched=kw,
                ))

            # 2) Les liens internes pertinents
            for l in links:
                ltext = (l["text"] + " " + l["href"]).lower()
                if not any(h in ltext for h in INTERESTING_LINK_HINTS):
                    continue
                lkw = matches_keywords(l["text"] + " " + l["href"])
                if not lkw:
                    continue
                offers.append(Offer(
                    title=l["text"] or l["href"],
                    url=l["href"],
                    source=self.name,
                    provider=src.get("provider", "Inconnu"),
                    offer_type=classify(l["text"] + " " + l["href"]) or "promotion",
                    description=l["text"][:300],
                    keywords_matched=lkw,
                ))
        log.info("[official] %d offres trouvées", len(offers))
        return offers
