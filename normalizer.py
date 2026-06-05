"""Normalisation : détection de mots-clés et classification du type d'offre."""
from __future__ import annotations

from typing import List, Optional

from config import OFFER_KEYWORDS, OFFER_TYPE_PATTERNS


def matches_keywords(text: str) -> List[str]:
    """Retourne la liste (dédupliquée) des mots-clés d'offre présents dans le texte."""
    if not text:
        return []
    low = text.lower()
    return list({kw for kw in OFFER_KEYWORDS if kw in low})


def classify(text: str) -> Optional[str]:
    """Devine le type d'offre à partir du texte (celui avec le plus de correspondances)."""
    if not text:
        return None
    low = text.lower()
    best, best_score = None, 0
    for otype, patterns in OFFER_TYPE_PATTERNS.items():
        score = sum(1 for p in patterns if p in low)
        if score > best_score:
            best, best_score = otype, score
    return best
