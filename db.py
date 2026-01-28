import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")
pool: asyncpg.Pool | None = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)

    async with pool.acquire() as conn:
        # USERS
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id BIGINT PRIMARY KEY,
            stage TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # STAGE 2
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS stage2_progress (
            tg_id BIGINT PRIMARY KEY REFERENCES users(tg_id) ON DELETE CASCADE,
            text_done BOOLEAN DEFAULT FALSE,
            audio_done BOOLEAN DEFAULT FALSE,
            video_done BOOLEAN DEFAULT FALSE,
            links_done BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """)


async def upsert_user(tg_id: int, stage: str | None = None):
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO users (tg_id, stage)
        VALUES ($1, $2)
        ON CONFLICT (tg_id)
        DO UPDATE SET stage = COALESCE($2, users.stage)
        """, tg_id, stage)


async def get_stage2(tg_id: int) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM stage2_progress WHERE tg_id=$1", tg_id
        )

        if not row:
            await conn.execute(
                "INSERT INTO stage2_progress (tg_id) VALUES ($1)", tg_id
            )
            row = await conn.fetchrow(
                "SELECT * FROM stage2_progress WHERE tg_id=$1", tg_id
            )

        return dict(row)


async def set_stage2_done(tg_id: int, field: str):
    async with pool.acquire() as conn:
        await conn.execute(f"""
        UPDATE stage2_progress
        SET {field}=TRUE, updated_at=NOW()
        WHERE tg_id=$1
        """, tg_id)
