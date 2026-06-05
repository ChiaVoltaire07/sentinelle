"""Déduplication des offres par URL normalisée."""
from __future__ import annotations

from typing import List
from urllib.parse import urlparse, urlunparse

from models import Offer


def _normalize_url(u: str) -> str:
    p = urlparse(u)
    # On garde scheme + netloc + path, sans query/fragment, slash final retiré
    path = p.path.rstrip("/")
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", "", ""))


def dedupe(offers: List[Offer]) -> List[Offer]:
    seen = set()
    out: List[Offer] = []
    for o in offers:
        key = _normalize_url(o.url) or o.uid
        if key in seen:
            continue
        seen.add(key)
        out.append(o)
    return out
