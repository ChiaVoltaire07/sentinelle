"""Scraper géopolitique / conflits via Google News RSS."""
from __future__ import annotations

import logging
import urllib.parse
from typing import List, Optional

from bs4 import BeautifulSoup

from bot.models import Offer
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

DEFAULT_QUERIES = [
    "guerre OR conflit OR sanctions géopolitique",
    "Ukraine war OR Russia conflict",
    "Middle East conflict OR Gaza OR Israel",
    "Sahel conflict OR Sudan war",
    "China Taiwan geopolitics",
]


class GeopoliticsScraper(BaseScraper):
    name = "geopolitics"

    def search(self, query: str, limit: int = 12) -> List[Offer]:
        escaped = urllib.parse.quote_plus(query)
        url = f"https://news.google.com/rss/search?q={escaped}&hl=fr&gl=FR&ceid=FR:fr"
        log.info("[geopolitics] RSS %s", url)
        xml = self.fetch_static(url)
        if not xml:
            return []
        soup = BeautifulSoup(xml, "html.parser")
        out: List[Offer] = []
        for item in soup.find_all("item")[:limit]:
            title = item.find("title").get_text() if item.find("title") else ""
            link = item.find("link").get_text() if item.find("link") else ""
            desc_raw = item.find("description").get_text() if item.find("description") else ""
            description = BeautifulSoup(desc_raw, "html.parser").get_text().replace("&nbsp;", " ").strip()
            provider = "Google News"
            if " - " in title:
                title, provider = title.rsplit(" - ", 1)
            out.append(Offer(
                title=title,
                url=link,
                source="geopolitics_news",
                provider=provider,
                offer_type="geopolitics",
                description=description or "Actu géopolitique",
                keywords_matched=["geopolitics", query],
            ))
        return out

    def run(self, query: Optional[str] = None) -> List[Offer]:
        if query:
            return self.search(query)
        seen = set()
        out: List[Offer] = []
        for q in DEFAULT_QUERIES:
            for o in self.search(q, limit=6):
                if o.url in seen:
                    continue
                seen.add(o.url)
                out.append(o)
        return out[:30]
