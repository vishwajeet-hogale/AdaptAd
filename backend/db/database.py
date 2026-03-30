"""
SQLite database setup and helpers using aiosqlite.

Tables:
- decisions: Every NegotiationResult logged with timestamp.
- ab_sessions: A/B test sessions.
- ab_ratings: Per-participant ratings.
- evolution_runs: GA run metadata and results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

from ..config import config


_DB_PATH: Optional[str] = None


def get_db_path() -> str:
    return _DB_PATH or config.database.path


async def get_db():
    """FastAPI dependency that yields a database connection."""
    if not AIOSQLITE_AVAILABLE:
        raise RuntimeError("aiosqlite is not installed. Run: pip install aiosqlite")
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db(path: Optional[str] = None) -> None:
    """Create tables if they do not exist."""
    if not AIOSQLITE_AVAILABLE:
        print("Warning: aiosqlite not installed. Database functionality disabled.")
        return
    db_path = path or get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                ad_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                combined_score REAL,
                user_advocate_score REAL,
                advertiser_advocate_score REAL,
                reasoning TEXT,
                chromosome_genes TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ab_sessions (
                id TEXT PRIMARY KEY,
                user_name TEXT,
                user_age_group TEXT,
                user_country TEXT,
                user_interests TEXT,
                user_ad_tolerance REAL,
                user_id INTEGER,
                content_id INTEGER,
                content_title TEXT,
                content_genre TEXT,
                content_language TEXT,
                x_is_adaptad INTEGER DEFAULT 0,
                session_x TEXT,
                session_y TEXT,
                is_custom INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                completed INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ab_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                session_label TEXT NOT NULL,
                is_adaptad INTEGER,
                annoyance INTEGER,
                relevance INTEGER,
                willingness INTEGER,
                score INTEGER,
                notes TEXT,
                rated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS evolution_runs (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                status TEXT NOT NULL,
                current_generation INTEGER DEFAULT 0,
                max_generations INTEGER,
                best_fitness REAL,
                best_chromosome TEXT,
                history TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        await db.commit()

    # Run sync migration to add any missing columns to pre-existing tables.
    _migrate_ab_tables(db_path)


def _migrate_ab_tables(db_path: str) -> None:
    """Add any missing columns to ab_sessions / ab_ratings (safe on repeat runs)."""
    import sqlite3
    new_session_cols = [
        ("user_name",         "TEXT"),
        ("user_age_group",    "TEXT"),
        ("user_country",      "TEXT"),
        ("user_interests",    "TEXT"),
        ("user_ad_tolerance", "REAL"),
        ("content_title",     "TEXT"),
        ("content_genre",     "TEXT"),
        ("content_language",  "TEXT"),
        ("x_is_adaptad",      "INTEGER DEFAULT 0"),
        ("session_x",         "TEXT"),
        ("session_y",         "TEXT"),
        ("is_custom",         "INTEGER DEFAULT 0"),
    ]
    new_rating_cols = [
        ("is_adaptad", "INTEGER"),
        ("score",      "INTEGER"),
        ("notes",      "TEXT"),
    ]
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        for col, typ in new_session_cols:
            try:
                cur.execute(f"ALTER TABLE ab_sessions ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass  # column already exists
        for col, typ in new_rating_cols:
            try:
                cur.execute(f"ALTER TABLE ab_ratings ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass
        con.commit()
        con.close()
    except Exception as e:
        print(f"Warning: AB table migration failed: {e}")


# ---------------------------------------------------------------------------
# Synchronous helpers (used by sync FastAPI routes in routes_ab.py)
# ---------------------------------------------------------------------------

def save_ab_session_sync(session: dict) -> None:
    """Persist an AB session dict to SQLite synchronously."""
    import sqlite3
    db_path = get_db_path()
    try:
        con = sqlite3.connect(db_path)
        con.execute("""
            INSERT OR REPLACE INTO ab_sessions
            (id, user_name, user_age_group, user_country, user_interests,
             user_ad_tolerance, user_id, content_id, content_title,
             content_genre, content_language, x_is_adaptad,
             session_x, session_y, is_custom, created_at, completed)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            session["session_id"],
            session.get("user_name", ""),
            session.get("user_age_group", ""),
            session.get("user_country", ""),
            json.dumps(session.get("user_interests", [])),
            session.get("user_ad_tolerance"),
            session.get("user_id"),
            session.get("content_id"),
            session.get("content_title", ""),
            session.get("content_genre", ""),
            session.get("content_language", ""),
            1 if session.get("x_is_adaptad") else 0,
            json.dumps(session.get("session_x", [])),
            json.dumps(session.get("session_y", [])),
            1 if session.get("is_custom") else 0,
            session.get("created_at", datetime.utcnow().isoformat()),
            1 if session.get("completed") else 0,
        ))
        con.commit()
        con.close()
    except Exception as e:
        print(f"Warning: could not save AB session to database: {e}")


