"""Configuration des sources et mots-clés pour le bot de scraping IA.

Modifie librement ces listes pour ajouter / retirer des sources.
"""
from __future__ import annotations

# En-têtes HTTP pour ressembler à un navigateur (évite les blocages basiques)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}

REQUEST_TIMEOUT = 20  # secondes

# Pages officielles des fournisseurs d'IA.
#   js=True  -> le bot essaiera Playwright (si installé) puis requests en repli
#   js=False -> requête HTTP simple (requests)
OFFICIAL_SOURCES = [
    {"name": "OpenAI ChatGPT pricing", "url": "https://openai.com/chatgpt/pricing/", "provider": "OpenAI", "js": True},
    {"name": "OpenAI API pricing", "url": "https://openai.com/api/pricing/", "provider": "OpenAI", "js": True},
    {"name": "Anthropic pricing", "url": "https://www.anthropic.com/pricing", "provider": "Anthropic", "js": True},
    {"name": "Anthropic Claude", "url": "https://www.anthropic.com/claude", "provider": "Anthropic", "js": True},
    {"name": "Google AI (Gemini) pricing", "url": "https://ai.google.dev/pricing", "provider": "Google", "js": True},
    {"name": "Google AI Studio", "url": "https://aistudio.google.com", "provider": "Google", "js": True},
    {"name": "Gemini app", "url": "https://gemini.google.com", "provider": "Google", "js": True},
    {"name": "Cline (GitHub)", "url": "https://github.com/cline/cline", "provider": "Cline", "js": False},
    {"name": "Groq pricing", "url": "https://groq.com/pricing/", "provider": "Groq", "js": True},
    {"name": "Mistral platform", "url": "https://mistral.ai/products/la-plateforme", "provider": "Mistral", "js": True},
    {"name": "Cohere pricing", "url": "https://cohere.com/pricing", "provider": "Cohere", "js": True},
    {"name": "Hugging Face pricing", "url": "https://huggingface.co/pricing", "provider": "Hugging Face", "js": True},
    {"name": "Together AI pricing", "url": "https://www.together.ai/pricing", "provider": "Together AI", "js": True},
    {"name": "Google Cloud free trial", "url": "https://cloud.google.com/free", "provider": "Google Cloud", "js": True},
    {"name": "AWS Bedrock", "url": "https://aws.amazon.com/bedrock/", "provider": "AWS", "js": True},
    {"name": "Azure free account", "url": "https://azure.microsoft.com/en-us/free/", "provider": "Azure", "js": True},
    {"name": "Google Cloud Skills Boost", "url": "https://www.cloudskillsboost.google/", "provider": "Google Cloud", "js": True},
]

# Agrégateurs de ressources gratuites
AGGREGATOR_SOURCES = [
    {"name": "free-for.dev (README)", "url": "https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md", "provider": "Aggregator", "js": False},
    {"name": "free-for.dev (GitHub)", "url": "https://github.com/ripienaar/free-for-dev", "provider": "Aggregator", "js": False},
]

# Requêtes de recherche sur Hacker News (API Algolia)
FORUM_QUERIES = [
    "free AI credits",
    "free LLM API",
    "AI free tier",
    "free AI course certification",
    "free GPU colab",
    "AI promotion",
    "free API key",
    "claude free",
    "gemini free",
]

# Subreddits à surveiller (via flux .json)
REDDIT_SUBREDDITS = [
    "LocalLLaMA",
    "OpenAI",
    "ChatGPT",
    "singularity",
    "artificial",
    "MachineLearning",
    "GoogleGeminiAI",
]

# Mots-clés qui signalent une offre (insensible à la casse)
OFFER_KEYWORDS = [
    "free", "gratuit", "gratuite", "gratuitos", "kostenlos",
    "promotion", "promo", "deal", "discount", "réduction", " off", "save",
    "pass", "credits", "credit", "tier", "plan", "starter", "trial", "essai",
    "certification", "certificate", "certifié", "certif",
    "formation", "training", "course", "cours", "bootcamp", "learn", "academy",
    "$0", "0€", "no cost", "no-cost", "freemium",
]

# Mapping pour classifier le type d'offre (insensible à la casse)
OFFER_TYPE_PATTERNS = {
    "free_tier": ["free tier", "free plan", "free version", "free access", "gratuit", "free api", "freemium"],
    "promotion": ["promotion", "promo", "deal", "discount", "% off", "save", "réduction", "limited time", "limited-time"],
    "pass": ["pass", "credits", "credit", "free credits", "api key", "api credit"],
    "training": ["formation", "training", "course", "cours", "bootcamp", "learn", "academy", "tutorial"],
    "certification": ["certification", "certificate", "certif", "certifié", "badge"],
    "trial": ["trial", "essai", "free trial", "essai gratuit"],
}
