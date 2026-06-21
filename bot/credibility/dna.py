"""Offer DNA : empreinte sémantique normalisée pour la déduplication sémantique.

Permet de reconnaître la MÊME offre sur plusieurs sources même si les URLs
diffèrent → condition nécessaire pour la corroboration.
"""
from __future__ import annotations

import hashlib
import re

from bot.models import Offer
from normalizer import classify

_STOP = {
    "the", "and", "for", "with", "your", "you", "this", "that", "from", "are",
    "has", "have", "not", "but", "get", "all", "can", "new", "now", "use",
    "using", "more", "les", "des", "une", "avec", "pour", "dans", "sur", "est",
    "qui", "que", "par", "the", "and", "open", "new", "window", "learn",
}

# Marques/produits IA qui structurent fortement l'identité d'une offre
_AI_BRANDS = {
    "openai", "chatgpt", "gpt", "anthropic", "claude", "google", "gemini",
    "groq", "mistral", "cohere", "hugging", "huggingface", "cline", "together",
    "perplexity", "replicate", "fireworks", "deepseek", "qwen", "llama",
    "azure", "aws", "bedrock", "cloud", "github", "copilot", "vertex",
}

_BENEFIT = {
    "free", "gratuit", "credits", "credit", "tier", "trial", "pass",
    "promotion", "promo", "certification", "certificate", "formation",
    "course", "training", "api", "key", "plan", "starter", "$0", "0",
}

# Ordre de priorité pour le "sujet" (la marque IA réellement offerte) :
# on cherche la marque dans le texte avant de tomber sur le provider source.
_AI_BRANDS_PRIORITY = [
    "chatgpt", "gpt", "openai", "claude", "anthropic", "gemini", "google",
    "groq", "mistral", "cohere", "cline", "huggingface", "hugging", "together",
    "perplexity", "replicate", "fireworks", "deepseek", "qwen", "llama",
    "copilot", "github", "azure", "bedrock", "aws", "vertex",
]


def _subject(o: Offer) -> str:
    """Marque IA sujette de l'offre (extraite du texte), sinon le provider."""
    blob = f"{o.title} {o.description} {' '.join(o.keywords_matched)}".lower()
    for b in _AI_BRANDS_PRIORITY:
        if b in blob:
            return b
    return re.sub(r"[^a-z0-9]", "", (o.provider or "").lower()) or "unknown"



def _tokens(text: str):
    low = re.sub(r"[^a-z0-9$€]+", " ", (text or "").lower())
    return [w for w in low.split() if w not in _STOP and len(w) > 1]


def offer_dna(o: Offer) -> str:
    """Calcule l'empreinte ADN d'une offre (hash 16 chars), basée sur le SUJET.

    Le sujet (marque IA offerte) est extrait du texte plutôt que du provider
    source : ainsi une vidéo YouTube et une page web parlant du même « ChatGPT
    free » partagent le même ADN → corroboration possible entre sources.
    """
    if o.offer_type in ("job", "news", "medical"):
        return hashlib.sha1((o.url or o.title).encode("utf-8")).hexdigest()[:16]
    subject = _subject(o)
    otype = (o.offer_type or classify(f"{o.title} {o.description}") or "unknown")
    blob = f"{o.title} {o.description} {' '.join(o.keywords_matched)}"
    toks = _tokens(blob)
    # signature : marques IA + tokens bénéfices + nombres (jours/crédits/$)
    sig = set()
    for t in toks:
        if t in _AI_BRANDS or t in _BENEFIT or re.search(r"\d", t):
            sig.add(t)
    sig.discard(subject)  # déjà dans le core
    core = f"{subject}|{otype}|" + ",".join(sorted(sig)[:10])
    return hashlib.sha1(core.encode("utf-8")).hexdigest()[:16]


def same_offer(a: Offer, b: Offer) -> bool:
    return offer_dna(a) == offer_dna(b)
