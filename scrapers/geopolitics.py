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


GEOPOLITICS_FEEDS = [
    {"name": "France 24 Monde", "url": "https://www.france24.com/fr/monde/rss"},
    {"name": "Courrier International", "url": "https://www.courrierinternational.com/feed/all/rss.xml"},
    {"name": "France Info International", "url": "https://www.francetvinfo.fr/monde.rss"},
]


class GeopoliticsScraper(BaseScraper):
    name = "geopolitics"

    def _extract_image(self, item, desc_soup) -> str:
        enc = item.find("enclosure")
        if enc and enc.get("url") and any(ext in enc["url"].lower() for ext in [".jpg", ".jpeg", ".png", ".webp", "image"]):
            return enc["url"]
        for tag in ["media:content", "media:thumbnail"]:
            m = item.find(tag)
            if m and m.get("url"):
                return m["url"]
        img = desc_soup.find("img")
        if img and img.get("src") and img["src"].startswith("http"):
            return img["src"]
        return "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=700&auto=format&fit=crop&q=80"

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
            desc_soup = BeautifulSoup(desc_raw, "html.parser")
            description = desc_soup.get_text().replace("&nbsp;", " ").strip()
            provider = "Google News"
            if " - " in title:
                title, provider = title.rsplit(" - ", 1)
            img_url = self._extract_image(item, desc_soup)
            out.append(Offer(
                title=title,
                url=link,
                source="geopolitics_news",
                provider=provider,
                offer_type="geopolitics",
                description=description or "Consultez l'analyse géopolitique complète.",
                keywords_matched=["geopolitics", query],
                image_url=img_url,
            ))
        return out

    def run(self, query: Optional[str] = None) -> List[Offer]:
        if query:
            return self.search(query)
        seen = set()
        out: List[Offer] = []

        # 1. Flux directs avec photos réelles
        for feed in GEOPOLITICS_FEEDS:
            try:
                xml = self.fetch_static(feed["url"])
                if not xml:
                    continue
                soup = BeautifulSoup(xml, "html.parser")
                for item in soup.find_all("item")[:8]:
                    title = (item.find("title").get_text() if item.find("title") else "").strip()
                    link = (item.find("link").get_text() if item.find("link") else "").strip()
                    if not title or link in seen:
                        continue
                    seen.add(link)
                    desc_raw = item.find("description").get_text() if item.find("description") else ""
                    desc_soup = BeautifulSoup(desc_raw, "html.parser")
                    description = desc_soup.get_text().replace("&nbsp;", " ").strip()
                    img_url = self._extract_image(item, desc_soup)
                    out.append(Offer(
                        title=title,
                        url=link,
                        source="geopolitics_news",
                        provider=feed["name"],
                        offer_type="geopolitics",
                        description=description or "Analyse des relations internationales.",
                        keywords_matched=["geopolitics", "international"],
                        image_url=img_url,
                    ))
            except Exception as e:
                log.warning("[geopolitics] Erreur flux %s: %s", feed["name"], e)

        # 2. Requêtes par mots-clés
        for q in DEFAULT_QUERIES:
            if len(out) >= 25:
                break
            for o in self.search(q, limit=4):
                if o.url in seen:
                    continue
                seen.add(o.url)
                out.append(o)
        return out
