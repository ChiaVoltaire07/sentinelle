"""Module IA (Gemini) pour la PWA : classification d'intentions, résumés et réponses chat."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, List, Optional
import requests

from bot.config import ENV_PATH

log = logging.getLogger(__name__)


def get_gemini_key() -> Optional[str]:
    """Récupère la clé API Gemini depuis l'environnement."""
    return os.getenv("GEMINI_API_KEY")


def call_gemini(prompt: str, json_mode: bool = False) -> Optional[str]:
    """Appelle l'API Gemini en direct via REST (sans dépendance lourde).

    Rotation automatique entre modèles : chaque modèle Gemini possède son propre
    quota (RPM/RPD) ; en cas de 429/404/503, on tente le modèle suivant.
    """
    key = get_gemini_key()
    if not key:
        return None

    primary = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    fallbacks = ["gemini-3-flash-preview", "gemini-3.1-flash-lite-preview", "gemini-flash-latest"]
    models = [primary] + [m for m in fallbacks if m != primary]

    payload: Dict = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    if json_mode:
        payload["generationConfig"] = {
            "responseMimeType": "application/json"
        }

    headers = {"Content-Type": "application/json"}
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code in (429, 404, 503):
                log.warning("[AI] Gemini %s indisponible (HTTP %d) — modèle suivant", model, resp.status_code)
                continue
            resp.raise_for_status()
            res_data = resp.json()
            
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                # Ignorer les parties "thought" des modèles de raisonnement (2.5+/3.x)
                texts = [p.get("text", "") for p in parts if p.get("text") and not p.get("thought")]
                if texts:
                    return "".join(texts).strip()
            return None
        except Exception as e:
            log.warning("[AI] Erreur appel Gemini (%s) : %s", model, e)
    
    return None


