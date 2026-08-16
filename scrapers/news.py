"""Scraper d'actualités via Google News RSS pour différentes thématiques."""
from __future__ import annotations

import logging
import html
import warnings
from typing import List
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from models import Offer
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

NEWS_SOURCES = {
    "top": {
        "name": "Top Actu",
        "urls": [
            "https://www.francetvinfo.fr/titres.rss",
            "https://www.lefigaro.fr/rss/figaro_actualites.xml",
            "https://news.google.com/rss?hl=fr&gl=FR&ceid=FR:fr",
        ],
    },
    "tech": {
        "name": "Actu Tech",
        "urls": [
            "https://www.clubic.com/feed/news.rss",
            "https://www.01net.com/actualites/feed/",
            "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=fr&gl=FR&ceid=FR:fr",
        ],
    },
    "sport": {
        "name": "Actu Sport",
        "urls": [
            "https://www.francetvinfo.fr/sports.rss",
            "https://www.lequipe.fr/rss/actu_rss.xml",
            "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=fr&gl=FR&ceid=FR:fr",
        ],
    },
    "finance": {
        "name": "Actu Finance",
        "urls": [
            "https://www.francetvinfo.fr/economie.rss",
            "https://services.lesechos.fr/rss/les-echos-economie.xml",
            "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=fr&gl=FR&ceid=FR:fr",
        ],
    },
    "politic": {
        "name": "Actu Politique",
        "urls": [
            "https://www.francetvinfo.fr/politique.rss",
            "https://news.google.com/rss/search?q=politique&hl=fr&gl=FR&ceid=FR:fr",
        ],
    },
    "economie": {
        "name": "Actu Économie",
        "urls": [
            "https://www.francetvinfo.fr/economie.rss",
            "https://services.lesechos.fr/rss/les-echos-economie.xml",
            "https://news.google.com/rss/search?q=economie&hl=fr&gl=FR&ceid=FR:fr",
        ],
    },
    "ia": {
        "name": "Actu IA",
        "urls": [
            "https://www.clubic.com/feed/tag/intelligence-artificielle.rss",
            "https://news.google.com/rss/search?q=intelligence+artificielle+OR+AI+OR+LLM&hl=fr&gl=FR&ceid=FR:fr",
        ],
    },
}

CATEGORY_FALLBACK_IMAGES = {
    "top": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=700&auto=format&fit=crop&q=80",
    "tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=700&auto=format&fit=crop&q=80",
    "sport": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=700&auto=format&fit=crop&q=80",
    "finance": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=700&auto=format&fit=crop&q=80",
    "politic": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=700&auto=format&fit=crop&q=80",
    "economie": "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=700&auto=format&fit=crop&q=80",
    "ia": "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=700&auto=format&fit=crop&q=80",
}


class NewsScraper(BaseScraper):
    name = "news"

    def _extract_image_from_item(self, item, desc_soup, category: str) -> str:
        """Extrait l'image réelle de l'article depuis les balises RSS standard."""
        # 1. Balise enclosure standard RSS (France Info, Le Figaro, Les Echos...)
        enc = item.find("enclosure")
        if enc and enc.get("url"):
            url = enc["url"]
            if any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", "image"]):
                return url

        # 2. Balise media:content ou media:thumbnail (Clubic, 01Net, TechCrunch...)
        for tag_name in ["media:content", "media:thumbnail"]:
            media = item.find(tag_name)
            if media and media.get("url"):
                return media["url"]

        # 3. Balise <img> dans la description HTML
        img = desc_soup.find("img")
        if img and img.get("src"):
            src = img["src"]
            if src.startswith("http"):
                return src

        # 4. Balise content:encoded
        content_enc = item.find("content:encoded")
        if content_enc:
            c_soup = BeautifulSoup(content_enc.get_text(), "html.parser")
            c_img = c_soup.find("img")
            if c_img and c_img.get("src") and c_img["src"].startswith("http"):
                return c_img["src"]

        return CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES["top"])

    def run_category(self, category: str) -> List[Offer]:
        """Scrape une catégorie d'actualités avec extraction des vraies images d'articles."""
        cfg = NEWS_SOURCES.get(category)
        if not cfg:
            log.warning("[news] Catégorie inconnue : %s", category)
            return []

        urls = cfg.get("urls") or [cfg.get("url")]
        offers: List[Offer] = []
        seen_titles = set()

        for url in urls:
            if not url or len(offers) >= 20:
                break
            try:
                xml_content = self.fetch_static(url)
                if not xml_content:
                    continue

                soup = BeautifulSoup(xml_content, "html.parser")
                items = soup.find_all("item")

                for item in items:
                    if len(offers) >= 20:
                        break

                    title = item.find("title").get_text() if item.find("title") else ""
                    title = title.strip()
                    if not title or title.lower() in seen_titles:
                        continue
                    seen_titles.add(title.lower())

                    link = item.find("link").get_text() if item.find("link") else ""
                    
                    desc_raw = item.find("description").get_text() if item.find("description") else ""
                    desc_soup = BeautifulSoup(desc_raw, "html.parser")
                    description = desc_soup.get_text().replace("&nbsp;", " ").strip()

                    # Déterminer le média
                    provider = cfg["name"]
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        title = parts[0].strip()
                        provider = parts[1].strip()
                    elif "francetvinfo" in url:
                        provider = "France Info"
                    elif "lefigaro" in url:
                        provider = "Le Figaro"
                    elif "clubic" in url:
                        provider = "Clubic"
                    elif "01net" in url:
                        provider = "01Net"
                    elif "lesechos" in url:
                        provider = "Les Échos"
                    elif "lequipe" in url:
                        provider = "L'Équipe"

                    # Extraire l'image réelle
                    img_url = self._extract_image_from_item(item, desc_soup, category)

                    offers.append(Offer(
                        title=title,
                        url=link,
                        source=f"news_{category}",
                        provider=provider,
                        offer_type="news",
                        description=description or "Consultez l'article complet pour tous les détails de cette actualité.",
                        keywords_matched=[category],
                        image_url=img_url,
                    ))
            except Exception as e:
                log.warning("[news] Erreur sur flux %s: %s", url, e)

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
