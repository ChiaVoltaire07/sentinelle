"""Génération du rapport : Markdown + JSON."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List

from models import Offer

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

TYPE_EMOJI = {
    "free_tier": "🆓",
    "promotion": "🏷️",
    "pass": "🎟️",
    "credits": "🎟️",
    "trial": "⏳",
    "training": "🎓",
    "certification": "📜",
    "unknown": "🔹",
}

TYPE_ORDER = ["free_tier", "promotion", "pass", "trial", "training", "certification", "unknown"]


def _group_by_type(offers: List[Offer]) -> dict:
    groups: dict = {}
    for o in offers:
        groups.setdefault(o.offer_type or "unknown", []).append(o)
    return groups


def render_markdown(offers: List[Offer]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 🤖 Offres & promotions IA — Rapport de scraping",
        "",
        f"_Généré le {now} — {len(offers)} offre(s) détectée(s)_",
        "",
        "> Bot de scraping pour partager les offres gratuites, promotions, crédits,",
        "> pass, formations et certifications liées à l'IA.",
        "",
    ]
    groups = _group_by_type(offers)
    for otype in TYPE_ORDER:
        items = groups.get(otype, [])
        if not items:
            continue
        emoji = TYPE_EMOJI.get(otype, "🔹")
        lines.append(f"## {emoji} {otype.replace('_', ' ').title()} ({len(items)})")
        lines.append("")
        for o in items:
            desc = f" — {o.description}" if o.description else ""
            lines.append(f"- **[{o.title}]({o.url})** `{o.provider}`{desc}")
            if o.keywords_matched:
                lines.append(f"  - mots-clés: {', '.join(o.keywords_matched[:8])}")
        lines.append("")
    if not offers:
        lines.append("_Aucune offre détectée cette exécution._")
    return "\n".join(lines)


def save(offers: List[Offer]) -> tuple:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(OUTPUT_DIR, f"rapport_ia_{ts}.md")
    json_path = os.path.join(OUTPUT_DIR, f"rapport_ia_{ts}.json")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(offers),
        "offers": [o.to_dict() for o in offers],
    }
    md_content = render_markdown(offers)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # Versions "latest" (écrasées à chaque exécution)
    with open(os.path.join(OUTPUT_DIR, "LATEST.md"), "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(os.path.join(OUTPUT_DIR, "LATEST.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return md_path, json_path