def save_ab_rating_sync(session_id: str, label: str, x_is_adaptad: bool,
                        annoyance: int, relevance: int, willingness: int,
                        notes: Optional[str] = None) -> None:
    """Persist an AB rating to SQLite synchronously."""
    import sqlite3
    db_path = get_db_path()
    is_adaptad = (label == "X" and x_is_adaptad) or (label == "Y" and not x_is_adaptad)
    score = willingness + relevance - annoyance
    try:
        con = sqlite3.connect(db_path)
        con.execute("""
            INSERT INTO ab_ratings
            (session_id, session_label, is_adaptad, annoyance, relevance,
             willingness, score, notes, rated_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            session_id, label, 1 if is_adaptad else 0,
            annoyance, relevance, willingness, score,
            notes, datetime.utcnow().isoformat(),
        ))
        # Mark session completed if both labels rated.
        con.execute("""
            UPDATE ab_sessions SET completed = 1 WHERE id = ?
            AND (SELECT COUNT(*) FROM ab_ratings WHERE session_id = ?) >= 2
        """, (session_id, session_id))
        con.commit()
        con.close()
    except Exception as e:
        print(f"Warning: could not save AB rating to database: {e}")


def get_ab_history_sync(limit: int = 100) -> list[dict]:
    """Return completed AB sessions with their ratings from SQLite."""
    import sqlite3
    db_path = get_db_path()
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        rows = cur.execute("""
            SELECT s.id, s.user_name, s.user_age_group, s.user_country,
                   s.user_interests, s.user_ad_tolerance,
                   s.content_title, s.content_genre, s.content_language,
                   s.x_is_adaptad, s.is_custom, s.created_at,
                   r_adapt.score  AS adaptad_score,
                   r_base.score   AS baseline_score,
                   r_adapt.annoyance  AS adaptad_annoyance,
                   r_adapt.relevance  AS adaptad_relevance,
                   r_adapt.willingness AS adaptad_willingness,
                   r_base.annoyance   AS baseline_annoyance,
                   r_base.relevance   AS baseline_relevance,
                   r_base.willingness AS baseline_willingness
            FROM ab_sessions s
            LEFT JOIN ab_ratings r_adapt ON r_adapt.session_id = s.id AND r_adapt.is_adaptad = 1
            LEFT JOIN ab_ratings r_base  ON r_base.session_id  = s.id AND r_base.is_adaptad  = 0
            WHERE s.completed = 1
            ORDER BY s.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        results = []
        for r in rows:
            adapt_score = r["adaptad_score"]
            base_score  = r["baseline_score"]
            if adapt_score is not None and base_score is not None:
                winner = "adaptad" if adapt_score > base_score else ("baseline" if base_score > adapt_score else "tie")
            else:
                winner = "unknown"
            results.append({
                "session_id":       r["id"],
                "user_name":        r["user_name"] or "Unknown",
                "user_age_group":   r["user_age_group"] or "",
                "user_country":     r["user_country"] or "",
                "user_interests":   json.loads(r["user_interests"] or "[]"),
                "user_ad_tolerance": r["user_ad_tolerance"],
                "content_title":    r["content_title"] or "",
                "content_genre":    r["content_genre"] or "",
                "content_language": r["content_language"] or "",
                "is_custom":        bool(r["is_custom"]),
                "created_at":       r["created_at"],
                "adaptad_score":    adapt_score,
                "baseline_score":   base_score,
                "adaptad_ratings":  {"annoyance": r["adaptad_annoyance"], "relevance": r["adaptad_relevance"], "willingness": r["adaptad_willingness"]},
                "baseline_ratings": {"annoyance": r["baseline_annoyance"], "relevance": r["baseline_relevance"], "willingness": r["baseline_willingness"]},
                "winner":           winner,
            })
        con.close()
        return results
    except Exception as e:
        print(f"Warning: could not load AB history from database: {e}")
        return []


async def log_decision(db, result, chromosome_genes: Optional[list] = None) -> int:
    """Insert a NegotiationResult into the decisions table."""
    try:
        cursor = await db.execute(
            """
            INSERT INTO decisions
            (session_id, user_id, ad_id, decision, combined_score,
             user_advocate_score, advertiser_advocate_score, reasoning,
             chromosome_genes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.session_id,
                result.user_id,
                result.ad_id,
                result.decision.value,
                result.combined_score,
                result.user_advocate.score,
                result.advertiser_advocate.score,
                result.reasoning,
                json.dumps(chromosome_genes) if chromosome_genes else None,
                result.timestamp.isoformat(),
            ),
        )
        await db.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Warning: could not log decision to database: {e}")
        return -1
