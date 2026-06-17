"""Scrapers RSS génériques pour bourses, voyages, événements."""
from __future__ import annotations

import logging
import urllib.parse
from typing import List, Optional

from bs4 import BeautifulSoup

from models import Offer
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)


def _rss_search(scraper: BaseScraper, query: str, offer_type: str, source: str, limit: int = 20) -> List[Offer]:
    escaped = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={escaped}&hl=fr&gl=FR&ceid=FR:fr"
    xml = scraper.fetch_static(url)
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
            source=source,
            provider=provider,
            offer_type=offer_type,
            description=description or offer_type,
            keywords_matched=[offer_type, query[:40]],
        ))
    return out


class ScholarshipScraper(BaseScraper):
    name = "scholarships"

    def run(self, query: Optional[str] = None, country: Optional[str] = None) -> List[Offer]:
        parts = ["(scholarship OR bourse OR fellowship OR grant study)"]
        if query:
            parts.append(query)
        if country:
            parts.append(country)
        q = " ".join(parts)
        return _rss_search(self, q, "scholarship", "scholarship_rss")


class TravelOppScraper(BaseScraper):
    name = "travel"

    def run(self, query: Optional[str] = None, country: Optional[str] = None) -> List[Offer]:
        parts = ['("travel grant" OR mobilité OR "visa opportunity" OR "échange étudiant" OR "voyage professionnel")']
        if query:
            parts.append(query)
        if country:
            parts.append(country)
        return _rss_search(self, " ".join(parts), "travel", "travel_rss")


class EventsScraper(BaseScraper):
    name = "events"

    def run(self, query: Optional[str] = None, interest: Optional[str] = None, city: Optional[str] = None) -> List[Offer]:
        theme = interest or "tech OR finance OR media OR startup"
        parts = [f"(événement OR event OR conférence OR meetup OR hackathon) ({theme})"]
        if query:
            parts.append(query)
        if city:
            parts.append(city)
        return _rss_search(self, " ".join(parts), "event", "events_rss")
