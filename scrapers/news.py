"""Scraper d'actualités via Google News RSS pour différentes thématiques."""
from __future__ import annotations

import logging
import html
from typing import List
from bs4 import BeautifulSoup

from models import Offer
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

NEWS_SOURCES = {
    "top": {"name": "Top Actu", "url": "https://news.google.com/rss?hl=fr&gl=FR&ceid=FR:fr"},
    "tech": {"name": "Actu Tech", "url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=fr&gl=FR&ceid=FR:fr"},
    "sport": {"name": "Actu Sport", "url": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=fr&gl=FR&ceid=FR:fr"},
    "finance": {"name": "Actu Finance", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=fr&gl=FR&ceid=FR:fr"},
    "politic": {"name": "Actu Politique", "url": "https://news.google.com/rss/search?q=politique&hl=fr&gl=FR&ceid=FR:fr"},
    "economie": {"name": "Actu Économie", "url": "https://news.google.com/rss/search?q=economie&hl=fr&gl=FR&ceid=FR:fr"},
    "ia": {"name": "Actu IA", "url": "https://news.google.com/rss/search?q=intelligence+artificielle+OR+AI+OR+LLM&hl=fr&gl=FR&ceid=FR:fr"},
}


class NewsScraper(BaseScraper):
    name = "news"

    def run_category(self, category: str) -> List[Offer]:
        """Scrape une catégorie d'actualités spécifique."""
        cfg = NEWS_SOURCES.get(category)
        if not cfg:
            log.warning("[news] Catégorie inconnue : %s", category)
            return []

        url = cfg["url"]
        log.info("[news] scraping category %s (%s)", category, cfg["name"])
        xml_content = self.fetch_static(url)
        if not xml_content:
            return []

        soup = BeautifulSoup(xml_content, "html.parser")
        items = soup.find_all("item")
        offers: List[Offer] = []

        for item in items[:15]:  # Limite à 15 actualités par thématique
            title = item.find("title").get_text() if item.find("title") else ""
            link = item.find("link").get_text() if item.find("link") else ""
            
            # Google News RSS encode la description en HTML
            desc_raw = item.find("description").get_text() if item.find("description") else ""
            desc_soup = BeautifulSoup(desc_raw, "html.parser")
            description = desc_soup.get_text()
            
            # Nettoyage sommaire de la description
            description = description.replace("&nbsp;", " ").strip()
            
            # Séparer le titre du média
            provider = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                provider = parts[1]

            offers.append(Offer(
                title=title,
                url=link,
                source=f"news_{category}",
                provider=provider,
                offer_type="news",
                description=description or "Aucun résumé disponible.",
                keywords_matched=[category],
            ))

        return offers

    def run(self) -> List[Offer]:
        """Parcourt toutes les thématiques configurées."""
        offers: List[Offer] = []
        for cat in NEWS_SOURCES.keys():
            try:
                offers.extend(self.run_category(cat))
            except Exception as e:
                log.exception("[news] Erreur sur la catégorie %s: %s", cat, e)
        log.info("[news] %d actualités trouvées au total", len(offers))
        return offers
