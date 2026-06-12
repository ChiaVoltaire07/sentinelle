"""Scraper des agrégateurs de ressources gratuites (free-for.dev, awesome-lists)."""
from __future__ import annotations

import logging
import re
from typing import List

from config import AGGREGATOR_SOURCES
from models import Offer
from normalizer import classify, matches_keywords
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)

# Détection IA : on exige un signal IA *fort* (mot entier ou composé IA),
# pour éviter le bruit des outils "data"/"model" génériques non-IA.
_AI_RE = re.compile(
    r"\b(?:ai|llm|gpt|gemini|claude|openai|anthropic|hugging\s?face|"
    r"nlp|rag|chatbot|transformer|embedding|generative|"
    r"machine[-_ ]learning|deep[-_ ]learning|neural|"
    r"computer vision|speech[-_ ]to[-_ ]text|text[-_ ]to[-_ ]speech|"
    r"language model|large language|vector database|vector db|"
    r"ai api|ai model|ai platform|ai assistant|ai agent|ai image|"
    r"groq|mistral|cohere|perplexity|replicate|fireworks|deepseek|"
    r"qwen|llama|ollama|langchain|whisper|stable diffusion|midjourney)\b",
    re.IGNORECASE,
)


def _is_ai(text: str) -> bool:
    return bool(_AI_RE.search(text or ""))

# Ligne markdown de lien : "- [text](url) — desc"
_MD_LINK_RE = re.compile(r"^\s*[-*]\s*\[([^\]]+)\]\(([^)]+)\)\s*(.*)$")


class AggregatorScraper(BaseScraper):
    name = "aggregator"

    def run(self) -> List[Offer]:
        offers: List[Offer] = []
        for src in AGGREGATOR_SOURCES:
            html = self.fetch(src["url"], js=src.get("js", False))
            if not html:
                continue
            if src["url"].endswith(".md"):
                offers.extend(self._parse_markdown(src, html))
            else:
                offers.extend(self._parse_html(src, html))
        log.info("[aggregator] %d offres trouvées", len(offers))
        return offers

    def _parse_markdown(self, src, md: str) -> List[Offer]:
        out: List[Offer] = []
        in_ai_section = False
        for line in md.splitlines():
            low = line.lower()
            if line.lstrip().startswith("#"):
                in_ai_section = _is_ai(line)
                continue
            m = _MD_LINK_RE.match(line)
            if not m:
                continue
            text, href, desc = m.group(1), m.group(2), m.group(3)
            blob = f"{text} {href} {desc}".lower()
            is_ai = in_ai_section or _is_ai(blob)
            kw = matches_keywords(blob)
            if not (is_ai and kw):
                continue
            out.append(Offer(
                title=text,
                url=href,
                source=self.name,
                provider=src.get("provider", "Aggregator"),
                offer_type=classify(blob) or "free_tier",
                description=desc.strip()[:300],
                keywords_matched=kw,
            ))
        return out

    def _parse_html(self, src, html: str) -> List[Offer]:
        out: List[Offer] = []
        links = self.extract_links(html, src["url"])
        for l in links:
            blob = (l["text"] + " " + l["href"]).lower()
            if _is_ai(blob) and matches_keywords(blob):
                kw = matches_keywords(blob)
                out.append(Offer(
                    title=l["text"] or l["href"],
                    url=l["href"],
                    source=self.name,
                    provider=src.get("provider", "Aggregator"),
                    offer_type=classify(blob) or "free_tier",
                    description=l["text"][:300],
                    keywords_matched=kw,
                ))
        return out
