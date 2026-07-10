"""File d'attente de synthèse de cheat sheets médicales (batch nocturne / CLI)."""
from __future__ import annotations

import argparse
import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from bot.config import DATA_DIR
from bot.ai import generate_medical_cheat_sheet
from bot.medical_store import MedicalStore

log = logging.getLogger(__name__)
QUEUE_DB = DATA_DIR / "cheat_sheet_queue.db"


class CheatSheetQueue:
    def __init__(self, path: Path = QUEUE_DB):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS queue (
                record_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                created_at TEXT DEFAULT (datetime('now', 'utc')),
                updated_at TEXT DEFAULT (datetime('now', 'utc'))
            )"""
        )

    def enqueue(self, record_id: str) -> None:
        self.conn.execute(
            """INSERT INTO queue (record_id) VALUES (?)
               ON CONFLICT(record_id) DO UPDATE SET
                 status='pending',
                 attempts=0,
                 last_error=NULL,
                 updated_at=datetime('now', 'utc')""",
            (record_id,),
        )

    def enqueue_missing(self, store: MedicalStore, limit: int = 200) -> int:
        records = store.get_records_missing_cheat_sheet(limit=limit)
        for r in records:
            self.enqueue(r["id"])
        return len(records)

    def pending(self, limit: int = 50) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM queue WHERE status='pending' ORDER BY created_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark(self, record_id: str, status: str, error: Optional[str] = None) -> None:
        self.conn.execute(
            """UPDATE queue SET status=?, attempts=attempts+1, last_error=?,
               updated_at=datetime('now', 'utc') WHERE record_id=?""",
            (status, error, record_id),
        )


def process_queue(limit: int = 50, sleep_s: float = 0.5, backoff_s: float = 90.0,
                  max_consecutive_failures: int = 3, max_backoff_rounds: int = 4) -> dict:
    store = MedicalStore()
    q = CheatSheetQueue()
    queued = q.enqueue_missing(store, limit=limit)
    items = q.pending(limit=limit)
    ok = fail = skip = 0
    consecutive_failures = 0
    backoff_rounds_without_success = 0
    for item in items:
        rid = item["record_id"]
        rec = store.get_record(rid)
        if not rec:
            q.mark(rid, "failed", "record introuvable")
            fail += 1
            continue
        if rec.get("ai_cheat_sheet"):
            q.mark(rid, "done")
            skip += 1
            continue
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
            store.update_cheat_sheet(rid, sheet)
            q.mark(rid, "done")
            ok += 1
            consecutive_failures = 0
            backoff_rounds_without_success = 0
        else:
            q.mark(rid, "pending" if item["attempts"] < 3 else "failed", "génération impossible")
            fail += 1
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                backoff_rounds_without_success += 1
                if backoff_rounds_without_success >= max_backoff_rounds:
                    log.warning(
                        "Quota IA épuisé (%d pauses sans succès) — arrêt du batch. "
                        "Relancer plus tard (le quota se réinitialise quotidiennement).",
                        backoff_rounds_without_success,
                    )
                    break
                # Quota / rate-limit probable (429) : pause longue avant de continuer
                log.warning(
                    "%d échecs consécutifs — pause %d/%d de %.0f s (quota/rate-limit probable)",
                    consecutive_failures, backoff_rounds_without_success, max_backoff_rounds, backoff_s,
                )
                time.sleep(backoff_s)
                consecutive_failures = 0
        time.sleep(sleep_s)
    return {"enqueued": queued, "processed": len(items), "ok": ok, "fail": fail, "skip": skip}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Batch nocturne de cheat sheets médicales")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--sleep", type=float, default=0.5)
    args = parser.parse_args()
    stats = process_queue(limit=args.limit, sleep_s=args.sleep)
    log.info("Batch terminé: %s", stats)


if __name__ == "__main__":
    main()
