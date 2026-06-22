"""Fraîcheur / expiration : infère la date d'expiration d'une offre depuis son texte.

Règle utilisateur : une offre « 7 jours d'essai gratuit, se termine aujourd'hui »
trouvée il y a plus de 7 jours ne doit PAS être reprise.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

_UNIT_DAYS = {
    "day": 1, "days": 1, "jour": 1, "jours": 1,
    "week": 7, "weeks": 7, "semaine": 7, "semaines": 7,
    "month": 30, "months": 30, "mois": 30,
    "year": 365, "years": 365, "an": 365, "ans": 365,
}

_DURATION_RE = re.compile(
    r"(\d+)\s*[- ]?\s*(day|days|jour|jours|week|weeks|semaine|semaines|"
    r"month|months|mois|year|years|an|ans)\b", re.IGNORECASE)

_LIMITED_RE = re.compile(
    r"(limited[- ]time|limited time offer|offre limitée|temps limité|"
    r"se termine|se finit|ends? (?:today|tomorrow|in|on)|expires? (?:on|in|today)|"
    r"valable jusqu|until|valid until|offre flash)", re.IGNORECASE)


def infer_expiry(text: str, found_at_iso: str) -> Optional[str]:
    """Retourne une date d'expiration ISO (UTC) si inférable, sinon None."""
    if not text:
        return None
    base = _parse_iso(found_at_iso) or datetime.now(timezone.utc)
    m = _DURATION_RE.search(text)
    if m:
        n = int(m.group(1)); unit = m.group(2).lower()
        days = n * _UNIT_DAYS.get(unit, 0)
        if days:
            return (base + timedelta(days=days)).isoformat()
    if _LIMITED_RE.search(text):
        # « limited time » sans durée précise → on garde 14 jours de prudence
        return (base + timedelta(days=14)).isoformat()
    return None


def is_expired(expires_at_iso: Optional[str], now: Optional[datetime] = None) -> bool:
    if not expires_at_iso:
        return False
    exp = _parse_iso(expires_at_iso)
    if not exp:
        return False
    return (now or datetime.now(timezone.utc)) > exp


def _parse_iso(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
