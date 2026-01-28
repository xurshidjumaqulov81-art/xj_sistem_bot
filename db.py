# db.py
import asyncpg
import secrets

_pool: asyncpg.Pool | None = None


async def init(dsn: str):
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)

    async with _pool.acquire() as conn:
        # 1) Asosiy jadvallarni yaratamiz (agar yo'q bo'lsa)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            inviter_id BIGINT NULL,
            ref_code TEXT UNIQUE,
            state TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            xj_id TEXT DEFAULT '',
            join_date_text TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            level TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS stage3_notes (
            user_id BIGINT NOT NULL,
            idx INT NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY(user_id, idx)
        );
        """)

        # 2) MIGRATION: eski bazada ustunlar yo'q bo'lsa, qo'shib chiqamiz
        await conn.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS stage2_text_done BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS stage2_audio_done BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS stage2_video_done BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS stage2_links_done BOOLEAN DEFAULT FALSE;

        ALTER TABLE users ADD COLUMN IF NOT EXISTS stage3_idx INT DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS stage3_waiting BOOLEAN DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS stage3_completed BOOLEAN DEFAULT FALSE;
        """)


async def close():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def _p() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB not initialized")
    return _pool


async def ensure_user(user_id: int, inviter_id: int | None = None):
    pool = _p()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM users WHERE user_id=$1", user_id)
        if row:
            if inviter_id is not None:
                await conn.execute(
                    "UPDATE users SET inviter_id=COALESCE(inviter_id,$2) WHERE user_id=$1",
                    user_id, inviter_id
                )
            return

        ref_code = secrets.token_hex(4)
        await conn.execute(
            "INSERT INTO users(user_id, inviter_id, ref_code) VALUES($1,$2,$3)",
            user_id, inviter_id, ref_code
        )


async def get_user_id_by_ref_code(ref_code: str) -> int | None:
    pool = _p()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM users WHERE ref_code=$1", ref_code)
        return int(row["user_id"]) if row else None


async def set_state(user_id: int, state: str):
    pool = _p()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET state=$2 WHERE user_id=$1", user_id, state)


async def get_state(user_id: int) -> str:
    pool = _p()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT state FROM users WHERE user_id=$1", user_id)
        return row["state"] if row else ""


async def set_user_field(user_id: int, field: str, value: str):
    if field not in {"full_name", "xj_id", "join_date_text", "phone", "level"}:
        raise ValueError("Invalid field")
    pool = _p()
    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE users SET {field}=$2 WHERE user_id=$1", user_id, value)


async def get_user_profile(user_id: int) -> dict:
    pool = _p()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return dict(row) if row else {}


async def get_stage2(user_id: int) -> dict:
    pool = _p()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT stage2_text_done, stage2_audio_done, stage2_video_done, stage2_links_done
            FROM users WHERE user_id=$1
        """, user_id)
        if not row:
            return {"text_done": False, "audio_done": False, "video_done": False, "links_done": False}
        return {
            "text_done": bool(row["stage2_text_done"]),
            "audio_done": bool(row["stage2_audio_done"]),
            "video_done": bool(row["stage2_video_done"]),
            "links_done": bool(row["stage2_links_done"]),
        }


async def mark_stage2(user_id: int, key: str):
    mapping = {
        "text_done": "stage2_text_done",
        "audio_done": "stage2_audio_done",
        "video_done": "stage2_video_done",
        "links_done": "stage2_links_done",
    }
    if key not in mapping:
        raise ValueError("Invalid stage2 key")
    col = mapping[key]
    pool = _p()
    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE users SET {col}=TRUE WHERE user_id=$1", user_id)


async def stage2_all_done(user_id: int) -> bool:
    p = await get_stage2(user_id)
    return p["text_done"] and p["audio_done"] and p["video_done"] and p["links_done"]


async def set_stage3_idx(user_id: int, idx: int):
    pool = _p()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET stage3_idx=$2 WHERE user_id=$1", user_id, idx)


async def get_stage3_idx(user_id: int) -> int:
    pool = _p()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT stage3_idx FROM users WHERE user_id=$1", user_id)
        return int(row["stage3_idx"]) if row else 0


async def set_stage3_waiting(user_id: int, waiting: bool):
    pool = _p()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET stage3_waiting=$2 WHERE user_id=$1", user_id, waiting)


async def set_stage3_completed(user_id: int, completed: bool):
    pool = _p()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET stage3_completed=$2 WHERE user_id=$1", user_id, completed)


async def save_stage3_note(user_id: int, idx: int, note: str):
    pool = _p()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO stage3_notes(user_id, idx, note)
            VALUES($1,$2,$3)
            ON CONFLICT(user_id, idx)
            DO UPDATE SET note=EXCLUDED.note, created_at=NOW()
        """, user_id, idx, note)


async def get_users_overview(limit: int = 50) -> list[dict]:
    pool = _p()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, full_name, xj_id, state,
                   stage2_text_done, stage2_audio_done, stage2_video_done, stage2_links_done,
                   stage3_idx, stage3_waiting, stage3_completed,
                   created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)
        return [dict(r) for r in rows]
