"""Moteur de refresh des suivis : news + cours (Yahoo) + insights IA ancrés."""
from __future__ import annotations

import logging
import urllib.parse
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from bot.ai import call_llm, get_gemini_key
from bot.watch_store import WatchStore, get_watch_store
from config import DEFAULT_HEADERS, REQUEST_TIMEOUT
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)


class WatchNewsScraper(BaseScraper):
    name = "watch_news"

    def search(self, query: str, limit: int = 20) -> List[dict]:
        escaped = urllib.parse.quote_plus(query)
        url = f"https://news.google.com/rss/search?q={escaped}&hl=fr&gl=FR&ceid=FR:fr"
        xml = self.fetch_static(url)
        if not xml:
            return []
        soup = BeautifulSoup(xml, "html.parser")
        out = []
        for item in soup.find_all("item")[:limit]:
            title = item.find("title").get_text() if item.find("title") else ""
            link = item.find("link").get_text() if item.find("link") else ""
            desc_raw = item.find("description").get_text() if item.find("description") else ""
            summary = BeautifulSoup(desc_raw, "html.parser").get_text().replace("&nbsp;", " ").strip()
            pub = item.find("pubDate").get_text() if item.find("pubDate") else None
            provider = "Google News"
            if " - " in title:
                title, provider = title.rsplit(" - ", 1)
            etype = "news"
            low = (title + " " + summary).lower()
            if any(k in low for k in ["earnings", "résultats", "resultats", "quarter", "trimestre"]):
                etype = "earnings"
            elif any(k in low for k in ["launch", "lancement", "annonce", "unveil", "release", "sortie"]):
                etype = "announcement"
            elif any(k in low for k in ["guerre", "attaque", "missile", "sanction", "ceasefire", "conflit"]):
                etype = "conflict"
            out.append({
                "title": title,
                "url": link,
                "provider": provider,
                "summary": summary,
                "event_type": etype,
                "published_at": pub,
            })
        return out


def fetch_yahoo_chart(ticker: str, range_: str = "3mo", interval: str = "1d") -> List[dict]:
    """Compat : délègue à la couche multi-providers (Yahoo / Binance / …)."""
    from bot.market_data import get_chart, is_crypto_symbol, normalize_symbol
    sym = normalize_symbol(ticker)
    # map interval loosely to range if caller used old signature
    range_map = {"1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y"}
    r = range_ if range_ in range_map else "3mo"
    chart = get_chart(sym, range_=r)
    return chart.get("points") or []


def refresh_watch(watch_id: int, store: Optional[WatchStore] = None) -> dict:
    store = store or get_watch_store()
    w = store.get(watch_id)
    if not w:
        return {"error": "not_found"}

    news = WatchNewsScraper().search(w["query"], limit=25)
    for n in news:
        store.add_event(
            watch_id,
            title=n["title"],
            url=n["url"],
            provider=n["provider"],
            summary=n["summary"],
            event_type=n["event_type"],
            published_at=n.get("published_at"),
        )

    prices_added = 0
    market_meta = {}
    if w.get("ticker"):
        from bot.market_data import get_chart, get_quote, is_crypto_symbol, normalize_symbol
        sym = normalize_symbol(w["ticker"])
        chart = get_chart(sym, range_="3mo", force=True)
        for p in chart.get("points") or []:
            store.add_price(watch_id, p["ts"], p["price"], p.get("volume"), source=p.get("source") or chart.get("source") or "market")
            prices_added += 1
        q = get_quote(sym, force=True)
        market_meta = {
            "symbol": sym,
            "asset_class": "crypto" if is_crypto_symbol(sym) else "equity",
            "quote": q,
            "chart_source": chart.get("source"),
            "latency": (q or {}).get("latency") or chart.get("latency"),
            "delay_note": (q or {}).get("delay_note") or chart.get("delay_note"),
        }

    store.touch_refreshed(watch_id)
    return {
        "watch_id": watch_id,
        "slug": w["slug"],
        "news_fetched": len(news),
        "prices_added": prices_added,
        "market": market_meta,
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_watch_insight(watch_id: int, kind: str = "summary", user_prompt: str = "", store: Optional[WatchStore] = None) -> dict:
    """Génère résumé / analyse / trading indicatif ancré sur les données du suivi."""
    store = store or get_watch_store()
    dash = store.dashboard(watch_id)
    if not dash:
        return {"error": "not_found"}

    w = dash["watch"]
    events = dash["events"][:15]
    stats = dash["stats"]
    prices = dash["prices"][-10:]

    payload = {
        "title": w["title"],
        "kind": w["kind"],
        "ticker": w.get("ticker"),
        "stats": stats,
        "recent_prices": prices,
        "recent_events": [
            {"title": e["title"], "type": e["event_type"], "provider": e["provider"], "summary": (e.get("summary") or "")[:200]}
            for e in events
        ],
    }

    kind = kind if kind in ("summary", "analysis", "trading") else "summary"
    if kind == "trading" and not w.get("ticker"):
        content = (
            f"**{w['title']}** n'a pas de ticker coté associé dans ce suivi "
            "(entreprise privée ou sujet non financier). "
            "Aucun conseil trading applicable. Suivez plutôt les annonces et signaux géopolitiques / produit."
        )
        return store.add_insight(watch_id, kind, content)

    instructions = {
        "summary": "Fais un résumé factuel de l'évolution récente (10-15 lignes max).",
        "analysis": "Analyse les tendances, risques et catalyseurs visibles dans les sources.",
        "trading": (
            "Donne des pistes trading INDICATIVES (pas un conseil personnalisé) : "
            "niveaux observés, biais haussier/baissier d'après les données, "
            "et rappels de risque. Interdiction de promettre un gain."
        ),
    }
    extra = f"\nDemande utilisateur : {user_prompt}" if user_prompt else ""

    if get_gemini_key() or True:
        prompt = f"""
Tu es l'analyste du hub Scout. Tu dois t'appuyer UNIQUEMENT sur les données JSON fournies.
Sujet suivi : {w['title']} ({w['kind']})
Type d'insight demandé : {kind}
{instructions[kind]}{extra}

Données :
{payload}

Règles :
1. Aucune invention hors données.
2. Cite quelques titres d'événements comme preuves.
3. Français, structuré en markdown.
4. Termine par une ligne Disclaimer.
"""
        text = call_llm(prompt)
        if not text:
            # Fallback déterministe
            lines = [f"### Suivi {w['title']}", f"- Événements indexés : {stats['events_count']}"]
            if stats.get("last_price") is not None:
                lines.append(f"- Dernier cours : {stats['last_price']} (var. période ~ {stats.get('price_change_pct')}%)")
            lines.append("- Dernières sources :")
            for e in events[:5]:
                lines.append(f"  - {e['title']} ({e.get('provider')})")
            lines.append("\n*Disclaimer : données scrapées, pas un conseil financier.*")
            text = "\n".join(lines)
        return store.add_insight(watch_id, kind, text)

    return {"error": "llm_unavailable"}
