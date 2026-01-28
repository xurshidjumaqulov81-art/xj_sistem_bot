import asyncpg
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def execute(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetchrow(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def init_schema(self):
        # users
        await self.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id         BIGINT PRIMARY KEY,
            state           TEXT DEFAULT 'REG_NAME',
            full_name       TEXT,
            xj_id           TEXT,
            join_date_text  TEXT,
            phone           TEXT,
            level           TEXT,
            inviter_id      BIGINT,
            ref_code        TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        # stage2 progress (4/4 gate)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage2_progress (
            user_id     BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            matn_done   BOOLEAN DEFAULT FALSE,
            audio_done  BOOLEAN DEFAULT FALSE,
            video_done  BOOLEAN DEFAULT FALSE,
            links_done  BOOLEAN DEFAULT FALSE,
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        # stage3 progress
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage3_progress (
            user_id         BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            confirmed_text  TEXT,
            confirmed_at    TIMESTAMPTZ
        );
        """)

        # leads (20)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            user_id     BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            lead_index  INT NOT NULL,
            name_raw    TEXT NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, lead_index)
        );
        """)

    # ---------- users ----------
    async def ensure_user(self, user_id: int):
        row = await self.fetchrow("SELECT user_id FROM users WHERE user_id=$1", user_id)
        if row is None:
            await self.execute(
                "INSERT INTO users(user_id, state, ref_code) VALUES($1, 'REG_NAME', md5(random()::text))",
                user_id
            )
            # create stage2 row too
            await self.execute(
                "INSERT INTO stage2_progress(user_id) VALUES($1) ON CONFLICT DO NOTHING",
                user_id
            )

    async def get_state(self, user_id: int) -> str:
        row = await self.fetchrow("SELECT state FROM users WHERE user_id=$1", user_id)
        return row["state"] if row else "REG_NAME"

    async def set_state(self, user_id: int, state: str):
        await self.execute("UPDATE users SET state=$2 WHERE user_id=$1", user_id, state)

    async def set_user_field(self, user_id: int, field: str, value: Any):
        if field not in {"full_name", "xj_id", "join_date_text", "phone", "level"}:
            raise ValueError("Invalid field")
        await self.execute(f"UPDATE users SET {field}=$2 WHERE user_id=$1", user_id, value)

    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        row = await self.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return dict(row) if row else None

    # ---------- stage2 ----------
    async def mark_stage2(self, user_id: int, key: str):
        if key not in {"matn_done", "audio_done", "video_done", "links_done"}:
            raise ValueError("Invalid stage2 key")
        await self.execute(
            f"UPDATE stage2_progress SET {key}=TRUE, updated_at=NOW() WHERE user_id=$1",
            user_id
        )

    async def get_stage2(self, user_id: int) -> Dict[str, bool]:
        row = await self.fetchrow("SELECT * FROM stage2_progress WHERE user_id=$1", user_id)
        if not row:
            return {"matn_done": False, "audio_done": False, "video_done": False, "links_done": False}
        return {
            "matn_done": row["matn_done"],
            "audio_done": row["audio_done"],
            "video_done": row["video_done"],
            "links_done": row["links_done"],
        }

    # ---------- stage3 ----------
    async def set_stage3_confirm(self, user_id: int, text: str):
        await self.execute("""
            INSERT INTO stage3_progress(user_id, confirmed_text, confirmed_at)
            VALUES($1, $2, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET confirmed_text=EXCLUDED.confirmed_text, confirmed_at=EXCLUDED.confirmed_at
        """, user_id, text)

    # ---------- leads ----------
    async def set_lead(self, user_id: int, idx: int, name_raw: str):
        await self.execute("""
            INSERT INTO leads(user_id, lead_index, name_raw)
            VALUES($1, $2, $3)
            ON CONFLICT (user_id, lead_index)
            DO UPDATE SET name_raw=EXCLUDED.name_raw
        """, user_id, idx, name_raw)

    async def get_leads(self, user_id: int) -> List[Dict[str, Any]]:
        rows = await self.fetch("SELECT lead_index, name_raw FROM leads WHERE user_id=$1 ORDER BY lead_index", user_id)
        return [dict(r) for r in rows]
