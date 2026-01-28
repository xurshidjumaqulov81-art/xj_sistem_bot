# db.py
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

        # stage3 flow: 11 audio + comments
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage3_flow (
            user_id             BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            current_idx         INT DEFAULT 0,
            waiting_comment     BOOLEAN DEFAULT FALSE,
            completed           BOOLEAN DEFAULT FALSE,
            updated_at          TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage3_comments (
            user_id     BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            idx         INT NOT NULL,
            comment     TEXT NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, idx)
        );
        """)

    # ---------- users ----------
    async def ensure_user(self, user_id: int, inviter_id: Optional[int] = None):
        row = await self.fetchrow("SELECT user_id FROM users WHERE user_id=$1", user_id)
        if row is None:
            await self.execute(
                "INSERT INTO users(user_id, state, inviter_id, ref_code) "
                "VALUES($1, 'REG_NAME', $2, md5(random()::text))",
                user_id, inviter_id
            )
            await self.execute(
                "INSERT INTO stage2_progress(user_id) VALUES($1) ON CONFLICT DO NOTHING",
                user_id
            )
            await self.execute(
                "INSERT INTO stage3_flow(user_id) VALUES($1) ON CONFLICT DO NOTHING",
                user_id
            )
        else:
            # make sure helper rows exist
            await self.execute("INSERT INTO stage2_progress(user_id) VALUES($1) ON CONFLICT DO NOTHING", user_id)
            await self.execute("INSERT INTO stage3_flow(user_id) VALUES($1) ON CONFLICT DO NOTHING", user_id)

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

    async def get_user_id_by_ref_code(self, ref_code: str) -> Optional[int]:
        row = await self.fetchrow("SELECT user_id FROM users WHERE ref_code=$1", ref_code)
        return int(row["user_id"]) if row else None

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
            "matn_done": bool(row["matn_done"]),
            "audio_done": bool(row["audio_done"]),
            "video_done": bool(row["video_done"]),
            "links_done": bool(row["links_done"]),
        }

    # ---------- stage3 ----------
    async def reset_stage3(self, user_id: int):
        await self.execute("""
            INSERT INTO stage3_flow(user_id, current_idx, waiting_comment, completed, updated_at)
            VALUES($1, 0, FALSE, FALSE, NOW())
            ON CONFLICT (user_id) DO UPDATE
            SET current_idx=0, waiting_comment=FALSE, completed=FALSE, updated_at=NOW()
        """, user_id)
        await self.execute("DELETE FROM stage3_comments WHERE user_id=$1", user_id)

    async def get_stage3_flow(self, user_id: int) -> Dict[str, Any]:
        row = await self.fetchrow("SELECT * FROM stage3_flow WHERE user_id=$1", user_id)
        if not row:
            return {"current_idx": 0, "waiting_comment": False, "completed": False}
        return {
            "current_idx": int(row["current_idx"]),
            "waiting_comment": bool(row["waiting_comment"]),
            "completed": bool(row["completed"]),
        }

    async def set_stage3_waiting(self, user_id: int, waiting: bool):
        await self.execute(
            "UPDATE stage3_flow SET waiting_comment=$2, updated_at=NOW() WHERE user_id=$1",
            user_id, waiting
        )

    async def set_stage3_idx(self, user_id: int, idx: int):
        await self.execute(
            "UPDATE stage3_flow SET current_idx=$2, updated_at=NOW() WHERE user_id=$1",
            user_id, idx
        )

    async def set_stage3_completed(self, user_id: int, completed: bool = True):
        await self.execute(
            "UPDATE stage3_flow SET completed=$2, updated_at=NOW() WHERE user_id=$1",
            user_id, completed
        )

    async def save_stage3_comment(self, user_id: int, idx: int, comment: str):
        await self.execute("""
            INSERT INTO stage3_comments(user_id, idx, comment)
            VALUES($1, $2, $3)
            ON CONFLICT (user_id, idx) DO UPDATE SET comment=EXCLUDED.comment
        """, user_id, idx, comment)


DB: Optional[Database] = None


async def init(dsn: str):
    global DB
    DB = Database(dsn)
    await DB.connect()
    await DB.init_schema()


async def close():
    global DB
    if DB:
        await DB.close()
        DB = None


# --- Proxy functions ---
async def ensure_user(user_id: int, inviter_id: Optional[int] = None):
    assert DB is not None
    return await DB.ensure_user(user_id, inviter_id)

async def get_user_id_by_ref_code(ref_code: str) -> Optional[int]:
    assert DB is not None
    return await DB.get_user_id_by_ref_code(ref_code)

async def get_state(user_id: int) -> str:
    assert DB is not None
    return await DB.get_state(user_id)

async def set_state(user_id: int, state: str):
    assert DB is not None
    return await DB.set_state(user_id, state)

async def set_user_field(user_id: int, field: str, value: Any):
    assert DB is not None
    return await DB.set_user_field(user_id, field, value)

async def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    assert DB is not None
    return await DB.get_user_profile(user_id)

async def mark_stage2(user_id: int, key: str):
    assert DB is not None
    return await DB.mark_stage2(user_id, key)

async def get_stage2(user_id: int) -> Dict[str, bool]:
    assert DB is not None
    return await DB.get_stage2(user_id)

async def reset_stage3(user_id: int):
    assert DB is not None
    return await DB.reset_stage3(user_id)

async def get_stage3_flow(user_id: int) -> Dict[str, Any]:
    assert DB is not None
    return await DB.get_stage3_flow(user_id)

async def set_stage3_waiting(user_id: int, waiting: bool):
    assert DB is not None
    return await DB.set_stage3_waiting(user_id, waiting)

async def set_stage3_idx(user_id: int, idx: int):
    assert DB is not None
    return await DB.set_stage3_idx(user_id, idx)

async def set_stage3_completed(user_id: int, completed: bool = True):
    assert DB is not None
    return await DB.set_stage3_completed(user_id, completed)

async def save_stage3_comment(user_id: int, idx: int, comment: str):
    assert DB is not None
    return await DB.save_stage3_comment(user_id, idx, comment)
