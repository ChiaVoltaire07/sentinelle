"""Corroboration : consensus multi-source (type PageRank-pour-offres).

Une offre vue sur >= K sources indépendantes gagne en confiance ;
une offre à source unique est déclassée.
"""
from __future__ import annotations

from bot.config import CORROBORATION_MIN_SOURCES
from bot.store import Store


def corroborating_sources(store: Store, dna: str) -> int:
    """Nombre de sources distinctes (vivantes) ayant vu cette offre (ADN)."""
    rows = store.conn.execute(
        "SELECT DISTINCT source FROM offer_sources WHERE offer_dna=? AND alive=1",
        (dna,),
    ).fetchall()
    return len(rows)


def is_well_corroborated(store: Store, dna: str) -> bool:
    return corroborating_sources(store, dna) >= CORROBORATION_MIN_SOURCES
