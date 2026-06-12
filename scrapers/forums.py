"""Scraper de forums : Hacker News (API Algolia) + Reddit (flux .json)."""
from __future__ import annotations

import logging
from typing import List

from config import FORUM_QUERIES, REDDIT_SUBREDDITS, REQUEST_TIMEOUT
from models import Offer
from normalizer import classify, matches_keywords
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)


class ForumScraper(BaseScraper):
    name = "forum"

    def run(self) -> List[Offer]:
        offers: List[Offer] = []
        offers.extend(self._hackernews())
        offers.extend(self._reddit())
        log.info("[forum] %d offres trouvées", len(offers))
        return offers

    def _hackernews(self) -> List[Offer]:
        out: List[Offer] = []
        for q in FORUM_QUERIES:
            url = (
                "https://hn.algolia.com/api/v1/search?"
                f"query={q.replace(' ', '+')}&tags=story&hitsPerPage=20"
            )
            data = self._get_json(url)
            if not data:
                continue
            for hit in data.get("hits", []):
                title = hit.get("title") or ""
                link = hit.get("url") or (
                    f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                )
                kw = matches_keywords(title)
                if not kw:
                    continue
                out.append(Offer(
                    title=title,
                    url=link,
                    source="hackernews",
                    provider="Forum",
                    offer_type=classify(title.lower()) or "promotion",
                    description=(
                        f"HN • {hit.get('points', 0)} pts • "
                        f"{hit.get('num_comments', 0)} commentaires"
                    ),
                    keywords_matched=kw,
                ))
        return out

    def _reddit(self) -> List[Offer]:
        out: List[Offer] = []
        for sub in REDDIT_SUBREDDITS:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=50"
            data = self._get_json(url)
            if not data:
                continue
            children = data.get("data", {}).get("children", [])
            for c in children:
                d = c.get("data", {})
                title = d.get("title", "")
                blob = (title + " " + d.get("selftext", "")).lower()
                kw = matches_keywords(blob)
                if not kw:
                    continue
                permalink = d.get("permalink")
                link = f"https://www.reddit.com{permalink}" if permalink else d.get("url", "")
                out.append(Offer(
                    title=title,
                    url=link,
                    source="reddit",
                    provider=f"r/{sub}",
                    offer_type=classify(blob) or "promotion",
                    description=f"score {d.get('score', 0)} • r/{sub}",
                    keywords_matched=kw,
                ))
        return out

    def _get_json(self, url: str):
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.warning("[forum] JSON échec %s : %s", url, e)
            return None
