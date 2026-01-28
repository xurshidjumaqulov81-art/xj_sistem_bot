import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")
pool: asyncpg.Pool | None = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    await pool.execute("""
    CREATE TABLE IF NOT EXISTS users (
        tg_id BIGINT PRIMARY KEY,
        full_name TEXT,
        xj_id TEXT,
        join_date_text TEXT,
        phone TEXT,
        level TEXT,
        stage TEXT
    );
    """)
    await pool.execute("""
    CREATE TABLE IF NOT EXISTS stage2_progress (
        tg_id BIGINT PRIMARY KEY REFERENCES users(tg_id) ON DELETE CASCADE,
        text_done BOOLEAN NOT NULL DEFAULT FALSE,
        audio_done BOOLEAN NOT NULL DEFAULT FALSE,
        video_done BOOLEAN NOT NULL DEFAULT FALSE,
        links_done BOOLEAN NOT NULL DEFAULT FALSE,
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)

async def get_user(tg_id: int):
    return await pool.fetchrow(
        "SELECT * FROM users WHERE tg_id=$1",
        tg_id
    )

async def upsert_user(tg_id: int, **fields):
    sets = ", ".join([f"{k}=${i+2}" for i, k in enumerate(fields)])
    values = list(fields.values())
    await pool.execute(
        f"""
        INSERT INTO users (tg_id, {', '.join(fields.keys())})
        VALUES ($1, {', '.join(f'${i+2}' for i in range(len(fields)))})
        ON CONFLICT (tg_id)
        DO UPDATE SET {sets}
        """,
        tg_id,
        *values
    )
