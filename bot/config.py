"""Configuration v2 : credentials (.env), sources réseaux, seuils de crédibilité.

Réutilise les sources web du config.py racine et ajoute la config réseaux sociaux
+ les seuils du moteur de crédibilité (spec utilisateur : 40% / 60%).
"""
from __future__ import annotations

import os
from pathlib import Path

# Reuse existing web sources config (officielles, agrégateurs, forums, mots-clés)
from config import (  # noqa: F401  (réexporté)
    DEFAULT_HEADERS, REQUEST_TIMEOUT,
    OFFICIAL_SOURCES, AGGREGATOR_SOURCES,
    FORUM_QUERIES, REDDIT_SUBREDDITS,
    OFFER_KEYWORDS, OFFER_TYPE_PATTERNS,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "scrapper.db"
ENV_PATH = BASE_DIR / ".env"

# --- Chargement léger du .env (pas de dépendance externe) ---
def _load_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


_load_env()

# --- Credentials réseaux (depuis .env) ---
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", str(DATA_DIR / "telegram_session"))
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")

# Canaux Telegram publics à surveiller (éditable ; les introuvables sont ignorés).
# Format : "@canal" ou "https://t.me/canal".
TELEGRAM_CHANNELS = [
    "@ai_ml_news",
    "@machinelearningai",
    "@deeplearningai",
    "@openai_channel",
    "@ai_tutorials",
]

# --- YouTube (yt-dlp, anonyme, zéro clé) ---
YOUTUBE_QUERIES = [
    "free AI API credits",
    "free LLM API no credit card",
    "free ChatGPT plus",
    "free Claude API",
    "free Gemini API",
    "free AI certification",
    "free AI course with certificate",
    "Groq free API",
]
YOUTUBE_MAX_RESULTS = 8          # vidéos par requête
YOUTUBE_MAX_COMMENTS = 60        # commentaires analysés par vidéo

# --- LinkedIn / X (best-effort, inactifs sans cookies) ---
LINKEDIN_ENABLED = os.getenv("LINKEDIN_ENABLED", "0") == "1"
LINKEDIN_COOKIES = os.getenv("LINKEDIN_COOKIES", "")  # chemin vers cookies.json
X_ENABLED = os.getenv("X_ENABLED", "0") == "1"
X_COOKIES = os.getenv("X_COOKIES", "")

# --- Seuils du moteur de crédibilité (spec utilisateur) ---
POLARITY_UNCERTAIN_THRESHOLD = 0.40   # >40% de "fake_calls" → tier "pas_sur"
POLARITY_REJECT_THRESHOLD = 0.60      # >60% → offre rejetée
CORROBORATION_MIN_SOURCES = 2         # sources indépendantes pour "verified"
CORROBORATION_BONUS_PER_SOURCE = 8    # points de score par source supplémentaire
VANISHING_PENALTY = 35                # points retirés si l'offre disparaît
EXPIRY_ENABLED = True                 # ignorer les offres expirées

# --- Lexique de polarité (FR/EN) pour classifier les commentaires ---
FAKE_CALL_TERMS = [
    "fake", "scam", "arna", "arnaqué", "arnaque", "faux", "fausse", "faux espoir",
    "it's fake", "this is fake", "not real", "doesn't work", "doesnt work",
    "ne fonctionne pas", "ça marche pas", "ca marche pas", "marche pas",
    "expired", "expiré", "expirée", "too good to be true", "clickbait",
    "phishing", "hameçonnage", "fraud", "fraude", "fake news", "bidon",
    "cgdlt", "fyo", "scamm", "rip off", "ripoff", "fake link", "virus",
]
ENDORSEMENT_TERMS = [
    "works", "it works", "ça marche", "ca marche", "merci", "thanks", "thank you",
    "verified", "vérifié", "confirmed", "confirmé", "legit", "légitime",
    "got it", "je l'ai eu", "received", "reçu", "awesome", "génial", "parfait",
    "confirmed working", "tested", "testé", "100% real", "vraiment",
]

# --- SMTP optionnel pour envoi direct (sinon mailto / Web Share) ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")

DATA_DIR.mkdir(parents=True, exist_ok=True)
