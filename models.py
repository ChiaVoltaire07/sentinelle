"""Modèle de données pour une offre IA détectée."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class Offer:
    title: str
    url: str
    source: str
    provider: str = "Inconnu"
    offer_type: str = "unknown"
    description: str = ""
    keywords_matched: List[str] = field(default_factory=list)
    found_at: str = ""

    def __post_init__(self):
        if not self.found_at:
            self.found_at = datetime.now(timezone.utc).isoformat()

    @property
    def uid(self) -> str:
        raw = f"{self.url}|{self.title.lower().strip()}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> dict:
        return asdict(self)
