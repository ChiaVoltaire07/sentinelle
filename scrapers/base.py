"""Scraper de base : fetch HTTP (requests) + fetch JS (Playwright optionnel).

Playwright est OPTIONNEL : le bot fonctionne sans (les pages très dynamiques
seront simplement ignorées). Si Playwright est installé, il est utilisé
automatiquement pour les sources marquées js=True.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import DEFAULT_HEADERS, REQUEST_TIMEOUT

log = logging.getLogger(__name__)

# Détection optionnelle de Playwright
_playwright_available = False
try:
    from playwright.sync_api import sync_playwright  # type: ignore

    _playwright_available = True
except Exception:  # pragma: no cover - dépend de l'environnement
    sync_playwright = None  # type: ignore


def is_playwright_available() -> bool:
    return _playwright_available


class BaseScraper:
    """Fournit fetch_static / fetch_dynamic + extraction de liens et de texte."""

    name = "base"

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    # --- récupération HTML ---
    def fetch_static(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            log.warning("[%s] fetch_static échec %s : %s", self.name, url, e)
            return None

    # Navigateur système : on utilise le Chrome déjà installé plutôt que de
    # télécharger un build Chromium via le CDN Playwright (souvent bloqué).
    _CHROME_PATH = "/usr/bin/google-chrome-stable"

    def fetch_dynamic(self, url: str, wait_ms: int = 2500) -> Optional[str]:
        """Récupère une page rendue par JS via Playwright (Chrome système si dispo)."""
        if not _playwright_available:
            log.info("[%s] Playwright indisponible — page JS ignorée : %s", self.name, url)
            return None
        launch_kwargs = {"headless": True}
        if os.path.exists(self._CHROME_PATH):
            launch_kwargs["executable_path"] = self._CHROME_PATH
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_kwargs)
                ctx = browser.new_context(
                    user_agent=DEFAULT_HEADERS["User-Agent"],
                    locale="en-US",
                    viewport={"width": 1366, "height": 900},
                )
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT * 1000)
                page.wait_for_timeout(wait_ms)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            log.warning("[%s] fetch_dynamic échec %s : %s", self.name, url, e)
            return None

    def fetch(self, url: str, js: bool = False) -> Optional[str]:
        """Stratégie : si js=True essaie Playwright puis requests ; sinon requests."""
        html = None
        if js:
            html = self.fetch_dynamic(url)
        if not html:
            html = self.fetch_static(url)
        return html

    # --- parsing ---
    @staticmethod
    def extract_links(html: str, base_url: str) -> List[dict]:
        """Retourne [{href, text}] nettoyés et absolutisés."""
        soup = BeautifulSoup(html, "html.parser")
        out: List[dict] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            text = " ".join(a.get_text(" ", strip=True).split())
            out.append({"href": urljoin(base_url, href), "text": text})
        return out

    @staticmethod
    def extract_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return " ".join(soup.get_text(" ", strip=True).split())
