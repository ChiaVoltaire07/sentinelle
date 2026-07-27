"""Digest de bienvenue personnalisé pour le hub Opportunités."""
from __future__ import annotations

import json
import logging
from typing import Optional

from bot.ai import call_llm
from bot.opportunities import feed_for_profile
from bot.user_profile import get_profile_store

log = logging.getLogger(__name__)


def build_welcome_digest(force_refresh: bool = False) -> dict:
    profile = get_profile_store().get()
    name = profile.get("display_name") or "là"
    feed = feed_for_profile(limit=6)
    sources = [
        {
            "title": i.get("title"),
            "url": i.get("url"),
            "provider": i.get("provider"),
            "offer_type": i.get("offer_type"),
            "match_score": i.get("match_score"),
            "description": (i.get("description") or "")[:180],
        }
        for i in feed
    ]

    if not sources:
        message = (
            f"Bienvenue {name}. Je n'ai pas encore trouvé d'opportunités scrapées "
            "qui matchent ton profil. Complète tes compétences / ville, ou lance une recherche."
        )
        return {"message": message, "sources": [], "profile": profile}

    data_str = json.dumps(sources, ensure_ascii=False)
    prompt = f"""
Tu es l'assistant Scout, ton conversationnel et utile.
Prénom utilisateur : {name}
Profil skills: {profile.get('skills')}
Intérêts: {profile.get('interests')}
Ville/Pays: {profile.get('city')} / {profile.get('country')}

OPPORTUNITÉS SCRAPÉES (seule vérité) :
{data_str}

Rédige un message d'accueil en français, style message personnel (pas de liste sèche) :
- Commence par « Bienvenue {{prénom}}… »
- Mentionne 2 à 4 opportunités concrètes avec leur org/titre
- Ton « ça devrait t'intéresser / tu as le profil » uniquement si le match est plausible d'après les données
- Termine par une question ouverte du type « + d'info ? »
- N'invente AUCUNE offre absente des données
- 1 court paragraphe fluide ou 2 max
"""
    message = call_llm(prompt)
    if not message:
        bits = [f"Bienvenue {name}, j'ai déniché quelques pistes qui matchent ton profil :"]
        for s in sources[:4]:
            bits.append(f"- {s['title']} ({s.get('provider') or s.get('offer_type')})")
        bits.append("Ça te dit d'en savoir plus sur l'une d'elles ?")
        message = "\n".join(bits)

    return {"message": message, "sources": sources, "profile": profile}
