"""Trust backpropagation : tes favoris → source → pattern.

Quand tu valides une offre, la confiance remonte vers (a) la source/profil
(favori, priorisé + scrapé plus souvent), (b) l'agent, (c) le pattern de
mots-clés. Le bot apprend quels patterns prédisent de vraies offres.
"""
from __future__ import annotations

from urllib.parse import urlparse

from bot.models import Favorite, Offer
from bot.store import Store


def backprop_validation(store: Store, offer: Offer) -> Favorite:
    """À appeler quand l'utilisateur valide une offre. Crée/renforce un favori."""
    host = urlparse(offer.url).netloc or offer.url
    fav = Favorite(
        key=host,
        kind="source",
        label=f"{offer.provider} — {host}",
        trust_score=1.0,
        last_verified=offer.last_seen,
        validated_count=1,
    )
    store.add_favorite(fav)
    return fav


def source_priority(store: Store) -> dict:
    """Map {host: poids} pour prioriser les sources favorisées (>1 = prioritaire)."""
    favs = store.get_favorites()
    return {f.key: 1.0 + min(f.trust_score, 2.0) for f in favs}


def trust_bonus(store: Store, offer: Offer) -> float:
    """Bonus de score si la source de l'offre est un favori de confiance."""
    host = urlparse(offer.url).netloc or offer.url
    pri = source_priority(store)
    w = pri.get(host)
    if not w:
        return 0.0
    return (w - 1.0) * 10.0  # +10 à +20 points
