"""Agent WhatsApp — STUB expérimental (inactif).

WhatsApp n'expose pas d'API publique et l'automatisation de WhatsApp Web est
anti-ToS + fragile (QR). Conformément au plan, cet agent ne fait rien par défaut.
"""
from __future__ import annotations

import logging
from typing import List

from bot.agents.base import BaseAgent
from bot.models import Offer

log = logging.getLogger(__name__)


class WhatsAppAgent(BaseAgent):
    name = "whatsapp"
    network = "whatsapp"

    def run(self) -> List[Offer]:
        log.info("[whatsapp] stub inactif (anti-ToS / pas d'API publique)")
        return []
