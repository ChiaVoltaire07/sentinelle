"""Adaptateurs des scrapers web v1 (officiel, agrégateur, forums) en agents v2.

Réutilise la logique de scraping déjà validée (scrapers/) en l'enrichissant
(ADN, expiration, provenance, crédibilité).
"""
from __future__ import annotations

import logging
from typing import List

from bot.agents.base import BaseAgent
from bot.models import Offer
from scrapers.aggregators import AggregatorScraper
from scrapers.forums import ForumScraper
from scrapers.official import OfficialScraper
from scrapers.news import NewsScraper
from scrapers.jobs import JobsScraper

log = logging.getLogger(__name__)


class WebOfficialAgent(BaseAgent):
    name = "official"
    network = "web"

    def run(self) -> List[Offer]:
        try:
            raws = OfficialScraper().run()
        except Exception as e:
            log.exception("[official] erreur: %s", e)
            return []
        return [self.convert(r) for r in raws]


class WebAggregatorAgent(BaseAgent):
    name = "aggregator"
    network = "web"

    def run(self) -> List[Offer]:
        try:
            raws = AggregatorScraper().run()
        except Exception as e:
            log.exception("[aggregator] erreur: %s", e)
            return []
        return [self.convert(r) for r in raws]


class WebForumAgent(BaseAgent):
    name = "forum"
    network = "web"

    def run(self) -> List[Offer]:
        try:
            raws = ForumScraper().run()
        except Exception as e:
            log.exception("[forum] erreur: %s", e)
            return []
        return [self.convert(r) for r in raws]


class WebNewsAgent(BaseAgent):
    name = "news"
    network = "web"

    def run(self) -> List[Offer]:
        try:
            raws = NewsScraper().run()
        except Exception as e:
            log.exception("[news] erreur: %s", e)
            return []
        return [self.convert(r) for r in raws]


class WebJobsAgent(BaseAgent):
    name = "jobs"
    network = "web"

    def run(self) -> List[Offer]:
        try:
            raws = JobsScraper().run()
        except Exception as e:
            log.exception("[jobs] erreur: %s", e)
            return []
        return [self.convert(r) for r in raws]

