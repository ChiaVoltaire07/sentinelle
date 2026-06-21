"""Polarité des commentaires → seuils 40% / 60% (spec utilisateur).

>40% de commentaires « fake_call » → tier "pas_sur" (🟠)
>60% → offre rejetée (🔴, masquée)
"""
from __future__ import annotations

from typing import List

from bot.config import (
    ENDORSEMENT_TERMS, FAKE_CALL_TERMS,
    POLARITY_REJECT_THRESHOLD, POLARITY_UNCERTAIN_THRESHOLD,
)


def classify_comment(text: str) -> str:
    """Renvoie 'fake_call' | 'endorsement' | 'neutral'."""
    if not text:
        return "neutral"
    low = text.lower()
    fake_hits = sum(1 for t in FAKE_CALL_TERMS if t in low)
    endo_hits = sum(1 for t in ENDORSEMENT_TERMS if t in low)
    if fake_hits > endo_hits and fake_hits > 0:
        return "fake_call"
    if endo_hits > fake_hits and endo_hits > 0:
        return "endorsement"
    return "neutral"


def polarity_stats(polarities: List[str]) -> dict:
    """Calcule le ratio de fake_calls et les compteurs."""
    total = len(polarities)
    if total == 0:
        return {"ratio_fake": 0.0, "fake_calls": 0, "total": 0}
    fake = sum(1 for p in polarities if p == "fake_call")
    return {"ratio_fake": fake / total, "fake_calls": fake, "total": total}


def tier_from_polarity(ratio_fake: float):
    """Renvoie 'rejected' (>60%) | 'pas_sur' (>40%) | None (ok)."""
    if ratio_fake > POLARITY_REJECT_THRESHOLD:
        return "rejected"
    if ratio_fake > POLARITY_UNCERTAIN_THRESHOLD:
        return "pas_sur"
    return None
