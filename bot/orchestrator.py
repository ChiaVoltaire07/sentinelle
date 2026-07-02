"""Orchestrateur : file asyncio + pool de workers (threads) + status live.

Dispatche les sous-agents en parallèle, collecte offres + commentaires, persiste
dans le store, calcule la crédibilité, et publie la progression (callback/SSE).
Les favoris sont priorisés (leurs agents tournent en premier).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Dict, List, Optional

from bot.agents.base import BaseAgent
from bot.agents.linkedin import LinkedInAgent
from bot.agents.telegram import TelegramAgent
from bot.agents.web_agents import (WebAggregatorAgent, WebForumAgent,
                                   WebOfficialAgent, WebNewsAgent, WebJobsAgent)
from bot.agents.whatsapp import WhatsAppAgent
from bot.agents.x_twitter import XAgent
from bot.agents.youtube import YouTubeAgent
from bot.credibility import engine
from bot.credibility.expiry import is_expired
from bot.models import Offer, Run
from bot.store import Store

log = logging.getLogger(__name__)

AGENTS: Dict[str, type] = {
    "official": WebOfficialAgent,
    "aggregator": WebAggregatorAgent,
    "forum": WebForumAgent,
    "youtube": YouTubeAgent,
    "telegram": TelegramAgent,
    "linkedin": LinkedInAgent,
    "x": XAgent,
    "whatsapp": WhatsAppAgent,
    "news": WebNewsAgent,
    "jobs": WebJobsAgent,
}

# Agents actifs par défaut (les réseaux à login sont opt-in)
DEFAULT_AGENTS = ["official", "aggregator", "forum", "youtube", "telegram", "news", "jobs"]


class Orchestrator:
    def __init__(self, store: Optional[Store] = None,
                 on_progress: Optional[Callable] = None):
        self.store = store or Store()
        self.on_progress = on_progress or (lambda **kw: None)
        self.status: Dict[str, dict] = {}

    @staticmethod
    def available_agents() -> List[str]:
        return list(AGENTS.keys())

    async def run(self, only: Optional[List[str]] = None,
                  score: bool = True) -> dict:
        targets = only or DEFAULT_AGENTS
        # Priorité : agents liés à des sources favorisées en premier (cosmétique)
        run = Run(agents=targets)
        run_id = self.store.save_run(run)
        self.on_progress(event="run_start", run_id=run_id, agents=targets)
        t0 = time.time()

        results = await asyncio.gather(
            *[self._run_agent(k) for k in targets], return_exceptions=True)

        all_offers: List[Offer] = []
        all_comments = []
        for key, res in zip(targets, results):
            if isinstance(res, Exception):
                self.status[key] = {"agent": key, "status": "error", "offers": 0,
                                    "comments": 0, "error": str(res)}
                self.on_progress(event="agent_error", agent=key, error=str(res))
                log.exception("[%s] erreur: %s", key, res)
            else:
                offers, comments = res
                self.status[key] = {"agent": key, "status": "done",
                                    "offers": len(offers), "comments": len(comments)}
                self.on_progress(event="agent_done", agent=key,
                                 offers=len(offers), comments=len(comments))
                all_offers += offers
                all_comments += comments

        # Persistance + provenance (corroboration)
        for o in all_offers:
            self.store.upsert_offer(o)
            self.store.add_provenance(o.dna_hash, o.source, o.url)
        for c in all_comments:
            self.store.upsert_comment(c)

        # Crédibilité (4 couches) sur tout le stock
        scored = 0
        if score:
            scored = await asyncio.to_thread(engine.score_all, self.store)
            self.on_progress(event="scored", count=scored)

        dropped = await asyncio.to_thread(self._drop_expired)
        self.store.update_run(run_id, "done", len(all_offers))
        elapsed = round(time.time() - t0, 1)
        self.on_progress(event="run_done", run_id=run_id, offers=len(all_offers),
                         comments=len(all_comments), dropped=dropped,
                         scored=scored, elapsed=elapsed)
        return {"offers": len(all_offers), "comments": len(all_comments),
                "dropped": dropped, "scored": scored, "elapsed": elapsed,
                "status": dict(self.status)}

    async def _run_agent(self, key: str):
        cls = AGENTS.get(key)
        if not cls:
            raise ValueError(f"agent inconnu: {key}")
        self.status[key] = {"agent": key, "status": "running", "offers": 0, "comments": 0}
        self.on_progress(event="agent_start", agent=key)
        agent: BaseAgent = cls()
        offers = await asyncio.to_thread(agent.run)
        comments = await asyncio.to_thread(agent.collect_comments, offers)
        return offers, comments

    def _drop_expired(self) -> int:
        n = 0
        for o in self.store.get_offers(limit=100000):
            if o.expires_at and is_expired(o.expires_at) and o.status != "expired":
                self.store.set_offer_status(o.id, "expired")
                n += 1
        return n