def call_ollama(prompt: str) -> Optional[str]:
    """Appelle l'API Ollama locale si elle est disponible."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "mistral")
    url = f"{host}/api/generate"
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        resp = requests.post(url, json=payload, timeout=45)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        log.debug("[AI] Ollama non disponible sur %s : %s", host, e)
        return None


def call_llm(prompt: str, json_mode: bool = False) -> Optional[str]:
    """Appelle le meilleur LLM disponible (Gemini par défaut, Ollama en repli ou préférence)."""
    prefer_ollama = os.getenv("PREFER_OLLAMA", "false").lower() == "true"
    if prefer_ollama:
        res = call_ollama(prompt)
        if res:
            return res
            
    res = call_gemini(prompt, json_mode)
    if res:
        return res
        
    # Repli final sur Ollama
    if not prefer_ollama:
        return call_ollama(prompt)
        
    return None


def parse_user_intent(message: str) -> dict:
    """Analyse la requête pour en extraire l'intention et les mots-clés."""
    key = get_gemini_key()
    if key:
        prompt = f"""
        Tu es le routeur d'intention d'un hub de recherche ancré sur le scraping (style Perplexity).
        Message : "{message}"

        Réponds UNIQUEMENT en JSON valide :
        - "intent" parmi :
            * "search_jobs"
            * "search_scholarships"
            * "search_travel"
            * "search_events"
            * "search_news"
            * "search_offers"
            * "search_medical"
            * "search_crypto"
            * "search_geopolitics"
            * "search_predictions"
            * "create_watch" (si l'utilisateur veut suivre une entreprise, un conflit, un événement dans le temps / dashboard)
            * "chat" (salutations uniquement, sans recherche)
        - "query" : requête nettoyée (pour create_watch : nom de l'entité ou du sujet)
        - "category" : si search_news : top|tech|sport|finance|politic|economie|ia sinon null
        - "reply" : courte phrase de transition en français
        """
        res = call_llm(prompt, json_mode=True)
        if res:
            try:
                data = json.loads(res)
                if "intent" in data:
                    return data
            except Exception:
                log.warning("[AI] Échec parsing JSON Gemini : %s", res)

    low = message.lower()

    if any(x in low for x in ["suis ", "suivre", "suivi", "watch", "dashboard", "tableau de bord", "monitorer", "surveille"]):
        query = message
        for word in ["je", "veux", "voudrais", "aimerais", "suis", "suivre", "le", "la", "les", "l'", "suivi", "de", "du", "des", "évolution", "evolution", "actu", "actualité"]:
            query = re.sub(rf"\b{word}\b", " ", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "create_watch",
            "query": query or message.strip(),
            "category": None,
            "reply": f"Je crée / mets à jour un tableau de suivi pour « {query or message.strip()} »...",
        }

    if any(x in low for x in ["crypto", "bitcoin", "btc", "ethereum", "eth", "coingecko", "token", "blockchain"]):
        query = re.sub(r"\b(cherche|trouve|crypto|prix|cours|de|du|des|le|la|les)\b", " ", message, flags=re.I)
        query = " ".join(query.split())
        return {
            "intent": "search_crypto",
            "query": query or "bitcoin",
            "category": None,
            "reply": f"Je consulte les marchés et actus crypto pour '{query or 'bitcoin'}'...",
        }

    if any(x in low for x in ["polymarket", "prédiction", "prediction", "probabilité", "probabilite", "pari", "odds", "marché de prédiction"]):
        query = re.sub(r"\b(cherche|trouve|polymarket|prédiction|prediction|probabilité|sur|de|du|des)\b", " ", message, flags=re.I)
        query = " ".join(query.split())
        return {
            "intent": "search_predictions",
            "query": query or "election",
            "category": None,
            "reply": f"Je récupère les probabilités Polymarket pour '{query or 'election'}'...",
        }

    if any(x in low for x in ["guerre", "conflit", "géopolit", "geopolit", "sanctions", "ukraine", "gaza", "otan", "taiwan", "sahel"]):
        query = message
        for word in ["cherche", "trouve", "actu", "actualite", "sur", "le", "la", "les", "de"]:
            query = re.sub(rf"\b{word}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "search_geopolitics",
            "query": query or "conflit",
            "category": None,
            "reply": f"Je rassemble des sources géopolitiques sur '{query or 'conflit'}'...",
        }

    if any(x in low for x in ["medecin", "medical", "essai", "clinique", "pathologie", "traitement", "paludisme", "malaria", "drepanocytose", "sickle cell", "hiv", "vih", "tuberculose", "tuberculosis", "cancer", "sante", "santé", "pubmed"]):
        query = message
        for word in ["cherche", "trouve", "trouver", "les", "des", "essais", "cliniques", "clinique", "sur", "le", "la", "l'", "pour", "contre"]:
            query = re.sub(rf"\b{word}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "search_medical",
            "query": query or "malaria",
            "category": None,
            "reply": f"Je recherche des études cliniques et publications sur '{query or 'malaria'}'..."
        }

    if any(x in low for x in ["bourse", "bourses", "scholarship", "fellowship", "grant study"]):
        query = message
        for word in ["cherche", "trouve", "trouver", "des", "les", "bourses", "bourse", "scholarship", "scholarships", "de", "pour", "en"]:
            query = re.sub(rf"\b{word}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "search_scholarships",
            "query": query or "scholarship",
            "category": None,
            "reply": f"Je cherche des bourses / scholarships pour « {query or 'études'} »...",
        }

    if any(x in low for x in ["voyage", "travel grant", "mobilité", "mobilite", "visa opportunity", "échange", "echange"]):
        query = message
        for word in ["cherche", "trouve", "trouver", "des", "les", "voyages", "voyage", "opportunités", "opportunites", "de", "pour", "en"]:
            query = re.sub(rf"\b{word}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "search_travel",
            "query": query or "mobilité",
            "category": None,
            "reply": f"Je cherche des opportunités de voyage / mobilité pour « {query or 'mobilité'} »...",
        }

    if any(x in low for x in ["événement", "evenement", "events", "event", "conférence", "conference", "meetup", "hackathon"]):
        query = message
        for word in ["cherche", "trouve", "trouver", "des", "les", "événements", "evenements", "événement", "evenement", "events", "event", "de", "pour", "en"]:
            query = re.sub(rf"\b{word}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "search_events",
            "query": query or "tech",
            "category": None,
            "reply": f"Je cherche des événements pour « {query or 'tech'} »...",
        }

    if any(x in low for x in ["job", "emploi", "recrute", "travail", "stage", "alternance", "position", "career", "poste", "developer"]):
        query = message
        for word in ["cherche", "trouve", "trouver", "des", "jobs", "job", "offres", "offre", "d'emploi", "emploi", "de", "pour", "en"]:
            query = re.sub(rf"\b{word}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "search_jobs",
            "query": query or "developer",
            "category": None,
            "reply": f"Je recherche des offres d'emploi pour '{query or 'developer'}'..."
        }

    if any(x in low for x in ["actu", "news", "nouvelle", "actualite", "actualité", "sport", "tech", "finance", "politique", "economie", "économie", "ia"]):
        category = "top"
        if "tech" in low:
            category = "tech"
        elif "sport" in low:
            category = "sport"
        elif "finance" in low or "affaires" in low:
            category = "finance"
        elif "politi" in low:
            category = "politic"
        elif "econo" in low:
            category = "economie"
        elif "ia" in low or "intelligence" in low or "ai" in low:
            category = "ia"
        query = message
        for word in ["actu", "actus", "news", "nouvelles", "actualites", "actualité", "sur", "l'", "la", "le", "les"]:
            query = re.sub(rf"\b{word}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "search_news",
            "query": query or category,
            "category": category,
            "reply": f"Je consulte les actualités '{category}'..."
        }

    if any(x in low for x in ["promo", "reduction", "free", "gratuit", "discount", "credits", "offre"]):
        query = message
        for word in ["cherche", "trouve", "promos", "promo", "gratuit", "free", "credits", "offres"]:
            query = re.sub(rf"\b{word}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())
        return {
            "intent": "search_offers",
            "query": query or "AI",
            "category": None,
            "reply": f"Je recherche des promotions liées à '{query or 'AI'}'..."
        }

    # Recherche générique -> news scrape
    if len(message.strip()) > 12 and not any(x in low for x in ["bonjour", "salut", "hello", "merci", "hey"]):
        return {
            "intent": "search_news",
            "query": message.strip(),
            "category": None,
            "reply": f"Je lance une recherche sourcée sur « {message.strip()[:60]} »...",
        }

    return {
        "intent": "chat",
        "query": "",
        "category": None,
        "reply": "Bonjour. Pose une question : j'irai scraper des sources et je répondrai uniquement à partir d'elles."
    }


def generate_summary(title: str, text: str) -> str:
    """Génère un résumé en français d'un texte d'actualité/offre."""
    key = get_gemini_key()
    if key or os.getenv("OLLAMA_HOST") or os.getenv("PREFER_OLLAMA") == "true":
        prompt = f"""
        Résume le texte suivant en une seule phrase courte et percutante en français (maximum 120 caractères).
        Titre : {title}
        Texte : {text[:1000]}
        """
        summary = call_llm(prompt)
        if summary:
            return summary

    if len(text) > 150:
        return text[:147] + "..."
    return text


def synthesize_digest(user_message: str, offers: list) -> str:
    """Synthèse ancrée STRICTEMENT sur les items scrapés (pas de connaissances hors sources)."""
    if not offers:
        return ""

    data_str = json.dumps([
        {
            "title": getattr(o, "title", ""),
            "description": getattr(o, "description", ""),
            "provider": getattr(o, "provider", ""),
            "url": getattr(o, "url", ""),
            "type": getattr(o, "offer_type", ""),
        } for o in offers[:20]
    ], ensure_ascii=False)

    key = get_gemini_key()
    if key or os.getenv("OLLAMA_HOST") or os.getenv("PREFER_OLLAMA", "").lower() == "true":
        prompt = f"""
Tu es l'assistant d'un hub de recherche type Perplexity.
Question utilisateur : "{user_message}"

SOURCES SCRAPÉES (seule vérité autorisée) :
{data_str}

Règles ABSOLUES :
1. Réponds UNIQUEMENT à partir des sources ci-dessus. Aucune connaissance externe.
2. Si les sources sont insuffisantes, dis-le clairement sans inventer.
3. 2 à 4 courts paragraphes en français, puis une liste de liens markdown des sources citées.
4. N'ajoute aucun conseil financier, médical ou militaire au-delà de ce que disent les sources.
"""
        res = call_llm(prompt)
        if res:
            return res

    # Fallback déterministe sans LLM
    lines = [f"Voici ce que les sources scrapées indiquent pour « {user_message} » :\n"]
    for o in offers[:8]:
        lines.append(f"- **{getattr(o, 'title', '')}** ({getattr(o, 'provider', '')})")
        desc = getattr(o, "description", "") or ""
        if desc:
            lines.append(f"  {desc[:160]}")
        url = getattr(o, "url", "")
        if url:
            lines.append(f"  [Source]({url})")
    return "\n".join(lines)

def generate_medical_cheat_sheet(
    title: str,
    summary: str,
    criteria: str,
    nct_id: Optional[str] = None,
    phase: Optional[str] = None,
    status: Optional[str] = None,
    sponsor: Optional[str] = None,
) -> Optional[str]:
    """Prend un protocole clinique brut et le résume en fiche 30s, avec garde-fous."""
    summary = (summary or "").strip()
    criteria = (criteria or "").strip()
    title = (title or "").strip()

    # Garde-fou : refuser si la source est trop pauvre pour éviter les hallucinations
    if len(summary) < 40 and len(criteria) < 40:
        log.info("[AI] Cheat sheet refusée (source trop pauvre) pour: %s", title[:80])
        return None

    key = get_gemini_key()
    if not (key or os.getenv("OLLAMA_HOST") or os.getenv("PREFER_OLLAMA", "").lower() == "true"):
        return None

    cite = nct_id or "source non fournie"
    prompt = f"""
Tu es un assistant d'aide à la décision clinique B2B pour professionnels de santé uniquement.
Synthétise STRICTEMENT à partir des données fournies. N'invente AUCUN effet secondaire, critère ou contact absent du texte.
Si une information manque, écris « Non précisé dans la source ».

Identifiant officiel à citer : {cite}
Titre : {title}
Phase déclarée : {phase or "Non précisé"}
Statut déclaré : {status or "Non précisé"}
Sponsor déclaré : {sponsor or "Non précisé"}
Résumé source : {summary[:1500]}
Critères source : {criteria[:1500]}

Structure STRICTE (Markdown) :
### MÉMO CLINIQUE
* **Référence** : {cite}
* **Objectif** : ...
* **Critères d'inclusion clés** : ...
* **Critères d'exclusion clés** : ...
* **Phase & Statut** : ...
* **Effets secondaires majeurs** : ... (ou Non précisé dans la source)
* **Sponsor / Contact** : ...
* **Disclaimer** : Fiche d'aide à la décision pour professionnels ; ne remplace pas le jugement clinique ni le protocole officiel.
"""

    res = call_llm(prompt)
    if not res:
        return None
    # Garde-fou post-génération : la fiche doit citer l'identifiant si disponible
    if nct_id and nct_id not in res:
        res = f"* **Référence** : {nct_id}\n\n" + res
    return res


def get_embedding(text: str) -> Optional[List[float]]:
    """Génère l'embedding vectoriel d'un texte (gemini-embedding-001, 768 dimensions).

    Les modèles text-embedding-00x ont été retirés de l'API ; gemini-embedding-001
    accepte outputDimensionality=768 (Matryoshka), ce qui reste compatible avec le
    schéma Postgres vector(768) et réduit le stockage (~3 Ko / dossier).
    """
    key = get_gemini_key()
    if not key or not text:
        return None
    model = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": f"models/{model}",
        "content": {
            "parts": [{"text": text}]
        },
        "outputDimensionality": 768
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("embedding", {}).get("values")
    except Exception as e:
        log.warning("[AI] Échec de la génération d'embeddings : %s", e)
        return None
