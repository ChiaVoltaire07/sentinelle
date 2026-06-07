"""CLI v2 : lance l'orchestrateur multi-agents (scraping + crédibilité)."""
from __future__ import annotations

import argparse
import asyncio
import logging

from bot.orchestrator import AGENTS, DEFAULT_AGENTS, Orchestrator
from bot.store import Store


def main() -> None:
    p = argparse.ArgumentParser(description="Bot Scrapper IA v2 (multi-agents + crédibilité)")
    p.add_argument("--only", nargs="+", choices=list(AGENTS.keys()),
                   help="Agents à lancer (défaut: %s)" % ",".join(DEFAULT_AGENTS))
    p.add_argument("-v", "--verbose", action="store_true", help="Logs détaillés")
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    try:
        from scrapers.base import is_playwright_available
        logging.getLogger("bot").info("Playwright (Chrome système): %s",
                                      is_playwright_available())
    except Exception:
        pass
    orch = Orchestrator(store=Store())
    res = asyncio.run(orch.run(only=args.only))
    print(f"\n✅ {res['offers']} offres · {res['comments']} commentaires · "
          f"{res['dropped']} expirées · {res['scored']} scorées en {res['elapsed']}s")


if __name__ == "__main__":
    main()
