"""Gestion de la base de données SQLite/PostgreSQL pour la partie médicale.

Gère les essais cliniques, les articles PubMed et la pharmacopée traditionnelle.
Prend en charge SQLite (par défaut) et PostgreSQL (avec PostGIS + pgvector) de manière transparente.
"""
from __future__ import annotations

import sqlite3
import json
import logging
import math
import os
import struct
from pathlib import Path
from typing import List, Optional, Dict

from bot.config import DATA_DIR
from bot.ai import get_embedding

log = logging.getLogger(__name__)
MED_DB_PATH = DATA_DIR / "medical.db"


def pack_embedding(vec: Optional[List[float]]) -> Optional[bytes]:
    """Sérialise un vecteur float en blob binaire compact (float32 little-endian)."""
    if not vec:
        return None
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack_embedding(blob: Optional[bytes]) -> Optional[List[float]]:
    """Désérialise un blob en liste de floats."""
    if not blob:
        return None
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def cosine_distance(a: List[float], b: List[float]) -> float:
    """Distance cosinus (0 = identique, 2 = opposé) entre deux vecteurs."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - dot / (na * nb)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover
    psycopg2 = None  # type: ignore

# --- Schéma SQLite ---
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS medical_records (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL, -- 'clinicaltrials' ou 'pubmed'
    nct_id TEXT,
    url TEXT,
    summary TEXT,
    eligibility_criteria TEXT,
    phase TEXT,
    status TEXT,
    conditions TEXT,
    sponsor TEXT,
    location_name TEXT,
    city TEXT,
    country TEXT,
    latitude REAL,
    longitude REAL,
    embedding BLOB, -- vecteur float32 (768 dims) pour recherche sémantique
    ai_cheat_sheet TEXT,
    created_at TEXT DEFAULT (datetime('now', 'utc'))
);

CREATE TABLE IF NOT EXISTS traditional_plants (
    name TEXT PRIMARY KEY,
    scientific_name TEXT,
    indications TEXT,
    active_compounds TEXT,
    references_json TEXT, -- Liste de liens vers PubMed
    created_at TEXT DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_med_source ON medical_records(source);
CREATE INDEX IF NOT EXISTS idx_med_nct ON medical_records(nct_id);
"""

