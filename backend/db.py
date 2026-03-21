"""
PostgreSQL connection pool — thin asyncpg wrapper.

Usage:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT ...")

The pool is initialised once at app startup via `init_pool()` and
closed at shutdown via `close_pool()`. All operations degrade
gracefully when DATABASE_URL is not set (returns None pool).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_pool = None          # asyncpg.Pool singleton
_db_available = None  # bool cache — avoids repeated connection attempts


async def init_pool() -> bool:
    """Create the asyncpg connection pool. Returns True on success."""
    global _pool, _db_available
    url = os.getenv("DATABASE_URL", "")
    if not url:
        logger.warning("DATABASE_URL not set — learning loop will be disabled")
        _db_available = False
        return False
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(
            url,
            min_size=2,
            max_size=10,
            command_timeout=30,
            statement_cache_size=0,   # required for PgBouncer compatibility
        )
        # Verify connection
        async with _pool.acquire() as conn:
            await conn.execute("SELECT 1")
        logger.info("PostgreSQL pool ready (min=2 max=10)")
        _db_available = True
        return True
    except Exception as exc:
        logger.error("PostgreSQL connection failed: %s — learning loop disabled", exc)
        _db_available = False
        return False


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
    logger.info("PostgreSQL pool closed")


def get_pool():
    """Return pool or None if DB is unavailable."""
    return _pool if _db_available else None


def is_available() -> bool:
    return bool(_db_available and _pool)


async def run_migrations() -> None:
    """Apply all SQL migrations from the migrations/ directory."""
    if not is_available():
        return
    import os, pathlib
    migrations_dir = pathlib.Path(__file__).parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))
    async with _pool.acquire() as conn:
        # Track applied migrations
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        applied = {r["filename"] for r in await conn.fetch("SELECT filename FROM _migrations")}
        for sql_file in sql_files:
            if sql_file.name in applied:
                continue
            logger.info("Applying migration: %s", sql_file.name)
            sql = sql_file.read_text()
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO _migrations(filename) VALUES($1)", sql_file.name
            )
            logger.info("Migration applied: %s", sql_file.name)
