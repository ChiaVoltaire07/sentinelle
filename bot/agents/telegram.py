"""Agent Telegram : Telethon (MTProto) → canaux publics IA.

Lit les messages récents des canaux configurés, filtre par mots-clés IA, et
récupère les réponses (reply) comme commentaires pour la polarité.

Nécessite TELEGRAM_API_ID + TELEGRAM_API_HASH (.env). La première authentification
est interactive : lance `python -m bot.telegram_login` une fois.
"""
from __future__ import annotations

import asyncio
import logging
from typing import List

from bot.agents.base import BaseAgent
from bot.config import (
    TELEGRAM_API_HASH, TELEGRAM_API_ID, TELEGRAM_CHANNELS,
    TELEGRAM_PHONE, TELEGRAM_SESSION,
)
from bot.credibility.dna import offer_dna
from bot.credibility.expiry import infer_expiry
from bot.credibility.polarity import classify_comment
from bot.models import Comment, Offer
from normalizer import classify, matches_keywords

log = logging.getLogger(__name__)

_TELETHON_OK = True
try:
    from telethon import TelegramClient
except Exception:
    _TELETHON_OK = False


class TelegramAgent(BaseAgent):
    name = "telegram"
    network = "telegram"

    def __init__(self):
        self._comments: List[Comment] = []

    def run(self) -> List[Offer]:
        if not _TELETHON_OK:
            log.warning("[telegram] telethon indisponible — agent inactif")
            return []
        if not (TELEGRAM_API_ID and TELEGRAM_API_HASH):
            log.warning("[telegram] API ID/HASH manquants — agent inactif (voir .env)")
            return []
        try:
            return asyncio.run(self._run_async())
        except Exception as e:
            log.warning("[telegram] erreur: %s", e)
            return []

    async def _run_async(self) -> List[Offer]:
        offers: List[Offer] = []
        client = TelegramClient(str(TELEGRAM_SESSION), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            log.warning(
                "[telegram] session non autorisée. Lance une fois "
                "`python -m bot.telegram_login` pour t'authentifier.")
            await client.disconnect()
            return []
        for ch in TELEGRAM_CHANNELS:
            try:
                entity = await client.get_entity(ch)
            except Exception as e:
                log.warning("[telegram] canal introuvable %s: %s", ch, e)
                continue
            username = getattr(entity, "username", None)
            async for msg in client.iter_messages(entity, limit=50):
                text = msg.message or ""
                if not matches_keywords(text):
                    continue
                url = f"https://t.me/{username}/{msg.id}" if username else ch
                o = Offer(
                    title=text[:80], url=str(url), source="telegram", agent="telegram",
                    provider=ch, offer_type=classify(text) or "promotion",
                    network="telegram", description=text[:300],
                    keywords_matched=matches_keywords(text),
                )
                o.dna_hash = offer_dna(o)
                o.expires_at = infer_expiry(text, o.found_at)
                o.provenance = [{"source": "telegram", "url": str(url),
                                 "found_at": o.found_at, "alive": True}]
                offers.append(o)
                await self._mine_replies(client, entity, msg.id, o.dna_hash)
        await client.disconnect()
        log.info("[telegram] %d offres, %d commentaires", len(offers), len(self._comments))
        return offers

    async def _mine_replies(self, client, entity, msg_id, dna) -> None:
        try:
            async for r in client.iter_messages(entity, reply_to=msg_id, limit=20):
                rt = r.message or ""
                if rt:
                    self._comments.append(Comment(
                        offer_dna=dna, source="telegram",
                        author=str(r.sender_id), text=rt,
                        polarity=classify_comment(rt),
                    ))
        except Exception as e:
            log.debug("[telegram] réponses échec: %s", e)

    def collect_comments(self, offers: List[Offer]) -> List[Comment]:
        return self._comments
