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

        # stage3 progress (old single confirm - qolsin, zarar qilmaydi)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage3_progress (
            user_id         BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            confirmed_text  TEXT,
            confirmed_at    TIMESTAMPTZ
        );
        """)

        # ✅ NEW: stage3 notes (11 ta audio izoh)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage3_notes (
            user_id     BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            lesson_no   INT NOT NULL,
            note_text   TEXT NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, lesson_no)
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
    async def ensure_user(self, user_id: int, inviter_id: Optional[int] = None):
        row = await self.fetchrow("SELECT user_id FROM users WHERE user_id=$1", user_id)
        if row is None:
            await self.execute(
                "INSERT INTO users(user_id, state, ref_code, inviter_id) VALUES($1, 'REG_NAME', md5(random()::text), $2)",
                user_id, inviter_id
            )
            await self.execute(
                "INSERT INTO stage2_progress(user_id) VALUES($1) ON CONFLICT DO NOTHING",
                user_id
            )
        else:
            # inviter_id bo‘sh bo‘lsa set qilmaymiz
            if inviter_id is not None:
                await self.execute(
                    "UPDATE users SET inviter_id=COALESCE(inviter_id, $2) WHERE user_id=$1",
                    user_id, inviter_id
                )

    async def get_user_id_by_ref_code(self, ref_code: str) -> Optional[int]:
        row = await self.fetchrow("SELECT user_id FROM users WHERE ref_code=$1", ref_code)
        return int(row["user_id"]) if row else None

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

    # ---------- stage3 (old) ----------
    async def set_stage3_confirm(self, user_id: int, text: str):
        await self.execute("""
            INSERT INTO stage3_progress(user_id, confirmed_text, confirmed_at)
            VALUES($1, $2, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET confirmed_text=EXCLUDED.confirmed_text, confirmed_at=EXCLUDED.confirmed_at
        """, user_id, text)

    # ✅ ---------- stage3 notes ----------
    async def save_stage3_note(self, user_id: int, lesson_no: int, note_text: str):
        note_text = (note_text or "").strip()
        if not note_text:
            raise ValueError("Empty note")
        await self.execute("""
            INSERT INTO stage3_notes(user_id, lesson_no, note_text, created_at, updated_at)
            VALUES($1, $2, $3, NOW(), NOW())
            ON CONFLICT (user_id, lesson_no)
            DO UPDATE SET note_text=EXCLUDED.note_text, updated_at=NOW()
        """, user_id, lesson_no, note_text)

    async def get_stage3_notes(self, user_id: int) -> List[Dict[str, Any]]:
        rows = await self.fetch("""
            SELECT lesson_no, note_text, updated_at
            FROM stage3_notes
            WHERE user_id=$1
            ORDER BY lesson_no
        """, user_id)
        return [dict(r) for r in rows]

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


# =========================
# module-level helpers
# =========================
_db: Optional[Database] = None


async def init(dsn: str):
    global _db
    _db = Database(dsn)
    await _db.connect()
    await _db.init_schema()


async def close():
    global _db
    if _db:
        await _db.close()
        _db = None


def _must_db() -> Database:
    assert _db is not None, "DB is not initialized"
    return _db


# proxy functions (main.py shu bilan ishlaydi)
async def ensure_user(user_id: int, inviter_id: Optional[int] = None):
    return await _must_db().ensure_user(user_id, inviter_id)

async def get_user_id_by_ref_code(ref_code: str) -> Optional[int]:
    return await _must_db().get_user_id_by_ref_code(ref_code)

async def get_state(user_id: int) -> str:
    return await _must_db().get_state(user_id)

async def set_state(user_id: int, state: str):
    return await _must_db().set_state(user_id, state)

async def set_user_field(user_id: int, field: str, value: Any):
    return await _must_db().set_user_field(user_id, field, value)

async def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    return await _must_db().get_user_profile(user_id)

async def mark_stage2(user_id: int, key: str):
    return await _must_db().mark_stage2(user_id, key)

async def get_stage2(user_id: int) -> Dict[str, bool]:
    return await _must_db().get_stage2(user_id)

async def set_stage3_confirm(user_id: int, text: str):
    return await _must_db().set_stage3_confirm(user_id, text)

# ✅ stage3 notes proxy
async def save_stage3_note(user_id: int, lesson_no: int, note_text: str):
    return await _must_db().save_stage3_note(user_id, lesson_no, note_text)

async def get_stage3_notes(user_id: int) -> List[Dict[str, Any]]:
    return await _must_db().get_stage3_notes(user_id)

# leads proxy
async def set_lead(user_id: int, idx: int, name_raw: str):
    return await _must_db().set_lead(user_id, idx, name_raw)

async def get_leads(user_id: int) -> List[Dict[str, Any]]:
    return await _must_db().get_leads(user_id)
