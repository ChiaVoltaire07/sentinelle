"""Point d'entrée : orchestre les scrapers, normalise, déduplique, génère le rapport."""
from __future__ import annotations

import argparse
import logging
import time
from typing import List, Optional

from dedupe import dedupe
from reporter import save
from scrapers.aggregators import AggregatorScraper
from scrapers.base import is_playwright_available
from scrapers.forums import ForumScraper
from scrapers.official import OfficialScraper

log = logging.getLogger("main")


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_all(only: Optional[List[str]] = None):
    scrapers = {
        "official": OfficialScraper,
        "aggregator": AggregatorScraper,
        "forum": ForumScraper,
    }
    targets = only or list(scrapers.keys())
    all_offers = []
    t0 = time.time()
    for key in targets:
        cls = scrapers.get(key)
        if not cls:
            log.warning("scraper inconnu: %s", key)
            continue
        try:
            all_offers.extend(cls().run())
        except Exception as e:
            log.exception("erreur scraper %s: %s", key, e)
    log.info("total brut: %d offres en %.1fs", len(all_offers), time.time() - t0)
    offers = dedupe(all_offers)
    log.info("après déduplication: %d offres", len(offers))
    md, js = save(offers)
    log.info("rapport Markdown : %s", md)
    log.info("rapport JSON     : %s", js)
    return offers, md, js


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bot de scraping d'offres/promotions IA (free tiers, pass, "
        "crédits, formations, certifications)."
    )
    parser.add_argument(
        "--only", nargs="+", choices=["official", "aggregator", "forum"],
        help="Lancer uniquement certains scrapers.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Logs détaillés.")
    args = parser.parse_args()
    setup_logging(args.verbose)
    log.info("Playwright disponible : %s", is_playwright_available())
    offers, md, _ = run_all(args.only)
    print(f"\n✅ {len(offers)} offre(s) détectée(s) — rapport : {md}")


if __name__ == "__main__":
    main()
