"""Paper trading éducatif (cash virtuel, pas d'ordres réels)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from bot.config import DATA_DIR
from bot.user_profile import get_profile_store

PAPER_DB = DATA_DIR / "paper_trading.db"
DEFAULT_CASH = 10_000.0


class PaperTradingStore:
    def __init__(self, path: Path = PAPER_DB):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS paper_accounts (
                id INTEGER PRIMARY KEY,
                cash REAL NOT NULL,
                unlocked_level TEXT DEFAULT 'beginner',
                trades_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'utc')),
                updated_at TEXT DEFAULT (datetime('now', 'utc'))
            );
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                qty REAL NOT NULL,
                avg_price REAL NOT NULL,
                updated_at TEXT DEFAULT (datetime('now', 'utc'))
            );
            CREATE TABLE IF NOT EXISTS paper_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                qty REAL NOT NULL,
                limit_price REAL,
                status TEXT NOT NULL,
                fill_price REAL,
                created_at TEXT DEFAULT (datetime('now', 'utc'))
            );
            CREATE TABLE IF NOT EXISTS paper_fills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty REAL NOT NULL,
                price REAL NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'utc'))
            );
            CREATE TABLE IF NOT EXISTS paper_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'utc'))
            );
            CREATE TABLE IF NOT EXISTS paper_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_slug TEXT NOT NULL,
                question TEXT NOT NULL,
                outcome TEXT NOT NULL,
                shares REAL NOT NULL,
                buy_price REAL NOT NULL,
                amount_invested REAL NOT NULL,
                potential_payout REAL NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT (datetime('now', 'utc'))
            );
            """
        )
        if not self.conn.execute("SELECT id FROM paper_accounts WHERE id=1").fetchone():
            level = get_profile_store().get().get("trading_level") or "beginner"
            self.conn.execute(
                "INSERT INTO paper_accounts (id, cash, unlocked_level) VALUES (1, ?, ?)",
                (DEFAULT_CASH, level),
            )

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def account(self) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM paper_accounts WHERE id=1").fetchone()
        return dict(row)

    def positions(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM paper_positions ORDER BY symbol").fetchall()]

    def orders(self, limit: int = 30) -> List[Dict[str, Any]]:
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM paper_orders ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        ]

    def fills(self, limit: int = 30) -> List[Dict[str, Any]]:
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM paper_fills ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        ]

    def journal(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM paper_journal ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        ]

    def add_journal(self, note: str) -> dict:
        cur = self.conn.execute("INSERT INTO paper_journal (note) VALUES (?)", (note,))
        return {"id": cur.lastrowid, "note": note}

    def set_level(self, level: str) -> dict:
        if level not in ("beginner", "intermediate", "pro"):
            level = "beginner"
        self.conn.execute(
            "UPDATE paper_accounts SET unlocked_level=?, updated_at=datetime('now','utc') WHERE id=1",
            (level,),
        )
        return self.account()

    def reset(self) -> dict:
        self.conn.execute("DELETE FROM paper_positions")
        self.conn.execute("DELETE FROM paper_orders")
        self.conn.execute("DELETE FROM paper_fills")
        level = get_profile_store().get().get("trading_level") or "beginner"
        self.conn.execute(
            "UPDATE paper_accounts SET cash=?, unlocked_level=?, trades_count=0, updated_at=datetime('now','utc') WHERE id=1",
            (DEFAULT_CASH, level),
        )
        return self.portfolio()

    def _last_price(self, symbol: str) -> Optional[float]:
        symbol = (symbol or "").upper().strip()
        try:
            from bot.market_data import get_quote
            q = get_quote(symbol, force=True)
            if q and q.get("price"):
                return float(q["price"])
        except Exception:
            pass
        return None

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "market",
        limit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        symbol = symbol.upper().strip()
        side = side.lower().strip()
        order_type = (order_type or "market").lower()
        if side not in ("buy", "sell"):
            raise ValueError("side must be buy|sell")
        if qty <= 0:
            raise ValueError("qty must be > 0")
        acc = self.account()
        level = acc.get("unlocked_level") or "beginner"
        if order_type == "limit" and level == "beginner":
            raise ValueError("Les ordres limites sont débloqués au niveau intermediate")
        price = self._last_price(symbol)
        if price is None:
            raise ValueError(f"Prix indisponible pour {symbol} (source Yahoo)")
        status = "filled"
        fill_price = price
        if order_type == "limit":
            if limit_price is None:
                raise ValueError("limit_price requis")
            # fill if market favorable
            if side == "buy" and price > float(limit_price):
                status = "open"
                fill_price = None
            elif side == "sell" and price < float(limit_price):
                status = "open"
                fill_price = None
            else:
                fill_price = float(limit_price)

        cur = self.conn.execute(
            """INSERT INTO paper_orders (symbol, side, order_type, qty, limit_price, status, fill_price)
               VALUES (?,?,?,?,?,?,?)""",
            (symbol, side, order_type, qty, limit_price, status, fill_price),
        )
        order_id = cur.lastrowid
        if status != "filled":
            return {"order_id": order_id, "status": status, "message": "Ordre limite en attente"}

        # Gardes-fous pré-fill (cohérents avec le sweep)
        cash = float(acc["cash"])
        if side == "buy":
            if fill_price * qty > cash:
                self.conn.execute("UPDATE paper_orders SET status='rejected' WHERE id=?", (order_id,))
                raise ValueError("Cash insuffisant")
        else:
            pos = self.conn.execute("SELECT * FROM paper_positions WHERE symbol=?", (symbol,)).fetchone()
            if not pos or float(pos["qty"]) < qty:
                self.conn.execute("UPDATE paper_orders SET status='rejected' WHERE id=?", (order_id,))
                raise ValueError("Position insuffisante")

        self._apply_fill(order_id, symbol, side, qty, fill_price, level)
        return {"order_id": order_id, "status": "filled", "fill_price": fill_price, "portfolio": self.portfolio()}

    def _apply_fill(
        self, order_id: int, symbol: str, side: str, qty: float, fill_price: float, level: str = "beginner"
    ) -> None:
        """Applique le remplissage d'un ordre : maj cash, position, fills, progression.

        Pré-conditions (à vérifier par l'appelant) : cash suffisant pour un buy,
        position suffisante pour un sell.
        """
        acc = self.account()
        cash = float(acc["cash"])
        pos = self.conn.execute("SELECT * FROM paper_positions WHERE symbol=?", (symbol,)).fetchone()
        if side == "buy":
            cost = fill_price * qty
            cash -= cost
            if pos:
                new_qty = float(pos["qty"]) + qty
                avg = (float(pos["avg_price"]) * float(pos["qty"]) + cost) / new_qty
                self.conn.execute(
                    "UPDATE paper_positions SET qty=?, avg_price=?, updated_at=datetime('now','utc') WHERE symbol=?",
                    (new_qty, avg, symbol),
                )
            else:
                self.conn.execute(
                    "INSERT INTO paper_positions (symbol, qty, avg_price) VALUES (?,?,?)",
                    (symbol, qty, fill_price),
                )
        else:
            proceeds = fill_price * qty
            cash += proceeds
            new_qty = float(pos["qty"]) - qty
            if new_qty <= 1e-9:
                self.conn.execute("DELETE FROM paper_positions WHERE symbol=?", (symbol,))
            else:
                self.conn.execute(
                    "UPDATE paper_positions SET qty=?, updated_at=datetime('now','utc') WHERE symbol=?",
                    (new_qty, symbol),
                )

        self.conn.execute(
            "UPDATE paper_accounts SET cash=?, trades_count=trades_count+1, updated_at=datetime('now','utc') WHERE id=1",
            (cash,),
        )
        self.conn.execute(
            "UPDATE paper_orders SET status='filled', fill_price=? WHERE id=?",
            (fill_price, order_id),
        )
        self.conn.execute(
            "INSERT INTO paper_fills (order_id, symbol, side, qty, price) VALUES (?,?,?,?,?)",
            (order_id, symbol, side, qty, fill_price),
        )
        # unlock progression
        trades = int(self.account()["trades_count"])
        if trades >= 5 and level == "beginner":
            self.set_level("intermediate")
        elif trades >= 15 and level == "intermediate":
            self.set_level("pro")

    def sweep_open_orders(self) -> dict:
        """Réévalue les ordres limites en attente (status='open') contre le prix
        courant (Yahoo) et remplit ceux dont la condition est devenue favorable.

        Appelée automatiquement au calcul du portefeuille (mark-to-market) et
        exposée via POST /api/learn/sweep pour un déclenchement manuel.
        """
        rows = self.conn.execute(
            "SELECT id, symbol, side, qty, limit_price FROM paper_orders WHERE status='open'"
        ).fetchall()
        filled = []
        for row in rows:
            oid = row["id"]
            symbol = row["symbol"]
            side = row["side"]
            qty = float(row["qty"])
            limit_price = float(row["limit_price"])
            price = self._last_price(symbol)
            if price is None:
                continue
            # Condition de fill cohérente avec place_order
            if side == "buy" and price <= limit_price:
                fill_price = limit_price
            elif side == "sell" and price >= limit_price:
                fill_price = limit_price
            else:
                continue
            # Vérifier cash (buy) ou position (sell) ; sinon laisse en attente
            acc = self.account()
            level = acc.get("unlocked_level") or "beginner"
            if side == "buy":
                if fill_price * qty > float(acc["cash"]):
                    continue
            else:
                pos = self.conn.execute(
                    "SELECT qty FROM paper_positions WHERE symbol=?", (symbol,)
                ).fetchone()
                if not pos or float(pos["qty"]) < qty:
                    continue
            self._apply_fill(oid, symbol, side, qty, fill_price, level)
            filled.append(
                {"order_id": oid, "symbol": symbol, "side": side, "qty": qty, "fill_price": fill_price}
            )
        return {"swept": len(filled), "filled": filled}

    def buy_prediction(self, market_slug: str, question: str, outcome: str, price: float, amount: float) -> dict:
        acc = self.account()
        cash = float(acc["cash"])
        if amount <= 0:
            return {"error": "Montant invalide"}
        if amount > cash:
            return {"error": f"Fonds virtuels insuffisants (disponible : {cash:.2f} $)"}
        
        p = max(0.01, min(float(price or 0.5), 0.99))
        shares = round(amount / p, 2)
        payout = round(shares * 1.0, 2)
        
        new_cash = cash - amount
        self.conn.execute("UPDATE paper_accounts SET cash=? WHERE id=1", (new_cash,))
        cur = self.conn.execute(
            """INSERT INTO paper_predictions 
               (market_slug, question, outcome, shares, buy_price, amount_invested, potential_payout, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'open')""",
            (market_slug, question, outcome.upper(), shares, p, amount, payout)
        )
        self.add_journal(f"Prédiction achetée : {amount:.2f} $ sur '{outcome}' @ {p:.2f} ({question[:50]}...)")
        return {
            "status": "success",
            "prediction_id": cur.lastrowid,
            "outcome": outcome.upper(),
            "shares": shares,
            "buy_price": p,
            "amount_invested": amount,
            "potential_payout": payout,
            "remaining_cash": new_cash,
        }

    def list_predictions(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM paper_predictions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]

    def portfolio(self) -> Dict[str, Any]:
        try:
            self.sweep_open_orders()
        except Exception:
            pass
        acc = self.account()
        positions = []
        equity = float(acc["cash"])
        for p in self.positions():
            last = self._last_price(p["symbol"]) or float(p["avg_price"])
            mkt = last * float(p["qty"])
            pnl = (last - float(p["avg_price"])) * float(p["qty"])
            equity += mkt
            positions.append({
                **p,
                "last_price": last,
                "market_value": round(mkt, 2),
                "pnl": round(pnl, 2),
            })
        
        preds = self.list_predictions(20)
        for pred in preds:
            equity += float(pred.get("amount_invested") or 0)

        return {
            "account": acc,
            "cash": round(float(acc["cash"]), 2),
            "equity": round(equity, 2),
            "positions": positions,
            "predictions": preds,
            "orders": self.orders(15),
            "fills": self.fills(15),
            "journal": self.journal(10),
            "disclaimer": "Simulation éducative uniquement — pas un conseil financier, pas d'argent réel.",
        }


_paper: Optional[PaperTradingStore] = None


def get_paper_store() -> PaperTradingStore:
    global _paper
    if _paper is None:
        _paper = PaperTradingStore()
    return _paper


def explain_term(question: str) -> dict:
    from bot.ai import call_llm
    portfolio = get_paper_store().portfolio()
    prompt = f"""
Tu es un assistant pédagogique de trading papier (simulation).
Réponds en français, termes simples, 5–10 phrases max.
Question: {question}
État portefeuille démo (JSON): {json.dumps({k: portfolio[k] for k in ('cash','equity','positions','account')}, ensure_ascii=False)}
Règles: pas de conseil d'investissement réel; rappelle que c'est une démo éducative.
"""
    text = call_llm(prompt) or (
        "En simulation, un ordre market s'exécute au dernier prix scrapé (Yahoo). "
        "Ce n'est pas un conseil financier."
    )
    return {"answer": text, "disclaimer": portfolio["disclaimer"]}
