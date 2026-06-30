"""Agent YouTube : yt-dlp (anonyme, zéro clé) → vidéos + commentaires.

Les vidéos qui parlent d'offres IA deviennent des offres ; les commentaires
sont classés en polarité (fake_call / endorsement) pour le moteur de crédibilité.
"""
from __future__ import annotations

import logging
from typing import List

from bot.agents.base import BaseAgent
from bot.config import YOUTUBE_MAX_COMMENTS, YOUTUBE_MAX_RESULTS, YOUTUBE_QUERIES
from bot.credibility.dna import offer_dna
from bot.credibility.expiry import infer_expiry
from bot.credibility.polarity import classify_comment
from bot.models import Comment, Offer
from normalizer import classify, matches_keywords

log = logging.getLogger(__name__)

try:
    import yt_dlp
    _YT_OK = True
except Exception:
    _YT_OK = False


class YouTubeAgent(BaseAgent):
    name = "youtube"
    network = "youtube"

    def __init__(self):
        self._comments: List[Comment] = []

    def run(self) -> List[Offer]:
        if not _YT_OK:
            log.warning("[youtube] yt-dlp indisponible — agent inactif")
            return []
        offers: List[Offer] = []
        search_opts = {
            "quiet": True, "no_warnings": True, "skip_download": True,
            "extract_flat": True, "ignoreerrors": True, "playlistend": YOUTUBE_MAX_RESULTS,
        }
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            for q in YOUTUBE_QUERIES:
                try:
                    info = ydl.extract_info(f"ytsearch{YOUTUBE_MAX_RESULTS}:{q}", download=False)
                except Exception as e:
                    log.warning("[youtube] recherche '%s' échec: %s", q, e)
                    continue
                for e in info.get("entries", []) or []:
                    if not e:
                        continue
                    title = e.get("title", "")
                    url = e.get("url") or e.get("webpage_url") or f"https://youtu.be/{e.get('id', '')}"
                    desc = e.get("description") or ""
                    blob = f"{title} {desc}"
                    if not matches_keywords(blob):
                        continue
                    o = Offer(
                        title=title, url=url, source="youtube", agent="youtube",
                        provider="YouTube", offer_type=classify(blob) or "promotion",
                        network="youtube", description=desc[:300],
                        keywords_matched=matches_keywords(blob),
                    )
                    o.dna_hash = offer_dna(o)
                    o.expires_at = infer_expiry(blob, o.found_at)
                    o.provenance = [{"source": "youtube", "url": url,
                                     "found_at": o.found_at, "alive": True}]
                    offers.append(o)
                    self._mine_comments(url, o.dna_hash)
        log.info("[youtube] %d offres, %d commentaires", len(offers), len(self._comments))
        return offers

    def _mine_comments(self, url: str, dna: str) -> None:
        opts = {"quiet": True, "no_warnings": True, "skip_download": True,
                "getcomments": True, "extract_flat": False, "ignoreerrors": True,
                "skip_download": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                vi = ydl.extract_info(url, download=False)
        except Exception as e:
            log.debug("[youtube] commentaires échec %s: %s", url, e)
            return
        for c in (vi.get("comments", []) or [])[:YOUTUBE_MAX_COMMENTS]:
            txt = c.get("text", "") or ""
            if not txt:
                continue
            self._comments.append(Comment(
                offer_dna=dna, source="youtube",
                author=c.get("author", "") or str(c.get("author_id", "")),
                text=txt, polarity=classify_comment(txt),
            ))

    def collect_comments(self, offers: List[Offer]) -> List[Comment]:
        return self._comments
