# db/connection.py — Async PostgreSQL connection pool using asyncpg

import os
import logging
import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("call-intelligence")

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    """Initialize the asyncpg connection pool. Call once at server startup."""
    global _pool
    if _pool is not None:
        return _pool

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Expected format: postgresql://user:password@host:port/dbname"
        )

    _pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        command_timeout=10,
        timeout=5.0,
    )
    logger.info("✅ PostgreSQL connection pool initialized")
    return _pool


def get_pool() -> asyncpg.Pool:
    """Get the current connection pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def close_pool():
    """Close the connection pool. Call at server shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("🛑 PostgreSQL connection pool closed")
