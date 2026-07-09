"""Ingestion batch Afrique centrale : ClinicalTrials.gov + PubMed → MedicalStore."""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from bot.config import DATA_DIR
from bot.ai import generate_medical_cheat_sheet
from bot.medical_store import MedicalStore
from scrapers.medical import MedicalScraper

log = logging.getLogger(__name__)

# Termes cliniques prioritaires Afrique centrale / maladies tropicales
DEFAULT_TERMS = [
    "malaria",
    "paludisme",
    "sickle cell",
    "drépanocytose",
    "tuberculosis",
    "HIV",
    "hepatitis B",
    "yellow fever",
    "ebola",
    "onchocerciasis",
    "schistosomiasis",
    "meningitis",
    "pneumonia children",
    "maternal mortality",
]

DEFAULT_LOCATIONS = [
    "Cameroon",
    "Gabon",
    "Congo",
    "Central African Republic",
    "Chad",
    "Democratic Republic of the Congo",
    "Equatorial Guinea",
]

RUN_LOG = DATA_DIR / "ingestion_runs.jsonl"


def _append_run_log(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def ingest(
    terms: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    with_cheat_sheets: bool = False,
    include_pubmed: bool = True,
    page_delay: float = 0.4,
) -> dict:
    terms = terms or DEFAULT_TERMS
    locations = locations or DEFAULT_LOCATIONS
    scraper = MedicalScraper()
    store = MedicalStore()
    started = datetime.now(timezone.utc).isoformat()
    inserted = 0
    failed_calls = 0
    seen = set()

    for term in terms:
        for loc in locations:
            try:
                records = scraper.scrape_clinical_trials(term, location=loc)
            except Exception as e:
                log.warning("Échec ClinicalTrials %s/%s : %s", term, loc, e)
                failed_calls += 1
                records = []
            for rec in records:
                rid = rec.get("id")
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                if with_cheat_sheets and not rec.get("ai_cheat_sheet"):
                    sheet = generate_medical_cheat_sheet(
                        rec.get("title") or "",
                        rec.get("summary") or "",
                        rec.get("eligibility_criteria") or "",
                        nct_id=rec.get("nct_id"),
                        phase=rec.get("phase"),
                        status=rec.get("status"),
                        sponsor=rec.get("sponsor"),
                    )
                    if sheet:
                        rec["ai_cheat_sheet"] = sheet
                store.upsert_record(rec)
                inserted += 1
            time.sleep(page_delay)

        if include_pubmed:
            try:
                pubs = scraper.scrape_pubmed(f"{term} Africa")
            except Exception as e:
                log.warning("Échec PubMed %s : %s", term, e)
                failed_calls += 1
                pubs = []
            for rec in pubs:
                rid = rec.get("id")
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                store.upsert_record(rec)
                inserted += 1
            time.sleep(page_delay)

    stats = store.get_stats()
    result = {
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "terms": len(terms),
        "locations": len(locations),
        "upserted": inserted,
        "unique_seen": len(seen),
        "failed_calls": failed_calls,
        "store": stats,
    }
    _append_run_log(result)
    store.record_ingestion_run(result)
    log.info("Ingestion terminée: %s", result)
    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingestion médicale Afrique centrale")
    parser.add_argument("--terms", nargs="*", help="Termes cliniques (défaut: liste intégrée)")
    parser.add_argument("--locations", nargs="*", help="Localisations ClinicalTrials")
    parser.add_argument("--with-cheat-sheets", action="store_true", help="Générer les fiches IA (plus lent)")
    parser.add_argument("--no-pubmed", action="store_true")
    parser.add_argument("--delay", type=float, default=0.4)
    args = parser.parse_args()
    ingest(
        terms=args.terms,
        locations=args.locations,
        with_cheat_sheets=args.with_cheat_sheets,
        include_pubmed=not args.no_pubmed,
        page_delay=args.delay,
    )


if __name__ == "__main__":
    main()
