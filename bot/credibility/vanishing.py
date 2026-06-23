"""Vanishing : la DISPARITION comme signal de vérité.

On re-probe les sources dans le temps. Une offre dont toutes les occurrences
disparaissent silencieusement = signal négatif massif (arnaque / expirée /
n'existait pas). Une offre qui persiste et s'amplifie = signal positif.
"""
from __future__ import annotations

from bot.store import Store


def is_vanished(store: Store, dna: str) -> bool:
    """True si l'offre a déjà été vue mais toutes ses sources ont disparu."""
    rows = store.conn.execute(
        "SELECT alive FROM offer_sources WHERE offer_dna=?", (dna,)
    ).fetchall()
    if not rows:
        return False  # jamais vu → on ne peut pas conclure
    return all(r["alive"] == 0 for r in rows)


def disappearing_velocity(store: Store, dna: str) -> float:
    """Ratio de sources disparues (0.0 = tout vivant, 1.0 = tout disparu)."""
    rows = store.conn.execute(
        "SELECT alive FROM offer_sources WHERE offer_dna=?", (dna,)
    ).fetchall()
    if not rows:
        return 0.0
    gone = sum(1 for r in rows if r["alive"] == 0)
    return gone / len(rows)
