"""Moteur de crédibilité : fusionne les 4 couches épistémiques → tier + score.

Couches : (1) polarité des commentaires 40/60%, (2) corroboration multi-source,
(3) vanishing (disparition), (4) fraîcheur/expiration, (+) trust backprop.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bot.config import (
    CORROBORATION_BONUS_PER_SOURCE, EXPIRY_ENABLED, VANISHING_PENALTY,
)
from bot.credibility import corroboration, expiry, polarity, trust, vanishing
from bot.credibility.dna import offer_dna
from bot.models import CredibilityScore, Offer
from bot.store import Store


def score_offer(store: Store, offer: Offer) -> CredibilityScore:
    """Évalue une offre et persiste le résultat. Renvoie le score décomposé."""
    dna = offer.dna_hash or offer_dna(offer)
    offer.dna_hash = dna

    if offer.offer_type in ("job", "news", "medical"):
        tier = "verified"
        score = 85
        reasons = ["Source d'information officielle"]
        cs = CredibilityScore(
            offer_id=offer.id, tier=tier, score=score,
            polarity_ratio=0.0, fake_calls=0,
            total_comments=0, corroborating_sources=1,
            vanished=False, expired=False, reasons=reasons,
        )
        offer.credibility_tier = tier
        offer.credibility_score = score
        store.set_credibility(offer.id, tier, score, offer.provenance or [])
        store.upsert_offer(offer)
        return cs

    comments = store.get_comments(dna)
    polarities = [c.polarity for c in comments]
    pstats = polarity.polarity_stats(polarities)
    ratio = pstats["ratio_fake"]

    reasons = []
    tier = "pending"
    score = 50  # base neutre

    # (1) Polarité — spec utilisateur 40/60%
    p_tier = polarity.tier_from_polarity(ratio)
    if p_tier == "rejected":
        tier = "rejected"
        reasons.append(f"{pstats['fake_calls']}/{pstats['total']} commentaires signalent une arnaque ({ratio:.0%} > 60%)")
        score = 10
    elif p_tier == "pas_sur":
        tier = "pas_sur"
        reasons.append(f"{pstats['fake_calls']}/{pstats['total']} commentaires doutent ({ratio:.0%} > 40%)")
        score = 35
    else:
        if pstats["total"]:
            reasons.append(f"Commentaires plutôt favorables ({pstats['total']})")
            score += 10

    # (4) Expiration — court-circuite tout si expirée
    if EXPIRY_ENABLED and offer.expires_at and expiry.is_expired(offer.expires_at):
        tier = "rejected"
        score = 0
        reasons.insert(0, "Offre expirée (date de fin dépassée)")
        offer.status = "expired"

    # (3) Vanishing — la disparition comme signal de fausseté
    if vanishing.is_vanished(store, dna):
        score = max(0, score - VANISHING_PENALTY)
        reasons.append("Offre disparue de toutes ses sources (signal de fausseté)")
        if tier == "pending":
            tier = "pas_sur"

    # (2) Corroboration — consensus multi-source
    n_src = corroboration.corroborating_sources(store, dna)
    if n_src >= 2:
        score += (n_src - 1) * CORROBORATION_BONUS_PER_SOURCE
        reasons.append(f"Corroboration : {n_src} sources indépendentes")
        if tier == "pending":
            tier = "verified"
    elif n_src <= 1 and pstats["total"] == 0:
        reasons.append("Source unique — à confirmer")
        if tier == "pending":
            tier = "pas_sur"

    # (+) Trust backprop — bonus si la source est un favori de confiance
    tb = trust.trust_bonus(store, offer)
    if tb:
        score += tb
        reasons.append("Source de confiance (favori validé)")

    score = max(0, min(100, score))

    # Recalibration finale du tier selon le score (sauf rejected déjà fixé)
    if tier != "rejected":
        if score >= 70:
            tier = "verified"
        elif score >= 40:
            tier = "pas_sur" if tier != "verified" else tier
        else:
            tier = "pas_sur"

    cs = CredibilityScore(
        offer_id=offer.id, tier=tier, score=score,
        polarity_ratio=ratio, fake_calls=pstats["fake_calls"],
        total_comments=pstats["total"], corroborating_sources=n_src,
        vanished=vanishing.is_vanished(store, dna),
        expired=bool(offer.status == "expired"), reasons=reasons,
    )
    offer.credibility_tier = tier
    offer.credibility_score = score
    prov = [{"source": s.source, "url": s.url if hasattr(s, "url") else "",
             "found_at": offer.found_at} for s in []]  # provenance construite par l'orchestrateur
    store.set_credibility(offer.id, tier, score, offer.provenance or [])
    store.upsert_offer(offer)
    return cs


def score_all(store: Store) -> int:
    """Recalcule la crédibilité de toutes les offres stockées. Renvoie le total."""
    offers = store.get_offers(limit=100000)
    for o in offers:
        if not o.dna_hash:
            o.dna_hash = offer_dna(o)
        score_offer(store, o)
    return len(offers)
