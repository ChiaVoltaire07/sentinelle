"""Backfill des embeddings vectoriels pour la recherche sémantique médicale.

Usage :
    python -m bot.embed_medical --limit 400 --sleep 0.3

Génère les embeddings (gemini-embedding-001, 768 dims) des dossiers médicaux
existant n'ayant pas encore de vecteur, avec pauses automatiques en cas de
rate-limit (429) et arrêt propre si le quota journalier est épuisé.
"""
from __future__ import annotations

import argparse
import logging
import time

from bot.ai import get_embedding
from bot.medical_store import MedicalStore

log = logging.getLogger(__name__)


def backfill_embeddings(limit: int = 200, sleep_s: float = 0.3, backoff_s: float = 60.0,
                        max_consecutive_failures: int = 3, max_backoff_rounds: int = 4) -> dict:
    store = MedicalStore()
    records = store.get_records_missing_embedding(limit=limit)
    ok = fail = 0
    consecutive_failures = 0
    backoff_rounds_without_success = 0
    for rec in records:
        rid = rec["id"]
        text = f"{rec.get('title') or ''} {rec.get('summary') or ''}"
        vec = get_embedding(text.strip())
        if vec:
            store.update_embedding(rid, vec)
            ok += 1
            consecutive_failures = 0
            backoff_rounds_without_success = 0
        else:
            fail += 1
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                backoff_rounds_without_success += 1
                if backoff_rounds_without_success >= max_backoff_rounds:
                    log.warning(
                        "Quota embeddings épuisé (%d pauses sans succès) — arrêt. Relancer plus tard.",
                        backoff_rounds_without_success,
                    )
                    break
                log.warning(
                    "%d échecs consécutifs — pause %d/%d de %.0f s (quota/rate-limit probable)",
                    consecutive_failures, backoff_rounds_without_success, max_backoff_rounds, backoff_s,
                )
                time.sleep(backoff_s)
                consecutive_failures = 0
        time.sleep(sleep_s)
    remaining = len(store.get_records_missing_embedding(limit=5000))
    stats = {"processed": len(records), "ok": ok, "fail": fail, "remaining": remaining}
    log.info("Backfill embeddings terminé: %s", stats)
    return stats


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Backfill des embeddings médicaux")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--sleep", type=float, default=0.3)
    args = parser.parse_args()
    backfill_embeddings(limit=args.limit, sleep_s=args.sleep)


if __name__ == "__main__":
    main()