# --- Schéma PostgreSQL ---
POSTGRES_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS medical_records (
    id VARCHAR(100) PRIMARY KEY,
    title TEXT NOT NULL,
    source VARCHAR(50) NOT NULL,
    nct_id VARCHAR(50),
    url TEXT,
    summary TEXT,
    eligibility_criteria TEXT,
    phase VARCHAR(50),
    status VARCHAR(50),
    conditions TEXT,
    sponsor TEXT,
    location_name TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom geography(Point, 4326),
    embedding vector(768),
    ai_cheat_sheet TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS traditional_plants (
    name VARCHAR(200) PRIMARY KEY,
    scientific_name VARCHAR(200),
    indications TEXT,
    active_compounds TEXT,
    references_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pg_med_source ON medical_records(source);
CREATE INDEX IF NOT EXISTS idx_pg_med_nct ON medical_records(nct_id);
CREATE INDEX IF NOT EXISTS idx_pg_med_geom ON medical_records USING gist(geom);
"""


class MedicalStore:
    def __init__(self, path=MED_DB_PATH):
        self.db_url = os.getenv("DATABASE_URL")
        self.use_pg = False
        self.conn = None

        if self.db_url:
            try:
                if psycopg2 is None:
                    raise ImportError("psycopg2 non installé")
                self.conn = psycopg2.connect(self.db_url)
                self.conn.autocommit = True

                with self.conn.cursor() as cur:
                    cur.execute(POSTGRES_SCHEMA)
                    cur.execute(
                        """CREATE TABLE IF NOT EXISTS ingestion_runs (
                            id SERIAL PRIMARY KEY,
                            payload JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )"""
                    )

                self.use_pg = True
                log.info("[medical] Connecté avec succès à PostgreSQL (PostGIS + pgvector)")
            except Exception as e:
                log.warning("[medical] Échec connexion PostgreSQL (%s). Repli sur SQLite.", e)
                self.conn = None

        if not self.use_pg:
            # Repli sur SQLite
            self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.executescript(SQLITE_SCHEMA)
            # Migration : ajouter la colonne embedding aux bases créées avant
            try:
                self.conn.execute("ALTER TABLE medical_records ADD COLUMN embedding BLOB")
            except sqlite3.OperationalError:
                pass  # colonne déjà présente
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS ingestion_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'utc'))
                )"""
            )
            self.conn.commit()

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def upsert_record(self, record: dict) -> None:
        """Insère ou met à jour une étude ou publication."""
        # Générer l'embedding s'il n'existe pas encore (quelle que soit la base)
        embedding = None
        text_to_embed = f"{record.get('title', '')} {record.get('summary', '')}"
        if text_to_embed.strip():
            embedding = get_embedding(text_to_embed)

        if self.use_pg:
            lat = record.get("latitude")
            lon = record.get("longitude")
            geom_expr = None
            if lat is not None and lon is not None:
                geom_expr = f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography"
            
            # Utilisation de psycopg2
            with self.conn.cursor() as cur:
                cur.execute(
                    f"""INSERT INTO medical_records (
                        id, title, source, nct_id, url, summary, eligibility_criteria,
                        phase, status, conditions, sponsor, location_name, city, country,
                        latitude, longitude, geom, embedding, ai_cheat_sheet
                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                         {geom_expr if geom_expr else 'NULL'}, %s, %s)
                       ON CONFLICT(id) DO UPDATE SET
                         title=EXCLUDED.title,
                         summary=EXCLUDED.summary,
                         eligibility_criteria=EXCLUDED.eligibility_criteria,
                         status=EXCLUDED.status,
                         latitude=EXCLUDED.latitude,
                         longitude=EXCLUDED.longitude,
                         geom={geom_expr if geom_expr else 'NULL'},
                         embedding=COALESCE(EXCLUDED.embedding, medical_records.embedding),
                         ai_cheat_sheet=COALESCE(EXCLUDED.ai_cheat_sheet, medical_records.ai_cheat_sheet)""",
                    (
                        record.get("id"),
                        record.get("title"),
                        record.get("source"),
                        record.get("nct_id"),
                        record.get("url"),
                        record.get("summary"),
                        record.get("eligibility_criteria"),
                        record.get("phase"),
                        record.get("status"),
                        record.get("conditions"),
                        record.get("sponsor"),
                        record.get("location_name"),
                        record.get("city"),
                        record.get("country"),
                        lat,
                        lon,
                        embedding,
                        record.get("ai_cheat_sheet"),
                    ),
                )
        else:
            # SQLite
            self.conn.execute(
                """INSERT INTO medical_records (
                    id, title, source, nct_id, url, summary, eligibility_criteria,
                    phase, status, conditions, sponsor, location_name, city, country,
                    latitude, longitude, embedding, ai_cheat_sheet
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     title=excluded.title,
                     summary=excluded.summary,
                     eligibility_criteria=excluded.eligibility_criteria,
                     status=excluded.status,
                     latitude=excluded.latitude,
                     longitude=excluded.longitude,
                      embedding=coalesce(excluded.embedding, medical_records.embedding),
                     ai_cheat_sheet=coalesce(excluded.ai_cheat_sheet, ai_cheat_sheet)""",
                (
                    record.get("id"),
                    record.get("title"),
                    record.get("source"),
                    record.get("nct_id"),
                    record.get("url"),
                    record.get("summary"),
                    record.get("eligibility_criteria"),
                    record.get("phase"),
                    record.get("status"),
                    record.get("conditions"),
                    record.get("sponsor"),
                    record.get("location_name"),
                    record.get("city"),
                    record.get("country"),
                    record.get("latitude"),
                    record.get("longitude"),
                    pack_embedding(embedding),
                    record.get("ai_cheat_sheet"),
                ),
            )

    def get_record(self, record_id: str) -> Optional[dict]:
        """Récupère une étude ou publication par son identifiant unique."""
        if self.use_pg:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM medical_records WHERE id = %s", (record_id,))
                row = cur.fetchone()
                return self._serialize_record(dict(row)) if row else None
        else:
            row = self.conn.execute("SELECT * FROM medical_records WHERE id=?", (record_id,)).fetchone()
            return dict(row) if row else None

    def _serialize_record(self, row: dict) -> dict:
        """Nettoie les types non JSON-serializables (vector, geometry)."""
        out = {}
        for k, v in row.items():
            if k in ("embedding", "geom"):
                continue
            if hasattr(v, "isoformat"):
                out[k] = v.isoformat()
            else:
                out[k] = v
        return out

    def get_records(
        self,
        search: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        country: Optional[str] = None,
        semantic: bool = True,
    ) -> List[dict]:
        """Récupère les études avec recherche textuelle ou sémantique pgvector."""
        if self.use_pg:
            embedding = None
            if search and semantic:
                embedding = get_embedding(search)

            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if embedding:
                    q = """SELECT *, (embedding <=> %s::vector) AS semantic_distance
                           FROM medical_records WHERE embedding IS NOT NULL"""
                    args: list = [embedding]
                    if source:
                        q += " AND source = %s"
                        args.append(source)
                    if phase:
                        q += " AND phase ILIKE %s"
                        args.append(f"%{phase}%")
                    if status:
                        q += " AND status ILIKE %s"
                        args.append(f"%{status}%")
                    if country:
                        q += " AND country ILIKE %s"
                        args.append(f"%{country}%")
                    q += " ORDER BY semantic_distance ASC LIMIT %s"
                    args.append(limit)
                    cur.execute(q, args)
                else:
                    q = "SELECT * FROM medical_records WHERE 1=1"
                    args = []
                    if source:
                        q += " AND source = %s"
                        args.append(source)
                    if search:
                        q += " AND (title ILIKE %s OR summary ILIKE %s OR conditions ILIKE %s)"
                        term = f"%{search}%"
                        args += [term, term, term]
                    if phase:
                        q += " AND phase ILIKE %s"
                        args.append(f"%{phase}%")
                    if status:
                        q += " AND status ILIKE %s"
                        args.append(f"%{status}%")
                    if country:
                        q += " AND country ILIKE %s"
                        args.append(f"%{country}%")
                    q += " ORDER BY created_at DESC LIMIT %s"
                    args.append(limit)
                    cur.execute(q, args)
                return [self._serialize_record(dict(r)) for r in cur.fetchall()]
        else:
            # SQLite — recherche sémantique (cosinus Python) si embeddings disponibles
            q_emb = get_embedding(search) if (search and semantic) else None
            if q_emb:
                q = "SELECT * FROM medical_records WHERE embedding IS NOT NULL"
                args = []
                if source:
                    q += " AND source=?"
                    args.append(source)
                if phase:
                    q += " AND phase LIKE ?"
                    args.append(f"%{phase}%")
                if status:
                    q += " AND status LIKE ?"
                    args.append(f"%{status}%")
                if country:
                    q += " AND country LIKE ?"
                    args.append(f"%{country}%")
                q += " LIMIT 5000"  # garde-fou mémoire (largement au-delà du volume actuel)
                rows = self.conn.execute(q, args).fetchall()
                scored = []
                for row in rows:
                    r = dict(row)
                    emb = unpack_embedding(r.pop("embedding", None))
                    if emb is None:
                        continue
                    r["semantic_distance"] = round(cosine_distance(q_emb, emb), 6)
                    scored.append(r)
                scored.sort(key=lambda x: x["semantic_distance"])
                return scored[:limit]
            # SQLite — repli recherche textuelle
            q = "SELECT * FROM medical_records WHERE 1=1"
            args = []
            if source:
                q += " AND source=?"
                args.append(source)
            if search:
                q += " AND (title LIKE ? OR summary LIKE ? OR conditions LIKE ? OR location_name LIKE ?)"
                term = f"%{search}%"
                args += [term] * 4
            if phase:
                q += " AND phase LIKE ?"
                args.append(f"%{phase}%")
            if status:
                q += " AND status LIKE ?"
                args.append(f"%{status}%")
            if country:
                q += " AND country LIKE ?"
                args.append(f"%{country}%")
            q += " ORDER BY created_at DESC LIMIT ?"
            args.append(limit)
            out = []
            for row in self.conn.execute(q, args):
                r = dict(row)
                r.pop("embedding", None)  # ne pas renvoyer le blob binaire aux appelants
                out.append(r)
            return out

    def get_nearby_studies(self, lat: float, lon: float, max_km: float = 1000.0) -> List[dict]:
        """Trouve les études à proximité (PostGIS ou Haversine SQLite)."""
        if self.use_pg:
            # PostGIS : ST_DWithin et ST_Distance en mètres
            max_meters = max_km * 1000.0
            q = """SELECT *, 
                          ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000.0 AS distance_km
                   FROM medical_records 
                   WHERE geom IS NOT NULL 
                     AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
                   ORDER BY distance_km ASC"""
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(q, (lon, lat, lon, lat, max_meters))
                out = []
                for r in cur.fetchall():
                    d = self._serialize_record(dict(r))
                    if "distance_km" in r:
                        d["distance_km"] = round(float(r["distance_km"]), 1)
                    out.append(d)
                return out
        else:
            # SQLite
            rows = self.conn.execute("SELECT * FROM medical_records WHERE latitude IS NOT NULL AND longitude IS NOT NULL").fetchall()
            nearby = []
            for r in rows:
                d = haversine_distance(lat, lon, r["latitude"], r["longitude"])
                if d <= max_km:
                    d_dict = dict(r)
                    d_dict.pop("embedding", None)  # ne pas renvoyer le blob binaire
                    d_dict["distance_km"] = round(d, 1)
                    nearby.append(d_dict)
            return sorted(nearby, key=lambda x: x["distance_km"])

    def update_cheat_sheet(self, record_id: str, cheat_sheet: str) -> None:
        if self.use_pg:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE medical_records SET ai_cheat_sheet=%s WHERE id=%s",
                    (cheat_sheet, record_id),
                )
        else:
            self.conn.execute(
                "UPDATE medical_records SET ai_cheat_sheet=? WHERE id=?",
                (cheat_sheet, record_id),
            )

    def update_embedding(self, record_id: str, embedding: List[float]) -> None:
        """Stocke le vecteur d'un dossier (blob SQLite / type vector Postgres)."""
        if self.use_pg:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE medical_records SET embedding=%s::vector WHERE id=%s",
                    (embedding, record_id),
                )
        else:
            self.conn.execute(
                "UPDATE medical_records SET embedding=? WHERE id=?",
                (pack_embedding(embedding), record_id),
            )

    def get_records_missing_embedding(self, limit: int = 100) -> List[dict]:
        """Dossiers sans vecteur (pour le backfill d'embeddings)."""
        if self.use_pg:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT id, title, summary FROM medical_records
                       WHERE embedding IS NULL
                       ORDER BY created_at DESC LIMIT %s""",
                    (limit,),
                )
                return [dict(r) for r in cur.fetchall()]
        rows = self.conn.execute(
            """SELECT id, title, summary FROM medical_records
               WHERE embedding IS NULL
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


    def get_records_missing_cheat_sheet(self, limit: int = 100) -> List[dict]:
        if self.use_pg:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM medical_records
                       WHERE (ai_cheat_sheet IS NULL OR ai_cheat_sheet='')
                       ORDER BY created_at DESC LIMIT %s""",
                    (limit,),
                )
                return [self._serialize_record(dict(r)) for r in cur.fetchall()]
        rows = self.conn.execute(
            """SELECT * FROM medical_records
               WHERE ai_cheat_sheet IS NULL OR ai_cheat_sheet=''
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        if self.use_pg:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) AS c FROM medical_records")
                total = cur.fetchone()["c"]
                cur.execute("SELECT source, COUNT(*) AS c FROM medical_records GROUP BY source")
                by_source = {r["source"]: r["c"] for r in cur.fetchall()}
                cur.execute(
                    "SELECT COUNT(*) AS c FROM medical_records WHERE ai_cheat_sheet IS NOT NULL AND ai_cheat_sheet<>''"
                )
                with_sheet = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) AS c FROM medical_records WHERE embedding IS NOT NULL")
                with_emb = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) AS c FROM traditional_plants")
                plants = cur.fetchone()["c"]
        else:
            total = self.conn.execute("SELECT COUNT(*) FROM medical_records").fetchone()[0]
            by_source = {
                r[0]: r[1]
                for r in self.conn.execute(
                    "SELECT source, COUNT(*) FROM medical_records GROUP BY source"
                ).fetchall()
            }
            with_sheet = self.conn.execute(
                "SELECT COUNT(*) FROM medical_records WHERE ai_cheat_sheet IS NOT NULL AND ai_cheat_sheet<>''"
            ).fetchone()[0]
            with_emb = self.conn.execute(
                "SELECT COUNT(*) FROM medical_records WHERE embedding IS NOT NULL"
            ).fetchone()[0]
            plants = self.conn.execute("SELECT COUNT(*) FROM traditional_plants").fetchone()[0]
        return {
            "backend": "postgres" if self.use_pg else "sqlite",
            "total_records": total,
            "by_source": by_source,
            "with_cheat_sheet": with_sheet,
            "with_embedding": with_emb,
            "plants": plants,
        }

    def record_ingestion_run(self, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False)
        if self.use_pg:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO ingestion_runs (payload) VALUES (%s::jsonb)", (raw,))
        else:
            self.conn.execute("INSERT INTO ingestion_runs (payload) VALUES (?)", (raw,))

    def find_related_for_plant(self, plant: dict, limit: int = 10) -> List[dict]:
        """Reverse-pharmacology : croise indications / composés avec medical_records."""
        tokens = []
        for field in ("indications", "active_compounds", "scientific_name", "name"):
            val = plant.get(field) or ""
            for part in val.replace(",", " ").replace("(", " ").replace(")", " ").split():
                t = part.strip().lower()
                if len(t) >= 4 and t not in tokens:
                    tokens.append(t)
        if not tokens:
            return []
        # Recherche sur les 3 tokens les plus discriminants
        query = " OR ".join(tokens[:5])
        return self.get_records(search=query, limit=limit, semantic=True)

    def upsert_plant(self, plant: dict) -> None:
        if self.use_pg:
            with self.conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO traditional_plants (name, scientific_name, indications, active_compounds, references_json)
                       VALUES (%s,%s,%s,%s,%s)
                       ON CONFLICT(name) DO UPDATE SET
                         scientific_name=EXCLUDED.scientific_name,
                         indications=EXCLUDED.indications,
                         active_compounds=EXCLUDED.active_compounds,
                         references_json=EXCLUDED.references_json""",
                    (
                        plant.get("name"),
                        plant.get("scientific_name"),
                        plant.get("indications"),
                        plant.get("active_compounds"),
                        json.dumps(plant.get("references", [])),
                    ),
                )
        else:
            self.conn.execute(
                """INSERT INTO traditional_plants (name, scientific_name, indications, active_compounds, references_json)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(name) DO UPDATE SET
                     scientific_name=excluded.scientific_name,
                     indications=excluded.indications,
                     active_compounds=excluded.active_compounds,
                     references_json=excluded.references_json""",
                (
                    plant.get("name"),
                    plant.get("scientific_name"),
                    plant.get("indications"),
                    plant.get("active_compounds"),
                    json.dumps(plant.get("references", [])),
                ),
            )

    def get_plants(self, search: Optional[str] = None) -> List[dict]:
        if self.use_pg:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                q = "SELECT * FROM traditional_plants"
                args = []
                if search:
                    q += " WHERE name ILIKE %s OR scientific_name ILIKE %s OR indications ILIKE %s"
                    term = f"%{search}%"
                    args += [term, term, term]
                cur.execute(q, args)
                rows = cur.fetchall()
                out = []
                for r in rows:
                    d = dict(r)
                    d["references"] = json.loads(d["references_json"] or "[]")
                    out.append(d)
                return out
        else:
            q = "SELECT * FROM traditional_plants"
            args = []
            if search:
                q += " WHERE name LIKE ? OR scientific_name LIKE ? OR indications LIKE ?"
                term = f"%{search}%"
                args += [term] * 3
            rows = self.conn.execute(q, args).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["references"] = json.loads(d["references_json"] or "[]")
                out.append(d)
            return out


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c
