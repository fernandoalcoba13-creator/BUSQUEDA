import json
import time
import aiosqlite

DB_PATH = "cache.db"
CACHE_TTL_SECONDS = 60 * 60 * 6


async def init_cache() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS search_cache (
                cache_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        await db.commit()


async def get_cache(cache_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT payload, created_at FROM search_cache WHERE cache_key = ?",
            (cache_key,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            payload, created_at = row
            if int(time.time()) - created_at > CACHE_TTL_SECONDS:
                return None
            return json.loads(payload)


async def set_cache(cache_key: str, payload: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "REPLACE INTO search_cache (cache_key, payload, created_at) VALUES (?, ?, ?)",
            (cache_key, json.dumps(payload), int(time.time())),
        )
        await db.commit()
