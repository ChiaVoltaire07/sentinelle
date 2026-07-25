"""Store SQLite pour les suivis d'entités / événements (watches)."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from bot.config import DATA_DIR

WATCH_DB = DATA_DIR / "watches.db"


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9àâäéèêëïîôùûüç\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:80] or "watch"


class WatchStore:
    def __init__(self, path: Path = WATCH_DB):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                kind TEXT NOT NULL, -- company | geopolitics | event | custom
                query TEXT NOT NULL,
                ticker TEXT,
                description TEXT,
                meta_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now', 'utc')),
                updated_at TEXT DEFAULT (datetime('now', 'utc')),
                last_refreshed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS watch_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watch_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                provider TEXT,
                summary TEXT,
                event_type TEXT DEFAULT 'news',
                published_at TEXT,
                created_at TEXT DEFAULT (datetime('now', 'utc')),
                UNIQUE(watch_id, url),
                FOREIGN KEY(watch_id) REFERENCES watches(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS watch_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watch_id INTEGER NOT NULL,
                ts TEXT NOT NULL,
                price REAL NOT NULL,
                volume REAL,
                source TEXT DEFAULT 'yahoo',
                UNIQUE(watch_id, ts),
                FOREIGN KEY(watch_id) REFERENCES watches(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS watch_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watch_id INTEGER NOT NULL,
                kind TEXT NOT NULL, -- summary | analysis | trading
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'utc')),
                FOREIGN KEY(watch_id) REFERENCES watches(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_watch_events_wid ON watch_events(watch_id, id DESC);
            CREATE INDEX IF NOT EXISTS idx_watch_prices_wid ON watch_prices(watch_id, ts);
            """
        )

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def create(
        self,
        title: str,
        kind: str = "custom",
        query: str = "",
        ticker: Optional[str] = None,
        description: str = "",
        meta: Optional[dict] = None,
    ) -> dict:
        kind = kind if kind in ("company", "geopolitics", "event", "custom") else "custom"
        query = query or title
        base = _slugify(title)
        slug = base
        n = 2
        while self.get_by_slug(slug):
            slug = f"{base}-{n}"
            n += 1
        cur = self.conn.execute(
            """INSERT INTO watches (slug, title, kind, query, ticker, description, meta_json)
               VALUES (?,?,?,?,?,?,?)""",
            (slug, title.strip(), kind, query.strip(), (ticker or "").upper() or None,
             description, json.dumps(meta or {}, ensure_ascii=False)),
        )
        return self.get(cur.lastrowid)

    def list(self) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM watches ORDER BY updated_at DESC, id DESC"
        ).fetchall()
        return [self._watch_row(r) for r in rows]

    def get(self, watch_id: int) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM watches WHERE id=?", (watch_id,)).fetchone()
        return self._watch_row(row) if row else None

    def get_by_slug(self, slug: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM watches WHERE slug=?", (slug,)).fetchone()
        return self._watch_row(row) if row else None

    def delete(self, watch_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM watches WHERE id=?", (watch_id,))
        return cur.rowcount > 0

    def touch_refreshed(self, watch_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE watches SET last_refreshed_at=?, updated_at=? WHERE id=?",
            (now, now, watch_id),
        )

    def add_event(
        self,
        watch_id: int,
        title: str,
        url: str = "",
        provider: str = "",
        summary: str = "",
        event_type: str = "news",
        published_at: Optional[str] = None,
    ) -> None:
        try:
            self.conn.execute(
                """INSERT INTO watch_events
                   (watch_id, title, url, provider, summary, event_type, published_at)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(watch_id, url) DO UPDATE SET
                     title=excluded.title,
                     summary=excluded.summary,
                     provider=excluded.provider""",
                (watch_id, title, url or f"local:{title[:40]}", provider, summary, event_type, published_at),
            )
        except sqlite3.IntegrityError:
            pass

    def list_events(self, watch_id: int, limit: int = 50) -> List[dict]:
        rows = self.conn.execute(
            """SELECT * FROM watch_events WHERE watch_id=?
               ORDER BY COALESCE(published_at, created_at) DESC, id DESC LIMIT ?""",
            (watch_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def add_price(self, watch_id: int, ts: str, price: float, volume: Optional[float] = None, source: str = "yahoo") -> None:
        self.conn.execute(
            """INSERT INTO watch_prices (watch_id, ts, price, volume, source)
               VALUES (?,?,?,?,?)
               ON CONFLICT(watch_id, ts) DO UPDATE SET
                 price=excluded.price, volume=excluded.volume, source=excluded.source""",
            (watch_id, ts, price, volume, source),
        )

    def list_prices(self, watch_id: int, limit: int = 120) -> List[dict]:
        rows = self.conn.execute(
            """SELECT * FROM watch_prices WHERE watch_id=?
               ORDER BY ts ASC""",
            (watch_id,),
        ).fetchall()
        data = [dict(r) for r in rows]
        if len(data) > limit:
            data = data[-limit:]
        return data

    def add_insight(self, watch_id: int, kind: str, content: str) -> dict:
        cur = self.conn.execute(
            "INSERT INTO watch_insights (watch_id, kind, content) VALUES (?,?,?)",
            (watch_id, kind, content),
        )
        row = self.conn.execute("SELECT * FROM watch_insights WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)

    def latest_insight(self, watch_id: int, kind: str) -> Optional[dict]:
        row = self.conn.execute(
            """SELECT * FROM watch_insights WHERE watch_id=? AND kind=?
               ORDER BY id DESC LIMIT 1""",
            (watch_id, kind),
        ).fetchone()
        return dict(row) if row else None

    def dashboard(self, watch_id: int) -> Optional[dict]:
        w = self.get(watch_id)
        if not w:
            return None
        prices = self.list_prices(watch_id)
        events = self.list_events(watch_id, limit=40)
        stats = {
            "events_count": len(events),
            "prices_count": len(prices),
            "last_price": prices[-1]["price"] if prices else None,
            "first_price": prices[0]["price"] if prices else None,
            "price_change_pct": None,
        }
        if prices and len(prices) >= 2 and prices[0]["price"]:
            stats["price_change_pct"] = round(
                (prices[-1]["price"] - prices[0]["price"]) / prices[0]["price"] * 100.0, 2
            )
        price_source = prices[-1].get("source") if prices else None
        market = None
        if w.get("ticker"):
            try:
                from bot.market_data import get_quote, is_crypto_symbol, normalize_symbol
                sym = normalize_symbol(w["ticker"])
                q = get_quote(sym)
                market = {
                    "symbol": sym,
                    "asset_class": "crypto" if is_crypto_symbol(sym) else "equity",
                    "quote": q,
                    "price_source": (q or {}).get("source") or price_source,
                    "latency": (q or {}).get("latency"),
                    "delay_note": (q or {}).get("delay_note"),
                }
                if q and q.get("price") is not None:
                    stats["last_price"] = q["price"]
                    stats["live_change_pct"] = q.get("change_pct_24h")
            except Exception:
                market = {"price_source": price_source}
        # event type breakdown
        by_type = {}
        for e in events:
            t = e.get("event_type") or "news"
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "watch": w,
            "stats": stats,
            "prices": prices,
            "events": events,
            "event_types": by_type,
            "insights": {
                "summary": self.latest_insight(watch_id, "summary"),
                "analysis": self.latest_insight(watch_id, "analysis"),
                "trading": self.latest_insight(watch_id, "trading"),
            },
            "market": market,
            "disclaimer": (
                "Données indicatives multi-providers (Yahoo ~15 min pour actions ; "
                "Binance near-realtime pour crypto ; Finnhub/Alpha Vantage si clé). "
                "Pas un flux pro tick-by-tick actions US. Pas un conseil financier."
            ),
        }

    def _watch_row(self, row) -> dict:
        d = dict(row)
        try:
            d["meta"] = json.loads(d.get("meta_json") or "{}")
        except Exception:
            d["meta"] = {}
        d.pop("meta_json", None)
        return d


_store: Optional[WatchStore] = None


def get_watch_store() -> WatchStore:
    global _store
    if _store is None:
        _store = WatchStore()
    return _store


# Tickers connus pour accélérer le suivi entreprises / crypto
KNOWN_TICKERS = {
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    "netflix": "NFLX",
    "intel": "INTC",
    "amd": "AMD",
    "samsung": "005930.KS",
    "total": "TTE",
    "totalenergies": "TTE",
    "lvmh": "MC.PA",
    "airbus": "AIR.PA",
    "spacex": None,  # privé
    "openai": None,
    "anthropic": None,
    "bitcoin": "BTCUSDT",
    "btc": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "eth": "ETHUSDT",
    "solana": "SOLUSDT",
    "bnb": "BNBUSDT",
}


def guess_kind_and_ticker(title: str, kind: Optional[str] = None, ticker: Optional[str] = None) -> tuple[str, Optional[str]]:
    low = title.lower()
    if ticker:
        t = ticker.upper().replace("-", "").replace("/", "")
        if t in ("BTC", "ETH", "SOL", "BNB"):
            t = t + "USDT"
        if t.endswith("USDT"):
            return kind or "crypto", t
        return kind or "company", t
    for name, tkr in KNOWN_TICKERS.items():
        if name in low:
            if tkr and str(tkr).endswith("USDT"):
                return "crypto", tkr
            return "company", tkr
    if kind:
        return kind, None
    if any(x in low for x in ["crypto", "bitcoin", "btc", "ethereum", "eth ", "solana"]):
        return "crypto", None
    if any(x in low for x in ["guerre", "conflit", "taiwan", "taïwan", "iran", "ukraine", "otan", "gaza", "sanctions"]):
        return "geopolitics", None
    return "custom", None
