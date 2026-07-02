"""Helper Playwright avec injection de cookies (LinkedIn / X best-effort).

Ces réseaux bloquent l'accès anonyme : scraping best-effout avec tes cookies de
session. Fragile + sujet aux ToS → inactif par défaut (LINKEDIN_ENABLED / X_ENABLED).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

_OK = True
try:
    from playwright.sync_api import sync_playwright
except Exception:
    _OK = False

CHROME = "/usr/bin/google-chrome-stable"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def fetch_with_cookies(url: str, cookies_path: str, wait_ms: int = 3000) -> Optional[str]:
    if not _OK:
        log.warning("[social_pw] Playwright indisponible")
        return None
    if not cookies_path or not os.path.exists(cookies_path):
        log.warning("[social_pw] fichier cookies manquant: %s", cookies_path)
        return None
    try:
        cookies = json.load(open(cookies_path, encoding="utf-8"))
    except Exception as e:
        log.warning("[social_pw] cookies illisibles: %s", e)
        return None
    kw = {"headless": True}
    if os.path.exists(CHROME):
        kw["executable_path"] = CHROME
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(**kw)
            ctx = b.new_context(user_agent=UA, locale="en-US",
                                viewport={"width": 1366, "height": 900})
            ctx.add_cookies(cookies)
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(wait_ms)
            html = page.content()
            b.close()
            return html
    except Exception as e:
        log.warning("[social_pw] fetch échec %s: %s", url, e)
        return None
